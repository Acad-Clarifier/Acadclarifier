const DEPLOYED_API_BASE =
  'https://acadclarifier-eyebgfaxfdgrcwe4.eastasia-01.azurewebsites.net';
const LOCAL_API_BASE = 'http://localhost:5000';

const isLocalHost =
  window.location.hostname === 'localhost' ||
  window.location.hostname === '127.0.0.1';

const API_BASE =
  window.APP_CONFIG?.apiBaseUrl ||
  (isLocalHost ? LOCAL_API_BASE : DEPLOYED_API_BASE);

const DEFAULT_TIMEOUT_MS = 150000;  // 150s - covers backend 120s timeout + buffer

function buildRequestError(message, details = {}) {
  const error = new Error(message);
  if (details.code) {
    error.code = details.code;
  }
  if (details.status) {
    error.status = details.status;
  }
  if (details.payload !== undefined) {
    error.payload = details.payload;
  }
  return error;
}

async function request(path, options = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options;
  const controller = new AbortController();
  let abortListener = null;
  let didTimeout = false;
  const timeoutId = window.setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, timeoutMs);

  if (fetchOptions.signal) {
    if (fetchOptions.signal.aborted) {
      controller.abort();
    } else {
      abortListener = () => controller.abort();
      fetchOptions.signal.addEventListener('abort', abortListener, {
        once: true,
      });
    }
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(fetchOptions.headers || {}),
      },
      ...fetchOptions,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      if (!didTimeout && fetchOptions.signal?.aborted) {
        throw buildRequestError('Request was cancelled', { code: 'ABORTED' });
      }
      throw buildRequestError('Request timed out', { code: 'TIMEOUT' });
    }
    throw buildRequestError('Network request failed', { code: 'NETWORK' });
  } finally {
    window.clearTimeout(timeoutId);
    if (fetchOptions.signal && abortListener) {
      fetchOptions.signal.removeEventListener('abort', abortListener);
    }
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    throw buildRequestError(`Request failed: ${response.status}`, {
      code: 'HTTP',
      status: response.status,
      payload,
    });
  }

  return payload;
}

export function fetchSession(options = {}) {
  return request('/session', { method: 'GET', ...options });
}

export function askQuestion(question, bookRef = null, options = {}) {
  const payload = { question };
  if (bookRef) {
    payload.book_ref = bookRef;
  }

  return request('/ask', {
    method: 'POST',
    body: JSON.stringify(payload),
    ...options,
  });
}

export function askWebQuestion(question, options = {}) {
  return request('/web/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
    ...options,
  });
}

export function fetchRecommendations(question, topK = 5, options = {}) {
  return request('/recommend', {
    method: 'POST',
    body: JSON.stringify({ question, top_k: topK }),
    ...options,
  });
}

export function fetchJournalRecommendations(
  query,
  topK = 10,
  filterType = 'all',
  options = {},
) {
  return request('/journal/recommend', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK, filter_type: filterType }),
    ...options,
  });
}

export function fetchLibrary(
  query = '',
  page = 1,
  pageSize = 20,
  options = {},
) {
  const params = new URLSearchParams();
  if (query && query.trim()) {
    params.set('q', query.trim());
  }
  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  return request(`/library?${params.toString()}`, {
    method: 'GET',
    ...options,
  });
}

export function fetchLibraryBook(bookRef, options = {}) {
  return request(`/library/${encodeURIComponent(bookRef)}`, {
    method: 'GET',
    ...options,
  });
}
