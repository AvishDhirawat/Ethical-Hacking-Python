// logger.ts
var Logger = class {
  constructor(level) {
    this.level = level;
  }
  debug(message, ...optionalParams) {
    if (this.level <= 0 /* DEBUG */)
      console.debug(message, ...optionalParams);
  }
  warn(message, ...optionalParams) {
    if (this.level <= 2 /* WARN */)
      console.warn(message, ...optionalParams);
  }
  info(message, ...optionalParams) {
    if (this.level <= 1 /* INFO */)
      console.info(message, ...optionalParams);
  }
  log(message, ...optionalParams) {
    if (this.level <= 1 /* INFO */)
      console.log(message, ...optionalParams);
  }
  error(message, ...optionalParams) {
    if (this.level <= 3 /* ERROR */)
      console.error(message, ...optionalParams);
  }
};

// stream-drm-engine.ts
var StreamDrmEngine = class {
  constructor(fpLicenseUrl, fpCertificateUrl, logLevel) {
    this.keysPromise = null;
    this.fpLicenseUrl = fpLicenseUrl;
    this.fpCertificateUrl = fpCertificateUrl;
    this.logger_ = new Logger(logLevel);
  }
  async loadFpCertificate() {
    try {
      const response = await fetch(this.fpCertificateUrl);
      this.fpCertificate = await response.arrayBuffer();
    } catch (e) {
      this.logger_.error(`Could not load FairPlay certificate at ${this.fpCertificateUrl}`);
    }
  }
  async createMediaKeys(video) {
    if (this.keysPromise)
      await this.keysPromise;
    if (!video.mediaKeys) {
      let resolve = null;
      this.keysPromise = new Promise((r) => resolve = r);
      const accessPromise = navigator.requestMediaKeySystemAccess("com.apple.fps", [{
        initDataTypes: ["cenc", "sinf", "skd"],
        videoCapabilities: [{ contentType: "application/vnd.apple.mpegurl", robustness: "" }],
        distinctiveIdentifier: "not-allowed",
        persistentState: "not-allowed",
        sessionTypes: ["temporary"]
      }]);
      const access = await accessPromise;
      const keys = await access.createMediaKeys();
      const success = await keys.setServerCertificate(this.fpCertificate);
      const keysResult = await video.setMediaKeys(keys);
      resolve();
    }
  }
  async initFairPlay(videoEl) {
    await this.loadFpCertificate();
    videoEl.addEventListener("encrypted", (e) => this.onFpEncrypted(e));
  }
  async onFpEncrypted(event) {
    try {
      const initDataType = event.initDataType;
      const video = event.target;
      await this.createMediaKeys(video);
      const initData = event.initData;
      const session = video.mediaKeys.createSession();
      await session.generateRequest(initDataType, initData);
      const message = await new Promise((resolve) => {
        session.addEventListener("message", (e) => {
          resolve(e);
        }, { once: true });
      });
      let response = await this.getResponse(message, this.fpLicenseUrl);
      await session.update(response).catch(() => this.logger_.error("FP license update failed;"));
      return session;
    } catch (e) {
      this.logger_.error(`Could not start FP encrypted playback due to exception "${e}"`);
    }
  }
  async getResponse(event, license_server_url) {
    const licenseResponse = await fetch(license_server_url, {
      method: "POST",
      body: event.message
    });
    return await licenseResponse.arrayBuffer();
  }
};
StreamDrmEngine.prototype.fpLicenseUrl = "";
