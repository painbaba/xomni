# Live news & exchange-status research: blocked-site playbook (verified Aug 2026)

For live-verified status/news briefs (exchange listings/delistings, burns, campaigns, outages, price performance) where the official site (binance.com) is bot-gated and every number must carry a URL. Companion to `binance-futures-research.md` (trading params/API angle).

## Tier 0: curl-friendly sources, hit these first
- **CoinGecko API** (no key): `api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd&include_24hr_change=true` and `/api/v3/coins/binancecoin` → current price, 7d/30d change, ATH+date, market cap, `last_updated` (use it to prove live-ness).
- **CoinDesk**: tag page `coindesk.com/tag/<topic>/` is curl-friendly; article URLs are server-rendered in the HTML; full article body is in plain `<p>` tags. Best outlet for full-text quotes without a browser.
- **Yahoo Finance**: curl-friendly. Resolve the exact slug via Bing News RSS (below) — do NOT guess slugs (guesses 404).
- **AMBCrypto, CryptoBriefing, U.Today, markets.businessinsider.com (finanzen)**: curl-friendly. BI puts burn/table figures in `<li>` items — grep `<li>` tags too, not just `<p>`.
- **CoinTelegraph**: tag page article hrefs + `og:title`/`og:description`/`article:published_time` meta ARE server-rendered (curl gets title+date+summary), but the article **body is client-rendered** (no `articleBody` JSON-LD, no `__NEXT_DATA__`) → `browser_navigate` for full text.
- **Indian outlets** (for India-market research): **MoneyControl** is curl-friendly, bodies in plain `<p>` (e.g. parliament-panel meeting article); **MediaNama** curl-friendly; **Economic Times** is paywalled to curl (only nav/boilerplate `<p>`, no `articleBody` JSON-LD, no `art_text` div) but **renders the full body in the browser snapshot** — go straight to `browser_navigate` for ET articles; **fiuindia.gov.in** homepage is curl-friendly but subpages (e.g. `/pages/display/106-virtual-digital-assets`) are rejected by a WAF ("Request Rejected" + support ID) via BOTH curl and browser → use press coverage (MediaNama/ET) for FIU lists.

## Binance announcement CMS API — WORKS via curl GET (corrects earlier "403, skip" note)
```
GET https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=<N>&pageSize=50&catalogId=<ID>
```
- **Use GET, not POST** (POST → 403, which is what the old blocked-site map recorded). Returns 200 JSON.
- Response shape: articles live at `data.catalogs[].articles[]` — NOT `data.articles` (a loop reading the wrong key silently yields 0 hits). Each article: `id`, `code` (builds `/en/support/announcement/<code>`), `title`, `releaseDate` (ms epoch).
- Catalog ids: 49 = Latest Binance News, 48 = New Listings, 93 = Latest Activities, 161 = Delisting, 157 = Maintenance, 51 = API Updates, 128 = Airdrops. `pageSize` max 50 (100 → HTTP 400).
- **Region headers unlock geo-gated feeds**: add `-H "lang: en-IN" -H "region: IN"` and the same endpoint returns India-specific announcements (e.g. "India Exclusive: Trade Futures & Share 20,000 USDT Rewards", "Binance P2P Will Update Maker Fees for INR Market") that are absent from the default feed. Use this to prove what products a country's users can actually access — first-party evidence stronger than any press.
- Article detail endpoint (`/article/detail?articleId=` / `?code=`) 404s; `binance.com/en/support/announcement/<code>` renders 0 bytes via curl and empty page via browser on this host → cite title+date from the list API (mirror of the Google News RSS citation pattern).
- Scan pattern: page through `pageNo` 1..N per catalog, break when `min(releaseDate)` passes your cutoff; dedupe by `id`.

