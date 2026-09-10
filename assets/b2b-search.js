/* Wyszukiwanie po kodzie produktu (Achti B2B).
   Shopify dopasowuje SKU tylko od początku tokenu („AZ-1145” znajdzie AZ-1145PC, ale samo „1145”, „114”
   czy „az 1145” zwracają 0 wyników). Gdy klient wpisze sam numer (albo „az 1145”, „az1145pc”),
   zamieniamy zapytanie na pełny prefiks „AZ-1145…” — w podpowiedziach (predictive-search.js) i przy wysłaniu formularza. */
(function () {
  var RX = /^(?:az[\s-]*)?(\d{2,})([a-z0-9-]*)$/i;
  function normalize(q) {
    var m = (q || '').trim().match(RX);
    return m ? 'AZ-' + m[1] + m[2].toUpperCase() : null;
  }
  window.b2bNormalizeSearch = normalize;
  document.addEventListener(
    'submit',
    function (e) {
      var form = e.target;
      if (!form || !form.action || form.action.indexOf('/search') === -1) return;
      var input = form.querySelector('input[name="q"]');
      if (!input) return;
      var n = normalize(input.value);
      if (n) input.value = n;
    },
    true
  );
})();
