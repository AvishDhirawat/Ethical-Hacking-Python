function initPlyrPositionSaver(player, videoId) {
    const STORAGE_KEY_PREFIX = 'plyr-video-position-';
    const END_THRESHOLD = 3;
    const SAVE_INTERVAL_MS = 1000;

    var seeked = false;

    function getStorageKey() {
        return STORAGE_KEY_PREFIX + videoId;
    }

    function savePosition(currentTime) {
        // Don't save when current position is less then 1 second from the start
        if (currentTime < 1) {
            return;
        }

        // If we have a valid duration and the currentTime is within END_THRESHOLD seconds from the end,
        // then delete the saved position instead of updating it.
        if (player.duration && currentTime >= player.duration - END_THRESHOLD) {
            localStorage.removeItem(getStorageKey());
            return;
        }
        const entry = {
            currentTime,
            timestamp: Date.now()
        };
        localStorage.setItem(getStorageKey(), JSON.stringify(entry));
    }

    // Load the saved position if it exists and is not older than 7 days.
    function loadPosition() {
        const stored = localStorage.getItem(getStorageKey());
        if (!stored) return 0;
        try {
            const entry = JSON.parse(stored);
            const SEVEN_DAYS = 7 * 24 * 60 * 60 * 1000;
            if (Date.now() - entry.timestamp > SEVEN_DAYS) {
                localStorage.removeItem(getStorageKey());
                return 0;
            }
            return entry.currentTime;
        } catch (error) {
            return 0;
        }
    }

    // When the video is ready to play, restore the saved position if available and if the &t= parameter is not set
    player.on('canplay', () => {
        const searchParams = new URLSearchParams(window.location.search);
        const skipSeek = searchParams.has('t');
        if (skipSeek) {
            return;
        }

        const savedTime = loadPosition();
        if (savedTime > 0 && !seeked) {
            player.currentTime = savedTime;
            seeked = true;
        }
    });

    // Save position on pause as a fallback.
    player.on('pause', () => {
        savePosition(player.currentTime);
    });

    // Also save the position when the user is about to leave the page.
    window.addEventListener('beforeunload', () => {
        savePosition(player.currentTime);
    });

    // Set up periodic saving every 1 second.
    setInterval(() => {
        // Ensure the video has a valid duration before saving.
        if (player.duration) {
            savePosition(player.currentTime);
        }
    }, SAVE_INTERVAL_MS);
}
