var PB = /** @class */ (function () {
    /**
     * Create a new progress bar object
     * @param element
     */
    function PB(element, progressBarElement, config) {
        this.mouse_over_progressbar = false;
        this.title_jumped = false;
        this.sections = new Array();
        this.moments = new Array();
        this.el_pbar = $(progressBarElement);
        this.el_body = $(element);
        this.el_body.css("pointer-events", "none");
        this.video_length = config.videoLength;
        this.ev_config = config;
        this.c_width = this.el_body.width() - 1;
        this.createElements();
        this.startResizeMonitoring();
    }
    PB.prototype.createElements = function () {
        this.el_base = $('<div class="sp__base"></div>');
        this.el_root = $('<ul class="sp__progressbar"></div>');
        this.el_title = $('<div class="sp__title">test</div>');
        this.el_base.append(this.el_root);
        this.el_base.append(this.el_title);
        this.el_body.append(this.el_base);
        // If no chapters are set, create only a default section
        if (this.ev_config.chapters == undefined || this.ev_config.chapters.length == 0) {
            var section = new PBSection(this, 0, PB.CONST_END, "", false);
            this.sections.push(section);
            this.el_root.append(section.GetElement());
        }
        else {
            var lastSectionEnd = 0;
            // Chapters should be ordered by time
            this.ev_config.chapters.sort(PBChapter.compare);
            for (var i = 0; i < this.ev_config.chapters.length; i++) {
                var chapter = this.ev_config.chapters[i];
                console.log("Found section at start " + chapter.start);
                // Align chapters and insert missing pieces if neccessary
                if (chapter.start > lastSectionEnd) {
                    var section = new PBSection(this, lastSectionEnd, chapter.start, "", false);
                    this.sections.push(section);
                    this.el_root.append(section.GetElement());
                }
                if (chapter.start < lastSectionEnd) {
                    chapter.start = lastSectionEnd;
                }
                var section = new PBSection(this, chapter.start, chapter.end, chapter.title, true);
                this.sections.push(section);
                this.el_root.append(section.GetElement());
                lastSectionEnd = chapter.end;
            }
            // Fill the last chunk if needed
            if (lastSectionEnd < this.video_length) {
                var section = new PBSection(this, lastSectionEnd, PB.CONST_END, "", false);
                this.sections.push(section);
                this.el_root.append(section.GetElement());
            }
        }
        // Add moments
        for (var i = 0; i < this.ev_config.moments.length; i++) {
            var moment = this.ev_config.moments[i];
            var momentCircle = new PBMomentCircle(this, moment.timestamp, moment.title);
            this.el_base.append(momentCircle.GetElement());
            this.moments.push(momentCircle);
            momentCircle.Reposition();
        }
        // Register the mouse position
        var self = this;
        if (!this.IsMobile()) {
            this.el_pbar.mousemove(function (e) {
                var parentOffset = self.el_pbar.parent().offset();
                self.mouse_x = (e.pageX - parentOffset.left) + 6;
                self.mouse_y = (e.pageY - parentOffset.top);
                self.mouse_over_progressbar = true;
                if (!self.el_root.hasClass("hover")) {
                    self.el_root.addClass("hover");
                }
                self.el_title.removeClass("animated");
                var seconds = self.getCurrentMouseSecnds();
                // Detect if we're hovering over a section
                self.DetectHoverMoments(seconds);
                if (!self.moment_active) {
                    self.DetectHoverSection(seconds);
                }
                self.updateSections("mark", seconds);
                self.CallThumbnailJumpDownEvent();
                self.CallThumbnailJumpUpEvent();
                if (self.c_highlightedSection != undefined && !self.moment_active) {
                    self.PositionTitleAndIndicator(seconds);
                }
            });
            this.el_pbar.mouseleave(function (e) {
                if (!self.el_title.hasClass("animated")) {
                    self.el_title.addClass("animated");
                }
                self.mouse_over_progressbar = false;
                self.DetectHoverMoments(-10000);
                self.el_root.removeClass("hover");
                self.updateSections("mark", 0);
                self.c_timeoutEvent = undefined;
                clearInterval(self.c_timeout);
            });
        }
        else {
            this.el_pbar.on("touchmove", function (e) {
                var touch = e.originalEvent.touches[0] || e.originalEvent.changedTouches[0] || e.touches[0] || e.changedTouches[0];
                var parentOffset = $(this).parent().offset();
                self.mouse_x = (touch.pageX - parentOffset.left) + 6;
                self.mouse_y = (touch.pageY - parentOffset.top);
                self.mouse_over_progressbar = true;
                if (!self.el_root.hasClass("hover")) {
                    self.el_root.addClass("hover");
                }
                var seconds = self.getCurrentMouseSecnds();
                // Detect if we're hovering over a section
                self.DetectHoverMoments(seconds);
                if (!self.moment_active) {
                    self.DetectHoverSection(seconds);
                }
                self.updateSections("mark", seconds);
                self.CallThumbnailJumpDownEvent();
                self.CallThumbnailJumpUpEvent();
                if (self.c_highlightedSection != undefined && !self.moment_active) {
                    self.PositionTitleAndIndicator(seconds);
                }
                // Set the thumbnail
                if (!$(".plyr__preview-thumb").hasClass("plyr__tooltip--drag")) {
                    $(".plyr__preview-thumb").addClass("plyr__tooltip--drag");
                }
                $(".plyr__preview-thumb__time-container span").text(self.secondsToTimeString(seconds));
                if (self.ev_config.onScrubbingChange != undefined)
                    self.ev_config.onScrubbingChange(self.getCurrentMouseSecnds(), self.SecondsToPixels(self.getCurrentMouseSecnds()));
            });
            this.el_pbar.on("touchstart", function (e) {
                self.mouse_over_progressbar = true;
                var touch = e.originalEvent.touches[0] || e.originalEvent.changedTouches[0] || e.touches[0] || e.changedTouches[0];
                var parentOffset = $(this).parent().offset();
                self.mouse_x = (touch.pageX - parentOffset.left);
                self.mouse_y = (touch.pageY - parentOffset.top);
                var seconds = self.getCurrentMouseSecnds();
                self.updateSections("mark", seconds);
                self.PositionTitleAndIndicator(seconds);
                // Detect if we're hovering over a section
                self.DetectHoverMoments(seconds);
                if (!self.moment_active) {
                    self.DetectHoverSection(seconds);
                }
                for (var i = 0; i < self.sections.length; i++) {
                    self.updateSections("progress", self.getCurrentMouseSecnds());
                }
                if (!$(".plyr__preview-thumb").hasClass("plyr__tooltip--drag")) {
                    $(".plyr__preview-thumb").addClass("plyr__tooltip--drag");
                }
                $(".plyr__preview-thumb__time-container span").text(self.secondsToTimeString(seconds));
                if (self.ev_config.onScrubbingChange != undefined)
                    self.ev_config.onScrubbingChange(self.getCurrentMouseSecnds(), self.SecondsToPixels(self.getCurrentMouseSecnds()));
            });
            this.el_pbar.on("touchend", function (e) {
                self.mouse_over_progressbar = false;
                self.updateSections("mark", 0);
                for (var i = 0; i < self.sections.length; i++) {
                    if (self.sections[i].section_interactive) {
                        self.sections[i].HideTitle();
                        self.sections[i].SetInactive();
                    }
                }
                $(".plyr__preview-thumb").removeClass("plyr__tooltip--drag");
                $(".plyr__preview-thumb__time-container span").text(self.secondsToTimeString(self.c_progress));
                if (self.ev_config.onScrubbingChange != undefined)
                    self.ev_config.onScrubbingChange(self.getCurrentMouseSecnds(), self.SecondsToPixels(self.getCurrentMouseSecnds()));
            });
        }
    };
    /**
     * Returns true if the device is a mobile device
     * */
    PB.prototype.IsMobile = function () {
        var check = false;
        (function (a) { if (/(android|bb\d+|meego).+mobile|avantgo|bada\/|blackberry|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|mobile.+firefox|netfront|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\/|plucker|pocket|psp|series(4|6)0|symbian|treo|up\.(browser|link)|vodafone|wap|windows ce|xda|xiino|android|ipad|playbook|silk/i.test(a) || /1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\-(n|u)|c55\/|capi|ccwa|cdm\-|cell|chtm|cldc|cmd\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\-s|devi|dica|dmob|do(c|p)o|ds(12|\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\-|_)|g1 u|g560|gene|gf\-5|g\-mo|go(\.w|od)|gr(ad|un)|haie|hcit|hd\-(m|p|t)|hei\-|hi(pt|ta)|hp( i|ip)|hs\-c|ht(c(\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\-(20|go|ma)|i230|iac( |\-|\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\/)|klon|kpt |kwc\-|kyo(c|k)|le(no|xi)|lg( g|\/(k|l|u)|50|54|\-[a-w])|libw|lynx|m1\-w|m3ga|m50\/|ma(te|ui|xo)|mc(01|21|ca)|m\-cr|me(rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\-2|po(ck|rt|se)|prox|psio|pt\-g|qa\-a|qc(07|12|21|32|60|\-[2-7]|i\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\-|oo|p\-)|sdk\/|se(c(\-|0|1)|47|mc|nd|ri)|sgh\-|shar|sie(\-|m)|sk\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\-|v\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\-|tdg\-|tel(i|m)|tim\-|t\-mo|to(pl|sh)|ts(70|m\-|m3|m5)|tx\-9|up(\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|yas\-|your|zeto|zte\-/i.test(a.substr(0, 4)))
            check = true; })(navigator.userAgent || navigator.vendor || window.opera);
        return check;
    };
    /**
     * Set the duration of the video
     * @param videoLength
     */
    PB.prototype.SetDuration = function (videoLength) {
        this.video_length = videoLength;
        this.resizeSections();
    };
    /**
     * Converts a second value into the number of pixels in the chart
     * @param seconds
     */
    PB.prototype.SecondsToPixels = function (seconds) {
        return this.c_width / this.video_length * seconds;
    };
    /**
     * Converts a number of pixels into second length
     * @param seconds
     */
    PB.prototype.PixelsToSeconds = function (pixels) {
        return pixels / (this.c_width / this.video_length);
    };
    /**
     * Set the current progress of the video
     * @param seconds
     */
    PB.prototype.SetCurrentProgress = function (seconds) {
        this.updateSections("progress", seconds);
        this.c_progress = seconds;
        if (!this.mouse_over_progressbar && !this.moment_active) {
            if (!this.moment_active) {
                this.DetectHoverSection(seconds);
            }
            if (this.c_highlightedSection != null) {
                this.PositionTitleAndIndicator(this.c_highlightedSection.section_start + ((this.c_highlightedSection.section_end - this.c_highlightedSection.section_start) / 2));
            }
        }
    };
    /**
     * Set the current buffer amount of the video
     * @param seconds
     */
    PB.prototype.SetBufferProgress = function (seconds) {
        this.updateSections("buffer", seconds);
    };
    PB.prototype.DetectHoverSection = function (seconds) {
        if (!this.moment_active) {
            var sectionToShow = null;
            for (var i = 0; i < this.sections.length; i++) {
                if (this.sections[i].section_interactive) {
                    if (this.sections[i].section_start <= seconds && this.sections[i].section_end > seconds) {
                        sectionToShow = this.sections[i];
                    }
                    else {
                        this.sections[i].HideTitle();
                        this.sections[i].SetInactive();
                    }
                }
            }
            if (sectionToShow != null) {
                sectionToShow.ShowTitle();
                sectionToShow.SetActive();
                this.c_highlightedSection = sectionToShow;
                return true;
            }
            else {
                this.c_highlightedSection = null;
            }
        }
        return false;
    };
    PB.prototype.DetectHoverMoments = function (seconds) {
        var momentToShow = null;
        for (var i = 0; i < this.moments.length; i++) {
            var widthToSeconds = this.PixelsToSeconds(12);
            if (this.moments[i].moment_timestamp - widthToSeconds < seconds && this.moments[i].moment_timestamp + widthToSeconds > seconds) {
                momentToShow = this.moments[i];
            }
            else {
                this.moments[i].RemoveHover();
            }
        }
        if (momentToShow != null) {
            momentToShow.ShowTitle();
            this.c_highlightedMoment = momentToShow;
            return true;
        }
        else {
            if (this.c_highlightedMoment != null) {
                this.c_highlightedMoment.HideTitle();
            }
            this.c_highlightedSection = null;
        }
        return false;
    };
    PB.prototype.PositionTitleAndIndicator = function (seconds) {
        var left = Math.max(this.SecondsToPixels(seconds) - (this.el_title.width() / 2), 0);
        left = Math.min(left, this.el_root.width() - this.el_title.width());
        this.el_title.css("left", left + "px");
    };
    PB.prototype.updateSections = function (bar, seconds) {
        for (var i = 0; i < this.sections.length; i++) {
            this.sections[i].SetMark(bar, seconds);
        }
    };
    PB.prototype.resizeSections = function () {
        for (var i = 0; i < this.sections.length; i++) {
            this.sections[i].Resize();
        }
        for (var i = 0; i < this.moments.length; i++) {
            this.moments[i].Reposition();
        }
    };
    PB.prototype.secondsToTimeString = function (sec) {
        var minutes = Math.floor(sec / 60);
        var seconds = Math.floor(sec % 60);
        if (minutes < 0)
            minutes = 0;
        if (seconds < 0)
            seconds = 0;
        var sMinutes = minutes.toString();
        var sSeconds = seconds.toString();
        if (sMinutes.length < 2)
            sMinutes = "0" + sMinutes;
        if (sSeconds.length < 2)
            sSeconds = "0" + sSeconds;
        return sMinutes + ":" + sSeconds;
    };
    PB.prototype.getCurrentMouseSecnds = function () {
        return this.mouse_x / (this.c_width / this.video_length);
    };
    PB.prototype.startResizeMonitoring = function () {
        var self = this;
        setInterval(function () {
            var currentWidth = self.c_width;
            self.c_width = self.el_body.width() - 1;
            if (self.c_width != currentWidth) {
                self.resizeSections();
            }
        }, 100);
    };
    PB.prototype.CallThumbnailJumpUpEvent = function (force) {
        if (force === void 0) { force = false; }
        if (!this.title_jumped && (this.moment_active || this.IsThumbnailInTitleHitBox())) {
            $(".plyr__preview-thumb").css("bottom", "45px");
        }
    };
    PB.prototype.CallThumbnailJumpDownEvent = function (force) {
        if (force === void 0) { force = false; }
        if (this.title_jumped && (!this.IsThumbnailInTitleHitBox() && !this.moment_active)) {
            $(".plyr__preview-thumb").css("bottom", "22px");
        }
    };
    PB.prototype.IsThumbnailInTitleHitBox = function () {
        if (this.moment_active) {
            this.title_jumped = true;
            return true;
        }
        if (this.el_title.position().left < -50 || !this.el_title.hasClass("active")) {
            this.title_jumped = false;
            return false;
        }
        var thumb = $(".plyr__preview-thumb");
        var thumbPosition = thumb.position();
        var titlePosition = this.el_title.position();
        if (titlePosition.left + this.el_title.width() < thumbPosition.left) {
            this.title_jumped = false;
            return false;
        }
        if (thumbPosition.left + thumb.width() > titlePosition.left) {
            this.title_jumped = true;
            return true;
        }
        this.title_jumped = false;
        return false;
    };
    PB.CONST_END = 2147483647;
    return PB;
}());
var PBChapter = /** @class */ (function () {
    function PBChapter() {
    }
    PBChapter.compare = function (a, b) {
        if (a.start < b.start) {
            return -1;
        }
        if (a.start > b.start) {
            return 1;
        }
        return 0;
    };
    return PBChapter;
}());
var PBMoment = /** @class */ (function () {
    function PBMoment() {
    }
    PBMoment.compare = function (a, b) {
        if (a.start < b.start) {
            return -1;
        }
        if (a.start > b.start) {
            return 1;
        }
        return 0;
    };
    return PBMoment;
}());
var PBConfig = /** @class */ (function () {
    function PBConfig() {
    }
    return PBConfig;
}());
var PBMomentCircle = /** @class */ (function () {
    function PBMomentCircle(pb, timestamp, title) {
        this.pb = pb;
        this.el_body = $('<div class="sp__moment"></div>');
        this.moment_timestamp = timestamp;
        this.moment_title = title;
        this.Reposition();
    }
    PBMomentCircle.prototype.Reposition = function () {
        this.el_body.css("left", (this.pb.SecondsToPixels(this.moment_timestamp) - 6) + "px");
    };
    PBMomentCircle.prototype.GetElement = function () {
        return this.el_body;
    };
    PBMomentCircle.prototype.ShowTitle = function () {
        if (!this.el_body.hasClass("hover")) {
            this.el_body.addClass("hover");
        }
        this.pb.PositionTitleAndIndicator(this.moment_timestamp);
        if (!this.pb.moment_active) {
            this.pb.moment_active = true;
            if (this.moment_title != "") {
                this.pb.CallThumbnailJumpUpEvent();
            }
            this.pb.el_title.addClass("active");
        }
        this.pb.el_title.text(this.moment_title);
    };
    PBMomentCircle.prototype.HideTitle = function () {
        if (this.pb.moment_active) {
            this.RemoveHover();
            this.pb.PositionTitleAndIndicator(this.moment_timestamp);
            // Set all sections to inactive (they should be activated by their own events)
            for (var i = 0; i < this.pb.sections.length; i++) {
                if (this.pb.sections[i].section_interactive) {
                    this.pb.sections[i].SetInactive();
                }
            }
            this.pb.moment_active = false;
            var detectedHoverSection = this.pb.DetectHoverSection(this.moment_timestamp);
            if (!detectedHoverSection) {
                this.pb.el_title.text("");
                this.pb.el_title.removeClass("active");
                if (this.moment_title != "") {
                    this.pb.title_jumped = true;
                    this.pb.CallThumbnailJumpDownEvent(true);
                }
            }
            else {
                this.pb.el_title.text(this.pb.c_highlightedSection.section_title);
            }
        }
    };
    PBMomentCircle.prototype.RemoveHover = function () {
        this.el_body.removeClass("hover");
    };
    return PBMomentCircle;
}());
var PBSection = /** @class */ (function () {
    function PBSection(pb, start, end, title, interactive) {
        this.bars = {};
        this.pb = pb;
        this.section_start = start;
        this.section_end = end;
        this.section_interactive = interactive;
        this.section_title = title;
        // Prepare the holder and boeis
        this.el_body = $('<li></li>');
        if (interactive) {
            this.el_body.addClass("interactive");
        }
        this.el_container = $('<div class="sp__container"></div>');
        this.el_bg = $('<div class="sp__bg"></div>');
        this.el_body.append(this.el_container);
        this.el_container.append(this.el_bg);
        //Add the marker position bar
        var markBar = new PBBar(this, 1, "#ffffff88");
        this.bars["mark"] = markBar;
        this.el_container.append(markBar.GetElement());
        var bufferBar = new PBBar(this, 2, "#ffffff50");
        this.bars["buffer"] = bufferBar;
        this.el_container.append(bufferBar.GetElement());
        var progressBar = new PBBar(this, 3, this.pb.ev_config.keyColor);
        this.bars["progress"] = progressBar;
        this.el_container.append(progressBar.GetElement());
        this.Resize();
    }
    PBSection.prototype.SetInactive = function () {
        this.el_body.removeClass("active");
    };
    PBSection.prototype.SetActive = function () {
        if (!this.el_body.hasClass("active")) {
            this.el_body.addClass("active");
        }
    };
    PBSection.prototype.HideTitle = function () {
        if (this.c_titleShown) {
            this.pb.el_title.text("");
            this.pb.el_title.removeClass("active");
            if (this.section_title != "") {
                this.pb.CallThumbnailJumpDownEvent();
            }
        }
        this.c_titleShown = false;
    };
    PBSection.prototype.ShowTitle = function () {
        if (!this.c_titleShown) {
            if (this.section_interactive && !this.pb.el_title.hasClass("active")) {
                this.pb.el_title.addClass("active");
                if (this.section_title != "") {
                    this.pb.CallThumbnailJumpUpEvent();
                }
            }
            this.pb.el_title.text(this.section_interactive ? this.section_title : "");
            this.c_titleShown = true;
        }
    };
    PBSection.prototype.Resize = function () {
        var end = this.section_end == PB.CONST_END ? this.pb.video_length : this.section_end;
        var width = this.pb.SecondsToPixels(end - this.section_start);
        this.el_body.width(width);
        this.c_width = width;
        var barKeys = Object.keys(this.bars);
        for (var i = 0; i < barKeys.length; i++) {
            this.bars[barKeys[i]].Measure();
        }
    };
    PBSection.prototype.SetMark = function (type, seconds) {
        this.bars[type].SetMark(seconds);
    };
    PBSection.prototype.GetElement = function () {
        return this.el_body;
    };
    return PBSection;
}());
var PBBar = /** @class */ (function () {
    function PBBar(section, zIndex, color) {
        this.section = section;
        this.c_zindex = zIndex;
        this.c_color = color;
        this.el_body = $('<div class="sp__section"></div>');
        this.el_body.css("background-color", this.c_color);
        this.el_body.css("z-index", this.c_zindex);
        this.el_body.width(0);
        this.Measure();
    }
    PBBar.prototype.SetMark = function (seconds) {
        if (seconds <= this.section.section_start) {
            this.el_body.width(0);
        }
        else {
            var offset = this.section.pb.SecondsToPixels(this.section.section_start);
            var width = this.section.pb.SecondsToPixels(seconds) - offset;
            this.el_body.width(Math.min(width, this.c_width));
        }
    };
    PBBar.prototype.Measure = function () {
        var end = this.section.section_end == PB.CONST_END ? this.section.pb.video_length : this.section.section_end;
        this.c_width = this.section.pb.SecondsToPixels(end - this.section.section_start);
        ;
    };
    PBBar.prototype.GetElement = function () {
        return this.el_body;
    };
    return PBBar;
}());
//# sourceMappingURL=pb.js.map