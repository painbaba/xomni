---
name: crypto-futures-market-data
description: "Use for crypto futures funding, OI, liquidation data."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [crypto, futures, funding, open-interest, liquidations, binance, coinglass, market-data]
    related_skills: [web-research, stock-technical-analysis, polymarket]
---

# Crypto Perp Futures Market Data (funding / OI / L/S / liquidations)

Live-verified research on perpetual futures positioning: funding rates, open interest, long/short ratios, and liquidation flows. User's hard requirements for this class of task: **every number quoted from a fetched page/API with its URL**, a `LIVE-VERIFIED FACTS` section listing every URL fetched, explicit "blocked" statements when a page refuses data, and **never assert from training memory**.

## Data sources (canonical)

1. **Binance Futures public REST API** (`https://fapi.binance.com`, no auth) — precise per-symbol data. Full endpoint reference in `references/binance-futures-endpoints.md`. Fallback mirror for all of these: `https://data-api.binance.vision`.
2. **Binance liquidation stream (WebSocket)** — REST liquidation endpoint `/fapi/v1/allForceOrders` **returns 404 (removed)**; the only public liquidation feed is the WS `!forceOrder@arr` stream. See script `scripts/capture_binance_liquidations.py`.
3. **CoinGlass web UI (real browser)** — cross-exchange aggregates + long/short liquidation splits + funding extremes. Homepage `https://www.coinglass.com/` is the richest single page (global OI/liq/volume + top-20 per-symbol table: price, funding, 24h vol, OI, OI 24h%, liq 24h). Dedicated pages: `/FundingRate` (per-exchange funding, highest/lowest lists) and `/liquidations` (heatmap, per-symbol Long/Short liq splits for 1h/4h/12h/24h, real-time order feed).

## Standard workflow

1. **Binance REST snapshot** — `premiumIndex` (all symbols, no symbol param) to rank extreme funding; then per symbol: `fundingRate` (last 3–4 paid), `openInterest`, `openInterestHist` (4h bars × 30 = 5d OI trend → spike vs drain), `globalLongShortAccountRatio` + `topLongShortPositionRatio` + `topLongShortAccountRatio` (period=1h), `ticker/24hr`. Compute OI % change from openInterestHist buckets (24h = last 6 vs prior 6; 5d = first vs last).
2. **CoinGlass browser pass** — load homepage; read global ticker + per-symbol table. Navigate to FundingRate and Liquidation pages **via the site's nav links, not direct URLs** (direct loads 404 — SPA). Extract per-symbol long/short liquidation splits and the "X traders liquidated, total $Y, largest order $Z" summary line.
3. **Live liquidation capture (optional but powerful)** — run the WS capture script for ~2 min. **Before trusting a zero-event result, prove the stream is actually delivering**: count a high-frequency control stream (btcusdt@aggTrade — expect hundreds in seconds). Zero forceOrders on a *verified-live* stream = genuinely quiet tape. Zero with no control traffic = blocked/blackholed connection, discard.
4. **Synthesize** — per-symbol table (price, funding now + paid trend, OI + 24h/5d change, top-trader L/S position & account ratios, global L/S, liq totals with long/short split), then top-N crowded setups with direction bias, then cascade-risk assessment. Flag Binance-vs-global OI divergence when present (e.g. Binance OI draining while global OI rising = leverage rotating venues).

## Semantics & traps

