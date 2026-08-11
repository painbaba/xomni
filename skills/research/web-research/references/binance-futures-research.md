# Binance Futures research: live-data access patterns (verified Aug 2026)

Recipe for live-verifying crypto-futures claims (leverage, liquidation, funding, OI, positioning) from Binance's own pages + public API. All endpoints/URLs below worked as of Aug 2026.

## Access rules of thumb
- `academy.binance.com` / `www.binance.com` academy+support pages return **0-byte bodies to curl** (Cloudflare). Don't retry curl with UA tricks — switch to the browser stack.
- Academy articles are **client-rendered**: `fetch(articleUrl)` from page context returns only the SSR shell (nav/footer, no body). You must `browser_navigate` to the article, then extract `document.querySelector('article').innerText` (or the snapshot).
- Old/guessed slugs silently 302-redirect to the `/en/academy/articles` listing. **Don't guess slugs** — resolve them via the internal search API below.

## Academy internal search API (same-origin fetch from page context)
```
GET https://www.binance.com/bapi/composite/v2/public/pgc/content/academy/search?lang=en&page=0&size=8&term=<TERM>&with=articles%2Cglossaries%2Ccourses
```
- Response shape: `data.pages.data[]` = articles (`title`, `slug`, `updated_at`, `reading_time`), `data.glossaries.data[]` = glossary entries, `data.courses`.
- Build URLs: `https://www.binance.com/en/academy/articles/<slug>` and `/en/academy/glossary/<slug>`.
- **PITFALL: multi-word terms return 0 results.** `term=liquidation price` → 0 hits; `term=liquidation` → hits. Query single words.
- Use `updated_at` to check freshness and quote the on-page "Updated <date>" — this is what lets you say "2026-current" with confidence.
- Discover any site's internal API by reading `performance.getEntriesByType('resource')` after loading a page, filter for `bapi|search|api`.

## Binance Support FAQ search
- `/en/support/search?query=...` often returns "Sorry, we can't come up with anything" — the URL param path is unreliable.
- Instead: type the query into the on-page search box (`browser_type` + Enter), then harvest results with `document.querySelectorAll('a[href*="faq/detail"]')`.
- FAQ pages render full text (formulas, tables, examples) in the snapshot. Note the "Published on / Updated on" dates — e.g. liquidation-price FAQ updated 2025-12-31, leverage/margin FAQ updated 2026-03-27.

## Leverage & Margin live table (JS page, snapshot-renderable)
`https://www.binance.com/en/futures/trading-parameters/perpetual/leverage-margin`
- Proves: "Initial Margin = Position Value / Leverage"; "Maintenance Margin = Position Value * Maintenance Margin Rate - Maintenance [Amount]".
- Tier table (BTCUSDT & ETHUSDT, rules last updated 2025/08/19): Tier 1 = 0–300,000 USDT position value, max 150x, MMR 0.40%, maint amount 0.
- Switch symbol: click the combobox, then in console `Array.from(document.querySelectorAll('[role="option"]')).filter(o=>o.textContent.indexOf('ETHUSDT')===0)[0].click()`, then re-read `table tbody tr` cells.

## Public futures API — plain curl works, no auth
Base: `https://fapi.binance.com`
- `/fapi/v1/premiumIndex?symbol=BTCUSDT` → markPrice, indexPrice, lastFundingRate (per interval), interestRate, nextFundingTime
- `/fapi/v1/ticker/24hr?symbol=BTCUSDT` → last, high, low, priceChangePercent, quoteVolume
- `/futures/data/openInterestHist?symbol=BTCUSDT&period=1h&limit=1` → sumOpenInterest (contracts), sumOpenInterestValue (USD)
- `/fapi/v1/fundingRate?symbol=BTCUSDT&limit=10` → funding history per interval (check persistence/positivity)
- `/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=5` and `/futures/data/topLongShortPositionRatio?symbol=...` → retail vs top-trader positioning skew
- `/fapi/v1/openInterest?symbol=...` → current OI in base tokens (e.g. 23.66B PUMP); USD ≈ OI × markPrice from premiumIndex
- `/fapi/v1/exchangeInfo` → per-symbol `onboardDate` (futures listing date, epoch ms — proves when a perp listed), `requiredMarginPercent` (5% ⇒ 20x max), `maintMarginPercent`, price/quantity precision
- Spot daily klines for trend claims: `https://api.binance.com/api/v3/klines?symbol=<SYMBOL>USDT&interval=1d&limit=320` → compute EMA-200 in python; report price/EMA ratio to verify "200-day EMA breakout" stories (CoinGecko OHLC endpoint is key-gated 401; Binance klines are not)

## Verified authority chain for leverage/liquidation claims (cross-check pattern)
1. Academy "What Is Leverage in Crypto Trading?" (Apr 2026): "At 10x leverage, a 10% adverse price move can result in total loss of your collateral. At 50x, a 2% move can be enough."; "experienced traders cap leverage at 3x to 10x".
2. Academy "What Are Short Liquidations in Crypto?" (Jun 2026): "At 10x ... roughly 8 to 10 percent ... can trigger liquidation"; Coinglass liquidation-heatmap methodology (clusters = price targets); OI + funding positioning reads.
3. Academy "What Are Funding Rates in Crypto Markets?" (Jul 2026): `Funding Rate = Premium Index + clamp(Interest Rate − Premium Index, −0.05%, +0.05%)`; 0.03%/day standard interest; 8h intervals (4h if |rate| ≤ 0.002% for 36 cycles).
4. Academy "How to Calculate Position Size in Trading" (Apr 2026): `position size = account size × account risk / invalidation point`; 1% rule.
5. Support FAQ `b3c689c1f50a44cabb3a84e663b81d93` (updated 2025-12-31): liquidation-price formula (cross-margin vars WB/TMM/UPNL/cum/MMR; isolated simplifies to wallet balance only).
6. Support FAQ `360033162192` (updated 2026-03-27): since 2025-12-07, **>20x leverage blocked for futures accounts in first 30 days** — cap relevant to retail playbooks.
7. Derived (label as COMPUTED, not quoted): isolated liq distance ≈ 1/leverage − MMR → 10x ≈ 9.6%, 20x ≈ 4.6% at BTC/ETH tier-1 MMR 0.40%; 5x ≈ 19.6%.

## Deliverable discipline (what the user asked for and got)
- Separate sections: **LIVE-VERIFIED FACTS** (exact quotes + URL each) vs **DERIVED MATH** (computed from verified inputs, explicitly labeled "not quoted").
- Quote the page's own "Updated <date>" so the reader can judge 2026-currency.
- Note which sites were unreachable for live checks (Coinglass returned 404 to this client) and cite the methodology from the authority that documents it instead of fabricating numbers.
