function normalizeError(raw, fallbackMessage = '请求失败') {
  if (!raw) return { message: fallbackMessage, status: 0, code: 'UNKNOWN', details: null };

  if (raw.name === 'AbortError') {
    return { message: '请求已取消', status: 0, code: 'ABORTED', details: null };
  }

  if (raw.__normalized) return raw;

  const error = {
    message: raw.message || fallbackMessage,
    status: raw.status || 0,
    code: raw.code || 'REQUEST_ERROR',
    details: raw.details || raw.data || null,
  };
  error.__normalized = true;
  return error;
}

export function createApiClient({ baseUrl, timeoutMs = 8000, log }) {
  const inFlight = new Map();

  function buildUrl(path) {
    return path.startsWith('http://') || path.startsWith('https://') ? path : `${baseUrl}${path}`;
  }

  async function request(path, options = {}) {
    const method = String(options.method || 'GET').toUpperCase();
    const url = buildUrl(path);
    const requestKey = options.requestKey || null;
    const requestTimeoutMs = options.timeoutMs || timeoutMs;

    if (requestKey && inFlight.has(requestKey)) {
      inFlight.get(requestKey).abort();
      inFlight.delete(requestKey);
    }

    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, requestTimeoutMs);

    if (requestKey) inFlight.set(requestKey, controller);

    const requestInit = {
      method,
      credentials: 'omit',
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      signal: controller.signal,
    };

    if (options.body !== undefined) {
      requestInit.body = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
    }

    if (log) log('info', `${method} ${path}`);

    try {
      const res = await fetch(url, requestInit);
      const contentType = res.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json');
      const payload = isJson ? await res.json() : await res.text();

      if (!res.ok) {
        const error = {
          message: payload?.message || payload?.error || res.statusText || '请求失败',
          status: res.status,
          code: payload?.code || `HTTP_${res.status}`,
          details: payload,
          __normalized: true,
        };
        throw error;
      }

      return payload;
    } catch (err) {
      const normalized = timedOut && err?.name === 'AbortError'
        ? {
            message: '请求超时，请重试',
            status: 0,
            code: 'TIMEOUT',
            details: { timeout_ms: requestTimeoutMs },
            __normalized: true,
          }
        : normalizeError(err, '网络请求失败');
      if (log) log(normalized.code === 'ABORTED' ? 'info' : 'error', `${method} ${path} failed`, normalized);
      throw normalized;
    } finally {
      clearTimeout(timer);
      if (requestKey && inFlight.get(requestKey) === controller) inFlight.delete(requestKey);
    }
  }

  function abortRequest(requestKey) {
    if (!requestKey || !inFlight.has(requestKey)) return;
    inFlight.get(requestKey).abort();
    inFlight.delete(requestKey);
  }

  return {
    request,
    get(path, options = {}) {
      return request(path, { ...options, method: 'GET' });
    },
    post(path, body, options = {}) {
      return request(path, { ...options, method: 'POST', body });
    },
    put(path, body, options = {}) {
      return request(path, { ...options, method: 'PUT', body });
    },
    del(path, options = {}) {
      return request(path, { ...options, method: 'DELETE' });
    },
    abortRequest,
    normalizeError,
  };
}