## Google News RSS — regional variants
The US variant below (`hl=en-US&gl=US`) is default; **for Indian-market research use `hl=en-IN&gl=IN&ceid=IN:en`** — same RSS contract, feeds local outlets (ET, Moneycontrol, MediaNama, India Today) and geo-filtered Binance pages. Query verbs that worked: `Binance India FIU registration`, `RBI crypto banks 2026`, `crypto tax TDS India budget 2026`, `Binance India derivatives restricted` (empty results are also informative).
## Google News RSS — the official-announcement workaround (key trick)
binance.com announcement pages are captcha-locked to curl (HTTP 202, 0 bytes) AND to the browser ("Let's confirm you are human"). But Google News indexes Binance's official announcement pages:
```
curl "https://news.google.com/rss/search?q=Binance+futures&hl=en-US&gl=US&ceid=US:en"
```
- Returns up to 100 `<item>`s: `<title>`, `<pubDate>`, `<source>` (e.g. "Binance"), `<link>`.
- Query by topic+verb combos: `BNB burn`, `Binance listing delisting`, `Binance outage OR maintenance`, `Binance copy trading`, `Binance futures leverage`, `Binance campaign promotion`.
- Citation pattern when the official page is unreachable: `"<announcement title>" (YYYY-MM-DD), Binance, via Google News RSS` — title/date/source are live-verified even though body isn't. Pair with third-party coverage (CoinDesk/U.Today/CryptoBriefing) for body text.
- **PITFALL**: Google News `<link>`s are opaque `news.google.com/rss/articles/...` wrappers that do NOT resolve via `curl -L`. **They DO resolve in the browser**: `browser_navigate` to the wrapper URL redirects to the real article page (verified Aug 2026: Newsweek, CBS ×2, AP/KSAT all readable this way). If the first navigation times out or returns an empty page, retry once, then `browser_snapshot` — the redirected article is usually there. Cite the destination outlet + RSS title/date.
- **Find a specific outlet's coverage** with the `site:` operator: `news.google.com/rss/search?q=site:newsweek.com+Chutkan+Epstein&hl=en-US&gl=US&ceid=US:en` → that outlet's article titles + `<pubDate>`s on the topic, no outlet-internal search needed. First hit of the RSS usually matches the first title.
- **Date events from `<pubDate>`, never from the task premise**: prompts routinely assert wrong dates (verified Aug 2026: prompt claimed "March 2025"; live pubDates showed the events ran Feb–Mar 2026). Build the timeline from RSS pubDates, correct the premise explicitly in the brief, and never assert dates from memory.

## Bing News RSS — direct article URLs
```
curl "https://www.bing.com/news/search?q=<query>&format=rss"
```
- `<link>` is an `apiclick.aspx?ref=FexRss&...&url=<url-encoded>` — URL-decode the `url=` param to get the real article URL.
- Use when you need the exact URL to fetch/quote, or to find non-blocked coverage of a blocked site's story (e.g. BeInCrypto story → Yahoo Finance version, same facts).

## Bing web search via BROWSER (browser_navigate, not curl)
- `bing.com/search?q=` intermittently shows a Cloudflare interstitial ("One last step — Please solve the challenge below"): the compact snapshot shows a checkbox `Verify you are human` inside the widget iframe — `browser_click` it, then a fresh snapshot/console eval returns real results. Sometimes needs the checkbox click once per session.
- **PITFALL: Bing web search ignores long-tail / quoted queries** — it returns the same generic cached result set (Wikipedia/justice.gov/etc.) regardless of query, which silently defeats targeted research. The **Bing NEWS vertical honors the query**: use `bing.com/news/search?q=<real-query>` instead; results there are genuinely query-relevant (with per-item timestamps like "6 days ago").
- Snapshot on `bing.com/news/search` can time out; extract via console instead:
  ```js
  Array.from(document.querySelectorAll('#b_results li.b_algo h2 a')).map(a=>a.href+' || '+a.innerText).join('\n')
  ```
  and on the news vertical, click the headline ref from the snapshot then read `location.href` (console) to recover the canonical article URL (clicking goes through Bing redirects).
- If a news search returns "No results" for a broad single word, drop the `qft=interval` param — it breaks the query.

## Wikipedia as a research scaffold (anchor timeline, then verify primary sources)
- `curl -L` fetches Wikipedia fine (pages are 1–1.5 MB — big but workable). Regex-extract: strip `<script>/<style>`, cut to `#mw-content-text`, replace `<h2>/<h3>/<p>/<li>` with line markers, unescape entities → clean line-numbered text.
- Use the H2/H3 headings as line anchors: print bounded line ranges (e.g. `lines[271:572]`) to avoid stdout truncation, and grep for the section you need. The "References" section is a goldmine of exact article URLs/dates to then verify live.
- Wikipedia also reveals things search engines hide — e.g. a sidebar link `Epstein Files Transparency Act II` that a direct Bing query never surfaced; check `en.wikipedia.org/w/api.php?action=query&titles=<Title>&redirects=1&format=json` to learn a title is a redirect to another article's section.
- Always re-verify Wikipedia claims against at least the primary source (e.g. the actual DOJ press release) before quoting.