- **`ticker/24hr` field names**: the response uses `lastPrice` (NOT `price` — a naive script KeyErrors instantly), `priceChangePercent`, `quoteVolume`. Filter USDT perps with `symbol.count("USDT")==1` (skips COINUSDT-style names). Non-ASCII symbols exist on Binance (e.g. a Chinese-name USDT pair) — ASCII-encode or skip or the print crashes with UnicodeEncodeError.
- **`openInterest` REQUIRES the `symbol` param** — a mass call without it returns HTTP 400. Loop per symbol.
- **`globalLongShortAccountRatio` may 404 on some hosts/networks** (Aug 2026: one agent hit 404, another got data) — the always-working endpoints are `topLongShortAccountRatio` + `topLongShortPositionRatio` (period=1h). If the global endpoint 404s, use top-accounts ratios and say so.
- **Force-order side**: in Binance WS forceOrder payloads, `S=SELL` = liquidated **LONG**, `S=BUY` = liquidated **SHORT**. CoinGlass tables label Long/Short columns explicitly.
- **Listing date = first fundingRate entry**: `fundingRate?symbol=X&startTime=0&limit=1000` — the first entry's `fundingTime` (UTC) marks the perp's listing moment (GRVT: first funding Jul 31 12:00 UTC → listed Jul 31, 2026; no need to wade through exchangeInfo). Also pull the FULL history (startTime=0) to read **funding floor vs spikes** before calling cost "unsustainable": new alts often pin at the 0.005% default floor through consolidation and only go hot on pump days (GRVT: 0.005% Aug 6-9, −0.15% negative spike on the Aug 5 listing pump, +0.084% during the Aug 10 run) — hot funding is a momentum symptom; check whether it normalizes to the floor between runs, and note the 8h → daily cost conversion (rate × 3 × leverage = % of margin/day).
- **Funding**: `premiumIndex.lastFundingRate` = current (latest settled) rate; `nextFundingTime` tells when the next payment lands. Coinglass "current" tab often shows *predicted* next funding. Convert: rate × 100 = %; APR ≈ rate × 3 × 365. Many alts pin at exactly 0.0100% for consecutive periods — that's a **cap**, not "rising".
- **Funding INTERVAL is per-symbol — verify before ANY cost math**: default 8h (×3/day) but new listings frequently settle every **4h** (×6/day — DOUBLE the daily cost; GRVTUSDT live Aug 2026). Authoritative check: `/fapi/v1/fundingInfo` → `fundingIntervalHours` + `adjustedFundingRateCap/Floor` (cap can be 2% — new listings run very hot). Confirm empirically from `fundingRate` timestamps (00/04/08/12/16/20 UTC = 4h). Quote interval + cap + daily% in the report (GRVT: +0.0862%/4h predicted ≈ 0.52%/day ≈ 189% APR; 3 days at 10x ≈ 15.5% of margin).
- **Extreme threshold**: |funding| ≥ 0.05%/**interval** ≈ crowded; ≥ 0.10% very crowded (per-interval, so 8h-vs-4h matters). In quiet markets the extremes live in small/mid caps (KAITO −0.41%, SKHYNIX +0.12–0.27%) while majors sit under ±0.01% — say so instead of forcing a narrative.
- **New perp listings (age check first)**: `/fapi/v1/exchangeInfo` `onboardDate` = contract age — "90 days of klines" may return only days of candles (GRVT: 59×4h = 10 days). Contract ATH ≠ global ATH (CoinGecko `ath`/`ath_date` shows the pre-listing pump elsewhere — GRVT global ATH $0.4545 Jul 30 vs contract ATH $0.3520 Aug 5). Spot pair often absent (futures-only). Books are thin (~$1M/side) — quote TOTAL per-side notional and size accordingly. Verify "listing pump" narratives against actual venue volumes (CoinGecko tickers, Upbit `/v1/candles/days`): the pump venue's volume may already be 97% faded while the perp keeps pumping. Full checklist + worked example: `references/new-perp-listing-analysis.md`.
- **OI trend from openInterestHist**: `sumOpenInterest`/`sumOpenInterestValue` are 4h-bucket sums; notional OI ≈ markPrice × contracts from `/fapi/v1/openInterest`.
- **CoinGlass API** (`fapi.coinglass.com/api/*`) is auth-gated — returns `{"success":true}` with no data. Don't waste time probing param variants; use the browser UI.
- **CoinGlass route discovery**: canonical page routes can be grepped from the homepage HTML (`curl -s coinglass.com/ | grep -oE 'href="[^"]*(unding|iquidation)[^"]*"'`). Per-symbol liq page: homepage → "Liquidation" nav → click the symbol in the heatmap list → `coinglass.com/liquidations/<SYMBOL>` (Long/Short $ split + %, "Mostly Short/Long Liquidations" status, largest single liq, peak liq hour, per-exchange long/short table, live feed). The homepage also carries a per-symbol RSI(4h) leaderboard — handy "is this overbought" check.
- **EMA cross detection**: compute EMA progressively (`e = c*k + e*(1-k)` per bar) and find the first bar with `close[i] > ema[i]` — comparing closes against the single final EMA value produces a bogus cross date (PUMP Aug 2026: wrong method said Jan 1, correct method said Jul 27). Also check the retest and max extension % — the "pullback zone" is usually a pivot, not the EMA (PUMP's 0.00272 zone was +31% above EMA200).
- **Stop-vs-liquidation coherence**: liq price ≈ entry × (1 − 1/lev + MMR). If the stop sits beyond the liq price it NEVER fires — the position is liquidated first (PUMP: 20x + 8% stop = liq ~0.00260 above stop 0.00252; only 10x or a tighter stop works). Quote per-leverage liq prices in every plan; stop must fire with ≥1% buffer.
- **OI trend framing**: always 3 horizons — 24h (5m buckets), 7d (1h buckets), 7d min/max churn. A rally on flat/declining 7d OI = spot-led / short-covering (PUMP: +39% rally on −2.8% 7d OI, with OI added only in the final ATH leg +5.7% 24h) — a materially weaker build signal than OI rising through the whole rally.
- **WS fallback**: `capture_binance_liquidations.py` now CONTINUES to the mirror host on CONTROL==0 (fixed Aug 2026 — it previously exited after the first host). If fstream blackholes, the mirror `wss://data-stream.binance.vision/ws/btcusdt@aggTrade/!forceOrder@arr` worked in one session (control 749/90s) but failed its handshake in another — if BOTH hosts fail, report liquidation data as blocked and label cluster estimates as inferred from funding/OI/L-S.

## Report format (user-required)

Plain English; per-symbol funding/OI table; top-3 most crowded setups each with direction bias; where liquidation cascades are most likely; a `LIVE-VERIFIED FACTS` section listing **every URL fetched** (and every blocked/removed source, stated explicitly); caveats with timestamps (UTC) and data provenance (Binance-only vs CoinGlass aggregate).

## Full-universe "scan every pair" workflow (user's standing ask)

When the user says "scan every pair" (or wants leverage-setup hunting), the live scan is:

1. **`ticker/24hr` ONCE** = every pair (Aug 2026: 678 USDT perps, ~$24B total 24h quote vol). Rank by `quoteVolume` desc → top-30 leaders; by `priceChangePercent` → top-15 gainers AND top-15 losers. Quote BTC/ETH + vol share of total.
2. **Watch list** = top-15 by volume + top-8 gainers + top-8 losers (dedupe). Per symbol: `premiumIndex` (funding + mark) and `openInterest?symbol=X` × lastPrice = OI in USD.
3. **Crowding** — `topLongShortAccountRatio` for majors (period=1h): XRP/DOGE at 77-79% long = crowded; BTC 55% = neutral.
4. **Funding extremes across the whole universe**: |funding| ≥ 0.05%/8h = crowded; rank top-10 with direction bias. Note OI/volume anomalies (OI ≫ volume = parked dry powder; volume spike with flat price = distribution).
5. Hand the snapshot to the research swarm (see `parallel-research-swarm` skill) with the numbers IN the agent contexts — agents analyze from real data instead of re-fetching.

## Leverage setup analysis (10-20x lens)

Full methodology in `references/leverage-setup-analysis.md`. Deep technicals+liquidity track
(klines→EMA/swings/volume-profile, depth-at-levels, OI 3-horizon framing, liq-cluster estimation,
TradingView listing check, full report format incl. 3-scenario map + invalidation) in
`references/leverage-setup-deep-dive.md` (worked PUMP example inside). The essentials:

- **Liquidation math (isolated)**: liq distance ≈ 1/leverage − MMR (BTC tier-1 MMR 0.40%, alts ~0.5%) → **10x ≈ 9.6% adverse move, 20x ≈ 4.6%**. Long liq price ≈ entry × (1 − 1/lev + MMR).
- **Stop-before-liquidation rule**: at 20x the whole budget is 4.6% → usable stops are 2-3% = scalps only; at 10x you get 3-5% stops = structure-based entries. A stop wider than the liq distance is a no-trade.
- **1% sizing rule**: notional = account × 0.01 / stop%. Size to the STOP, never to the margin limit.
- **Setup-card format** (per pair): trend structure (swing highs/lows from 90d + 7d klines) / crowding read (funding + OI trend + L/S) / entry zone + SL + TPs with liq prices at 10x AND 20x / verdict LONG / SHORT / FLAT / WAIT + conviction.
- **Honest environment call**: in a low-vol, mildly-long, cheap-funding tape, 20x is a scalping tool only — say so instead of manufacturing setups.

## Support files

- `references/binance-futures-endpoints.md` — exact REST endpoint recipes, params, response fields, fallback mirror.
- `references/leverage-setup-analysis.md` — setup-card methodology, liquidation math, pair-class taxonomy (majors / alt movers / losers+squeezes), trap flags, CPI/event overlay.
- `references/leverage-setup-deep-dive.md` — per-symbol technicals+liquidity deep dive: progressive EMA200 cross detection, depth-at-levels aggregation, volume-profile proxy, OI 3-horizon attribution, long/short liq-cluster estimation, stop-vs-liq coherence check, CoinGlass per-symbol liq page navigation, verified WS mirror fallback, TradingView stale-price note, 3-scenario report format, worked PUMP example.
- `references/new-perp-listing-analysis.md` — deep dive on brand-new perp listings (days of history): onboardDate age check, fundingInfo interval/cap verification (4h settlements), contract-vs-global ATH, thin-book sizing, venue-narrative verification (Upbit/CoinGecko tickers), no-spot-pair note, worked GRVTUSDT example.
- `scripts/fetch_binance_futures.py` — one-shot REST snapshot (extreme funding ranking + per-symbol funding/OI/L-S table).
- `scripts/capture_binance_liquidations.py` — WS liquidation capture with built-in connectivity control (aggTrade counter), auto-fallback fstream → data-stream mirror.
