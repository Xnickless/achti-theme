/* Typografia PL (Achti B2B): jednoliterowe spójniki i przyimki (a, i, o, u, w, z) nie zostają na końcu linii —
   po takim słowie wstawiamy twardą spację. Działa na tekstach treści (opisy, nagłówki, karty), nie rusza formularzy ani skryptów. */
(function () {
  var RX = /(^|[\s(„"'>])([aiouwzAIOUWZ])[ \t]+(?=\S)/g;
  var SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, SELECT: 1, OPTION: 1, CODE: 1, PRE: 1, NOSCRIPT: 1 };
  function fix(root) {
    if (!root || !root.querySelectorAll) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        var p = n.parentNode;
        if (!p || SKIP[p.nodeName] || p.closest('form, .no-typo')) return NodeFilter.FILTER_REJECT;
        return n.nodeValue.length > 2 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (n) {
      var v = n.nodeValue;
      var out = v.replace(RX, function (m, pre, letter) { return pre + letter + ' '; });
      if (out !== v) n.nodeValue = out;
    });
  }
  function run() {
    document.querySelectorAll('main, .footer, .announcement-bar').forEach(fix);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
  // treść dogrywana później (doładowanie listingu, podmiana koloru modelu, wyniki podpowiedzi)
  var pending = null;
  new MutationObserver(function (muts) {
    if (pending) return;
    pending = setTimeout(function () {
      pending = null;
      muts.forEach(function (m) {
        m.addedNodes.forEach(function (n) { if (n.nodeType === 1) fix(n); });
      });
    }, 50);
  }).observe(document.body, { childList: true, subtree: true });
})();
