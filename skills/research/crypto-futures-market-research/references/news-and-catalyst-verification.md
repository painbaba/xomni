# News & Catalyst Verification Workflow (verified live Aug 2026)

Goal: turn a tape anomaly (e.g. BMT +176%, GRVT +23%, NIL +28%) into a VERIFIED catalyst with a dated URL — the "WHY" half of a LIVE-VERIFIED FACTS section.

## Order of operations
1. Identify movers from the tape scan (funding/OI/price anomalies).
2. Catalyst check: Binance announcements API (catalogId=48) — covers listing-driven pumps (GRVT perp 2026-07-31, bStocks pairs 2026-08-05).
3. News scan: RSS feeds (below) for dated headlines. Homepage curl is useless — CoinTelegraph/CoinDesk homepages are React shells with no article titles in raw HTML; their RSS feeds are clean and dated.
4. Deep-read 3-6 articles for quotes/numbers; extract via curl where SSR, browser_console where React/paywalled.
5. Cross-check numbers against live tape (funding, OI, price) — if the article's numbers disagree with Binance, say so in the facts section.

## RSS feeds (curl-able, dated headlines)
- CoinTelegraph: `https://cointelegraph.com/rss` (30 items, includes markets/magazine)
- CoinDesk: `https://www.coindesk.com/arc/outboundfeeds/rss/`
- The Block: `https://www.theblock.co/rss.xml` (small; often blocked → use gnews search instead)

## Search fallback: Google News RSS (the one that works)
DuckDuckGo HTML (`html.duckduckgo.com/html/?q=`) returned EMPTY results for every query; Bing RSS (`bing.com/search?q=..&format=rss`) returned unrelated junk. The reliable curl search is Google News RSS:
```python
url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en-US&gl=US&ceid=US:en"
# parse <item> → <title>, <source>, <pubDate>, <link>
```
- Works with plain urllib + UA header, no key, returns dated results with source names.
- PITFALL: generic queries surface STALE articles (a "token unlocks this week" query returned a Feb 2025 article from CryptoRank). ALWAYS read pubDate and discard anything not within the research window.
- `<link>` values are `news.google.com/rss/articles/...` wrappers. curl does NOT follow them (200 OK, no Location). Resolution: browser_navigate the wrapper → page lands on the target site → check `window.location.href` via browser_console → extract body.

## Article body extraction
- SSR sites (CoinTelegraph): curl + regex works —
  `re.findall(r'<p[^>]*>(.*?)</p>', html)` then strip tags; also grab `<meta name="description">` (good summary even when body extraction fails).
- React/paywalled (CoinDesk): the registration wall ("You have 2 articles remaining") does NOT remove the body from the DOM. Dismiss the dialog, then:
```js
(() => { const ps = document.querySelectorAll('article p, main p, [class*="article"] p'); const out = [];
ps.forEach(p => { const t = p.innerText.trim(); if (t.length > 40) out.push(t); });
return [...new Set(out)].join('\n---\n').slice(0, 6000); })()
```
- Google News wrapper: first browser_navigate often shows "(empty page)" — the JS redirect lands after; re-check `window.location.href` via console, then run the extractor. Retry navigation once if the snapshot is empty.

## Quote discipline
- Quote exact numbers WITH the URL. When an article cites a third-party number (e.g. Coinglass liquidation $3.26M via Coin Gabbar), attribute it as such — you haven't verified the underlying source yourself.
- Name the token's identity explicitly (BMT = Bubblemaps, BICO = Biconomy, NIL = Nillion) — ticker alone is ambiguous to the reader.
- Unlock dates: Tokenomist data appears via aggregators (Bitcoin World, Bitget) — dollar values disagree between outlets ($35.2M vs $35.7M vs $35.5M for the same YZY unlock); quote one source + the % of circulating supply (the more decision-relevant number).
