var BunnyStreamSessionTracker = /** @class */ (function () {
    /*
     *
     **/
    function BunnyStreamSessionTracker(iframeDomain, videoApiHostname, videoLibraryId, videoId, serverId) {
        if (serverId === void 0) { serverId = ""; }
        this.untrackedTime = 0;
        this.timeToFirstFrameTracked = false;
        this.timeToFirstFrameCollected = false;
        this.timeToFirstFrameMs = 0;
        this.playEventTimeMs = 0;
        this.VideoId = videoId;
        this.ServerId = serverId;
        this.currentVideoProgress = 0;
        this.videoLibraryId = videoLibraryId;
        this.IframeDomain = iframeDomain;
        this.VideoApiHostname = videoApiHostname;
    }
    BunnyStreamSessionTracker.prototype.OnPlay = function () {
        this.startTime = this.GetUnix();
        this.playing = true;
        this.playEventTimeMs = new Date().getTime();
        // Fire the collection handler if the video was just played for the first time
        if (!this.firstPlayTracked) {
            this.firstPlayTracked = true;
            var self = this;
            setInterval(function () {
                self.CollectionIntervalHandler();
            }, 5000);
        }
    };
    BunnyStreamSessionTracker.prototype.OnPlaying = function () {
        if (!this.timeToFirstFrameTracked && this.playEventTimeMs > 0) {
            this.timeToFirstFrameTracked = true;
            var currentTime = new Date().getTime();
            this.timeToFirstFrameMs = currentTime - this.playEventTimeMs;
        }
    };
    BunnyStreamSessionTracker.prototype.OnPause = function () {
        this.playing = false;
        this.IncreaseUntrackedTime();
    };
    BunnyStreamSessionTracker.prototype.OnProgress = function (videoProgress) {
        this.currentVideoProgress = videoProgress;
        if (this.playing) {
            this.IncreaseUntrackedTime();
        }
    };
    BunnyStreamSessionTracker.prototype.IncreaseUntrackedTime = function () {
        var currentTime = this.GetUnix();
        if (currentTime > this.startTime) {
            this.untrackedTime += (currentTime - this.startTime);
            this.startTime = currentTime;
        }
    };
    BunnyStreamSessionTracker.prototype.CollectionIntervalHandler = function () {
        var postObject = {
            VideoId: this.VideoId,
            TimeWatched: this.untrackedTime,
            IsPlaying: this.playing,
            CurrentTime: Math.floor(this.currentVideoProgress),
            VideoLibraryId: this.videoLibraryId,
            TimeToFirstFrame: null
        };
        if (this.timeToFirstFrameTracked && !this.timeToFirstFrameCollected) {
            postObject.TimeToFirstFrame = this.timeToFirstFrameMs;
            this.timeToFirstFrameCollected = true;
        }
        this.untrackedTime = 0;
        var hostname = "video-" + this.ServerId + "." + this.IframeDomain;
        if (this.ServerId == "" || this.ServerId == undefined)
            hostname = this.VideoApiHostname;
        this.postUrl("https://" + hostname + "/.metrics/track-session", postObject, function (data) {
        });
        return 0;
    };
    BunnyStreamSessionTracker.prototype.GetUnix = function () {
        var unix = Math.round(+new Date() / 1000);
        return unix;
    };
    BunnyStreamSessionTracker.prototype.postUrl = function (url, data, onFinished) {
        var xmlhttp = new XMLHttpRequest();
        xmlhttp.onreadystatechange = function () {
            if (xmlhttp.readyState == XMLHttpRequest.DONE) { // XMLHttpRequest.DONE == 4
                if (xmlhttp.status == 200) {
                    onFinished(xmlhttp.responseText);
                }
            }
        };
        xmlhttp.open("POST", url);
        xmlhttp.setRequestHeader("Content-Type", "application/json");
        xmlhttp.send(JSON.stringify(data));
    };
    return BunnyStreamSessionTracker;
}());
