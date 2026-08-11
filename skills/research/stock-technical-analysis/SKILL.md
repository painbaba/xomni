---
name: stock-technical-analysis
description: Use when producing a live-verified stock technical report.
---

# Stock Technical & Market Data Reports (live-verified)

## When to use
User asks for a technical/market report on a stock/ETF: current price + market cap + 52w range + liquidity; exact returns over windows; daily AND weekly chart structure; 20/50/100/200-day MAs + RSI/MACD/volume; relative strength vs index and peers; labeled BULLISH / BEARISH / CRITICAL SUPPORT / TECHNICAL INVALIDATION levels; ending with a LIVE-VERIFIED FACTS section. Works for NSE (`.NS`), BSE (`.BO`), US tickers.

## Hard rules (user's standing requirements)
1. **Never assert price/levels/returns from training memory.** Every figure must come from a fetched source, quoted with its URL. If a source blocks you, say so explicitly in the report.
2. **Anchor on live-fetched price.** If the user gives a reference close (e.g., "approx Rs 40.54"), verify it against the fetched data, don't assume it.
3. Report must end with a **LIVE-VERIFIED FACTS** section: every URL fetched, every key figure + its source, and a list of blocked sources.
4. **Compute indicators yourself** from the raw OHLC series (SMA/RSI/MACD/ATR/returns) — exact, reproducible numbers; never copy indicator values from third-party pages.
5. Quote returns with exact % AND the base close/date. Flag the last bar if it is **intraday/live** (provisional).

## Fetching price data — Yahoo chart API, no auth needed
```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
curl -s -H "User-Agent: $UA" "https://query1.finance.yahoo.com/v8/finance/chart/SYM.NS?interval=1d&range=2y" -o sym_daily.json
curl -s -H "User-Agent: $UA" "https://query1.finance.yahoo.com/v8/finance/chart/SYM.NS?interval=1wk&range=2y" -o sym_weekly.json
```
- `interval=1d|1wk`, `range=1mo|3mo|6mo|1y|2y|5y|max`. **2y daily ≈ 500 bars** — enough for SMA200 + all return windows.
- `meta` holds 52w high/low, live price, day H/L, volume. `indicators.quote[]` holds OHLCV arrays; `timestamp` is UTC epoch → **add 5:30 h for IST dates**.
- Return-window bars: 1M=21, 3M=63, 6M=126, 1Y=252 (use `closes[-n]` as base).
- Fetch all tickers (stock + index + peers) in ONE batched curl loop — saves round-trips.

## Market cap / shares / EPS — crumb-authenticated quoteSummary
`v7/finance/quote` returns **401** — use v10 quoteSummary with a crumb:
```bash
curl -s -c cookies.txt -H "User-Agent: $UA" "https://fc.yahoo.com/" -o /dev/null
CRUMB=$(curl -s -b cookies.txt -H "User-Agent: $UA" "https://query1.finance.yahoo.com/v1/test/getcrumb")
curl -s -b cookies.txt -H "User-Agent: $UA" \
  "https://query1.finance.yahoo.com/v10/finance/quoteSummary/SYM?modules=summaryDetail,defaultKeyStatistics,price&crumb=$CRUMB" -o sym_quoteSummary.json
```
Gives marketCap, sharesOutstanding, floatShares, heldPercentInsiders, trailingEps, fiftyDayAverage, twoHundredDayAverage, averageVolume, 52WeekChange. Note: Yahoo marketCap is raw INR (e.g., 179044941824 = ₹17,904 cr) — quote both forms if user thinks in crore.

## Ticker discovery
Guessing NSE symbols fails (Ather is **ATHERENERG.NS**, not ATHENERG.NS). Use the search API:
`https://query1.finance.yahoo.com/v1/finance/search?q=Ather%20Energy&quotesCount=5&newsCount=0` → returns correct exchange symbol.

## Compute indicators locally
Run `scripts/yahoo_tech_analysis.py <daily.json> [weekly.json]` — prints returns (1D..1Y with base dates), SMA/EMA 20/50/100/200 + price position %, Wilder RSI(14) (daily + weekly), MACD(12,26,9) + cross dates, ATR(14), swing highs/lows (fractal k=2), gap scan (>0.5%), avg volumes, month-end closes. All functions were validated in production (see references/yahoo-finance-api.md).

## Cross-verification — Google Finance (bot-friendly second source)
`https://www.google.com/finance/quote/SYM:NSE` — shows live price, day O/H/L, 52-wk range, market cap, EPS, a **news panel with headlines+numbers** (e.g., "Net loss narrows to Rs 336 cr but revenue falls 45%"), and TipRanks AI bull/bear summaries. In the OLAELEC session every Yahoo figure (price, OHLC, 52w range, mcap, EPS) matched Google Finance exactly. Use it to confirm everything you quote and to grab catalyst context (results dates, QIP/block deals).

