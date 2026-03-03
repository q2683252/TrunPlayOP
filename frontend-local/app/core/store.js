function isPlainObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value);
}

function deepMerge(target, patch) {
  if (!isPlainObject(target) || !isPlainObject(patch)) return patch;
  const result = { ...target };
  Object.keys(patch).forEach((key) => {
    if (isPlainObject(target[key]) && isPlainObject(patch[key])) {
      result[key] = deepMerge(target[key], patch[key]);
    } else {
      result[key] = patch[key];
    }
  });
  return result;
}

export function createStore(initialState) {
  let state = initialState;
  const listeners = new Set();

  function emit() {
    listeners.forEach((listener) => {
      try {
        listener(state);
      } catch (err) {
        console.error('[TrunPlay][store] listener error', err);
      }
    });
  }

  return {
    getState() {
      return state;
    },
    set(next) {
      state = typeof next === 'function' ? next(state) : next;
      emit();
      return state;
    },
    patch(partial) {
      state = deepMerge(state, partial);
      emit();
      return state;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
