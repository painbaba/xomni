---
name: crypto-futures-market-research
description: "Binance Futures scans: funding, OI, crowding, leverage."
---

# Crypto Futures Market Research (Binance)

## When to use
- "research crypto market today", "scan every pair", "any good 10-20x leverage setups", "what's moving on Binance"
- Any live market-state question where exchange data beats news articles

## Live data: public endpoints, NO API key
- `GET https://fapi.binance.com/fapi/v1/ticker/24hr` — every futures symbol in one call (field is `lastPrice`)
- `GET /fapi/v1/premiumIndex` — NO symbol arg = ENTIRE universe (857 symbols incl. USDC/non-ASCII) with lastFundingRate + markPrice + nextFundingTime in ONE call. This is the whole-universe funding scan; per-symbol only for isolated re-fetches.
- `GET /fapi/v1/openInterest?symbol=X` — REQUIRED per-symbol; the no-arg batch call 400s. Thread with 20 workers for full-universe OI.
- `GET /futures/data/topLongShortAccountRatio?symbol=X&period=1h&limit=1` — top-account long/short crowding (same shape for topLongShortPositionRatio)
- `GET /fapi/v1/fundingRate?symbol=X&limit=12` — APPLIED funding history (trend); INTERVAL is per-symbol (see fundingInfo pitfall — 8h default, 4h on many new listings)
- `GET https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&pageNo=1&pageSize=20&catalogId=48` — official Binance announcement feed, JSON, NO key. catalogId=48 = "New Cryptocurrency Listing". THE source for exchange-listing catalyst claims (e.g. GRVT perp launched 2026-07-31; 10 bStocks spot pairs 2026-08-05). Parse with python; keys at data.catalogs[].articles[].title/releaseDate.
- `GET /fapi/v1/klines?symbol=X&interval=4h&limit=12` — quote volume = k[7]; sum last 6 vs first 6 = last-24h vs prior-24h volume ratio (spike detection)
- Scripts: `scripts/binance_market_scan.py` (watchlist) + `scripts/full_universe_funding_scan.py` (whole-universe funding/OI/volume anomaly scan) — run them, don't re-type them.

## API pitfalls (all hit live, Aug 2026)
- Futures 24hr ticker field is `lastPrice`, NOT `price` (a spot-style script crashes with KeyError).
- `openInterest` endpoint REQUIRES `?symbol=` — batch request without symbol = HTTP 400.
- Some symbols are non-ASCII (e.g. 龙虾USDT) — ascii()-guard or skip them before printing, or the print crashes.
- funding % is per 8h by default — but CHECK `/fapi/v1/fundingInfo` first: `fundingIntervalHours` is per-symbol and new listings often settle 4h (×6/day, DOUBLE cost) with caps up to 2%. |funding| > ~0.05%/interval is extreme (the crowded side pays). Live Aug 2026: GRVTUSDT settled 4h; +0.0862%/4h predicted ≈ 0.52%/day.
- OI in USD = openInterest × lastPrice (openInterest is in base-coin units).
- `premiumIndex.lastFundingRate` is the CURRENT/next-interval rate (drifts continuously; what gets charged at nextFundingTime). `fundingRate` history = APPLIED rates. Big mismatches are normal (BRKBUSDT +0.2345% current vs 0.0000% applied — fresh flip, not an error). Quote premiumIndex for "what traders pay next", history for trend.
- `/fapi/v1/futures/data/openInterestHist` can 404 from some regions while `topLongShortAccountRatio` works — don't assume the whole /futures/data/ tree is reachable; fall back to klines volume ratio for trend inference. Per-symbol 404s also happen on `/fapi/v1/fundingRate` history (hit on GRVTUSDT live) — wrap every per-symbol call in try/except so one 404 doesn't kill the loop; `premiumIndex` is the reliable current-funding source.

## Reading the tape for leverage setups
- Funding: positive + high = longs paying (crowded long); negative = shorts paying → squeeze fuel.
- Long/short ratio > ~2.5 = one-sided market; when the flush comes it hits the crowded side hardest (DOGE 79% long / XRP 77% long, Aug 2026).
- OI spike + flat price = contested new positions; OI drain = unwinding.
- Volume share (symbol quoteVolume / total quoteVolume) shows where money actually is — memes can out-volumize majors (TUT 2.2B vs SOL 1.0B, Aug 2026).
- Honest read: quiet funding + quiet OI + flat majors = no edge, just casino — say so instead of inventing setups.

