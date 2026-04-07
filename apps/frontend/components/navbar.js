export function createNavbar({ onThemeToggle }) {
  const nav = document.createElement('nav');
  nav.className = 'navbar';
  nav.innerHTML = `
    <a class="brand" href="#/" aria-label="Go to home page">
      <span class="brand-mark">AC</span>
      <span>AcadClarifier</span>
    </a>
    <button class="nav-toggle" type="button" data-action="menu" aria-expanded="false" aria-label="Toggle navigation menu">
      Menu
    </button>
    <div class="nav-links" data-role="links">
      <a class="nav-link" href="#/">Home</a>
      <a class="nav-link" href="#/local">Book Retrieval</a>
      <a class="nav-link" href="#/book_rec">Recommendations</a>
      <a class="nav-link" href="#/web">Web Retrieval</a>
    </div>
    <div class="nav-actions">
      <button type="button" data-action="admin">Admin</button>
      <button type="button" data-action="theme">Theme</button>
    </div>
  `;

  const menuButton = nav.querySelector("[data-action='menu']");
  const links = nav.querySelector("[data-role='links']");

  nav.addEventListener('click', (event) => {
    const trigger = event.target.closest('button');
    if (!trigger) {
      return;
    }

    const action = trigger.dataset.action;
    if (action === 'admin') {
      // Streamlit had an admin page placeholder; keep the same behavior lightweight.
      alert(
        'Admin dashboard will be added here.\nFuture: logs, book manager, settings.',
      );
    } else if (action === 'theme') {
      onThemeToggle();
    } else if (action === 'menu' && menuButton && links) {
      const isOpen = links.classList.toggle('is-open');
      menuButton.setAttribute('aria-expanded', String(isOpen));
    }
  });

  return nav;
}
