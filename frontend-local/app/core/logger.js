export function createLogger(namespace) {
  return function log(level, msg, data) {
    const prefix = `[TrunPlay][${namespace}] ${msg}`;
    const args = data === undefined ? [prefix] : [prefix, data];
    if (level === 'error') console.error(...args);
    else if (level === 'warn') console.warn(...args);
    else console.log(...args);
  };
}

export function createLoggers() {
  return {
    api: createLogger('api'),
    ui: createLogger('ui'),
    status: createLogger('status'),
    playback: createLogger('playback'),
    plans: createLogger('plans'),
    study: createLogger('study'),
    devices: createLogger('devices'),
    smb: createLogger('smb'),
    history: createLogger('history'),
  };
}
