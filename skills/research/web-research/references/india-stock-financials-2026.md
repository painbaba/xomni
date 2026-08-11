# Indian Listed-Company Financials — Verified Sourcing Ladder (Aug 10, 2026)

Validated end-to-end on OLAELEC (Ola Electric Mobility) valuation research: quote/market data, 13-quarter results history, annual P&L, balance-sheet cash, share count post-QIP, peer comps, broker targets. All URLs live-tested this session.

## Blocked at fetch time (don't burn turns)
- **moneycontrol.com** quote pages AND news articles — "Access Denied" via browser AND curl (bot wall). r.jina.ai returns nav chrome only for their pages.
- **NDTV Profit**, **MSN.com** article bodies — Access Denied / empty via jina.
- **NSE/BSE** (nseindia.com, bseindia.com) — bot-blocked; the official Q1 results filing PDF stayed unreachable. Workaround: filing content mirrored on **stockwatch.live** (see below).
- **trendlyne.com** — 404 on guessed slugs; **investing.com** — nav junk.
- Google News RSS token links (`news.google.com/rss/articles/...`) are DEAD (HTTP 400) — use the RSS title as a search query instead.

## Working ladder (in order of value)
1. **Google Finance via browser** — `google.com/finance/quote/SYMBOL:NSE` renders fully: price, mkt cap, 52-wk high/low, EPS, shares outstanding, P/E, dividend, related stocks, and a news-headline list with outlet + age (great discovery: "Q1 results, net loss narrows to Rs X, revenue falls Y%" headlines). Verified: OLAELEC, BAJAJ-AUTO, ATHERENERG. Note: GF mkt cap can use a stale pre-issue share count (OLAELEC showed ₹179.18B on 4.42B shares while the true post-QIP count is 4.63B → recompute mkt cap = price × verified shares).
2. **TradingView India scanner API** (curl POST, JSON out, no auth):
   `curl -X POST https://scanner.tradingview.com/india/scan -H "Content-Type: application/json" -d '{"symbols":{"tickers":["NSE:OLAELEC","NSE:TVSMOTOR","NSE:HEROMOTOCO"],"query":{"types":[]}},"columns":["name","close","market_cap_basic","price_earnings_ttm","price_sales_ttm","total_revenue_ttm","ebitda_ttm","52_week_high","52_week_low","shares_outstanding"]}'`
   Returns INR values; nulls for companies with thin coverage (P/E etc. null for loss-makers — expected). **Pitfall: some tickers silently return totalCount 0** (NSE:BAJAJ-AUTO failed twice) — fall back to Google Finance for those.
3. **screener.in** (plain urllib + Chrome UA, no JS needed): `/company/SYMBOL/consolidated/` — the gold mine:
   - Quarterly results table: 13 quarters × (Sales, Expenses, Operating Profit, OPM%, Other Income, Interest, Depreciation, PBT, Tax%, Net Profit, EPS)
   - Annual P&L: FY2021→latest + TTM (Sales, Expenses, Op Profit, OPM, Other Inc, Interest, D&A, PBT, Net Profit, EPS), CAGR, ROE
   - Balance sheet, cash flow (CFO/CFI/CFF/Net/FCF), ratios (debtor/inventory days, ROCE), market cap, book value, ROCE/ROE, pros/cons alerts, index membership
   - **Caveat: screener merges cash into "Other Assets" — no separate cash line. Use stockanalysis.com for cash.**
   - Market cap uses the updated post-issue share count (OLAELEC: ₹18,773 cr @ ₹40.6 → implies 4,624M shares post-QIP ✓) — useful cross-check for share count.
   - Parse note: "Profit & Loss"/"Balance Sheet" strings appear in the nav FIRST — take the LAST occurrence (`t.rfind()`), then slice to the next section marker.
4. **stockanalysis.com** (plain urllib): `/quote/nse/SYMBOL/financials/balance-sheet/`, `/financials/`, `/financials/cash-flow/` — full balance sheet **in ₹ millions (÷10 = ₹ crore)**: Cash & Equivalents, Short-Term Investments, Trading Asset Securities, Total Debt, **Net Cash (Debt)**, Receivables/Inventory/Other Current Assets, Total Assets/Liabilities/Equity, **Filing Date Shares Outstanding**, Book Value Per Share, PP&E/CWIP detail. TTM column = latest quarter (can lag right after results — cross-check). Cross-validation: Total Assets must match screener's (OLAELEC Mar-26: ₹7,788 cr on both ✓). **Some symbols 404** (BAJAJ-AUTO) — accept and move on.
5. **Company IR site** — fetch the IR page, regex `href="([^"]+\.pdf)"`, look for quarterly shareholders' letters / results PDFs (often on a CDN like cdn.<company>.com). Download with curl, extract with **pdftotext (ships in git-bash at /mingw64/bin/pdftotext)**. Image-based metric tables extract as interleaved column text — readable, but cross-check rows against screener (segment CFO/FCF/PAT tables came through).
6. **Bing News RSS** — `bing.com/news/search?q=<quoted query>&format=rss`; decode the `url=` param in apiclick links. Best backend for Indian market news: Q1 results coverage, broker target prices, auditor-flag stories, QIP news. Batch 4-6 queries per execute_code call.
7. **r.jina.ai** — renders article bodies these publishers block:
   - **Hindu BusinessLine** (thehindubusinessline.com): full brokerage-coverage articles render completely (target prices, ratings counts, EBITDA comments) — best single source for "what do the brokers say".
   - **CNBC TV18** (cnbctv18.com): full body works but nav junk precedes it — slice from the article's first sentence marker (`t.find("Shares of <Company> ...")`), not from the top.
   - **stockwatch.live** — mirrors BSE/NSE corporate-action filings (QIP allotment: share count, issue price, discount-to-floor; auditor appointments; trust deed changes). The discount-to-floor lets you back out the SEBI floor price: floor = price ÷ (1 − discount).
