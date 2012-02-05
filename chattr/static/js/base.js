$(document).ready(function() {

    var canvas = $('#canvas').get(0);
    var context = canvas.getContext('2d');

    var width;    
    var height;

    var tile_size = 32;

    var tiles_wide;
    var tiles_tall;

    var tiles = {
        terrain: '/static/img/terrain-tiles.gif',
        character: '/static/img/character-tiles.gif'
    };

    function to_tile_pos(i) { return Math.floor(i/tile_size) }
    function from_tile_pos(i) { return i * tile_size }

    function size() {
        width = window.innerWidth - 5;
        height = window.innerHeight - 5;

        tiles_wide = width / tile_size;
        tiles_tall = height / tile_size;

        console.log('resized: ', width, height);
        console.log('tiles: ', tiles_wide, tiles_tall);

        context.canvas.width = width;
        context.canvas.height = height;       
    }

    $(window).resize(size).resize();

    function load_images(sources, progress, complete) {
        var images = {};
        var loaded_images = 0;
        var num_images = 0;

        for(var src in sources)
            num_images++;

        for(var src in sources) {
            images[src] = new Image();

            images[src].onload = function() {
                loaded_images++;

                progress(loaded_images, num_images);
                
                if (loaded_images >= num_images)
                    complete(images);
            };

            images[src].src = sources[src];
        }
    }

    function draw_tile(image, tile_size, x, y, dx, dy) {
        var sx = from_tile_pos(x);
        var sy = from_tile_pos(y);
        var sw = tile_size;
        var sh = tile_size;
        var dw = tile_size;
        var dh = tile_size;
        context.drawImage(image, sx, sy, sw, sh, dx, dy, dw, dh);
    }

    // FIXME monitor resize

    window.Avatars = {
        avatars: {},
        add: function(avatar) {
            this.avatars[avatar.uid] = avatar;
        },
        remove: function(uid) {
            if(uid)
                delete this.avatars[uid];
        },
        get: function(uid) {
            return this.avatars[uid] || null;
        }, 
        clear: function() {
            for(var uid in this.avatars)
                this.avatars[uid].clear();
        },
        draw: function(images) {
            for(var uid in this.avatars)
                this.avatars[uid].draw(images);
        }
    };

    function Avatar(data) {
        this.update(data)
    }

    Avatar.prototype.update = function(data) {
        for(var i in data)
            this[i] = data[i];
    }

    Avatar.prototype.draw = function(images) {
        draw_tile(images.character, tile_size, 0, 0,
                  this.position[0], this.position[1])

        if(this.waypoint) {
            context.beginPath();
            context.rect(this.waypoint[0] - tile_size/2,
                         this.waypoint[1] - tile_size/2,
                         tile_size,
                         tile_size);
            context.stroke();
        }
            

    } 
 
    Avatar.prototype.clear = function() {
        context.clearRect(this.position[0] - this.size,
                          this.position[1] - this.size,
                          this.size * 2, 
                          this.size * 2);
    }

    var host = 'ws://' + window.location.host + '/end-point'

    console.log('connecting to', host);
    var socket = new WebSocket(host);

    function message(type, data) {
        return JSON.stringify({'type': type, 'data': data})
    }

    function send(type, data) {
        return socket.send(message(type, data));
    }
 
    var MessageHandlers = {
        ping: function(data) {
            console.log('pong');
            send('pong', data);
        },
        spawn: function(data) {
            console.log('spawn');
            Avatars.add(new Avatar(data));
        },        
        die: function(data) {
            console.log('die');
            Avatars.die(data);
        },        
        state: function(data) {
            console.log('state');

            for(var i=0; i<data.length; i++)
                Avatars.add(new Avatar(data[i]));
        }, 
        update: function(data) {
            Avatars.get(data.uid).update(data);
        }
    };
   
    socket.onopen = function(msg) {
        console.log('open');
    };
    
    socket.onmessage = function(msg) {
        obj = JSON.parse(msg.data);

        if(obj.type in MessageHandlers)
            MessageHandlers[obj.type](obj.data);
        else 
            console.log('Unknown Message:', obj.type);
    };

    socket.onclose = function() {
        console.log('close');
    };

    socket.onerror = function() {
        console.log('error');
    };

    var Keys = {
        32: 'SPACE',
        13: 'ENTER',
        27: 'ESC',
        37: 'LEFT',
        38: 'UP',
        39: 'RIGHT',
        40: 'DOWN'
    };

    $(document).keydown(function(evt) {
        if(evt.keyCode in Keys)
            send('input', Keys[evt.keyCode]);
    });

    $(document).mousemove(function(evt) {
        var tile_x = to_tile_pos(evt.pageX);
        var tile_y = to_tile_pos(evt.pageY);
    });

    $(document).click(function(evt) {
        var tile_x = to_tile_pos(evt.pageX);
        var tile_y = to_tile_pos(evt.pageY);
        send('click', [tile_x, tile_y]);
    });

    $(document).dblclick(function(evt) {
        send('dblclick', [evt.pageX, evt.pageY]);
    });

    function progress(loaded_images, num_images) {
        console.log('loaded', loaded_images, 'of', num_images);
    }
    
    function main(images) {

        function renderer() {
            context.clearRect(0,0,context.canvas.width,context.canvas.height)

            for(var i=0; i<tiles_tall; i++)
                for(var j=0; j<tiles_wide; j++)
                    draw_tile(images.terrain,
                              tile_size,
                              0,
                              1,
                              from_tile_pos(j),
                              from_tile_pos(i));

            Avatars.draw(images);
        }

        window.setInterval(renderer, 50);
    }
    
    load_images(tiles, progress, main);
    
});
