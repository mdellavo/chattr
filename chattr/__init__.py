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

log = logging.getLogger(__name__)

message = lambda type_, data=None: {'type': type_, 'data': data}
flatten_message = lambda msg: json.dumps(msg)
parse_message = lambda data: json.loads(data)

# FIXME add reader/writer greenlets incoming/outgoing queus
class Channel(object):
    def __init__(self, socket):
        self.socket = socket
        
        self.incoming = Queue(None)
        self.outgoing = Queue(None)

        self.reader = gevent.spawn(self.do_read)
        self.writer = gevent.spawn(self.do_write)

    def do_read(self):
        pass

    def do_write(self):
        pass

    def run(self):
        pass

    def receive(self):
        data = self.socket.receive()
        return parse_message(data) if data is not None else None

    def send(self, type_, data):
        return self.socket.send(flatten_message(message(type_, data)))

    def send_ping(self):
        return self.send('ping', time.time())

    def send_spawn(self, avatar):
        return self.send('spawn', avatar.stat())

    def send_die(self, avatar):
        return self.send('die', avatar.uid)

    def send_state(self, avatars):
        return self.send('state', [i.stat() for i in avatars])

    def send_update(self, avatar):
        return self.send('update', avatar.stat())


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

    def tick(self):
        for avatar in self.all():
            avatar.tick()

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

    def broadcast_spawn(self, avatar):
        self.broadcast(Channel.send_spawn, avatar)

    def broadcast_die(self, avatar):
        self.broadcast(Channel.send_die, avatar)

    def broadcast_update(self, avatar):
        self.broadcast(Channel.send_update, avatar)


# FIXME make a greenlet?
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
        self.world.channels.get(avatar).send_state(self.world.avatars.all())
        self.world.channels.broadcast_spawn(avatar)

    def on_die(self, avarar, data):
        self.world.channels.broadcast_die(avatar)

    def on_input(self, avatar, data):
        input_map = {
            'UP': (0, -1),
            'DOWN': (0, 1),
            'LEFT': (-1, 0),
            'RIGHT': (1, 0)
        }

        if data in input_map:
            dx, dy = input_map.get(data)
            avatar.move(dx, dy)
            self.world.channels.broadcast_update(avatar)


class WorldThread(Greenlet):

    TICKRATE = 10

    def __init__(self):
        super(WorldThread, self).__init__()
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

    def tick(self):
        for avatar, msg in self.incoming_messages():
            self.message_handler.dispatch(avatar, msg)
            
        self.avatars.tick()

    def _run(self):
        self.running = True

        while self.running:
            last = time.time()

            self.tick()
            self.ticks += 1

            now = time.time()
            delta = now - last            
            sleepy_time = (1.0 / self.TICKRATE)  - delta
            log.debug('sleeping world for %s', sleepy_time)

            gevent.sleep(sleepy_time)

    def spawn(self, channel):
        avatar = Avatar()
        self.avatars.add(avatar)
        self.channels.add(avatar, channel)
        self.enqueue(avatar, message('spawn'))
        return avatar
        
    def die(self, avatar):
        self.channels.remove(avatar)
        self.avatars.remove(avatar)
        self.enqueue(avatar, message('die'))
    

World = WorldThread()
World.start()

class Avatar(object):
    def __init__(self):
        self.uid = uuid.uuid4().hex
        self.size = random.randint(5, 20)
        self.position(random.randint(0, 100),
                      random.randint(0, 100))
        self.velocity(0, 0)
        self.rotation = 0

    def stat(self):
        return vars(self)

    def position(self, x, y):
        self.x = x
        self.y = y

    def velocity(self, dx, dy):
        self.dx = dx
        self.dy = dy

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def tick(self):
        pass

@view_config(route_name='endpoint', renderer='string')
def endpoint(request):

    channel = Channel(request.environ['wsgi.websocket'])
    avatar = World.spawn(channel)

    log.debug('spawned avatar %s', avatar.uid)

    while True:
        msg = channel.receive()

        if msg is None:
            break

        World.enqueue(avatar, msg)

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

    return config.make_wsgi_app()
