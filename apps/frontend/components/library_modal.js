function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function renderBookCard(book, selectedUid) {
  const selected = selectedUid === book.uid;
  return `
    <button class="library-item${selected ? ' is-selected' : ''}" type="button" data-action="library-pick" data-uid="${escapeHtml(book.uid)}" aria-pressed="${selected ? 'true' : 'false'}">
      <span class="library-item-bullet" aria-hidden="true"></span>
      <div class="library-item-main">
        <h3 class="library-item-title">${escapeHtml(book.title)}</h3>
        <p class="library-item-sub">${escapeHtml(book.author)}${book.publishedYear ? ` • ${escapeHtml(String(book.publishedYear))}` : ''}</p>
      </div>
      <span class="library-item-tag">${escapeHtml(book.topic || 'General')}</span>
    </button>
  `;
}

export function createLibraryModal({
  books,
  total,
  query,
  selectedUid,
  loading,
  error,
  onClose,
  onSearch,
  onPick,
  onSelect,
}) {
  const wrapper = document.createElement('section');
  wrapper.className = 'library-modal';
  wrapper.setAttribute('role', 'dialog');
  wrapper.setAttribute('aria-modal', 'true');
  wrapper.setAttribute('aria-labelledby', 'library-modal-title');

  const content = loading
    ? '<div class="library-modal-empty">Loading library...</div>'
    : error
      ? `<div class="library-modal-empty">${escapeHtml(error)}</div>`
      : books.length
        ? books.map((book) => renderBookCard(book, selectedUid)).join('')
        : '<div class="library-modal-empty">No books found for this query.</div>';

  wrapper.innerHTML = `
    <div class="library-modal-backdrop" data-action="library-close"></div>
    <div class="library-modal-panel">
      <header class="library-modal-header">
        <div>
          <h2 id="library-modal-title">Explore Library</h2>
          <p>Select a book to start contextual Q and A.</p>
        </div>
        <button class="secondary-btn" type="button" data-action="library-close">Close</button>
      </header>

      <form class="library-search-row" id="library-search-form">
        <input id="library-modal-search" type="text" value="${escapeHtml(query)}" placeholder="Search title, author, ISBN, or topic" autocomplete="off" />
        <button class="primary-btn" type="submit">Search</button>
      </form>

      <p class="library-modal-meta">${loading ? 'Loading...' : `${total} books available`}</p>

      <div class="library-list">${content}</div>

      <footer class="library-modal-footer">
        <button class="primary-btn" type="button" data-action="library-select" ${selectedUid ? '' : 'disabled'}>
          Select Book
        </button>
      </footer>
    </div>
  `;

  wrapper.addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'library-close') {
      onClose();
      return;
    }

    if (action === 'library-pick') {
      const uid = event.target.closest('[data-uid]')?.dataset.uid;
      if (uid) {
        onPick(uid);
      }
      return;
    }

    if (action === 'library-select') {
      onSelect();
    }
  });

  wrapper
    .querySelector('#library-search-form')
    .addEventListener('submit', (event) => {
      event.preventDefault();
      const searchInput = wrapper.querySelector('#library-modal-search');
      onSearch(searchInput.value.trim());
    });

  return wrapper;
}
