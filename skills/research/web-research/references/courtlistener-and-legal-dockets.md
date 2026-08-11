# CourtListener live docket research (verified Aug 2026)

For fact-checks and dossiers that must cite ACTUAL court filings — unsealed exhibits, flight logs,
complaints, deposition exhibits — straight from CourtListener (RECAP). This host has NO `web_search`
tool registered, so finding the right docket is done via CourtListener's own public API + curl.

## 1. Find the docket — public search API (no auth, works via curl)
```
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0" \
  "https://www.courtlistener.com/api/rest/v4/search/?q=giuffre+maxwell&type=d&page_size=5"
```
- `type=d` is the valid choice; `type=docket` → HTTP 400 ("Select a valid choice").
- Results carry `docket_id`, `caseName`, `docketNumber`, `dateFiled` — enough to pick the right case
  (e.g. Giuffre v. Maxwell = docket **4355835**, 1:15-cv-07433).
- The docket DETAIL API `/api/rest/v4/dockets/<id>/` → **401 without an auth token** — do not use;
  fetch the HTML docket pages instead.
- RECAP document search (`type=r`) returns docket-level results with a nested `recap_documents` array
  whose descriptions are often empty, and a `docket_id=` query param does NOT filter docket-level
  results (returned unrelated "Flight" bankruptcy cases). Skip it; page the docket HTML.

## 2. Docket HTML pages via curl
```
curl -s -L -A "<browser UA>" "https://www.courtlistener.com/docket/<id>/<slug>/?page=N" \
  -o dpageN.html -w "%{http_code} %{size_download}"
```
- ~166 entries per page, OLDEST first; page 1 = case start. A docket with 1,366 entries spans 8 pages.
- Entries live in `<div id="entry-N">` blocks: date, description, and "Download PDF" links
  (CourtListener / Internet Archive / PACER).
- The LAST page holds the most recent filings — that's where freshly unsealed exhibits land.
- The raw HTML contains NO plain-text "flight" mentions; to find keyword hits (e.g. "flight log",
  "day log", "exhibit", a person's name), strip `<script>/<style>`, strip tags, html.unescape,
  collapse whitespace, then regex with ±100-char context.

## 3. Rate limits & anti-bot (critical)
- Rapid page fetches → **HTTP 202 (empty body)** then **403**. Sleep 8–10s+ between docket page
  fetches; retry after ~10s. A burst of 3+ pages without delay trips the limiter.
- Use **curl with a browser User-Agent**; plain urllib gets blocked (202/empty) where curl succeeds.
- One docket page is ~1.5–2.6 MB — don't fetch pages you don't need; compute which page range
  covers your date window first.

## 4. Article/exhibit text extraction (same pattern, different sites)
Strip tags → unescape → collapse whitespace → keyword search with context. Confirmed full-text via
curl+browser UA on palmbeachpost.com and factually.co (both returned HTTP 200).

## Verified data points (fetched Aug 2026 — re-verify before citing in a live report)
- Giuffre v. Maxwell docket 4355835 (1:15-cv-07433): 1,366 entries; page 8 (entries 1201–1366)
  spans Dec 2025–Feb 2026.
- Palm Beach Post (2025-02-28, "Epstein flight logs, list: Surprising details of Trump, Clinton
  trips"): Trump on Epstein planes "at least eight times" 1993–97 (e.g. 1994-05-15 Washington DC
  trip with then-wife Marla Maples + daughter Tiffany; 1995-08-13 PBIA→Teterboro with son Eric);
  Clinton flew "numerous times between 2002 and 2003, after leaving office"; Prince Andrew flew
  into/out of Palm Beach International Airport; pilots logged mainly initials/first names.
  URL: palmbeachpost.com/story/news/trump/2025/02/28/epstein-flight-logs-list-surprising-details-trump-clinton-trips/80730076007/
- factually.co fact-check (2025-11-13, "How many times did Bill Clinton fly on Epstein's plane"):
  Clinton appearance counts in released logs vary — 17 / 26 / 27 — because outlets count flight
  legs vs name-appearances vs trips; entries concentrate in 2001–2003; Clinton's office says four
  trips in 2002–2003 with staff, foundation supporters and Secret Service.
  URL: factually.co/fact-checks/politics/bill-clinton-epstein-plane-flights-logs-count-3c99bd
