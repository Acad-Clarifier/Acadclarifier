function normalizeRoute(hash) {
  if (!hash || hash === '#' || hash === '#/') {
    return '/';
  }

  const normalized = hash.startsWith('#') ? hash.slice(1) : hash;
  return normalized.startsWith('/') ? normalized : `/${normalized}`;
}

function routeToPagePath(route) {
  if (route === '/') {
    return './pages/home.html';
  }

  const slug = route.replace(/^\//, '');
  return `./pages/${slug}.html`;
}

async function loadPage(root, route) {
  const pagePath = routeToPagePath(route);
  try {
    const response = await fetch(pagePath, { cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`Route not found: ${route}`);
    }

    root.innerHTML = await response.text();
    return true;
  } catch (_error) {
    root.innerHTML = `<section class="page"><h2 class="page-title">Page not found</h2><p class="caption">Route: ${route}</p></section>`;
    return false;
  }
}

export function initRouter({ root, onRouteReady }) {
  async function handleRouteChange() {
    const route = normalizeRoute(window.location.hash);
    await loadPage(root, route);
    onRouteReady(route);
  }

  window.addEventListener('hashchange', handleRouteChange);
  handleRouteChange();
}
