/* XOMNI docs search — zero-network, framework-free client-side filter.
 * Only activates on pages that include the #docsSearch box (docs/install.html).
 * Fetches docs-index.json (relative: docs/ -> website root), then filters
 * title + headings + summary by substring on every keystroke. Top 10 results.
 */
(function () {
  "use strict";

  var root = document.getElementById("docsSearch");
  if (!root) return;

  var input = document.getElementById("docsSearchInput");
  var resultsEl = document.getElementById("docsResults");
  var statusEl = document.getElementById("docsSearchStatus");
  if (!input || !resultsEl || !statusEl) return;

  var INDEX_URL = "../docs-index.json"; // resolved relative to this page (docs/)
  var MAX_RESULTS = 10;

  var pages = [];
  var debounce = null;

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function setStatus(msg) {
    statusEl.textContent = msg || "";
  }

  function haystack(p) {
    return (p.title + " " + p.headings.join(" ") + " " + p.summary).toLowerCase();
  }

  function rank(p, q) {
    var t = p.title.toLowerCase();
    if (t.indexOf(q) === 0) return 0;       // title prefix
    if (t.indexOf(q) !== -1) return 1;      // title contains
    if (p.headings.join(" ").toLowerCase().indexOf(q) !== -1) return 2; // heading
    return 3;                                // summary-only
  }

  function render(query) {
    var q = query.trim().toLowerCase();
    resultsEl.innerHTML = "";
    if (!q) {
      setStatus(pages.length ? "Type to search " + pages.length + " docs pages." : "");
      return;
    }
    var hits = [];
    for (var i = 0; i < pages.length; i++) {
      if (haystack(pages[i]).indexOf(q) !== -1) hits.push(pages[i]);
    }
    hits.sort(function (a, b) { return rank(a, q) - rank(b, q); });
    var top = hits.slice(0, MAX_RESULTS);

    for (var j = 0; j < top.length; j++) {
      var p = top[j];
      var a = el("a");
      a.href = p.path;
      a.appendChild(el("span", "t", p.title));
      if (p.summary) a.appendChild(el("span", "s", p.summary));
      var headingHit = null;
      for (var k = 0; k < p.headings.length; k++) {
        if (p.headings[k].toLowerCase().indexOf(q) !== -1) { headingHit = p.headings[k]; break; }
      }
      if (headingHit) a.appendChild(el("span", "h", "\u25B8 " + headingHit));
      var li = el("li");
      li.appendChild(a);
      resultsEl.appendChild(li);
    }

    if (top.length) {
      setStatus(top.length + (hits.length > top.length ? " of " + hits.length : "") +
        " result" + (hits.length === 1 ? "" : "s") + ".");
    } else {
      setStatus("No results for \u201C" + query.trim() + "\u201D.");
    }
  }

  input.addEventListener("input", function () {
    clearTimeout(debounce);
    debounce = setTimeout(function () { render(input.value); }, 60);
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      input.value = "";
      render("");
      input.focus();
    }
  });

  fetch(INDEX_URL, { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (data) {
      pages = data && Array.isArray(data.pages) ? data.pages : [];
      setStatus("Search ready \u2014 " + pages.length + " docs pages indexed.");
    })
    .catch(function (err) {
      setStatus("Docs search unavailable (" + err.message + ").");
      input.disabled = true;
    });
})();
