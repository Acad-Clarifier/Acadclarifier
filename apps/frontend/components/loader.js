export function createLoader(text = 'Loading...') {
  const wrapper = document.createElement('div');
  wrapper.setAttribute('role', 'status');
  wrapper.setAttribute('aria-live', 'polite');
  wrapper.innerHTML = `<span class="loader" aria-hidden="true"></span>${text}`;
  return wrapper;
}
