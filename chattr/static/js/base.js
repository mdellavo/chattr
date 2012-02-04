$(document).ready(function() {

    var attrs = {
        'width': $(document).innerWidth(),
        'height': $(document).innerHeight()
    };

    var canvas = $('#canvas').get(0);
    var context = canvas.getContext('2d');

    var width = $(canvas).innerWidth();    
    var height = $(canvas).innerHeight();    
    context.setTransform(1, 0, 0, 1, 0, 0);
    context.clearRect(0, 0, width, height);
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
        draw: function() {
            for(var uid in this.avatars)
                this.avatars[uid].draw();
        }
    };

    function Avatar(data) {
        this.update(data)
    }

    Avatar.prototype.update = function(data) {
        for(var i in data)
            this[i] = data[i];
    }

    Avatar.prototype.draw = function() {
        context.beginPath()
        context.arc(this.x, this.y, this.size, 0, Math.PI * 2, true);
        context.stroke();
    } 
 
    Avatar.prototype.clear = function() {
        context.clearRect(this.x - this.size,
                          this.y - this.size,
                          this.size * 2, 
                          this.size * 2);
    }


    var Keys = {
        32: 'SPACE',
        13: 'ENTER',
        27: 'ESC',
        37: 'LEFT',
        38: 'UP',
        39: 'RIGHT',
        40: 'DOWN'
    };

    var host = 'ws://localhost:6543/end-point'
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
            var avatar = new Avatar(data);
            Avatars.add(avatar);
        },        
        die: function(data) {
            console.log('die');
            Avatars.die(data);
        },        
        state: function(data) {
            console.log('state');

            for(var i=0; i<data.length; i++)
                Avatars.add(data[i]);
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
    
    function renderer() {
        //Avatars.clear();
        context.clearRect(0,0,context.canvas.width,context.canvas.height)
        Avatars.draw();
    }
    window.setInterval(renderer, 50);

    $(document).keydown(function(evt) {
        if(evt.keyCode in Keys)
            send('input', Keys[evt.keyCode]);
    });

});
