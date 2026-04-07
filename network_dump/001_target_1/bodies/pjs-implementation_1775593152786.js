var BunnyPlayerJs = /** @class */ (function () {
    function BunnyPlayerJs(player) {
        var _this = this;
        this.init = function () {
            // @ts-ignore
            // this is due to TS not recognizing external types
            _this.receiver = new playerjs.Receiver();
            _this.receiver.on("play", function () {
                _this.playerInstance.play();
                _this.receiver.emit("play");
            });
            _this.receiver.on("pause", function () {
                _this.playerInstance.pause();
                _this.receiver.emit("pause");
            });
            _this.receiver.on("getDuration", function (callback) {
                return callback(_this.playerInstance.duration);
            });
            _this.receiver.on("getCurrentTime", function (callback) {
                return callback(_this.playerInstance.currentTime);
            });
            _this.receiver.on("setCurrentTime", function (value) { return (_this.playerInstance.currentTime = value); });
            _this.receiver.on("getVolume", function (callback) {
                return callback(_this.playerInstance.volume * 100);
            });
            _this.receiver.on("setVolume", function (value) { return (_this.playerInstance.volume = value / 100); });
            _this.receiver.on("mute", function () { return (_this.playerInstance.muted = true); });
            _this.receiver.on("unmute", function () { return (_this.playerInstance.muted = false); });
            _this.receiver.on("getMuted", function (callback) {
                return callback(_this.playerInstance.muted);
            });
            _this.receiver.on("getLoop", function (callback) {
                return callback(_this.playerInstance.loop);
            });
            _this.receiver.on("setLoop", function (value) { return (_this.playerInstance.loop = value); });
            _this.playerInstance.on("playing", function () { return _this.receiver.emit("play"); });
            _this.playerInstance.on("play", function () { return _this.receiver.emit("play"); });
            _this.playerInstance.on("pause", function () { return _this.receiver.emit("pause"); });
            _this.playerInstance.on("timeupdate", function () {
                return _this.receiver.emit("timeupdate", {
                    seconds: _this.playerInstance.currentTime,
                    duration: _this.playerInstance.duration,
                });
            });
            _this.playerInstance.on("ended", function () { return _this.receiver.emit("ended"); });
            _this.playerInstance.on("seeking", function () { return _this.receiver.emit("seeking"); });
            _this.playerInstance.on("seeked", function () {
                return _this.receiver.emit("seeked", {
                    seconds: _this.playerInstance.currentTime
                });
            });
            _this.playerInstance.on("error", function () { return _this.receiver.emit("error", _this.playerInstance.error); });
            _this.playerInstance.on("progress", function () {
                return _this.receiver.emit("progress", {
                    duration: _this.playerInstance.duration,
                    percent: _this.playerInstance.buffered
                });
            });
            _this.receiver.on("getPaused", function (callback) {
                return callback(_this.playerInstance.paused);
            });
            _this.receiver.ready();
        };
        this.playerInstance = player;
    }
    return BunnyPlayerJs;
}());
