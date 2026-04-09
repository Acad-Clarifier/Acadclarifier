import { createNavbar } from '../components/navbar.js';
import { createLoader } from '../components/loader.js';
import { createLibraryModal } from '../components/library_modal.js';
import {
  askQuestion,
  fetchJournalRecommendations,
  askWebQuestion,
  fetchRecommendations,
  fetchLibrary,
  fetchLibraryBook,
  fetchSession,
} from './api.js';
import { initRouter } from './router.js';
import {
  addChatMessage,
  clearChat,
  getState,
  setApiResults,
  setLibraryData,
  setLibraryError,
  setLibraryLoading,
  setLibraryModalOpen,
  setJournalRecommendationState,
  setRecommendationState,
  setWebLoading,
  setLibraryQuery,
  setSelectedLibraryBook,
  setState,
  setTheme,
} from './state.js';

const pageRoot = document.getElementById('page-root');
const navbarRoot = document.getElementById('navbar-root');
let localPollingTimer = null;
let localPollingFailureCount = 0;
let libraryFetchController = null;
let libraryBookFetchController = null;
const MAX_LOCAL_POLL_FAILURES = 5;

const PAGE_STYLE_BY_ROUTE = {
  '/': './css/home.css',
  '/local': './css/local.css',
  '/web': './css/web.css',
  '/book_rec': './css/book_rec.css',
  '/journal_rec': './css/journal_rec.css',
};

function getFriendlyRequestError(error, fallbackMessage) {
  if (!error) {
    return fallbackMessage;
  }
  if (error.code === 'TIMEOUT') {
    return 'Request timed out. Please try again.';
  }
  if (error.code === 'NETWORK') {
    return 'Network error while contacting backend.';
  }
  if (error.code === 'ABORTED') {
    return fallbackMessage;
  }
  if (error.code === 'HTTP') {
    const backendMessage =
      typeof error.payload === 'object' && error.payload !== null
        ? error.payload.error || error.payload.message
        : '';
    return backendMessage || `Backend request failed (${error.status}).`;
  }
  return fallbackMessage;
}

function removeLoadingMessage(mode) {
  const chat = mode === 'local' ? getState().localChat : getState().webChat;
  if (!chat.length) {
    return;
  }
  const lastMessage = chat[chat.length - 1];
  if (lastMessage?.role === 'assistant' && lastMessage?.message === '...') {
    chat.pop();
  }
}

function applyPageStyles(route) {
  const head = document.head;
  if (!head) {
    return;
  }

  let link = document.getElementById('page-stylesheet');
  if (!link) {
    link = document.createElement('link');
    link.id = 'page-stylesheet';
    link.rel = 'stylesheet';
    head.appendChild(link);
  }

  const href = PAGE_STYLE_BY_ROUTE[route] || '';
  if (!href) {
    link.removeAttribute('href');
    return;
  }

  if (link.getAttribute('href') !== href) {
    link.setAttribute('href', href);
  }
}

function applyThemeToDom() {
  document.body.dataset.theme = getState().theme;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function parseMarkdown(text) {
  const source = typeof text === 'string' ? text : String(text ?? '');

  // Fallback if CDN libraries are unavailable for any reason.
  if (!window.marked || !window.DOMPurify) {
    return escapeHtml(source).replace(/\n/g, '<br />');
  }

  window.marked.setOptions({
    breaks: true,
    gfm: true,
  });

  let html = window.marked.parse(source);
  html = processLatexMath(html);

  return window.DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      'p',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'ul',
      'ol',
      'li',
      'em',
      'strong',
      'br',
      'span',
      'div',
      'code',
      'pre',
      'blockquote',
      'hr',
      'a',
    ],
    ALLOWED_ATTR: ['class', 'href', 'target', 'rel'],
  });
}

function processLatexMath(text) {
  if (!window.katex) {
    return text;
  }

  // Handle display math ($$...$$)
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
    try {
      const html = window.katex.renderToString(formula, { displayMode: true });
      return `<span class="math-display">${html}</span>`;
    } catch (e) {
      console.warn('KaTeX rendering error:', e);
      return match; // Return original if error
    }
  });

  // Handle inline math ($...$), but not if it's part of HTML entity
  text = text.replace(/(?<!\$)\$([^\$\n]+?)\$(?!\$)/g, (match, formula) => {
    // Skip if it looks like it's inside HTML tags
    if (match.includes('<') || match.includes('>')) {
      return match;
    }
    try {
      const html = window.katex.renderToString(formula, { displayMode: false });
      return `<span class="math-inline">${html}</span>`;
    } catch (e) {
      console.warn('KaTeX rendering error:', e);
      return match; // Return original if error
    }
  });

  return text;
}

