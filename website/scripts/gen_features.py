#!/usr/bin/env python3
"""XOMNI features site generator.

Consumes <repo>/docs/FEATURES.md (the master feature matrix) and emits:

  website/features.html - self-contained "XOMNI FEATURES" page rendering the
                          matrix tables in the flagship docs-page style.

Usage:  python scripts/gen_features.py
"""

from __future__ import annotations

import html
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FEATURES_MD = REPO_ROOT / "docs" / "FEATURES.md"
WEBSITE_DIR = REPO_ROOT / "website"
OUT_HTML = WEBSITE_DIR / "features.html"

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Features — XOMNI Docs</title>
<meta name="description" content="XOMNI feature matrix: 35 plugins, 1142 tests, every feature of every source repo, tracked.">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="stylesheet" href="css/style.css">

<style>
/* ===== flagship void/emerald token aliases (map to css/style.css palette) ===== */
:root{
  --font-sans:var(--sans);--font-mono:var(--mono);
  --radius-1:6px;--dur-fast:150ms;--dur-med:300ms;--ease-out-expo:cubic-bezier(.16,1,.3,1);
  --surface-1:var(--bg-soft);--surface-2:var(--panel);--elevated:var(--card);
  --ink:var(--text);--faint:#7B828A;
  --accent-hover:#00FFB0;--accent-dim:var(--accent2);--success:var(--green);--danger:var(--red);--warning:var(--amber);
}
/* ===== flagship nav ===== */
html{scroll-behavior:smooth}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
::selection{background:color-mix(in srgb,var(--accent) 35%,transparent)}
.skip-link{position:absolute;left:-999px;top:0;background:var(--accent);color:#000;padding:10px 16px;z-index:100;border-radius:0 0 var(--radius-1) 0}
.skip-link:focus{left:0}
header.site-nav{display:block;position:sticky;top:0;z-index:50;background:var(--bg);border-bottom:1px solid var(--border);transition:box-shadow var(--dur-med),border-color var(--dur-med)}
header.site-nav.scrolled{box-shadow:0 8px 24px rgba(0,0,0,.5)}
.nav-inner{max-width:1200px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;gap:24px}
.wordmark{font-family:var(--font-mono);font-weight:700;font-size:17px;letter-spacing:.12em;color:var(--accent)}
.wordmark:hover{text-decoration:none}
.wordmark span{color:var(--ink)}
.nav-links{display:flex;gap:4px;margin-left:auto;align-items:center;flex-wrap:wrap}
.nav-links a{padding:8px 12px;border-radius:var(--radius-1);color:var(--muted);font-size:14px;position:relative;transition:color var(--dur-fast)}
.nav-links a::after{content:"";position:absolute;left:12px;right:12px;bottom:4px;height:1px;background:var(--accent);transform:scaleX(0);transform-origin:left;transition:transform var(--dur-med) var(--ease-out-expo)}
.nav-links a:hover{color:var(--ink)}
.nav-links a:hover::after{transform:scaleX(1)}
.nav-links a[aria-current="page"]{color:var(--accent)}
.nav-links a[aria-current="page"]::after{transform:scaleX(1)}
.nav-links .nav-cta{margin-left:0;padding:8px 16px!important;min-height:36px}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#000;font-weight:600}
.btn-primary:hover{background:var(--accent-hover);box-shadow:0 0 24px var(--accent-dim);color:#000;text-decoration:none}
.bg-grid{position:fixed;inset:0;z-index:-1;pointer-events:none;background-image:linear-gradient(var(--border) 1px,transparent 1px),linear-gradient(90deg,var(--border) 1px,transparent 1px);background-size:56px 56px;opacity:.35;mask-image:radial-gradient(ellipse 80% 60% at 50% 0%,#000 40%,transparent 75%)}
/* ===== docs polish (emerald, no legacy blues) ===== */
.docs-body h2{scroll-margin-top:96px}
.docs-link.active{background:color-mix(in srgb,var(--accent) 8%,transparent)}
.docs-body table{width:100%;border-collapse:collapse;font-size:13.5px;margin:0 0 26px}
.docs-body th,.docs-body td{border:1px solid var(--border);padding:8px 10px;text-align:left;vertical-align:top}
.docs-body th{background:var(--panel);font-family:var(--font-mono);font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.docs-body td code{font-size:12.5px}
.docs-body blockquote{border-left:3px solid var(--accent);margin:0 0 22px;padding:4px 0 4px 18px;color:var(--muted)}
.docs-body ul{margin:0 0 22px 22px}
.docs-body li{margin-bottom:8px}
@media(max-width:860px){
  header.site-nav{display:block;position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--border);padding:0}
  .nav-inner{flex-wrap:wrap;padding:12px 20px}
  .nav-links .nav-cta{margin:0}
}
@media(max-width:600px){.nav-links{display:none}}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}.bg-grid{display:none}}
</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<div class="bg-grid" aria-hidden="true"></div>
<header class="site-nav" id="siteNav">
  <div class="nav-inner">
    <a class="wordmark" href="index.html">XOMNI<span>.</span></a>
    <nav class="nav-links" aria-label="Primary">
      <a href="index.html">Home</a>
      <a href="skills.html">Skills</a>
      <a href="mcp.html">MCP Catalog</a>
      <a href="gallery.html">Gallery</a>
      <a href="docs/install.html">Docs</a>
      <a href="docs/sponsorship.html">Sponsorship</a>
      <a href="https://github.com/painbaba/xomni">GitHub</a>
      <a class="nav-cta btn-primary" href="docs/install.html">Install</a>
    </nav>
  </div>
</header>

<main id="main">
  <div class="container page">
    <aside class="docs-side" aria-label="Docs navigation">
      <p class="docs-h">Docs</p>
      <a href="docs/install.html" class="docs-link">Install</a>
      <a href="docs/byo-provider.html" class="docs-link">BYO Provider</a>
      <a href="docs/sponsorship.html" class="docs-link">Sponsorship</a>
      <a href="docs/faq.html" class="docs-link">FAQ</a>
      <a href="docs/security.html" class="docs-link">Security</a>
      <a href="features.html" class="docs-link active">Features</a>
      <p class="docs-h">Site</p>
      <a href="skills.html" class="docs-link">Skills</a>
      <a href="index.html" class="docs-link">Home</a>
    </aside>

    <article class="docs-body">
"""

FOOT = """    </article>
  </div>
</main>

<footer class="site-footer">
  <div class="container footer-inner">
    <div>
      <p class="footer-brand"><span class="logo-x">X</span>OMNI</p>
      <p class="muted">one agent. every feature. every free model.</p>
    </div>
    <div class="footer-cols">
      <div class="footer-col">
        <p class="footer-h">Docs</p>
        <a href="docs/install.html">Install</a>
        <a href="docs/byo-provider.html">BYO Provider</a>
        <a href="docs/sponsorship.html">Sponsorship</a>
      </div>
      <div class="footer-col">
        <p class="footer-h">More</p>
        <a href="docs/faq.html">FAQ</a>
        <a href="docs/security.html">Security</a>
        <a href="skills.html">Skills</a>
      </div>
      <div class="footer-col">
        <p class="footer-h">Project</p>
        <a href="https://github.com/painbaba/xomni" target="_blank" rel="noopener">GitHub</a>
        <a href="index.html">Home</a>
      </div>
    </div>
  </div>
  <p class="footer-bottom muted">© <span data-year>2026</span> XOMNI · compose, don't merge.</p>
</footer>

<script src="js/site.js"></script>
</body>
</html>
"""


def inline(text: str) -> str:
    """Light markdown inline -> HTML: **bold**, `code`, [link](url)."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def render_tables(lines: list[str], i: int):
    """Consume consecutive markdown table lines starting at i. Return (html, next_i)."""
    rows = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
        i += 1
    if not rows:
        return "", i
    # skip separator row (|---|...)
    body = rows[1:] if len(rows) > 1 and all(set(r) <= {"-", ":"} for r in rows[0]) else rows
    header = rows[1][0] if body is rows[1:] else None
    out = ['<div class="table-wrap"><table>']
    if header is not None:
        out.append("<thead><tr>" + "".join(f"<th>{inline(h)}</th>" for h in header) + "</tr></thead>")
    out.append("<tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out), i


def main() -> None:
    text = FEATURES_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    i = 0
    in_list = False
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            if in_list:
                out.append("</ul>")
                in_list = False
            i += 1
            continue
        if line.startswith("|"):
            tbl, i = render_tables(lines, i)
            out.append(tbl)
            continue
        if line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            slug = re.sub(r"[^a-z0-9]+", "-", line[3:].lower()).strip("-")
            out.append(f'<h2 id="{slug}">{inline(line[3:])}</h2>')
        elif line.startswith(">"):
            out.append(f"<blockquote>{inline(line[1:].strip())}</blockquote>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
        elif re.match(r"^\d+\.\s", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            item = re.sub(r"^\d+\.\s", "", line)
            out.append(f"<li>{inline(item)}</li>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    if in_list:
        out.append("</ul>")
    body = "\n".join(out)
    OUT_HTML.write_text(HEAD + body + "\n" + FOOT, encoding="utf-8")
    print(f"wrote {OUT_HTML} ({len(HEAD + body + FOOT)} bytes)")


if __name__ == "__main__":
    main()
