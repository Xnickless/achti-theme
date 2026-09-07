/* Kółka „Inne kolory tego modelu”: podmiana produktu bez przeładowania strony.
   Pobiera sekcje (main-product, quick-order-list) drugiego produktu przez Section Rendering API
   i podmienia je w miejscu; adres i tytuł aktualizowane przez history API. */
(function () {
  const SECTION_SUFFIXES = ['__main', '__quick-order-list'];
  let busy = false;
  const titleSuffix = document.title.includes(' – ') ? document.title.slice(document.title.lastIndexOf(' – ')) : '';

  function sectionsToSwap(fromEl) {
    const main = fromEl.closest('.shopify-section');
    if (!main) return [];
    const base = main.id.replace('shopify-section-', '').replace(/__main$/, '');
    return SECTION_SUFFIXES.map((s) => document.getElementById('shopify-section-' + base + s)).filter(Boolean);
  }

  async function swapTo(url, sections) {
    const results = await Promise.all(
      sections.map(async (sec) => {
        const id = sec.id.replace('shopify-section-', '');
        const res = await fetch(url.pathname + '?section_id=' + encodeURIComponent(id), { headers: { Accept: 'text/html' } });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return [sec, await res.text()];
      })
    );
    results.forEach(([sec, html]) => {
      const doc = new DOMParser().parseFromString(html, 'text/html');
      const fresh = doc.getElementById(sec.id) || doc.body;
      sec.innerHTML = fresh.innerHTML;
    });
  }

  document.addEventListener('click', async (e) => {
    const a = e.target.closest('a.model-colors__circle');
    if (!a || busy || e.metaKey || e.ctrlKey || e.shiftKey) return;
    const sections = sectionsToSwap(a);
    if (!sections.length) return;
    e.preventDefault();
    busy = true;
    const url = new URL(a.href, location.origin);
    const main = sections[0];
    main.classList.add('model-colors-loading');
    try {
      await swapTo(url, sections);
      history.pushState({ modelColors: true }, '', url.pathname);
      const title = main.querySelector('.product__title h1, .product__title');
      if (title) document.title = title.textContent.trim() + titleSuffix;
      const header = document.querySelector('.section-header');
      const top = main.getBoundingClientRect().top + window.scrollY - (header ? header.offsetHeight : 0) - 8;
      if (window.scrollY > top) window.scrollTo({ top, behavior: 'smooth' });
    } catch (err) {
      location.href = a.href; // awaryjnie: zwykłe przejście
    } finally {
      main.classList.remove('model-colors-loading');
      busy = false;
    }
  });

  window.addEventListener('popstate', (e) => {
    if (e.state && e.state.modelColors) location.reload();
    else if (history.state === null && document.querySelector('.model-colors')) location.reload();
  });
})();
