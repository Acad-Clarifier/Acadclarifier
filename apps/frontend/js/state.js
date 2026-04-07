const state = {
  query: '',
  selectedMode: '',
  apiResults: null,
  theme: localStorage.getItem('acadclarifier-theme') || 'light',
  localChat: [],
  webChat: [],
  activeBook: null,
  libraryBooks: [],
  libraryTotal: 0,
  libraryQuery: '',
  libraryLoading: false,
  libraryError: '',
  isLibraryModalOpen: false,
  selectedLibraryBook: null,
  isWebLoading: false,
  recommendationResults: [],
  recommendationQuery: '',
  recommendationLoading: false,
  recommendationError: '',
  journalRecommendationResults: [],
  journalRecommendationQuery: '',
  journalRecommendationLoading: false,
  journalRecommendationError: '',
  journalRecommendationFilter: 'all',
};

export function getState() {
  return state;
}

export function setState(patch) {
  Object.assign(state, patch);
}

export function setTheme(theme) {
  state.theme = theme;
  localStorage.setItem('acadclarifier-theme', theme);
}

export function addChatMessage(mode, role, message) {
  const target = mode === 'local' ? state.localChat : state.webChat;
  target.push({ role, message });
}

export function clearChat(mode) {
  if (mode === 'local') {
    state.localChat = [];
  } else if (mode === 'web') {
    state.webChat = [];
  }
}

export function setApiResults(results) {
  state.apiResults = results;
}

export function setLibraryData({ items = [], total = 0 }) {
  state.libraryBooks = items;
  state.libraryTotal = total;
}

export function setLibraryQuery(query) {
  state.libraryQuery = query;
}

export function setLibraryLoading(loading) {
  state.libraryLoading = loading;
}

export function setLibraryError(message) {
  state.libraryError = message;
}

export function setLibraryModalOpen(open) {
  state.isLibraryModalOpen = open;
}

export function setSelectedLibraryBook(book) {
  state.selectedLibraryBook = book;
  state.activeBook = book ? book.uid : null;
}

export function setWebLoading(loading) {
  state.isWebLoading = loading;
}

export function setRecommendationState({
  results,
  query,
  loading,
  error,
} = {}) {
  if (Array.isArray(results)) {
    state.recommendationResults = results;
  }

  if (typeof query === 'string') {
    state.recommendationQuery = query;
  }

  if (typeof loading === 'boolean') {
    state.recommendationLoading = loading;
  }

  if (typeof error === 'string') {
    state.recommendationError = error;
  }
}

export function setJournalRecommendationState({
  results,
  query,
  loading,
  error,
  filter,
} = {}) {
  if (Array.isArray(results)) {
    state.journalRecommendationResults = results;
  }

  if (typeof query === 'string') {
    state.journalRecommendationQuery = query;
  }

  if (typeof loading === 'boolean') {
    state.journalRecommendationLoading = loading;
  }

  if (typeof error === 'string') {
    state.journalRecommendationError = error;
  }

  if (typeof filter === 'string' && filter.trim()) {
    state.journalRecommendationFilter = filter.trim();
  }
}