8. **DDG-via-jina** (`r.jina.ai/https://duckduckgo.com/html/?q=...`) — URL discovery when you only have a headline; grep `## [Title](url)` blocks, decode `uddg=` params.

## Share-count & unit math (verify, don't trust)
- **Shares from equity capital**: equity capital ₹4,411 cr @ ₹10 face value = 4,411/10 = 441.1 cr shares = 4.411B. (OLAELEC: 4,411M at Mar-26 BS.)
- **QIP**: 217,578,428 shares @ ₹35.86 = ₹780.24 cr; 4.98% discount to floor → floor = 35.86/0.9502 = ₹37.74 ✓ (matches news). Post-QIP = 4,411 + 217.6 = **4,628.6M shares**.
- **Unit traps**: TradingView mkt cap = ₹ (INR); stockanalysis = ₹ millions (÷10 → crore); screener = ₹ crore. Always sanity-check one figure across ≥2 sources (OLAELEC TTM revenue: TradingView ₹18.8B = screener ₹1,880 cr ✓; FY26 net loss: screener −1,833 = scanx/ANI headlines −1,833 ✓).
- **TTM revenue** = sum of last 4 reported quarters (screener quarterly table) — equals TradingView total_revenue_ttm when both current.
- Media-reported revenue can differ from screener by scope (~3%): FY25 Ola ₹4,645 cr (media) vs ₹4,514 cr (screener) — cite screener + note the alternative.

## Loss-making equity valuation playbook (used for OLAELEC)
1. **Multiples**: P/Sales + EV/Sales (EV = mkt cap + total debt − cash). P/E n/a → quote P/E only for profitable peers. Compute historical range at 52-wk high/low.
2. **Peer comps table**: mkt cap, TTM revenue, P/S, P/E (where positive), EBITDA TTM, growth status (Ather at 13.8x P/S loss-making vs TVS 3.5x profitable — the spread IS the analysis).
3. **Scenarios (bear/base/bull)**: revenue via unit volume × ASP; EBITDA = GM×rev − opex; net ≈ EBITDA − D&A − interest + other income; CFO/FCF per quarter; track cumulative FCF vs starting cash; terminal price = terminal-year revenue × P/S band ÷ end share count (incl. scenario dilution). Assign probabilities; report probability-weighted price vs current.
4. **Reverse DCF**: implied terminal revenue = EV ÷ terminal P/S; implied EBITDA = EV ÷ EV/EBITDA. State what the current price assumes (OLAELEC at ₹40.54: FY29 revenue ~2–3.7x FY26 with EBITDA breakeven AND zero further dilution — i.e., base case fully priced, no margin of safety).
5. **Cash runway**: cash ÷ quarterly CFO (conservative) and ÷ quarterly FCF (stricter); also under the company's stated cost plan. Report months, not quarters.
6. **Dilution risk**: scenario cumulative FCF − available cash = raise size; shares issued = raise ÷ assumed price; new share count → recut per-share values (bear dilution on top of a falling multiple compounds fast).

## OLAELEC worked dataset (Aug 10, 2026 — reuse, don't re-fetch)
- Price ₹40.49–40.54; 52wk ₹22.25–71.25; shares 4,628.6M; mkt cap ~₹18,750 cr; EV ₹20,818 cr (debt ₹2,763 − cash ₹709, Mar-26).
- FY25: rev ₹4,514 / net −₹2,276 | FY26: rev ₹2,253 / net −₹1,833 (deliveries 173,794; CFO −775, FCF −1,301) | Q1 FY27: rev ₹455 (−45% YoY), net −₹336, GM 30.5%, adj EBITDA −195, CFO −215, FCF −351; orders 44,071, deliveries 39,192; E2W share 5.1%→8.4%.
- Cash: ₹709 cr (Mar-26) + ₹780 QIP (Jun-26) → ~₹1,000 cr est. current; runway 9–14 mo at current burn, ~22 mo under plan.
- Peers: Ather ₹1,483 / ₹58,476 cr / P/S 13.8x (EBITDA+ first time Q1 FY27; QIP ₹1,300 cr @ ₹1,202 Jul-26); TVS ₹4,444 / ₹209,110 cr / 3.48x / P/E 61.6; Bajaj ₹11,779 / ₹324,000 cr / 4.53x / P/E 28; Hero ₹5,898 / ₹114,613 cr / 2.26x / P/E 21.7.
- Broker coverage post-Q1: 0 buy / 2 hold / 6 sell; Kotak ₹20, Citi ₹26, Emkay ₹30, Goldman neutral ₹40. Auditor-flagged ₹57 cr PLI penalty reversal (MHI approval pending).
- Sources used: screener.in/company/OLAELEC/consolidated/, stockanalysis.com/quote/nse/OLAELEC/financials/balance-sheet/, google.com/finance/quote/OLAELEC:NSE, scanner.tradingview.com/india/scan, cdn.olaelectric.com Q1 FY27 shareholders' letter PDF, stockwatch.live QIP allotment article, thehindubusinessline.com brokerage article (via jina), cnbctv18.com auditor-flag article (via jina), Bing/Google News RSS.
