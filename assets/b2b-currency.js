/* Achti B2B: podgląd cen w innej walucie (PLN / EUR / USD).
   Przelicznik jest orientacyjny — koszyk i zamówienie zostają w walucie sklepu.
   Kursy: api.frankfurter.app (Europejski Bank Centralny), zapisane w localStorage na 12 h,
   z awaryjnymi kursami zaszytymi w pliku, gdy API nie odpowie. */
(function () {
  var STORAGE_RATES = 'achti-currency-rates';
  var STORAGE_PICK = 'achti-currency';
  var MAX_AGE = 12 * 60 * 60 * 1000;
  var BASE = (window.Shopify && window.Shopify.currency && window.Shopify.currency.active) || 'PLN';
  var LOCALES = { PLN: 'pl-PL', EUR: 'de-DE', USD: 'en-US' };
  // awaryjne kursy za 1 PLN (stan 11.09.2026) — używane tylko, gdy nie uda się pobrać aktualnych
  var FALLBACK = { PLN: 1, EUR: 0.235, USD: 0.256 };
  var TOKENS = { 'zł': 'PLN', PLN: 'PLN', '€': 'EUR', EUR: 'EUR', $: 'USD', USD: 'USD' };
  var MONEY = /(zł|PLN|€|EUR|\$|USD)?\s?(\d{1,3}(?:[\s  .]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s?(zł|PLN|€|EUR|\$|USD)?/g;
  var SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, NOSCRIPT: 1, SELECT: 1, OPTION: 1 };

  var rates = null;
  var current = BASE;
  var originals = new WeakMap();
  var observer = null;

  function readRates() {
    try {
      var raw = JSON.parse(localStorage.getItem(STORAGE_RATES) || 'null');
      if (raw && raw.base === BASE && Date.now() - raw.time < MAX_AGE) return raw.rates;
    } catch (e) { /* brak dostępu do localStorage */ }
    return null;
  }

  function fetchRates() {
    var cached = readRates();
    if (cached) { rates = cached; return Promise.resolve(rates); }
    var want = Object.keys(LOCALES).filter(function (c) { return c !== BASE; });
    return fetch('https://api.frankfurter.app/latest?from=' + BASE + '&to=' + want.join(','))
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (d) {
        var out = {};
        out[BASE] = 1;
        Object.keys(d.rates || {}).forEach(function (c) { out[c] = d.rates[c]; });
        if (!out.EUR || !out.USD) throw new Error('brak kursów');
        rates = out;
        try { localStorage.setItem(STORAGE_RATES, JSON.stringify({ base: BASE, time: Date.now(), rates: out })); } catch (e) { /* ignoruj */ }
        return rates;
      })
      .catch(function () {
        var out = {};
        Object.keys(FALLBACK).forEach(function (c) { out[c] = FALLBACK[c] / (FALLBACK[BASE] || 1); });
        rates = out;
        return rates;
      });
  }

  function toNumber(text) {
    var s = text.replace(/[\s  ]/g, '');
    var comma = s.lastIndexOf(',');
    var dot = s.lastIndexOf('.');
    var cut = Math.max(comma, dot);
    if (cut > -1 && s.length - cut - 1 <= 2) {
      return parseFloat(s.slice(0, cut).replace(/[.,]/g, '') + '.' + s.slice(cut + 1));
    }
    return parseFloat(s.replace(/[.,]/g, ''));
  }

  function format(value, code) {
    try {
      return new Intl.NumberFormat(LOCALES[code] || 'pl-PL', {
        style: 'currency', currency: code, minimumFractionDigits: 2, maximumFractionDigits: 2,
      }).format(value);
    } catch (e) {
      return value.toFixed(2) + ' ' + code;
    }
  }

  function convertText(text, code) {
    return text.replace(MONEY, function (match, pre, num, post) {
      var from = TOKENS[pre] || TOKENS[post];
      if (!from || !rates || !rates[from] || !rates[code]) return match;
      var value = toNumber(num);
      if (!isFinite(value)) return match;
      return format((value / rates[from]) * rates[code], code);
    });
  }

  function nodes(root) {
    var out = [];
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue || node.nodeValue.length > 200) return NodeFilter.FILTER_REJECT;
        if (!/\d/.test(node.nodeValue)) return NodeFilter.FILTER_REJECT;
        if (!/(zł|PLN|€|EUR|\$|USD)/.test(node.nodeValue)) return NodeFilter.FILTER_REJECT;
        var parent = node.parentElement;
        if (!parent || SKIP[parent.tagName]) return NodeFilter.FILTER_REJECT;
        if (parent.closest('.b2b-currency')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    var n;
    while ((n = walker.nextNode())) out.push(n);
    return out;
  }

  function paint(root) {
    var scope = root || document.body;
    nodes(scope).forEach(function (node) {
      if (!originals.has(node)) originals.set(node, node.nodeValue);
      var source = originals.get(node);
      node.nodeValue = current === BASE ? source : convertText(source, current);
    });
  }

  function watch() {
    if (observer) return;
    observer = new MutationObserver(function (list) {
      if (current === BASE) return;
      list.forEach(function (m) {
        m.addedNodes.forEach(function (node) {
          if (node.nodeType === 1) { paint(node); if (node.querySelector && node.querySelector('[name="checkout"]')) cartNote(); }
          else if (node.nodeType === 3 && node.parentElement) paint(node.parentElement);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function cartNote() {
    var note = document.querySelector('.b2b-currency__note');
    var text = note ? note.textContent.trim() : '';
    document.querySelectorAll('[name="checkout"]').forEach(function (btn) {
      var host = btn.parentElement;
      if (!host) return;
      var line = host.querySelector('.b2b-currency-cart-note');
      if (current === BASE) { if (line) line.remove(); return; }
      if (!line) {
        line = document.createElement('p');
        line.className = 'b2b-currency-cart-note';
        host.insertBefore(line, btn);
      }
      line.textContent = text;
    });
  }

  function setCurrency(code, remember) {
    current = code;
    document.querySelectorAll('.b2b-currency').forEach(function (el) {
      el.querySelectorAll('[data-currency]').forEach(function (btn) {
        btn.setAttribute('aria-current', btn.dataset.currency === code ? 'true' : 'false');
      });
      var label = el.querySelector('.b2b-currency__value');
      if (label) label.textContent = code;
      el.classList.toggle('b2b-currency--converted', code !== BASE);
    });
    if (remember) {
      try { localStorage.setItem(STORAGE_PICK, code); } catch (e) { /* ignoruj */ }
    }
    paint();
    cartNote();
  }

  function bind(el) {
    var summary = el.querySelector('summary');
    el.querySelectorAll('[data-currency]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        var code = btn.dataset.currency;
        var go = function () { setCurrency(code, true); el.removeAttribute('open'); if (summary) summary.focus(); };
        if (code !== BASE && !rates) fetchRates().then(go);
        else go();
      });
    });
    document.addEventListener('click', function (e) {
      if (el.hasAttribute('open') && !el.contains(e.target)) el.removeAttribute('open');
    });
    el.addEventListener('keyup', function (e) { if (e.key === 'Escape') el.removeAttribute('open'); });
  }

  function init() {
    var widgets = document.querySelectorAll('.b2b-currency');
    if (!widgets.length) return;
    widgets.forEach(bind);
    watch();
    var saved = null;
    try { saved = localStorage.getItem(STORAGE_PICK); } catch (e) { /* ignoruj */ }
    if (saved && saved !== BASE && LOCALES[saved]) fetchRates().then(function () { setCurrency(saved, false); });
    else setCurrency(BASE, false);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
