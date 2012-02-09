# -----------------------------------------------------------------------------
#
# Websocket Server
#
# Notes
#
# https://developer.valvesoftware.com/wiki/Source_Multiplayer_Networking
# http://pousse.rapiere.free.fr/tome/tiles/AngbandTk/tome-angbandtktiles.htm
# -----------------------------------------------------------------------------

from gevent import monkey, Greenlet
from gevent.queue import Queue, Empty
from gevent.pywsgi import WSGIServer
import gevent
monkey.patch_all()

from geventwebsocket.handler import WebSocketHandler

from pyramid.config import Configurator
from pyramid.view import view_config

import json
import logging
import random
import time
import uuid

from chattr.vector import Vector

log = logging.getLogger(__name__)


def json_encoder(obj):
    if hasattr(obj, '__json__'):
        return obj.__json__()

    raise TypeError('%s is not JSON serializable' % obj)

message = lambda type_, data=None: {'type': type_, 'data': data}
flatten_message = lambda msg: json.dumps(msg, default=json_encoder)
parse_message = lambda data: json.loads(data)


# FIXME throttle incoming/outgoing
class Channel(object):
    def __init__(self, socket):
        self.socket = socket

        self.running = False

        self.incoming = Queue(None)
        self.outgoing = Queue(None)

        self.reader = Greenlet(self.do_read)
        self.writer = Greenlet(self.do_write)

    def do_read(self):
        while self.running:
            data = self.socket.receive()

            if not data:
                break

            if data:
                self.incoming.put(parse_message(data))

    def do_write(self):
        while self.running:
            msg = self.outgoing.get()
            self.socket.send(flatten_message(msg))

    def is_running(self):
        return self.running and not any([self.reader.ready(),
                                         self.writer.ready()])

    def run(self):
        self.running = True
        self.reader.start()
        self.writer.start()

    def wait(self):
        self.running = False
        gevent.killall([self.reader, self.writer])

    def receive(self):
        return self.incoming.get()

    def send(self, type_, data):
        return self.outgoing.put(message(type_, data))

    def send_ping(self):
        return self.send('ping', time.time())

    def send_notice(self, msg):
        return self.send('notice', msg)

    def send_spawn(self, avatar):
        return self.send('spawn', avatar)

    def send_die(self, avatar):
        return self.send('die', avatar.uid)

    def send_tiles(self, tiles):
        return self.send('tiles', tiles)

    def send_chunk(self, chunk):
        return self.send('chunk', list(chunk))

    def send_state(self, avatars):
        return self.send('state', avatars)

    def send_update(self, avatar):
        return self.send('update', avatar)


class AvatarCollection(object):
    def __init__(self):
        self.avatars = dict()

    def add(self, avatar):
        self.avatars[avatar.uid] = avatar

    def remove(self, avatar):
        del self.avatars[avatar.uid]

    def get(self, uid):
        return self.avatars.get(uid)

    def all(self):
        return self.avatars.values()

    def tick(self, delta):
        for avatar in self.all():
            avatar.tick(delta)

    def dirty(self):
        return [a for a in self.all() if a.dirty]

    def clean(self):
        for avatar in self.all():
            avatar.mark_clean()


class ChannelCollection(object):
    def __init__(self):
        self.channels = dict()

    def add(self, avatar, channel):
        self.channels[avatar.uid] = channel

    def remove(self, avatar):
        del self.channels[avatar.uid]

    def get(self, o):
        if isinstance(o, Avatar):
            uid = o.uid
        else:
            uid = o

        return self.channels.get(uid)

    def broadcast(self, method, *args, **kwargs):
        for uid in self.channels:
            method(self.channels[uid], *args, **kwargs)

    def broadcast_notice(self, msg):
        self.broadcast(Channel.send_notice, msg)

    def broadcast_spawn(self, avatar):
        self.broadcast(Channel.send_spawn, avatar)

    def broadcast_die(self, avatar):
        self.broadcast(Channel.send_die, avatar)

    def broadcast_update(self, avatar):
        self.broadcast(Channel.send_update, avatar)


class Tile(object):
    def __init__(self, name, x, y, w, h, flags=None):
        self.name = name
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.flags = set(flags or '')

    def __json__(self):
        return self.to_dict()

    def to_dict(self):
        return dict((k, v) for k, v in vars(self).items() if k != 'flags')


class Map(object):
    def __init__(self, tiles, data, tile_map):
        self.tiles = tiles
        self.data = data
        self.tile_map = tile_map

    @classmethod
    def load(cls, path):
        rv = None

        with open(path) as f:
            obj = json.load(f)

            tiles = [Tile(**i) for i in obj['tiles']]
            data = obj['data']
            tile_map = obj['tile_map']

            rv = cls(tiles, data, tile_map)

        return rv

    def get(self, x, y):
        return self.tiles[self.data[y][x]]

    def chunk(self, x, y, s):
        px = max(x - s / 2, 0)
        py = max(y - s / 2, 0)

        for i in range(py, py + s):
            yield self.data[i][px:px + s]