function renderMessages(container, messages) {
  const fragment = document.createDocumentFragment();
  for (const item of messages) {
    const msg = document.createElement('article');
    const cssRole = item.role === 'user' ? 'user' : 'assistant';
    msg.className = `message message-${cssRole}`;

    // Apply loading animation class for "..." message
    if (item.message === '...') {
      msg.classList.add('message-loading');
      msg.textContent = '';
    } else if (cssRole === 'assistant') {
      msg.innerHTML = parseMarkdown(item.message);
    } else {
      msg.innerHTML = escapeHtml(item.message).replace(/\n/g, '<br />');
    }
    fragment.appendChild(msg);
  }

  container.innerHTML = '';
  container.appendChild(fragment);
  container.scrollTop = container.scrollHeight;
}

function renderRecommendationResults() {
  const resultsRoot = document.getElementById('book-rec-results');
  const state = getState();

  if (!resultsRoot) {
    return;
  }

  if (state.recommendationLoading) {
    resultsRoot.innerHTML =
      '<div class="book-rec-empty">Fetching recommendations...</div>';
    return;
  }

  if (state.recommendationError) {
    resultsRoot.innerHTML = `<div class="book-rec-empty">${escapeHtml(state.recommendationError)}</div>`;
    return;
  }

  if (!state.recommendationResults.length) {
    resultsRoot.innerHTML =
      '<div class="book-rec-empty">Describe your learning goal and click Get Recommendations.</div>';
    return;
  }

  resultsRoot.innerHTML = state.recommendationResults
    .map(
      (item) => `
      <article class="book-rec-card">
        <header class="book-rec-card-head">
          <span class="book-rec-rank">#${escapeHtml(String(item.rank || '-'))}</span>
          <span class="book-rec-score">${escapeHtml(String(item.match_percentage || 0))}% match</span>
        </header>
        <h3 class="book-rec-title">${escapeHtml(item.title || 'Untitled')}</h3>
        <p class="book-rec-meta">${escapeHtml(item.author || 'Unknown author')} • ${escapeHtml(item.category || 'General')}</p>
        <p class="book-rec-summary">${escapeHtml(item.summary || 'No summary available.')}</p>
      </article>
    `,
    )
    .join('');
}

function setActiveJournalFilterButton() {
  const { journalRecommendationFilter } = getState();
  const buttons = document.querySelectorAll('[data-journal-filter]');

  for (const button of buttons) {
    if (!(button instanceof HTMLElement)) {
      continue;
    }

    const isActive =
      (button.dataset.journalFilter || 'all') === journalRecommendationFilter;
    button.classList.toggle('is-active', isActive);
  }
}

function renderJournalRecommendationResults() {
  const resultsRoot = document.getElementById('journal-rec-results');
  const queryRoot = document.getElementById('journal-rec-query-display');
  const state = getState();

  if (!resultsRoot) {
    return;
  }

  setActiveJournalFilterButton();

  if (queryRoot) {
    queryRoot.textContent =
      state.journalRecommendationQuery || 'your research topic';
  }

  if (state.journalRecommendationLoading) {
    resultsRoot.innerHTML =
      '<div class="journal-rec-empty">Running AI journal analysis...</div>';
    return;
  }

  if (state.journalRecommendationError) {
    resultsRoot.innerHTML = `<div class="journal-rec-empty">${escapeHtml(state.journalRecommendationError)}</div>`;
    return;
  }

  if (!state.journalRecommendationResults.length) {
    resultsRoot.innerHTML =
      '<div class="journal-rec-empty">Describe your research topic and click Send to receive journal recommendations.</div>';
    return;
  }

  resultsRoot.innerHTML = state.journalRecommendationResults
    .map(
      (item) => `
      <article class="journal-rec-card">
        <div class="journal-rec-rank">${escapeHtml(String(item.rank || '-'))}</div>
        <div class="journal-rec-content">
          <div class="journal-rec-head">
            <h3>${escapeHtml(item.title || 'Untitled')}</h3>
            ${
              item.source_url
                ? `<a class="journal-rec-link" href="${escapeHtml(item.source_url)}" target="_blank" rel="noopener noreferrer">View Original</a>`
                : ''
            }
          </div>
          <p class="journal-rec-meta">
            ${item.publisher ? `<span>${escapeHtml(item.publisher)}</span>` : ''}
            <span>DOI: ${escapeHtml(item.doi || 'N/A')}</span>
            <span>${escapeHtml(String(item.year || 'Unknown Year'))}</span>
            <span>${escapeHtml(String(item.match_percentage || 0))}% match</span>
          </p>
          <p class="journal-rec-abstract">${escapeHtml(item.abstract || item.summary || 'No abstract available.')}</p>
        </div>
      </article>
    `,
    )
    .join('');
}

