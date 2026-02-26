/* ── Metazooa/Metaflora Shared Utilities ───────────── */
(function() {
  'use strict';

  /* ── Wikipedia cache ─────────────────────────────── */
  const wikiCache = new Map(); /* name → { extract, thumb } | null | undefined */
  const wikiFetching = new Map(); /* name → [callback, ...] */

  function truncateSentences(text, max) {
    const sentences = text.match(/[^.!?]*[.!?]+/g) || [text];
    let result = '';
    for (let i = 0; i < Math.min(sentences.length, max); i++) {
      result += sentences[i];
    }
    return result.trim() || text.slice(0, 200);
  }

  function highlightMatch(text, query) {
    const i = text.toLowerCase().indexOf(query.toLowerCase());
    if (i < 0) return text;
    return text.slice(0, i) + '<span class="sr-match">' + text.slice(i, i + query.length) + '</span>' + text.slice(i + query.length);
  }

  /* ── Tree initializer ────────────────────────────── */
  async function initTree(game) {
    const dataFile = game === 'metaflora' ? 'species-metaflora.json' : 'species-metazooa.json';
    const resp = await fetch(dataFile);
    const treeData = await resp.json();

    const root = d3.hierarchy(treeData);
    let uid = 0;
    root.each(n => { n._uid = uid++; });
    const allNodes = root.descendants();
    const allLinks = root.links();
    const labeledNodes = allNodes.filter(n => n.data.label);
    const totalLabeled = labeledNodes.length;

    const uidToNode = new Map();
    allNodes.forEach(n => uidToNode.set(n._uid, n));
    const nameToNode = new Map();
    allNodes.forEach(n => nameToNode.set(n.data.name, n));
    const labelToNode = new Map();
    labeledNodes.forEach(n => labelToNode.set(n.data.label, n));

    return { root, allNodes, allLinks, labeledNodes, totalLabeled, uidToNode, nameToNode, labelToNode };
  }

  /* ── Ancestor helpers ────────────────────────────── */
  function ancestors(node) {
    const a = []; let n = node;
    while (n) { a.push(n); n = n.parent; }
    return a;
  }

  function lca(a, b) {
    const sa = new Set(ancestors(a).map(n => n._uid));
    let n = b;
    while (n) { if (sa.has(n._uid)) return n; n = n.parent; }
    return a; /* fallback: should not happen in same tree */
  }

  function pathBetween(a, b) {
    const l = lca(a, b);
    const s = new Set();
    let n = a; while (n) { s.add(n._uid); if (n._uid === l._uid) break; n = n.parent; }
    n = b; while (n) { s.add(n._uid); if (n._uid === l._uid) break; n = n.parent; }
    return s;
  }

  function ancestryPath(node) {
    return ancestors(node).reverse().map(n => n.data.label || n.data.name);
  }

  function isDescendantOf(node, ancestor) {
    let n = node;
    while (n) { if (n._uid === ancestor._uid) return true; n = n.parent; }
    return false;
  }

  /* ── Wikipedia fetcher ───────────────────────────── */
  /* callback(entry) is called once when data arrives.
     entry = { extract, thumb } | null
     If name already cached, callback is called immediately. */
  function fetchWiki(name, callback) {
    if (wikiCache.has(name)) {
      if (callback) callback(wikiCache.get(name));
      return;
    }
    if (wikiFetching.has(name)) {
      /* Already fetching — queue callback */
      if (callback) wikiFetching.get(name).push(callback);
      return;
    }
    const callbacks = callback ? [callback] : [];
    wikiFetching.set(name, callbacks);

    (async () => {
      try {
        const url = 'https://en.wikipedia.org/api/rest_v1/page/summary/' + encodeURIComponent(name);
        const resp = await fetch(url);
        if (!resp.ok) {
          wikiCache.set(name, null);
        } else {
          const data = await resp.json();
          if (data.type === 'disambiguation' || !data.extract) {
            wikiCache.set(name, null);
          } else {
            wikiCache.set(name, {
              extract: truncateSentences(data.extract, 2),
              thumb: data.thumbnail ? data.thumbnail.source : null
            });
          }
        }
      } catch (e) {
        wikiCache.set(name, null);
      }
      const cbs = wikiFetching.get(name) || [];
      wikiFetching.delete(name);
      const result = wikiCache.get(name);
      cbs.forEach(cb => cb(result));
    })();
  }

  /* ── Toast ───────────────────────────────────────── */
  let toastTimer;
  function showToast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2000);
  }

  /* ── Export ──────────────────────────────────────── */
  window.MetazooaShared = {
    initTree,
    ancestors,
    lca,
    pathBetween,
    ancestryPath,
    isDescendantOf,
    truncateSentences,
    highlightMatch,
    wikiCache,
    fetchWiki,
    showToast
  };
})();
