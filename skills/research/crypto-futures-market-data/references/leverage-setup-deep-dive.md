# Per-Symbol Leverage-Setup Deep Dive (technicals + liquidity track)

Verified end-to-end Aug 10, 2026 on PUMPUSDT (worked example with numbers at the bottom).
Use when the ask is a single-symbol long/short setup with leverage: "refine entry/stop/target",
"where are longs stacked", "is the pullback zone real support", 3-scenario map + invalidation.

## Data pull (Binance fapi, no auth — all in one script)

- Klines 1d (limit 500) for EMA200/50/20. Klines 4h + 1h over 90d (paginate: limit 1500, advance `startTime = last[0]+1`, cap ~2500 bars).
- `depth?symbol=X&limit=1000` — full book snapshot for depth-at-levels.
- `openInterest` (notional = contracts × lastPrice), `openInterestHist` period=5m limit=288 (24h) AND period=1h limit=168 (7d).
- `fundingRate` limit=1000 (≈333 days of 4h settles), `premiumIndex` (mark, lastFundingRate, nextFundingTime).
- `globalLongShortAccountRatio`, `topLongShortPositionRatio`, `topLongShortAccountRatio`, `takerlongshortRatio` (period=1h).
- `ticker/24hr` for range + volume + change.

## Analytics recipes

