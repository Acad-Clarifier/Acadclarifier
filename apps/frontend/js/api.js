const API_BASE = window.APP_CONFIG?.apiBaseUrl || 'http://localhost:5000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

export function fetchSession() {
  return request('/session', { method: 'GET' });
}

export function askQuestion(question) {
  return request('/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

export function askWebQuestion(question) {
  return request('/web/ask', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}

export function fetchRecommendations(question, topK = 5) {
  return request('/recommend', {
    method: 'POST',
    body: JSON.stringify({ question, top_k: topK }),
  });
}

export function fetchJournalRecommendations(
  query,
  topK = 10,
  filterType = 'all',
) {
  return request('/journal/recommend', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK, filter_type: filterType }),
  });
}

export function fetchLibrary(query = '', page = 1, pageSize = 20) {
  const params = new URLSearchParams();
  if (query && query.trim()) {
    params.set('q', query.trim());
  }
  params.set('page', String(page));
  params.set('page_size', String(pageSize));

  return request(`/library?${params.toString()}`, { method: 'GET' });
}

export function fetchLibraryBook(bookRef) {
  return request(`/library/${encodeURIComponent(bookRef)}`, { method: 'GET' });
}