async function applyJournalFilter(filterType) {
  const state = getState();
  const query = (state.journalRecommendationQuery || '').trim();
  const topKSelect = document.querySelector('#journal-rec-topk');
  const topK = Number(topKSelect?.value || 10);

  setJournalRecommendationState({ filter: filterType });

  if (!query) {
    renderJournalRecommendationResults();
    return;
  }

  setJournalRecommendationState({
    loading: true,
    error: '',
    results: [],
  });
  renderJournalRecommendationResults();

  try {
    const response = await fetchJournalRecommendations(query, topK, filterType);
    setJournalRecommendationState({
      loading: false,
      error:
        response?.status === 'no_results'
          ? response.message || 'No matching journals found.'
          : '',
      results: response?.items || [],
    });
  } catch (error) {
    setJournalRecommendationState({
      loading: false,
      error: getFriendlyRequestError(
        error,
        'Unable to fetch journal recommendations right now.',
      ),
      results: [],
    });
  } finally {
    renderJournalRecommendationResults();
  }
}

async function submitRecommendation(formElement) {
  const input = formElement.querySelector("textarea[name='question']");
  const topKSelect = formElement.querySelector("select[name='top_k']");
  const submitButton = formElement.querySelector("button[type='submit']");

  if (!input || !submitButton) {
    return;
  }

  const question = input.value.trim();
  const topK = Number(topKSelect?.value || 5);

  if (!question) {
    setRecommendationState({
      error: 'Please enter your topic or learning goal.',
    });
    renderRecommendationResults();
    return;
  }

  setRecommendationState({
    query: question,
    loading: true,
    error: '',
    results: [],
  });
  renderRecommendationResults();
  submitButton.disabled = true;

  try {
    const response = await fetchRecommendations(question, topK);
    setRecommendationState({
      loading: false,
      error:
        response?.status === 'no_results'
          ? response.message || 'No matching books found.'
          : '',
      results: response?.items || [],
    });
  } catch (error) {
    setRecommendationState({
      loading: false,
      error: getFriendlyRequestError(
        error,
        'Unable to fetch recommendations right now.',
      ),
      results: [],
    });
  } finally {
    submitButton.disabled = false;
    renderRecommendationResults();
  }
}

async function submitJournalRecommendation(formElement) {
  const input = formElement.querySelector("textarea[name='query']");
  const topKSelect = formElement.querySelector("select[name='top_k']");
  const submitButton = formElement.querySelector("button[type='submit']");
  const filterType = getState().journalRecommendationFilter || 'all';

  if (!input || !submitButton) {
    return;
  }

  const question = input.value.trim();
  const topK = Number(topKSelect?.value || 10);

  if (!question) {
    setJournalRecommendationState({
      error: 'Please describe your research topic.',
    });
    renderJournalRecommendationResults();
    return;
  }

  setJournalRecommendationState({
    query: question,
    loading: true,
    error: '',
    results: [],
  });
  renderJournalRecommendationResults();
  submitButton.disabled = true;

  try {
    const response = await fetchJournalRecommendations(
      question,
      topK,
      filterType,
    );
    setJournalRecommendationState({
      loading: false,
      error:
        response?.status === 'no_results'
          ? response.message || 'No matching journals found.'
          : '',
      results: response?.items || [],
    });
  } catch (error) {
    setJournalRecommendationState({
      loading: false,
      error: getFriendlyRequestError(
        error,
        'Unable to fetch journal recommendations right now.',
      ),
      results: [],
    });
  } finally {
    submitButton.disabled = false;
    renderJournalRecommendationResults();
  }
}