### EMA200 breakout — compute PROGRESSIVELY, or you get a bogus cross date
```python
k = 2/201; e = closes[0]; ema = [e]
for c in closes[1:]:
    e = c*k + e*(1-k); ema.append(e)
cross = next(i for i in range(200, len(closes)) if closes[i] > ema[i] and closes[i-1] <= ema[i-1])
```
Do NOT compare closes against the single final EMA value (e.g. `closes[i] > e_final`) — that found a
"cross" on Jan 1 when the real first close-above-EMA200 was Jul 27 (PUMP, Aug 2026). Also check the
retest: last bar where close within ~1% of EMA200, and max extension % — tells you if the pullback
zone is ON the EMA (it usually isn't: 0.00272 zone was +31% above EMA200 = pivot support, not EMA).

### Depth at levels (order book)
```python
bids = [(float(b[0]), float(b[1])) for b in d['bids']]; asks = [(float(a[0]), float(a[1])) for a in d['asks']]
def depth(lvl, side):  # side 'bid': notional resting AT/ABOVE lvl; 'ask': AT/BELOW lvl
    return sum(p*q for p,q in (bids if side=='bid' else asks) if (p >= lvl if side=='bid' else p <= lvl))
```
Compute for entry/stop/target levels. Also report biggest single wall per side (can be a 100M+ coin
order = real floor/ceiling or a spoof — label as such). Typical reads: thin book vs OI notional =
few-$M moves price; 1-tick spread on majors, wider on microcaps.

### OI trend framing — always 3 horizons
- 24h (5m buckets, first vs last) — building through TODAY's leg?
- 7d (1h buckets) — building through the RALLY, or flat/churning? PUMP: +39% rally on −2.8% 7d OI
  = spot-led/short-covering rally; only the final ATH leg added OI (+5.7% 24h, +3.2% last 75 min).
- 7d min/max spread — churn range (±13% was the PUMP signature, not a monotonic build).
- Sample OI at key swing timestamps (nearest 1h bucket) to attribute OI to legs.

### Liquidation cluster estimation (model, not direct data — say so)
- Long liq ≈ entry × (1 − 1/lev), minus maintenance/fees (add ~0.2-0.5% buffer).
- Entry zones come from price action (recent swing structure) + volume profile (below).
- Cross-check against bid walls from depth: a 10x-long cluster landing exactly on a 154M-coin bid
  wall = support magnet + flush target if the wall breaks.
- Short liq ≈ entry × (1 + 1/lev): shorts opened fading the rally are squeeze fuel above.
- Confirm direction of crowding with CoinGlass per-symbol liq split (below) — e.g. PUMP 24h liqs
  were 84.5% SHORTS during a rally = shorts are the crowded side; longs were NOT stacked below.

### Volume profile (cheap, from 1h klines)
Distribute each candle's notional (v × mid) across price buckets between low and high; rank nodes.
PUMP: 0.00272-0.00276 zone = 2.0% of 7d volume (thin), 0.00245-0.00260 = ~22% (real shelf).
Use it to grade "is this pullback zone real support" beyond swing-level confluence.

### THE stop-vs-liquidation coherence check (quote before recommending leverage)
If stop distance > liquidation distance (≈1/lev ignoring fees), the stop NEVER fires — the position
is liquidated first. PUMP example: entry 0.00274, stop 0.00252 (8% risk) is fine at 10x (liq
~0.00248-0.00250) but at 20x liq ≈ 0.00260-0.00262 is ABOVE the stop → unmanageable. Present a
table: per-leverage liq price vs proposed stop, and adjust stop or leverage so stop fires first with
≥1% buffer. Add slippage caveat for thin books (stop fills can be 10-20% worse in a cascade).

## CoinGlass per-symbol liquidation page (SPA navigation, verified)
Direct URL 404s. Path: homepage `coinglass.com/` → nav link "Liquidation" → click the symbol in the
heatmap list → URL becomes `coinglass.com/liquidations/<SYMBOL>`. Gives: 24h Long/Short $ split
(+ %), "Market Liquidation Status: Mostly Short/Long", largest single liq, peak liq hour, multiple
vs 7d avg (e.g. "2.35x Extreme"), per-exchange table with long/short, and a LIVE liquidation feed
(Symbol/Price/Value/Time). Homepage itself is useful for free: per-symbol RSI(4h) leaderboard
(PUMP was 78.96 = #4 most overbought market-wide) and 1h liquidation leaderboard.

## Live Binance liquidation WS — fallback that actually worked
`wss://fstream.binance.com` was blackholed from this host (control=0 → discard). The skill's capture
script exited after the first host on CONTROL==0 without trying the mirror; the manual mirror run
worked (control 749 aggTrades in 90s = provably live, 0 PUMP forceOrders = genuinely quiet tape):
```python
# wss://data-stream.binance.vision/ws/btcusdt@aggTrade/!forceOrder@arr
# S=SELL -> liquidated LONG, S=BUY -> liquidated SHORT; filter o['s']=='<SYM>'
```

## TradingView listing check
`curl https://www.tradingview.com/symbols/<SYM>/` → meta tags give exchange + description
("PUMP / TetherUS", BINANCE). The `"price"` in the HTML is a STALE server render (0.002689 vs live
0.002849) — cite it only as listing confirmation, never as the quote.

## Report format for this class (user's requirements)
1. Snapshot (price, 24h chg, mark, funding, OI notional, vol, timestamp UTC).
2. Chart structure: EMA200 breakout date + retest + current extension %, swing map, verdict on the
   pullback zone (on-EMA vs pivot vs volume-shelf).
3. Order book: top-10 summary, depth at entry/stop/targets, big walls.
4. OI: 24h/7d/intraday change + attribution to rally legs (build vs churn).
5. Funding + L/S + liquidation clusters (model-based, labeled).
6. Refined entry/stop/target table — per-leverage liq prices, RR, size note.
7. 3-scenario map (bull/base/bear with % probability + trigger conditions) + EXACT invalidation level.
8. LIVE-VERIFIED FACTS: every URL fetched, blocked sources stated explicitly (e.g. fstream
   blackholed), timestamps, provenance. Plain English throughout.

## Worked example — PUMPUSDT Aug 10 2026 06:22 UTC (numbers above all from this session)
Price 0.0028490 (+14.28%), ATH 0.002885 printed 06:00 UTC same day. EMA200 0.0020663 (price +37.7%),
breakout Jul 27, retest Jul 29-30. Pullback zone 0.00272-0.00276 = Aug 9 breakout-candle high +
today's 4h low, 2.0% of volume, $2.3M bids → real but thin pivot. Depth: bid walls 154M coins @
0.00250, ask 141.7M @ 0.0030. OI $67.4M: +5.74% 24h, −2.76% 7d, +3.2% last 75 min = final-leg
build. Funding −0.0003%, 120-period avg +0.0027%/4h = no long crowding. CoinGlass: 24h liq $2.74M,
84.5% shorts (Hyperliquid 38.8% all-short, Binance $639K short), 1h 98% shorts = squeeze fuel above
(~0.00297 at 10x); long liq clusters est. 0.00257-0.00271 (20x today's longs) and 0.00243-0.00257
(10x). Plan: limit 0.00272-0.00276 @10x, stop 0.00252 (fires before liq ~0.00248), T1 0.00305 /
T2 0.0032 / T3 0.0035; 20x variant needs stop 0.00262 (liq ~0.00260, 1.3% buffer) — 8% stop at 20x
is unexecutable. Invalidation: 4h close < 0.00272 (trade), < 0.00262 (thesis dead → 0.00245-0.00250
shelf).