## Indian-stock fundamentals & news (works when the big sites are blocked)
- **Screener.in works with a plain UA** — the fundamentals goldmine when NSE/Moneycontrol/Trendlyne 403. URL: `https://www.screener.in/company/<NSE_SYMBOL>/` (e.g. `/company/SSDL/`; Yahoo symbol may differ from the NSE symbol — resolve via Yahoo search API first). Gives: 10 quarters of quarterly results, 5-yr P&L, balance sheet, cash flow, ratios (inventory/debtor days, cash-conversion cycle, working-capital days, ROCE), shareholding incl. shareholder-count trend, machine-generated pros/cons, and "Upcoming result date" (the earnings-catalyst field — e.g. "14 August 2026"). Cross-check its mcap/CMP header against Yahoo — they should agree.
- Parse recipe + section ids + corporate-action scan snippet: `references/india-stock-fundamentals-and-news.md`.
- **Google News RSS = dated headline timeline, no auth** (works when Google web search and DDG html are CAPTCHA'd): `https://news.google.com/rss/search?q=<query>%20when:2y&hl=en-IN&gl=IN&ceid=IN:en` → 30+ dated items with source names. Enough to build a 12-month catalyst timeline (results dates, margin-collapse headlines, pledge/governance disclosures like "promoter confirms no encumbrance"). Pitfall: item links are JS-gated Google News redirects — RSS is reliably headlines-only; get full text via the publisher site or exchange filings.

## Known blocked sources — report them, don't fight them
- **NSE India** site & `/api/quote-equity` → 403 Akamai (browser: ERR_HTTP2_PROTOCOL_ERROR; curl: Access Denied)
- **Moneycontrol** → "Access Denied" · **Trendlyne** → 403 CloudFront · **Stooq CSV** (`stooq.com/q/d/l/`) → JS proof-of-work challenge
- **Google web search**: ~1 query free, then `/sorry` CAPTCHA — use the Google Finance page instead; DuckDuckGo html → challenge
- **Yahoo v7/finance/quote** → 401 (use quoteSummary+crumb above)
When one of these is needed and blocked, state it in LIVE-VERIFIED FACTS and rely on the working pair (Yahoo API + Google Finance).

## Pitfalls
- **Last bar may be LIVE**: if fetch happens during NSE hours (09:15–15:30 IST), the final bar is intraday — partial volume, provisional close. Label it clearly, use the prior bar for completed-day stats, give the day range.
- **Data quirks**: duplicate closes on consecutive days (e.g., 41.44 on both Aug 5–6 in the OLAELEC 2y series) — flag as a Yahoo quirk, verify it doesn't move any level, never "fix" silently.
- **Huge single-day volume (5–10x average) = corporate event**: block deal / QIP allotment / results day. Check the news panel before calling it accumulation/distribution.
- **Gaps**: scan >0.5% of price; filled gaps are not levels; only cite unfilled gaps near current price.
- **Corporate actions**: check consistency of all-time high vs IPO price (157.40 IPO pop in OLAELEC rules out any split). If adjclose == close throughout, no adjustment is in play. To detect splits/bonus/dividends precisely, scan the adjclose/close ratio per bar — a change >~0.0005 marks an adjustment; correlate the change dates with ex-dividend dates (constant small ratio across the whole series = dividends only; a big step = split). 
- **`meta.chartPreviousClose` can be garbage** (SSDL: reported 194.0 vs actual prior close 53.83) — always read the last completed bar from `indicators.quote[]`, never from chart meta.
- **Yahoo marketCap is raw INR → divide by 1e7 for crore** (2,145,517,184 = ₹214.5 cr, NOT ₹2,145 cr — misread mid-session). Sanity-check mcap ≈ price × sharesOutstanding and cross-check against Screener.in's header.
- **Date the user's cost basis in the series**: locate the entry price among historical closes (SSDL ₹166 ≈ 26–28 Aug 2024) — then loss % (−67%) and the breakeven multiple needed (+206%) become concrete report numbers instead of abstractions.
- **Relative strength**: compute peers over the SAME windows as the stock (1M/3M), and state index level + 52w context (e.g., peer at 52w high).

## Report structure (user's template — follow exactly)
1. Market data snapshot: price, day change/range, market cap, shares, 52w H/L **with dates**, ATH/ATL, avg volumes, ATR
2. Returns table 1D/1W/1M/3M/6M/1Y — exact % + base close + base date
3. Daily AND weekly chart structure: trend state, HH/HL/LH/LL sequence, S/R levels, gaps, accumulation/distribution read, volume trend
4. MAs 20/50/100/200 with price position %, RSI(14), MACD, cross dates (golden/death)
5. Relative strength vs index and vs peers (same windows, % + levels)
6. Labeled levels: 🟢 BULLISH (above which structure improves), 🔴 BEARISH (below which it breaks down), ⚠️ CRITICAL SUPPORT, ❌ TECHNICAL INVALIDATION
7. **LIVE-VERIFIED FACTS**: URL → what it provided; blocked sources listed; verification status statement