## Full-universe anomaly scan (funding / OI / volume) — verified live Aug 2026
One-shot recipe (675 USDT pairs, ~2 min, script in `scripts/full_universe_funding_scan.py`):
1. `premiumIndex` (no arg) → funding for every symbol; filter |f| ≥ 0.05% (42 pairs on a typical day).
2. `ticker/24hr` → price, 24h%, quoteVolume, high/low.
3. `openInterest?symbol=` threaded (20 workers) → OI in USD = openInterest × lastPrice.
4. Crowding: `topLongShortAccountRatio` for the shortlist (≤50 symbols, 1 call each).

Anomaly metrics (thresholds hit live Aug 10 2026):
- OI/VOL = OI_usd / 24h quoteVolume. ≥1.5 = positions parked vs flow; ≥3 = extreme (WLFI 7.03 with $119M OI on $17M volume was the universe max). Big parked OI + neutral funding = dry powder that fires when flow returns.
- Distribution = volume spike without price confirmation: klines 4h ×12 → vol_last24 = sum qv[-6:], vol_prev24 = sum qv[:6], ratio ≥1.5× AND |24h%| ≤ ~35% of (high-low)/low range. Daily range of spikes: 2-25× (XAN 26.6×, MINIMAX 9.7×, SKHYNIX 6.5×).
- Volume fade <0.5× after a dump = selling exhausted (BLUAI 0.20×, MMT 0.27×) — bounce fuel, not fresh distribution.
- Squeeze setup = funding extreme AGAINST price direction + one-sided L/S (EUL: −0.12% funding, +7.7% price, 63.9% short). Crowded-trend flush risk = funding extreme WITH price + L/S >2.5 (SKHYNIX: +0.12% funding, 88% long, 6.5× vol, price −1.9% — textbook crowded-long distribution).
- Read `premiumIndex.lastFundingRate` as CURRENT rate; confirm direction with applied history before calling something "sustained".

## Coinglass cross-check (live, Aug 2026)
- Coinglass funding widgets are CROSS-EXCHANGE: "Highest/Lowest funding" lists Bitget/Bybit/OKX names. ALWAYS check the exchange label before attributing a number to Binance (BICO +0.34% on the widget was Bitget; Binance BICO was +0.01% — the discrepancy was an attribution error, not a data error).
- Working access from this host: coinglass.com renders in the browser; the Funding Rate page table has per-exchange columns and a "Predicted" column that matches Binance premiumIndex. Extract rows via browser_console JS (`Array.from(document.querySelectorAll('table tr'))` filtering innerText) — the a11y snapshot only shows the first ~10 majors.
- The site's own REST API (api.coinglass.com) can be geo-blocked (connection failure, HTTP 000) — use the rendered browser page instead. Per-symbol `/tv/<SYM>` routes can 500; homepage → "Funding Rate" nav link works.
- Validation ritual: cross-check 5-10 of your Binance numbers on Coinglass before trusting the pipeline (BTC 0.0066% matched exactly both times).

## Pairing the tape with news catalysts
- Tape (funding/OI/price) tells you WHAT; news tells you WHY. Before naming a catalyst for a mover (listing, unlock, migration, squeeze), verify it against a dated source: Binance announcements API (above) first, then RSS feeds. Never attribute a catalyst from memory.
- Curl-friendly news feeds: cointelegraph.com/rss, coindesk.com/arc/outboundfeeds/rss/, theblock.co/rss.xml — dated headlines, no JS needed. Homepage HTML is React-shell (no article titles in raw HTML); go straight to RSS.
- Full workflow, search fallbacks, and paywall-extraction snippets: `references/news-and-catalyst-verification.md`

## Deliverable format for live market research (user requirement)
- Quote EXACT numbers with the URL they came from; end with a `LIVE-VERIFIED FACTS` section listing every URL fetched (include the API server timestamp).
- If a page/endpoint blocks you, SAY SO explicitly in the facts section — never assert from training memory.
- Structure: top-10 table (with direction bias / who pays) + "hidden gems" (setups the market isn't watching) + distribution watch.

## Risk math (quote this every time leverage is discussed)
- Liquidation distance ≈ 1/leverage ignoring fees: 10x ≈ 9-10% adverse move, 20x ≈ 4.7%.
- BTC/ETH daily candles routinely move 3-5% → at 20x that is 60-100% of margin in hours.
- Pro ceiling: 1-2% of account risk per trade; stop-loss placed BEFORE the liquidation price, always.

## Regulatory note
- Passive market-data research is always legal. Whether the user can ACTUALLY trade Binance Futures (India FIU status, KYC restrictions, 30% VDA tax, 1% TDS) changes over time — verify live before advising, never assert from training memory (same rule as parallel-research-swarm).

## Related
- Run with `python` (3.11 on this host; `python3` may lack deps): `python scripts/binance_market_scan.py`