function setLocalStatus(kind, message, showSpinner = false) {
  const panel = document.getElementById('local-status');
  if (!panel) {
    return;
  }

  panel.className = `status-panel status-${kind}`;
  panel.innerHTML = '';

  if (showSpinner) {
    panel.appendChild(createLoader(''));
  }

  const text = document.createElement('span');
  text.textContent = message;
  panel.appendChild(text);
}

function setLocalChatLocked(locked) {
  const form = document.getElementById('local-form');
  const input = document.getElementById('local-question');
  const submit = form?.querySelector("button[type='submit']");
  const chat = document.getElementById('local-chat');
  const note = document.getElementById('local-chat-lock-note');

  if (!form || !input || !submit || !chat || !note) {
    return;
  }

  input.disabled = locked;
  submit.disabled = locked;
  chat.classList.toggle('chat-disabled', locked);

  if (locked) {
    input.placeholder = 'Select a scanned book to start a conversation...';
    note.textContent = 'Locked until a book is scanned.';
  } else {
    input.placeholder = 'Ask a question about this book...';
    note.textContent = 'Book ready. Ask your question below.';
  }
}

function renderLibraryModal() {
  const root = document.getElementById('library-modal-root');
  if (!root) {
    return;
  }

  const state = getState();
  root.innerHTML = '';

  if (!state.isLibraryModalOpen) {
    return;
  }

  const modal = createLibraryModal({
    books: state.libraryBooks,
    total: state.libraryTotal,
    query: state.libraryQuery,
    selectedUid: state.selectedLibraryBook?.uid || '',
    loading: state.libraryLoading,
    error: state.libraryError,
    onClose: closeLibraryModal,
    onSearch: (query) => {
      setLibraryQuery(query);
      loadLibraryBooks(query);
    },
    onPick: async (uid) => {
      if (libraryBookFetchController) {
        libraryBookFetchController.abort();
      }
      libraryBookFetchController = new AbortController();
      try {
        const book = await fetchLibraryBook(uid, {
          signal: libraryBookFetchController.signal,
        });
        setSelectedLibraryBook(book);
      } catch (error) {
        if (error.code !== 'ABORTED') {
          setLibraryError(
            getFriendlyRequestError(
              error,
              'Failed to fetch selected book details.',
            ),
          );
        }
      } finally {
        libraryBookFetchController = null;
      }
      renderLibraryModal();
    },
    onSelect: applySelectedBook,
  });

  root.appendChild(modal);
}

async function loadLibraryBooks(query = '') {
  if (libraryFetchController) {
    libraryFetchController.abort();
  }
  libraryFetchController = new AbortController();

  setLibraryLoading(true);
  setLibraryError('');
  renderLibraryModal();

  try {
    const data = await fetchLibrary(query, 1, 60, {
      signal: libraryFetchController.signal,
    });
    setLibraryData({ items: data.items || [], total: data.total || 0 });
  } catch (error) {
    setLibraryData({ items: [], total: 0 });
    if (error.code !== 'ABORTED') {
      setLibraryError(
        getFriendlyRequestError(error, 'Unable to load library right now.'),
      );
    }
  } finally {
    libraryFetchController = null;
    setLibraryLoading(false);
    renderLibraryModal();
  }
}

function openLibraryModal(initialQuery = '') {
  setLibraryModalOpen(true);
  if (initialQuery !== undefined) {
    setLibraryQuery(initialQuery);
  }
  renderLibraryModal();
  loadLibraryBooks(getState().libraryQuery || '');
}

function closeLibraryModal() {
  if (libraryFetchController) {
    libraryFetchController.abort();
    libraryFetchController = null;
  }
  if (libraryBookFetchController) {
    libraryBookFetchController.abort();
    libraryBookFetchController = null;
  }
  setLibraryModalOpen(false);
  renderLibraryModal();
}

function applySelectedBook() {
  const selected = getState().selectedLibraryBook;
  if (!selected) {
    return;
  }

  stopLocalPolling();
  setState({ activeBook: selected.uid });
  setLocalChatLocked(false);
  setLocalStatus('ok', `Selected book: ${selected.title} (${selected.author})`);
  closeLibraryModal();
}

