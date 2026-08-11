# Yahoo Finance API — endpoint cheat-sheet (validated Aug 10, 2026)

All endpoints below worked with a plain browser User-Agent:
`Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36`
No API key needed. Use `query1.finance.yahoo.com` (query2 also exists as fallback).

## 1. Chart / OHLCV (no auth) — PRIMARY SOURCE
```
GET /v8/finance/chart/{SYM}?interval=1d&range=2y
```
- `interval`: 1d | 1wk | 1mo | 1h | 5m ...
- `range`: 1d | 5d | 1mo | 3mo | 6mo | 1y | 2y | 5y | ytd | max
- Response: `chart.result[0].meta` (regularMarketPrice, fiftyTwoWeekHigh/Low, regularMarketDayHigh/Low, regularMarketVolume, chartPreviousClose, firstTradeDate) and `.timestamp[]` + `.indicators.quote[0].{open,high,low,close,volume,adjclose}`.
- Timestamps are UTC epoch (session start). IST = +5:30 h. `close` may be null on holiday bars — skip.
- **Live bar caveat**: during NSE hours the last bar is intraday (partial volume, provisional close). `meta.regularMarketPrice` is the live print; `chartPreviousClose` is the last completed close.
- ~500 bars at range=2y daily → enough for SMA200 and 1Y (252-bar) returns.
- When `adjclose == close` for all bars, no corporate action is in play (no split/bonus) — verify with `meta.allTimeHigh` consistency vs IPO price.

## 2. Quote summary (crumb auth) — market cap, shares, EPS
```
GET /v7/finance/quote?symbols=...        → 401 Unauthorized (crumb required; skip this)
```
Working crumb flow:
```
curl -s -c cookies.txt -H "User-Agent: $UA" "https://fc.yahoo.com/" -o /dev/null
CRUMB=$(curl -s -b cookies.txt -H "User-Agent: $UA" "https://query1.finance.yahoo.com/v1/test/getcrumb")
curl -s -b cookies.txt -H "User-Agent: $UA" \
  "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{SYM}?modules=summaryDetail,defaultKeyStatistics,price&crumb=$CRUMB"
```
Useful fields (raw + fmt):
- summaryDetail: marketCap (raw INR), averageVolume, averageVolume10days, fiftyTwoWeekHigh/Low, fiftyDayAverage, twoHundredDayAverage, dayHigh/Low, allTimeHigh, allTimeLow, priceToSalesTrailing12Months
- defaultKeyStatistics: sharesOutstanding, floatShares, heldPercentInsiders, heldPercentInstitutions, trailingEps, forwardEps, bookValue, priceToBook, profitMargins, 52WeekChange, SandP52WeekChange
- price: regularMarketPrice, regularMarketChangePercent, averageDailyVolume10Day/3Month

## 3. Symbol search (no auth) — find correct ticker
```
GET /v1/finance/search?q={company name}&quotesCount=5&newsCount=0
```
- NSE tickers end `.NS`, BSE `.BO` (field `exchange` = NSI/BOM).
- Example: "Ather Energy" → `ATHERENERG.NS` (NOT the guessed `ATHENERG.NS`).
- Returns `symbol`, `shortname`, `exchange`, `quoteType`.

## 4. Blocked / unavailable endpoints (as of Aug 2026)
- `v7/finance/quote` → 401 (use v10 quoteSummary + crumb instead).
- `v8/finance/chart/{SYM}` for a wrong symbol → `"No data found, symbol may be delisted"` — that's a ticker problem, fix via search API.

## 5. Rate limiting / throttling notes
- Batched sequential curl of 6-8 tickers in one command worked fine.
- Google web search CAPTCHAs after ~1 query; Google Finance quote pages (`google.com/finance/quote/SYM:NSE`) are bot-tolerant and matched Yahoo exactly in testing (price, OHLC, 52w range, mcap, EPS) — use as the independent second source.
