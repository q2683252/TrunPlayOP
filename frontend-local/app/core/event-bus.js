export function createEventBus() {
  const handlers = new Map();

  return {
    on(event, fn) {
      if (!handlers.has(event)) handlers.set(event, new Set());
      handlers.get(event).add(fn);
      return () => handlers.get(event)?.delete(fn);
    },
    emit(event, payload) {
      const set = handlers.get(event);
      if (!set || set.size === 0) return;
      set.forEach((fn) => {
        try {
          fn(payload);
        } catch (err) {
          console.error(`[TrunPlay][bus] handler error for ${event}`, err);
        }
      });
    },
  };
}
