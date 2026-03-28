class AnalyticsBrowser {
  load() {}

  addSourceMiddleware() {}

  track() {
    return Promise.resolve();
  }

  identify() {
    return Promise.resolve();
  }

  ready() {
    return Promise.resolve();
  }
}

export { AnalyticsBrowser };
export default { AnalyticsBrowser };