# FIXME make a greenlet?
# FIXME map chunk size
class MessageHandler(object):

    def __init__(self, world):
        self.world = world

    def dispatch(self, avatar, msg):
        handler_name = 'on_' + msg['type']
        handler = getattr(self, handler_name, None)

        if handler:
            log.debug('dispatching message %s', msg['type'])

            handler(avatar, msg['data'])

        return handler is not None

    def on_spawn(self, avatar, data):
        channel = self.world.channels.get(avatar)

        if channel:
            channel.send_tiles(self.world.map.tiles)
            channel.send_chunk(self.world.map.chunk(avatar.position.x / 32,
                                                    avatar.position.y / 32, 50))
            channel.send_state(self.world.avatars.all())

        msg = 'The server welcomes avatar %s to the world!' % avatar.uid
        self.world.channels.broadcast_notice(msg)
        self.world.channels.broadcast_spawn(avatar)

    def on_die(self, avatar, data):
        self.world.channels.broadcast_die(avatar)

    def on_input(self, avatar, data):
        input_map = {
            'UP': Vector(0, -1),
            'DOWN': Vector(0, 1),
            'LEFT': Vector(-1, 0),
            'RIGHT': Vector(1, 0)
        }

        if data in input_map:
            avatar.move(input_map.get(data))
            avatar.mark_dirty()

    # FIXME select
    def on_click(self, avatar, data):
        pass

    def on_dblclick(self, avatar, data):
        x, y = data
        avatar.set_waypoint(Vector(x, y))


class WorldThread(Greenlet):

    TICKRATE = 10

    def __init__(self, map):
        super(WorldThread, self).__init__()
        self.map = map
        self.running = False
        self.ticks = 0
        self.input = Queue(None)

        self.avatars = AvatarCollection()
        self.channels = ChannelCollection()
        self.message_handler = MessageHandler(self)

    def enqueue(self, avatar, msg):
        self.input.put((avatar, msg))

    def incoming_messages(self):
        try:
            while True:
                yield self.input.get(False)
        except Empty:
            pass

    def tick(self, delta):
        for avatar, msg in self.incoming_messages():
            self.message_handler.dispatch(avatar, msg)

        self.avatars.tick(delta)

        dirty_avatars = self.avatars.dirty()
        for avatar in dirty_avatars:
            self.channels.broadcast_update(avatar)

        self.avatars.clean()

    def _run(self):
        self.running = True

        while self.running:
            last = time.time()

            # FIXME track delta

            self.tick(0)
            self.ticks += 1

            now = time.time()
            delta = now - last
            sleepy_time = max((1.0 / self.TICKRATE) - delta, 0)

            #log.debug('tick took %s, sleeping for %s', delta, sleepy_time)

            gevent.sleep(sleepy_time)

    def spawn(self, cls=None, args=None, kwargs=None):
        cls = cls or Avatar
        args = args or ()
        kwargs = kwargs or {}

        avatar = cls(*args, **kwargs)
        self.avatars.add(avatar)
        self.enqueue(avatar, message('spawn'))
        return avatar

    def attach(self, avatar, channel):
        self.channels.add(avatar, channel)

    def detach(self, avatar):
        self.channels.remove(avatar)

    def kill(self, avatar):
        self.channels.remove(avatar)
        self.avatars.remove(avatar)
        self.enqueue(avatar, message('die'))

# FIXME limit map chunk by vision
class Avatar(object):
    def __init__(self):
        self.uid = uuid.uuid4().hex
        self.size = random.randint(5, 20)
        self.position = Vector(random.randint(0, 640), random.randint(0, 640))
        self.velocity = Vector()
        self.rotation = 0
        self.dirty = True
        self.ticks = 0
        self.waypoint = None

    def __json__(self):
        return self.stat()

    def mark_dirty(self):
        self.dirty = True

    def mark_clean(self):
        self.dirty = False

    def set_waypoint(self, vec):
        self.waypoint = vec

    def stat(self):
        exclude = ('ticks', 'dirty')
        return dict((k, v) for k, v in vars(self).items() if k not in exclude)

    def move(self, vec):
        self.position += vec

    def tick(self, delta):
        self.ticks += 1

        if self.waypoint:
            dist_to_waypoint = self.position.distance(self.waypoint)

            if dist_to_waypoint <= 1:
                self.position = self.waypoint
                self.velocity.zero()
                self.waypoint = None
            elif dist_to_waypoint > 1:
                self.velocity = (self.waypoint - self.position).normalize()

            self.position += self.velocity

            self.mark_dirty()


class NPCAvatar(Avatar):
    pass


class Wanderer(NPCAvatar):
    def __init__(self, range):
        super(Wanderer, self).__init__()
        self.range = range

    def tick(self, delta):
        if not self.waypoint:
            tmp = Vector(random.randint(-self.range, self.range),
                         random.randint(-self.range, self.range))
            self.waypoint = self.position + tmp

        super(Wanderer, self).tick(delta)


World = WorldThread(Map.load('map.json'))


@view_config(route_name='endpoint', renderer='string')
def endpoint(request):
    avatar = World.spawn()
    channel = Channel(request.environ['wsgi.websocket'])

    World.attach(avatar, channel)

    log.debug('spawned avatar %s', avatar.uid)

    channel.run()

    while channel.is_running:
        msg = channel.receive()
        World.enqueue(avatar, msg)

    channel.wait()

    World.detach(avatar)
    World.kill(avatar)

    log.debug('killed avatar %s', avatar.uid)

    return ''


@view_config(route_name='root', renderer='/base.mako')
def root(request):
    return {}


def server_factory(global_conf, host, port):
    port = int(port)

    def serve(app):
        server = WSGIServer(('', port), app, handler_class=WebSocketHandler)
        log.info('serving on port %s...', port)
        server.serve_forever()

    return serve


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.add_static_view('static', 'chattr:static')

    config.add_route('root', '/')
    config.add_route('endpoint', '/end-point')

    config.scan()

    log.info('Starting the world')
    World.start()

    for i in range(20):
        World.spawn(Wanderer, args=(100,))

    return config.make_wsgi_app()
