/* XOMNI site — small interactions only. No frameworks. */
(function () {
  "use strict";

  /* ---------- mobile nav ---------- */
  var toggle = document.getElementById("nav-toggle");
  var nav = document.getElementById("site-nav");

  function closeNav() {
    if (!nav || !toggle) return;
    nav.classList.remove("open");
    toggle.setAttribute("aria-expanded", "false");
  }

  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    // close the menu when a link is chosen
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) closeNav();
    });
    // close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeNav();
    });
  }

  /* ---------- active nav link ---------- */
  (function highlight() {
    var path = window.location.pathname.split("/").pop() || "index.html";
    var key = "index";
    if (path === "install.html") key = "install";
    else if (path === "byo-provider.html") key = "byo";
    else if (path === "sponsorship.html") key = "sponsorship";
    else if (path === "faq.html") key = "faq";
    else if (path === "security.html") key = "security";
    else if (path === "skills.html") key = "skills";
    var links = document.querySelectorAll(".nav-link[data-nav]");
    for (var i = 0; i < links.length; i++) {
      if (links[i].getAttribute("data-nav") === key) links[i].classList.add("active");
    }
  })();

  /* ---------- copy buttons ---------- */
  function fallbackCopy(text, btn) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    if (ok) flashCopied(btn);
  }

  function flashCopied(btn) {
    var old = btn.textContent;
    btn.textContent = "copied ✓";
    btn.classList.add("copied");
    setTimeout(function () {
      btn.textContent = old;
      btn.classList.remove("copied");
    }, 1600);
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest(".copy-btn[data-copy]");
    if (!btn) return;
    var text = btn.getAttribute("data-copy");
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { flashCopied(btn); },
        function () { fallbackCopy(text, btn); }
      );
    } else {
      fallbackCopy(text, btn);
    }
  });

  /* ---------- footer year ---------- */
  var yearEls = document.querySelectorAll("[data-year]");
  var year = String(new Date().getFullYear());
  for (var i = 0; i < yearEls.length; i++) yearEls[i].textContent = year;

  /* ---------- easter egg ---------- */
  console.log(
    "%cXOMNI%c one agent. every feature. every free model. — compose, don't merge.",
    "font-weight:900;font-size:14px;color:#6ea8fe;",
    "color:#8b96b0;"
  );
})();
