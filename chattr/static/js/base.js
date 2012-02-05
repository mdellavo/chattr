$(document).ready(function() {

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

    var tile_size = 32;
    var tiles = {
        terrain: '/static/img/terrain-tiles.gif',
        character: '/static/img/character-tiles.gif'
    };

    function draw_tile(image, tile_size, x, y, dx, dy, dw, dh) {
        var sx = tile_size * x;
        var sy = tile_size * y;
        var sw = tile_size;
        var sh = tile_size;
        context.drawImage(image, sx, sy, sw, sh, dx, dy, dw, dh);
    }

    var attrs = {
        'width': $(document).innerWidth(),
        'height': $(document).innerHeight()
    };

    var canvas = $('#canvas').get(0);
    var context = canvas.getContext('2d');

    var width = $(canvas).innerWidth();    
    var height = $(canvas).innerHeight();    

    console.log(width, height);
    
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
        draw_tile(images.character, tile_size, 0, 0, this.x, this.y, tile_size, tile_size)
    } 
 
    Avatar.prototype.clear = function() {
        context.clearRect(this.x - this.size,
                          this.y - this.size,
                          this.size * 2, 
                          this.size * 2);
    }

    var host = 'ws://' + window.location.host + '/end-point'

    console.log('connecting to', host);
    var socket = new WebSocket(host);
    var avatar = new Avatar();

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
            console.log('update');
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

    function progress(loaded_images, num_images) {
        console.log('loaded', loaded_images, 'of', num_images);
    }
    
    function main(images) {

        function renderer() {
            context.clearRect(0,0,context.canvas.width,context.canvas.height)

            for(var i=0; i<20; i++)
                for(var j=0; j<20; j++)
                    draw_tile(images.terrain,
                              tile_size,
                              0,
                              1,
                              j * tile_size,
                              i * tile_size, 
                              tile_size, 
                              tile_size);

            Avatars.draw(images);
        }

        window.setInterval(renderer, 50);
    }
    
    load_images(tiles, progress, main);
    
});