async function pollLocalBookSession() {
  const selected = getState().selectedLibraryBook;
  if (selected) {
    setState({ activeBook: selected.uid });
    setLocalStatus(
      'ok',
      `Selected book: ${selected.title} (${selected.author})`,
    );
    setLocalChatLocked(false);
    return;
  }

  try {
    const result = await fetchSession();
    localPollingFailureCount = 0;
    const activeBook = result?.active_book || null;
    setState({ activeBook });

    if (activeBook) {
      setLocalStatus('ok', `Book scanned: ${activeBook}`);
      setLocalChatLocked(false);
      if (localPollingTimer) {
        clearInterval(localPollingTimer);
        localPollingTimer = null;
      }
    } else {
      // Streamlit used a timed rerun until book scan exists; this polling mirrors it.
      setLocalStatus('warn', 'Please scan a book to begin...', true);
      setLocalChatLocked(true);
    }
  } catch (error) {
    localPollingFailureCount += 1;

    if (localPollingFailureCount >= MAX_LOCAL_POLL_FAILURES) {
      setLocalStatus(
        'warn',
        'Session check is unstable. Select a book from Explore Library to continue.',
      );
      setLocalChatLocked(true);
      stopLocalPolling();
      return;
    }

    setLocalStatus(
      'warn',
      getFriendlyRequestError(error, 'Waiting for book scan...'),
    );
    setLocalChatLocked(true);
  }
}

function startLocalPolling() {
  if (localPollingTimer) {
    clearInterval(localPollingTimer);
  }

  localPollingFailureCount = 0;

  pollLocalBookSession();
  localPollingTimer = window.setInterval(pollLocalBookSession, 2000);
}

function stopLocalPolling() {
  if (localPollingTimer) {
    clearInterval(localPollingTimer);
    localPollingTimer = null;
  }
  localPollingFailureCount = 0;
}

function setupPageState(route) {
  if (route === '/local') {
    setState({ selectedMode: 'local' });
    const selected = getState().selectedLibraryBook;
    if (selected) {
      setState({ activeBook: selected.uid });
      setLocalStatus(
        'ok',
        `Selected book: ${selected.title} (${selected.author})`,
      );
      setLocalChatLocked(false);
      stopLocalPolling();
    } else {
      setLocalChatLocked(true);
      startLocalPolling();
    }

    const chat = document.getElementById('local-chat');
    if (chat) {
      renderMessages(chat, getState().localChat);
    }

    renderLibraryModal();
  } else if (route === '/web') {
    setState({ selectedMode: 'web' });
    stopLocalPolling();

    const chat = document.getElementById('web-chat');
    if (chat) {
      renderMessages(chat, getState().webChat);
    }
  } else if (route === '/book_rec') {
    setState({ selectedMode: 'book_rec' });
    stopLocalPolling();
    renderRecommendationResults();
  } else if (route === '/journal_rec') {
    setState({ selectedMode: 'journal_rec' });
    stopLocalPolling();
    renderJournalRecommendationResults();
  } else {
    setState({ selectedMode: '' });
    stopLocalPolling();
  }
}

async function submitQuestion(mode, formElement) {
  const input = formElement.querySelector("input[name='question']");
  const submitButton = formElement.querySelector("button[type='submit']");
  const chatId = mode === 'local' ? 'local-chat' : 'web-chat';
  const chatContainer = document.getElementById(chatId);
  const question = input.value.trim();

  if (!question || !chatContainer) {
    return;
  }

  addChatMessage(mode, 'user', question);
  setState({ query: question });
  renderMessages(
    chatContainer,
    mode === 'local' ? getState().localChat : getState().webChat,
  );

  input.value = '';
  input.focus();
  submitButton.disabled = true;

  // Show loading indicator for long-running requests.
  if (mode === 'web' || mode === 'local') {
    if (mode === 'web') {
      setWebLoading(true);
    }
    addChatMessage(mode, 'assistant', '...');
    renderMessages(
      chatContainer,
      mode === 'local' ? getState().localChat : getState().webChat,
    );
  }

  try {
    const activeBookRef = mode === 'local' ? getState().activeBook : null;
    const response =
      mode === 'local'
        ? await askQuestion(question, activeBookRef)
        : await askWebQuestion(question);
    setApiResults(response);

    // Remove loading indicator and add real response
    if (mode === 'web' || mode === 'local') {
      if (mode === 'web') {
        setWebLoading(false);
      }
      removeLoadingMessage(mode);
    }

    const answer = response?.answer || 'No answer';
    const confidence = response?.confidence;
    const assistantMessage =
      confidence === null || confidence === undefined
        ? answer
        : `${answer}\n\nConfidence: ${confidence}`;
    addChatMessage(mode, 'assistant', assistantMessage);
  } catch (error) {
    if (mode === 'web' || mode === 'local') {
      if (mode === 'web') {
        setWebLoading(false);
      }
      removeLoadingMessage(mode);
    }
    addChatMessage(
      mode,
      'assistant',
      getFriendlyRequestError(error, 'Backend error while answering.'),
    );
  } finally {
    renderMessages(
      chatContainer,
      mode === 'local' ? getState().localChat : getState().webChat,
    );
    submitButton.disabled = false;
  }
}

