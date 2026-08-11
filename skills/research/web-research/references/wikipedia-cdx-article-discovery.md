# Article-URL discovery when search engines are blocked: Wikipedia wikitext + Wayback CDX (verified Aug 2026)

Companion to `search-when-browser-blocked.md` and `live-news-and-blocked-sites.md`. Use when you have a topic, no working web_search tool, and search engines captcha/ignore curl — but you still need DIRECT publisher URLs to quote.

## 1. Wikipedia API: harvest primary-source URLs from a topic article (key trick)
Instead of downloading a 1.5 MB article HTML to mine its References section, pull the wikitext over the API and regex out the URLs:

```
https://en.wikipedia.org/w/api.php?action=query&titles=<Title>&prop=revisions&rvprop=content&rvslots=main&format=json&redirects=1
```
- Content lives at `query.pages[*].revisions[0].slots.main["*"]`.
- Locate a section (`wt.find("== Estate and victim settlements ==")`) and run `re.findall(r"https?://[^\s\]\|}]+", seg)` — the `{{Cite news |url=... |date=... |title=...}}` templates around each sentence hand you primary URLs WITH dates and headlines, zero searching. Verified: Epstein article → CNBC (USVI $105M, Nov 30 2022), CNBC (Deutsche $75M, May 18 2023), Guardian (JPMorgan–USVI $75M, Sep 26 2023), CNN (estate $35M, Feb 20 2026), justice.gov PR (Jan 30 2026), dailymontanan.com (NM probe), usvidoj.com (AG release).
- **Clean rendered text** (plain, for "current status" answers): `prop=extracts&explaintext=1&format=json` → `pages[*].extract`. The two endpoints can DIVERGE (extract showed a 2nd-Circuit ruling and release date absent from the wikitext) — check both before concluding.
- Parse gotchas: responses are huge and contain literal control characters — `json.loads(text, strict=False)`; transient empty replies happen — `retry(fn, max_attempts=4, delay=2)`.
- Always re-verify the harvested URL's content itself (curl/jina/archive) before quoting; Wikipedia is the directory, not the evidence.

## 2. Wayback CDX: find a publisher's article URL from a headline
When Google News RSS gives you a title/outlet/date but no usable link (its `<link>`s are opaque `news.google.com/rss/articles/...` wrappers — curl `-L` lands on HTTP 400, and the protobuf payload doesn't decode to a plain URL), find the real URL via CDX:

```
http://web.archive.org/cdx/search/cdx?url=<domain>&matchType=domain&filter=urlkey:.*<keyword>.*&collapse=urlkey&fl=original,timestamp&limit=50
```
- Works great on small domains: `url=bankingdive.com` + `filter=urlkey:.*epstein.*` surfaced the exact `banking-dive.com/news/bank-of-america-72M-settlement-epstein-related-lawsuit/816095/` slug the RSS headline described.
- PITFALL: domain-wide queries with `filter=original:.*kw.*` on big domains (reuters.com, bbc.com) → 504 Gateway Time-out. Narrow to a subdomain prefix (`url=bbc.com/news&matchType=prefix`) and keep `limit` small.
- REFINEMENT (verified Aug 2026): the prefix can be a full SECTION path, not just a subdomain — `url=snopes.com/fact-check/&matchType=prefix&filter=original:.*epstein.*&collapse=urlkey&fl=original&limit=500` returned hundreds of exact slugs (500-cap; grep further). Date-bucketed outlets: `url=factcheck.org/2024/01/&matchType=prefix&filter=original:.*epstein.*` finds by month. This is THE tool when a site's own search is JS-rendered (Snopes `/search/?q=` returns nav-only HTML via curl; PolitiFact's `/search/` DOES return article links raw — try the site search once, then CDX).
- Fetching snapshots: `id_` in the timestamp path (`/web/<ts>id_/<url>`) returns the raw original; if the body comes back as binary garbage it's gzip — add `--compressed`. Some sites stay gated even in archive (Banking Dive serves its newsletter interstitial) → cite headline + URL, mark headline-only.
- PITFALL (rate limits): wayback snapshot fetches intermittently 401 even with `id_` and a plain UA. Wait 10-20s between snapshot fetches (batched CDX queries are fine; snapshot fetches are the rate-limited path). If a specific URL keeps 401ing after 2 spaced retries, mark it blocked and move on — e.g. two Reuters fact-checks stayed 401 for the whole session while a third (same day) fetched fine via `web.archive.org/web/2024id_/<url>`.
- Verified direct-curl hosts (browser UA, article pages): snopes.com, politifact.com (article AND search), factcheck.org (article pages; its `/?s=` WP search 404'd — don't rely on it), usatoday.com (article HTML works), aap.com.au. Reuters direct → 401 always; go to wayback.

## 3. r.jina.ai reader proxy quirks (this host, Aug 2026)
- CNN: curl returns nav/CSS junk; `https://r.jina.ai/<cnn-url>` returns Title + `Published Time` (ISO 8601) + clean markdown body. Best free CNN reader.
- Reuters: anonymous jina → `403 AbuseAlleviationError` ("blocked until <ts>"). Don't retry; use the web.archive.org snapshot of the same URL instead (Reuters is well-archived; title + lede verify the facts).
- BBC live blogs and Guardian render fine via jina.

## 4. JS-heavy publisher extraction without a browser (curl only)
Phrase-anchored context windows on tag-stripped text remain the workhorse. When the body is client-rendered (curl returns only a CSS/JSON shell), escalate in this order:
1. `og:title` / `og:description` meta — often carries the exact figure (verified: CNBC `og:description` = "Deutsche Bank agrees to pay $75 million to Jeffrey Epstein sex abuse victims to settle suit").
2. JSON-LD `<script type="application/ld+json">` blocks — `articleBody` present on some sites, absent on others (CoinTelegraph-class); parse with `json.loads(strict=False)`.
3. `window.guardian = {"config": {...}}` — The Guardian embeds `page.headline`, `page.author`, standfirst, and `webPublicationDate` in that config blob, greppable via curl.
- Never guess article slugs on date-based outlets (Guardian `/2026/feb/23/...`) — resolve via Bing News RSS `url=` param, CDX, or Wikipedia refs first.

## 5. Headline-only citation discipline (repeated, kept here for one-stop reference)
A story verified only via RSS headline (title + outlet + pubDate, every copy paywalled/gated) is cited as `"<headline>" (<outlet>, <date>), <URL if known>` and flagged headline-only in the LIVE-VERIFIED FACTS section. Never invent body details for it; never merge it into "fetched OK".
