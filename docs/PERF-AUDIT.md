# PERF-AUDIT — Homepage (`website/index.html`)

**Audit date:** 2026-08-12 · **Backlog item:** 22 (P1 wave) · **Scope:** homepage only
**Method:** static analysis (Python: gzip, regex, HTMLParser, WCAG 2.1 relative-luminance math) + live check (Chromium on `127.0.0.1`, `performance.getEntriesByType('resource')`).

## Checklist & measured numbers

| # | Check | Target | Measured | Status |
|---|-------|--------|----------|--------|
| 1 | Page weight (raw) | — | **25.34 KB** (25,944 B) | ✅ |
| 2 | Page weight (gzip, level 9) | ≤ 20 KB | **7.59 KB** (7,773 B, −70.0%) | ✅ |
| 3 | Network requests (sub-resources) | **0** | **0** — live `performance.getEntriesByType('resource')` = `[]`; only the 1 document navigation | ✅ |
| 4 | External CSS/JS/fonts/images | 0 | 0 — all CSS + JS inline; favicon is a `data:` URI; no `@font-face` | ✅ |
| 5 | Render-blocking items | minimal | 1 inline `<style>` (10.2 KB, request-free); `<script>` is at end of `<body>` (non-blocking); 0 external blocking requests | ✅ |
| 6 | Image sizes | — | **0 images** — hero art is a CSS/HTML mock terminal; favicon is a 535 B inline SVG data URI | ✅ |
| 7 | WCAG AA contrast (lowest pair) | ≥ 4.5:1 | **4.79:1** (faint on surface-2); all 14 pairs pass | ✅ |
| 8 | Skip link | present | `.skip-link` → `#main`, `:focus` reveals; target `<main id="main">` exists | ✅ |
| 9 | ARIA labels | present | 6 `aria-label`s (nav "Primary", hero, stats band, terminal demo, copy button); `aria-current="true"` on Home | ✅ |
| 10 | Button accessible names | all named | 6/6 (Install XOMNI, Browse 170 skills, Copy ×2, Browse 311 MCP servers) | ✅ |
| 11 | HTML parses | no errors | HTMLParser: 0 errors; live `readyState: complete`, no console errors | ✅ |
| 12 | Reduced-motion / focus | present | `prefers-reduced-motion` block (kills animations, shows `.reveal`); `:focus-visible` outline on accent | ✅ |

## WCAG AA contrast math (WCAG 2.1, relative luminance)

`L = 0.2126R + 0.7152G + 0.0722B` (sRGB linearized); `ratio = (L1+0.05)/(L2+0.05)`. Threshold: 4.5:1 normal text.

| Foreground | Background | Ratio | Status | Used for |
|---|---|---|---|---|
| `#00E5A0` accent | `#050607` bg | **12.28:1** | ✅ AA (also AAA) | brand headline, wordmark, stats, prompt — **brand accent untouched** |
| `#00E5A0` accent | `#0A0C0E` surface-1 | 11.86:1 | ✅ | card `.tag` |
| `#00FFB0` accent-hover | `#050607` bg | 15.38:1 | ✅ | hover states |
| `#00B87E` accent-dim | `#050607` bg | 7.88:1 | ✅ | borders (1.4.11 non-text 3:1 also met) |
| `#A6ADB5` muted | `#050607` bg | 8.95:1 | ✅ | sub, lede, nav links |
| `#A6ADB5` muted | `#0A0C0E` surface-1 | 8.65:1 | ✅ | card body text |
| `#7B828A` faint | `#050607` bg | 5.22:1 | ✅ | footer meta, section h4 labels |
| `#7B828A` faint | `#0A0C0E` surface-1 | 5.04:1 | ✅ | plugin descriptions |
| `#7B828A` faint | `#101316` surface-2 | **4.79:1** | ✅ (lowest, 0.29 margin) | terminal bar label |
| `#E8EAED` ink | `#050607` bg | 16.82:1 | ✅ | body copy |
| `#5CC8FF` syntax | `#0A0C0E` surface-1 | 10.41:1 | ✅ | code, formula |
| `#2FD6A1` success | `#050607` bg | 10.87:1 | ✅ | terminal `.ok` |
| `#FFB454` warning | `#050607` bg | 11.50:1 | ✅ | sponsor line highlight |
| `#000000` | `#00E5A0` accent | 12.72:1 | ✅ | `.btn-primary` label |

**Conclusion: no contrast failures.** The only near-margin pair is `--faint:#7B828A` on `--surface-2:#101316` (4.79:1 vs 4.5 threshold) — passes, so per policy the brand accent `#00E5A0` and the muted palette are left unchanged.

## Fixes applied

**None required.** Every threshold met as measured above; `index.html` unchanged (still 25,944 B, still parses). Recommended (optional, non-blocking) future items:

- `--faint` could be nudged to `#8A929B` (+~0.9:1 margin) at the next visual pass — cosmetic, not required.
- `og:image` points at `favicon.svg` (absolute URL) — meta-only, never fetched by the browser; fine.
- Homepage `style`/`script` are intentionally inline to hold the 0-request guarantee — do **not** extract to `css/style.css`/`js/site.js` (that would add 2 requests and break target #3).

## Verification

- [x] Numbers recorded above from measured output (not estimates).
- [x] No fixes needed → no source edits; `index.html` re-parsed clean (0 errors) after audit.
- [x] Live render: `readyState=complete`, resource entries `[]`, 0 console errors, skip-link + `#main` present, 0 `<img>`, 1 inline stylesheet, 1 inline script.
