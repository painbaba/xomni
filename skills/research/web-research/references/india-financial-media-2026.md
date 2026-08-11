# Indian Financial-Media Fetch Matrix (validated Aug 2026, Ola Electric governance research)

Which backends worked for Indian listed-company research from this host, in order of reliability.

## Discovery
- **Bing News RSS + India market params** — `https://www.bing.com/news/search?q=<q>&format=rss&setmkt=en-IN&cc=IN`. Reliable dated items. Decode the apiclick `<link>` `url=` param with `urllib.parse.unquote` (plain urlencode — NOT the b_algo `u=a1` base64 trick used for Bing web SERPs) to get canonical article URLs. Batch 6–10 queries per execute_code call, ~1.2s sleeps, print `date | title | decoded URL` rows.
- Google News RSS titles: useful discovery supplement; token links dead (see SKILL.md pitfalls) — do not attempt resolution.
- Pitfall: Bing News RSS can collapse MANY different queries onto ONE syndicated/paywalled URL (this session, ~5 SEBI queries all resolved to the same Livemint premium article). Fall back to site-native search (`https://<site>/?s=<q>`, WordPress REST `https://<site>/wp-json/wp/v2/search?search=<q>`) or direct-URL construction for the target outlet.

## Fetch — direct curl (desktop Chrome UA) WORKS for these Indian financial outlets
Returned full HTML this session (strip tags, then `find(marker)` + window ±150..2000 chars):
- Moneycontrol (moneycontrol.com) — body in HTML; works
- Financial Express (financialexpress.com) — works (large pages ~500KB)
- ET Auto (auto.economictimes.indiatimes.com) — works, clean body
- The Hindu BusinessLine (thehindubusinessline.com) — works; body may sit past nav; widen the window
- YourStory — works
- Entrackr — works
- Free Press Journal (freepressjournal.in) — works (PTI-syndicated copy common)
- SiliconIndia — works (loose numbers; prefer primary outlets)
- IndiaInfoline — works
- India TV News — works
- News18 — works (has AI "Rapid Read" summary; use article body)
- Times of India (timesofindia.indiatimes.com) — works
- Hindustan Times — works
- BW Businessworld — works (headline-first; body sometimes thin)
- Autocar India — works (industry news)
- Rediff — works (Reuters syndication)
- Inc42 — works (nav-heavy; find marker past menus)

## Fetch — browser required / other paths
- **Business Standard: curl 403.** Bing News RSS usually lists the BS story as an msn.com URL — `browser_navigate` the MSN link; the accessibility snapshot carries the FULL article incl. numbers and brokerage targets. Also works for ET-syndicated content on MSN (e.g. "Ola Electric shares fall 6%..." article with 4 broker target prices).
- **Livemint/Mint premium:** curl returns nav + summary + first paragraphs of the body. Those often contain the KEY facts (qualified-audit flags, SEBI probe specifics, guidance numbers) — harvest the visible window before declaring paywalled. Premium body = only summary + "Gift this article" note.
- **CNBC TV18:** curl worked this session (market article).
- Blocked this session: r.jina.ai (403 from this host — known), DuckDuckGo html via browser (challenge page with checkbox grid), Business Standard direct curl (403).

## Cross-check techniques that worked
- **Share counts when no source states them:** derive market cap ÷ price, confirm with a second mcap datapoint. Session example: ₹14,467 cr mcap @ ₹32.80 → ~441 cr shares (Dec 2025); later mcap > ₹18,990 cr @ ~₹41 → ~463 cr shares post-QIP (consistent with 441 + 21.8 cr QIP shares). Flag derived numbers as computed.
- **Guidance-vs-actual scorecards:** fetch the EARLIER quarter's results coverage for the guidance quote (e.g. Q4-call guidance: "Q1 FY27 revenue ₹500–550 cr, orders 40k–45k") and the later quarter's article for actuals (revenue ₹455 cr = miss; orders 44,071 = hit). The actuals article rarely re-quotes the guidance.
- **Financials timeline:** build quarterly table from YoY-comparison clauses in later articles (e.g. Q3 FY26 article quotes Q3 FY25 revenue/loss), cross-fill remaining quarters by subtraction from the annual total; mark derived cells.
- **Brokerage targets:** the MSN/ET post-results article is the single best source for the full analyst set (Sell/TP list).
