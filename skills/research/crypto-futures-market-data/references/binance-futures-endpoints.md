# Binance Futures Public Endpoints (no auth) — verified Aug 2026

Base: `https://fapi.binance.com` — all market-data endpoints below are unauthenticated JSON.
Fallback mirror (same paths, use when fapi.binance.com is unreachable/blocked): `https://data-api.binance.vision`.
All timestamps are epoch **milliseconds**, times UTC. Funding settles every 8h (00:00 / 08:00 / 16:00 UTC) for USDT perps.

## Core snapshot (per symbol)

| Endpoint | Params | Returns | Use |
|---|---|---|---|
| `/fapi/v1/premiumIndex` | (none → ALL symbols) or `symbol=BTCUSDT` | `markPrice`, `lastFundingRate` (latest settled), `nextFundingTime` | current funding + next payment time; rank all symbols by \|funding\| |
| `/fapi/v1/fundingRate` | `symbol=X&limit=4` | array: `fundingTime`, `fundingRate` | last N **paid** rates (trend) |
| `/fapi/v1/openInterest` | `symbol=X` | `openInterest` (contracts), `symbol` | current OI; notional ≈ markPrice × contracts |
| `/futures/data/openInterestHist` | `symbol=X&period=4h&limit=30` | `sumOpenInterest` (contracts), `sumOpenInterestValue`, `timestamp` | 5d OI trend (30×4h buckets); 24h chg = last/[-7], 5d = last/[0] |
| `/fapi/v1/ticker/24hr` | `symbol=X` | `lastPrice`, `priceChangePercent`, `quoteVolume` | price, 24h change, volume |

## Long/short ratios (all period=1h, limit≈12 for trend)

| Endpoint | Meaning |
|---|---|
| `/futures/data/globalLongShortAccountRatio?symbol=X&period=1h` | all accounts with positions; >1 = more longs |
| `/futures/data/topLongShortPositionRatio?symbol=X&period=1h` | top-trader **position** ratio; fields `longAccount`/`shortAccount` = long/short share |
| `/futures/data/topLongShortAccountRatio?symbol=X&period=1h` | top-trader **account** ratio (same fields) |

Crowding read: position ratio >1.5 and account ratio >2 = heavily long-crowded (DOGE 2.81/3.68, XRP 1.90/3.42 were extreme in Aug 2026).

## Liquidations — REST IS GONE

- `/fapi/v1/allForceOrders` → **HTTP 404 (removed as of 2026)**. Do not retry with param variants.
- Only public liquidation feed: WebSocket `!forceOrder@arr` (all symbols) — see `scripts/capture_binance_liquidations.py`.
- ForceOrder payload: `o.S` side (`SELL` = liquidated **LONG**, `BUY` = liquidated **SHORT**), `o.q` executed qty, `o.ap` avg price, `E` event time. Notional = qty × price.
- WS hosts: `wss://fstream.binance.com` (can be blackholed from some networks — zero messages even for aggTrade) → fallback `wss://data-stream.binance.vision` (public mirror, worked).

## Verified value semantics

- Funding % = rate × 100 (e.g. 0.00006211 → +0.0062%). APR ≈ rate × 3 × 365.
- Many alts pin at exactly `0.00010000` (0.0100%) for consecutive periods = per-symbol cap, not a rising trend.
- Extreme crowding threshold: |funding| ≥ 0.0005 (0.05%)/8h; ≥ 0.001 (0.10%) very crowded.
- OpenInterestHist buckets: `sumOpenInterest` is the sum over the 4h bucket (fine for trend, not exact level).
- premiumIndex without `symbol` returns every listed perp (~hundreds) — filter `.endswith("USDT")` and sort by |lastFundingRate| for the extremes list.
