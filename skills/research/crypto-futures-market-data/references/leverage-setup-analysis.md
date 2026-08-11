# Leverage Setup Analysis (10-20x lens) — methodology from the Aug 10 2026 campaign

Live-verified setup-hunting playbook for Binance Futures leverage trades. Every number
in a setup card must come from a fetched API/page (klines, premiumIndex, openInterest,
topLongShortAccountRatio, orderbook/depth) — never training memory.

## Liquidation math (isolated margin, before fees)

- Liq distance ≈ 1/leverage − MMR. BTC tier-1 MMR = 0.40%, alts ≈ 0.5%.
  - 5x → ~19.6% | 10x → ~9.6% | 20x → ~4.6%
- Long liq price ≈ entry × (1 − 1/lev + MMR). Short liq ≈ entry × (1 + 1/lev − MMR).
- Binance Academy cross-checks: "10x = 8-10% adverse move to liquidation" ✓
- **Stop-before-liquidation rule**: the stop MUST sit inside the liq distance or you're
  liquidated before the stop fills. At 20x the whole budget is 4.6% → usable stops 2-3%
  (≈5-7 ATRs) = scalps only. At 10x → 3-5% stops (8-12 ATRs) = structure-based entries.
  Verdict shorthand: "20x is a scalping tool, not a holding tool."

## Sizing (1% rule)

- notional = account × 0.01 / stop%. Example: $5K account, 10x, 4% stop → $1,250 notional
  ($125 margin). Size to the STOP, never to the margin limit.
- Funding bleed is paid on NOTIONAL → leverage multiplies it against margin. 0.05%/8h ≈
  55%/yr of notional = 5.5%/yr of margin at 10x, 11%/yr at 20x. A hot-funder (GRVT +0.086%
  ≈ 2.6% of margin/day at 10x) caps hold time — shorter-hold trade only.

## Setup-card format (per pair)

1. **Trend structure**: swing highs/lows from 90d + 7d of 1h/4h klines; SMA20/50 relation;
   key support/resistance (nearest 3 levels); where price sits in the range.
2. **Crowding read**: funding now + last 3 paid (cap vs rising), OI trend (building through
   rally = healthy; draining into rally = short-covering = weak fuel), top-account L/S +
   global L/S. Extreme crowding (77-79% long) + flat price + 79-87% of 24h liq being longs
   = downside-wick risk, NOT a long entry.
3. **Plan**: entry zone, SL, 2-3 TPs, liq price at 10x AND 20x from the entry. Verify SL
   fires before liq at both. R/R ≥ 1:2 (pro target).
4. **Verdict**: LONG / SHORT / FLAT / WAIT + conviction (MEDIUM-HIGH / MEDIUM / LOW) + the
   one-line reason. FLAT with HIGH conviction on staying out is a valid, strong output.

## Pair-class taxonomy

### Majors (BTC/ETH/SOL/BNB/XRP/DOGE)
- Entries justified by price STRUCTURE only — funding is usually quiet, so positioning
  won't rescue a bad entry. BTC 55/45 L/S = neutral; XRP 77/23, DOGE 79/21 = crowded.
- Range-bound + low ATR (BTC 4h ATR 0.40% of price) = WAIT for breakout/pullback trigger;
  chasing mid-range before a macro event = paying the spread into the event.

### Alt movers (hot gainers)
- Classify pump stage: early / mid / exhausted. Signals: volume profile (still expanding
  vs fading), funding (neutral = early, spiking = late), price vs ATH/range.
- **Trap flags** (late longs = exit liquidity): volume ≫ mcap (BMT +180% on $590M futures
  vol vs $29.6M mcap = pyramid churn, 20× turnover); RSI ~96; top-10 wallets hold >75% of
  supply; no news catalyst behind the pump; funding normalized after a spike = squeeze
  already fired, not about to fire.
- Real-catalyst setups > pure momentum: exchange listing (GRVT Upbit Aug 5), revenue-backed
  project with flat funding (PUMP $1.13B mcap, $67.8M OI rising).

### Losers + squeezes
- Negative funding (shorts pay) + thin OI = squeeze fuel, BUT check if the squeeze ALREADY
  fired (funding printed −0.84% one settlement ago then normalized to −0.054% = tail, not
  peak) and if retail already flipped long (half-spent fuel).
- **Liquidity is the real killer, not direction**: live top-5 book depth of $53-$2.6K/side
  (BLUAI/EPIC/IOTX) means a $1K order moves the book several % — the stop-loss is a HOPE,
  not a guarantee. State max notional for these ($100-300) explicitly.
- Positive-funding dumps (longs pay) = no short-cover pressure = knives keep falling; the
  squeeze mechanism is absent.
- 24h volume ≫ OI (28× churn) = rotation/exit market, fresh buyers can vanish mid-candle.

## Event overlay (CPI-type macro prints)

- Positioning light + funding neutral before the print = NO crowded side to front-run;
  the trade is POST-print, not pre-print. Do nothing pre-print.
- Benign print → buy the relief; hot print → the crowded memes (77-79% long) flush
  hardest. The only true 20x-shaped window is a conditional post-print fade/buy for
  HOURS, not days.
- Unlock cliffs kill leveraged longs: check Tokenomist/Bitcoin World unlock schedules for
  the next 7-14 days BEFORE finalizing a long card; be flat by danger dates.

## Danger-zone calls worth recording as norms (Aug 2026 tape)

- "Today's low-vol, mild-long-skew, cheap-funding tape is a 10x-or-less environment" —
  when funding is ≤0.01% everywhere and ATR is tiny, the professional verdict is 10x,
  not 20x.
- New Binance futures accounts (<30 days) are capped at 20x by policy — 10-20x IS the
  legal band for new accounts; there is no "crank it to 50x" option.