function wireGlobalEvents() {
  pageRoot.addEventListener('click', (event) => {
    const routeButton = event.target.closest('[data-route]');
    if (routeButton) {
      const route = routeButton.dataset.route;
      window.location.hash = route === 'home' ? '#/' : `#/${route}`;
      return;
    }

    const actionButton = event.target.closest("[data-action='back']");
    if (actionButton) {
      const mode = actionButton.dataset.mode;
      clearChat(mode);
      window.location.hash = '#/';
      return;
    }

    const ctaButton = event.target.closest("[data-action='start-demo']");
    if (ctaButton) {
      window.location.hash = '#/web';
      return;
    }

    const topicButton = event.target.closest('[data-rec-topic]');
    if (topicButton) {
      const prompt = topicButton.dataset.recTopic || '';
      const input = document.getElementById('book-rec-question');
      if (input) {
        input.value = prompt;
        input.focus();
      }
      return;
    }

    const journalTopicButton = event.target.closest('[data-journal-topic]');
    if (journalTopicButton) {
      const prompt = journalTopicButton.dataset.journalTopic || '';
      const input = document.getElementById('journal-rec-question');
      if (input) {
        input.value = prompt;
        input.focus();
      }
      return;
    }

    const filterButton = event.target.closest('[data-journal-filter]');
    if (filterButton) {
      const filter = filterButton.dataset.journalFilter || 'all';
      applyJournalFilter(filter);
      return;
    }

    const exploreLibraryButton = event.target.closest(
      "[data-action='open-library']",
    );
    if (exploreLibraryButton) {
      const searchInput = document.getElementById('local-book-search');
      const initialQuery = searchInput?.value?.trim() || '';
      openLibraryModal(initialQuery);
      return;
    }

    const findLibraryButton = event.target.closest(
      "[data-action='find-library']",
    );
    if (findLibraryButton) {
      const searchInput = document.getElementById('local-book-search');
      const initialQuery = searchInput?.value?.trim() || '';
      openLibraryModal(initialQuery);
    }
  });

  pageRoot.addEventListener('submit', (event) => {
    if (!(event.target instanceof HTMLFormElement)) {
      return;
    }

    event.preventDefault();

    if (event.target.id === 'local-form') {
      submitQuestion('local', event.target);
    } else if (event.target.id === 'web-form') {
      submitQuestion('web', event.target);
    } else if (event.target.id === 'book-rec-form') {
      submitRecommendation(event.target);
    } else if (event.target.id === 'journal-rec-form') {
      submitJournalRecommendation(event.target);
    }
  });
}

function bootstrap() {
  const navbar = createNavbar({
    onThemeToggle: () => {
      const nextTheme = getState().theme === 'light' ? 'dark' : 'light';
      setTheme(nextTheme);
      applyThemeToDom();
    },
  });

  navbarRoot.appendChild(navbar);
  applyThemeToDom();
  wireGlobalEvents();

  initRouter({
    root: pageRoot,
    onRouteReady: (route) => {
      applyPageStyles(route);
      const navLinks = navbarRoot.querySelector("[data-role='links']");
      const menuButton = navbarRoot.querySelector("[data-action='menu']");
      if (navLinks && menuButton) {
        navLinks.classList.remove('is-open');
        menuButton.setAttribute('aria-expanded', 'false');
      }
      setupPageState(route);
    },
  });
}

bootstrap();