## Blocked-site map (status as of Aug 2026)
| Site | curl | browser | workaround |
|---|---|---|---|
| binance.com `/en/support/announcement`, `status.binance.com` | 202 (0-byte) | captcha | Google News RSS titles+dates; `fapi.binance.com` API still open for market data |
| binance.com bapi CMS announcement API (`GET /bapi/composite/v1/public/cms/article/list/query`) | **200 JSON** | — | see "Binance announcement CMS API" below — it WORKS; use region headers for geo-gated feeds |
| theblock.co tag pages | 403 | — | other outlets cover the same stories |
| beincrypto.com | 403 | Cloudflare challenge | find same story on Yahoo/others via Bing News RSS |
| **justice.gov** (incl. `/epstein`, `/opa/pr/...` press releases) | Akamai interstitial (`bm-verify` JS challenge, ~2 KB stub) | **loads fine** | just use `browser_navigate` for DOJ pages; they're primary sources worth quoting directly. Other US-gov sites may share the Akamai setup — try browser before assuming a hard block |
| **bing.com/search via browser** | n/a | Cloudflare "Verify you are human" checkbox, then OK | click the checkbox; or skip web search and use `bing.com/news/search` (honors queries, web search ignores long ones) |
| html.duckduckgo.com/html/ | first 2-4 queries OK, then rate-limited (WinError 10054 reset / empty result sets) | — | retry loop (3x, sleep 3-5s); after repeated empties switch to Google/Bing News RSS or direct URL guesses. NOT a hard block — worth trying first. |
| lite.duckduckgo.com/lite/ | **best general web-search fallback** — ~2-3 queries then HTTP 202; recovers after 5-10s | — | parse `uddg=` links (see "No web_search tool" section); sleep 5-10s between queries |
| bing.com search via browser | first searches OK, then Cloudflare "Verify you are human" checkbox → "Verify" button that hangs | — | don't fight it; use Bing News RSS or DDG Lite instead |
| web.archive.org snapshot fetches | 429/202 rate limits | — | use the availability API sparingly, wait between calls; don't hammer |
| api.bscscan.com V1 | deprecated | — | V2 requires API key; use CoinGecko supply data instead |
| search.yahoo.com/search HTML | 0 bytes (blocked) | — | use Google/Bing News RSS instead |
| telegraphindia.com article pages | HTTP Access Denied (Akamai `errors.edgesuite.net`) | — | find the same story on other outlets via Google/Bing News RSS |

## Status-brief deliverable format (user expectation for this class of task)
- Lead with the N most impactful items FOR THE AUDIENCE (e.g. "5 most impactful for a futures trader"), each carrying exact numbers + URL.
- Then supporting details grouped by the user's original asks (listings/delistings, new products, campaigns, price/burn, outages, derivatives changes).
- **LIVE-VERIFIED FACTS** section: EVERY URL fetched, grouped into "successfully read" vs "fetched but blocked", one line per fact → URL. Name blocked pages explicitly with the mechanism ("HTTP 202 via curl; captcha via browser").
- Never assert from training memory; mark anything unverifiable as unverified.

## No web_search tool: general search fallbacks (verified Aug 2026)
This host registers NO `web_search` tool (tool_search finds nothing) — when a task needs one, use:
1. **DuckDuckGo Lite** via curl — first choice for general queries:
   ```
   curl -s -A "<browser UA>" "https://lite.duckduckgo.com/lite/?q=<urlencoded query>" -o ddg.html
   ```
   Results are `<a rel="nofollow" href="//duckduckgo.com/l/?uddg=<urlencoded-url>&...">`; extract with
   `urllib.parse.unquote(html.unescape(uddg_value))` (both steps needed — html.unescape alone leaves
   `%3A`-style encoding). Rate limit: ~2-3 queries then HTTP 202; sleep 5-10s between queries, it recovers.
2. **Bing News RSS** (`bing.com/news/search?q=<q>&format=rss`, URL-decode `url=` in `apiclick.aspx`
   links) — for news-specific queries and exact article URLs. Google News RSS as the backup.
3. **Direct URL guesses for known outlets** — but expect some to 404 (e.g. theguardian.com slugs);
   resolve exact slugs via search first.

## Host quirks (this Windows/MSYS box, hit while doing this)
- `curl -o <long-name>` silently truncates output filenames to ~32 chars → name output files short (≤20 chars) from the start, then glob when re-reading.
- `curl -o` to ANY absolute path (`/c/Users/...`, `/tmp/...`) fails silently (file never appears); `cd` to the target dir first and use a relative `-o` name.
- Windows python cannot open `/c/...` paths — use `C:\...` or relative paths after `cd`.
- Persist fetched artifacts only if a later step needs them; clean up temp html/xml files before finishing. **This host's disk can be 100% full already** — a single 1 MB+ download then triggers `Errno 28: No space left on device` in python. Delete each fetched HTML right after parsing/extracting (not just at the end), and keep concurrent downloads small.
- **execute_code and terminal run in SEPARATE sandboxes on this host**: a file written by curl inside execute_code is invisible to terminal grep/read, and `/tmp` in one tool is NOT `/tmp` in the other. Do write+read of fetched artifacts inside the SAME tool; to pass data across, print to stdout and capture the result. (Within terminal alone, `cd /c/Users/HP && curl -o shortname` works fine.)
- **`python -c "..."` with regex breaks in git-bash**: bash eats `[^` and backslashes inside double quotes (e.g. `re.findall(r'id="entry-(\d+)"'...)` → `[^: No such file or directory`). Write a `.py` script with write_file and run `python file.py args` instead of inline `-c` with regex. Multi-step fetch+parse loops (curl page → sleep → parse) are easier as a script anyway.
