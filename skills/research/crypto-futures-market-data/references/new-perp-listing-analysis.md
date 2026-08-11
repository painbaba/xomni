# New Perp Listing Deep Dive (days of history, not years)

Use when the target perp listed recently. The generic deep dive
(`references/leverage-setup-deep-dive.md`) assumes 90d+ of klines, EMA200 from ~500 daily candles,
~333 days of funding history — all of that silently fails or misleads on a 10-day-old contract.
Verified end-to-end Aug 10, 2026 on GRVTUSDT (Binance perp, listed 2026-07-31 12:45Z).

## Step 0 — contract age & mechanics (BEFORE promising any history)
- `/fapi/v1/exchangeInfo` → `onboardDate` (epoch ms). GRVT: 10 days old at analysis — the "90d
  klines" pull returned only 59×4h candles. Say "N days of history exist" up front; fetch
  limit=540 and take what comes. Do NOT compute EMA200 or other long-window indicators on this.
- `/fapi/v1/fundingInfo` → `fundingIntervalHours` + `adjustedFundingRateCap/Floor`. GRVT: **4h
  interval, 2% cap** — daily funding cost is ×6 (not ×3), and the cap lets it run very hot.
  Confirm the interval empirically from `fundingRate` timestamps (00/04/08/12/16/20 UTC = 4h).
- Spot pair often absent (GRVT spot `ticker/24hr` 400s) → futures-only: no spot/perp basis arb,
  the perp IS the market, and the book is the whole liquidity story.

## Step 1 — structure on what exists
- Daily OHLC + 4h fractals (window=2) over the whole contract life. Record contract ATH/ATL.
- GLOBAL ATH from CoinGecko `coins/{id}` (`ath`, `ath_date`) — usually a pre-listing pump on
  other venues (GRVT global ATH $0.4545 Jul 30, the day before Binance listed; contract ATH
  $0.3520 Aug 5). A "-24% from ATH" headline can mean "-24% from a pump that already faded
  before this venue listed".

## Step 2 — volume profile: support vs air (cheap proxy)
Distribute candle volume across ~0.005 price buckets (loop low→high, divide volume by bucket
count). GRVT (4h profile): 0.28–0.32 = 1.19B GRVT (real accumulation base) vs 0.32–0.33 = 144M
(valley) vs 0.33–0.35 = 174M. Verdict: the proposed pullback zone in the valley is support by
structural memory (broken swing-high retest), NOT volume — grade it as such and note the real
shelf sits below.

## Step 3 — book reality check
Sum TOTAL notional per side over all 1000 depth levels. GRVT: ~$1.3M/side — a $50k market order
is ~4% of the book; slippage on entry AND exit is material. Quote: "total bids below price $X,
asks above $Y" plus depth at entry/stop/targets (±0.005 windows). Never call book depth at these
sizes "support" — it's a puddle.

## Step 4 — verify the listing-narrative with actual venue volumes
- `coins/{id}/tickers` (CoinGecko): venue volume split. GRVT: OKX $48.6M ≫ LBank $11.9M > Upbit
  $3.5M — the "Upbit listing" venue was NOT the driver; Binance futures ($99M 24h) + OKX led.
- Korean venues: `api.upbit.com/v1/ticker?markets=KRW-<SYM>` (live px), `/v1/market/all?isDetails=true`
  (pairs + caution flags), `/v1/candles/days?market=KRW-<SYM>&count=8` (volume trend). GRVT Upbit
  daily vol: 108M GRVT (Aug 5) → 3.0M (Aug 9) — the listing pump was already 97% faded while the
  perp kept pumping → "if the Upbit volume fades" is already priced in; the real fade risk is the
  main perp's own volume normalizing.
- Listing-date confirmation: Binance announcements feed (bapi composite cms article list,
  catalogId=48 — see crypto-futures-market-research skill).

## Step 5 — leverage vs stop: liq-price check (mandatory, quote it)
- 10x liq ≈ entry × 0.90; 20x liq ≈ entry × 0.947 (add ~0.5% MMR buffer).
- If stop < liq price the position is liquidated BEFORE the stop fires: GRVT entry 0.325 / stop
  0.303 → 20x liq ~0.308 = INVALID at 20x, fine at 10x (liq ~0.2925). Max leverage is capped by
  stop placement, not by appetite.
- New-listing funding eats margin fast: 3 days at +0.0862%/4h at 10x ≈ 15.5% of margin. Factor
  into holding time — a resting limit that waits days for a retest pays the piper.

## Worked numbers — GRVTUSDT, 2026-08-10 ~07:00 UTC
Listed 2026-07-31 12:45Z, perp-only. Contract low 0.2320 (Aug 2), contract ATH 0.3520 (Aug 5),
broke to 0.3583 DURING the analysis (market moved — re-snapshot before finalizing; the first
"24h high" reading was stale within the hour). Funding 4h / cap 2%: pinned +0.0050% (min)
through the chop, spiked +0.0782% → +0.0862% predicted next on the breakout. OI 4.7M → 36.5M
GRVT (+675%, $12.97M) building WITH price = healthy. Global L/S flipped 0.66→1.03 in 12h (longs
piling in) while top traders stayed net short (0.72, 42% long) = squeeze fuel overhead. Book
$1.3M/side. Plan: two-tier entry (0.335–0.345 shallow / 0.320–0.330 deep retest), stop 0.303
@10x ONLY, T1 0.40 / T2 0.45; invalidation = 4h close < 0.311 (launch-pad low), thesis dead
< 0.3048. Blocked sources this session: CoinGlass (connection timeout) and both WS liquidation
hosts (fstream blackholed, mirror handshake timeout) → liquidation clusters labeled as inferred
from funding/OI/L-S/price action.
