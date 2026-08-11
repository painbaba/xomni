# News Research Workflow — Discovery, Redirect Resolution, Article Extraction, Verification
Validated Aug 2026 while building a verified biography dossier on a public figure (IAS officer Tukaram Mundhe). Generalizes to any current-affairs / public-figure research.

## 1. Discovery: Google News RSS (primary)
```
https://news.google.com/rss/search?q=<urlencoded query>&hl=en-IN&gl=IN&ceid=IN:en
```
- `hl/gl/ceid` set the edition — use `en-IN&gl=IN&ceid=IN:en` for Indian coverage, `en-US` for US.
- Returns `<item>` blocks: title, link, source, pubDate — gives you a dated, outlet-attributed headline inventory in one call.
- Query tactics that worked:
  - `"Full Name" + <aspect>` (e.g. `"Tukaram Mundhe" Nashik`, `"Tukaram Mundhe" publicity`) for per-aspect sweeps.
  - No `when:` date operator — inject year terms into the query (`"Tukaram Mundhe" 2019 OR 2020 OR 2021`) to pull older coverage.
  - The same query surfaces both breaking news AND years-old explainers — the pubDate field is how you sort the arc.
- Batch 4-6 queries per execute_code call; print `title | source | pubDate` compactly. This alone reconstructed a 20-year posting timeline before any article was opened.

## 2. Redirect resolution (the step that trips people)
Google News RSS `<link>` values are `https://news.google.com/rss/articles/CBMi...?oc=5` — **client-side redirects**. `urllib.request.urlopen(...).geturl()` returns the wrapper, NOT the article.
Working recipe:
1. Copy the `<link>` **verbatim** from the RSS parse output (do not hand-edit; a single altered char → Google "Redirect notice / invalid web address" page).
2. `browser_navigate(<link>)` — the browser executes the JS redirect and lands on the article.
3. `browser_console` → `window.location.href` to capture the canonical article URL for citations.
4. If you need many articles, do them one `browser_navigate` per article — there is no batch shortcut; prioritize which articles earn a full read.

**Truncation failure mode (cost a fetch in Aug 2026):** if the stub URL is cut off at ANY length (e.g. copied from a truncated terminal/console print), Google returns a **"400. That's an error. The server cannot process the request because it is malformed."** page — a different symptom from the hand-edit "Redirect notice" page. Both mean: the URL you passed ≠ the RSS `<link>`.

**Fix pattern for long-URL batch work:**
- Persist RSS items (title/source/date/gurl) to a JSON file on disk in the first execute_code pass; append a second JSON with resolved canonical URLs later. Intermediate files survive context limits and let you re-print URLs in full.
- Immediately before each `browser_navigate`, re-print the FULL gurl from the JSON (small batches of 3-6) — never copy from earlier truncated display output.
- When re-mapping saved JSON indices to your target list, index-math mistakes mislabel entries silently (a mislabeled fetch still lands on a REAL article — e.g. expected IE, got ThePrint). Verify after navigating: the page headline in the snapshot/console must match the item you intended to fetch.
- Some articles return an EMPTY snapshot (`element_count: 0`) even after a successful redirect — `browser_console` with an `innerText` extraction still works on the same page; don't navigate away thinking it failed.
- If a `browser_navigate` snapshot is truncated, the full snapshot is auto-saved to a file and the path is printed in the tool result — `read_file` that path (with offset) to page through the rest of the article body instead of re-fetching.

## 3. Per-outlet article reading (browser, not curl)
| Outlet | What works |
|---|---|
| Times of India | Full body text appears directly in the accessibility snapshot (incl. old 2022 articles). No paywall. |
| Indian Express | Intro + subhead visible free; premium body cut at "This story requires a subscription." JSON-LD trick: `document.querySelectorAll('script[type="application/ld+json"]')` → NewsArticle node has `articleBody` (same truncation point, but the deck + first paragraphs are citation-grade). |
| ThePrint | Blocks curl (Cloudflare). Site search works in browser: `https://theprint.in/?s=<q>` and `https://theprint.in/page/N/?s=<q>` — paginated, dated inventory. Articles show ~3 free paragraphs + subhead before "Show Full Article". |
| Moneycontrol | JS-rendered; first `innerText` grab may return only the byline — re-query `document.querySelector('article').innerText` after the page settles. |
| CNBC TV18 | Full text via `document.querySelector('article').innerText` (this yielded the complete dated posting-by-posting career list). |
| NDTV Profit | Full text in snapshot. |
| India Today / Business Today | Headline + first paragraphs free; canonical URL visible in page source links / sign-in redirect base64. |
| Gulf News | Full text in snapshot. |
| The Quint | Full text in snapshot; old (2016) articles still live. |

General extraction one-liner (works on most sites):
```js
document.querySelector('article').innerText  // or document.body.innerText
```

## 4. Public-figure dossier verification checklist
- [ ] **Cross-confirm every load-bearing fact in ≥2 outlets** (batch year, posting dates, incident claims). Single-source claims are flagged inline: "(News18-only claim, treat as reported)".
- [ ] **Allegations vs established facts — label explicitly.** Example: officer got EOW/police clean chit in one probe (established) while a separate 'pressure on female officials' inquiry was still pending (alleged/unresolved). Never merge the two.
- [ ] **Counts and figures are point-in-time.** Transfer counts, seizure totals, etc. change as coverage accretes — cite the count WITH its date ("23 in 20 years (Dec 2025); 25 in 21 years (May 2026)") and note the arc.
- [ ] **Don't assert labels the sources never use.** "Publicity officer", "encounter officer" etc. may be user-supplied or folk framing — if the exact phrase isn't in the record, say so in a Gaps/UNVERIFIED section and give the closest documented equivalent.
- [ ] **Negative findings are findings.** "No evidence of a Latur collector posting; his district postings were Jalna and Solapur" — record the absence.
- [ ] End with a **Gaps/UNVERIFIED** section; date-stamp every source.

## 5. Sources of friction (expected, not bugs)
- Google/Bing/DDG HTML search endpoints return empty or challenge pages via curl on Windows/MSYS — don't burn time; the RSS ladder + browser covers the space.
- Headline-level facts (from RSS) may be cited to outlet+date even when the article body is paywalled — the RSS pubDate and title are themselves evidence.
