# India IPO Deep Research — verified sources & patterns (Ardee Industries run, Aug 2026)

For "deep research on <company> IPO" / "should I apply" requests. Runs on the deep swarm
(deep_run.py + topic cache), but these source URLs and patterns apply to any method.

## Verified source set (all curl-able with browser UA on this host)

| Source | URL pattern | What it's best for |
|---|---|---|
| Chittorgarh | `chittorgarh.com/ipo/<slug>/<id>/` | MOST complete: issue structure (fresh/OFS split, lot, price band, dates, listing exchange), FINAL subscription table (live), anchor details, registrar/BRLM, promoter holding, RHP docs |
| gmpipowatch | `gmpipowatch.in/ipo/<company>` | Company profile + current GMP + est. listing price + est. listing gain % |
| ipowatch | `ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/` | LIVE GMP table across all current IPOs (premium ₹, est. listing, % gain, dates, open/closed status) — one page, many IPOs |
| Finshots | `finshots.in/archive/<slug>/` | Best plain-English RHP explainer: business, financials, valuation vs peers, risks, promoter dilution, use of proceeds. LONG — agent 4500-char cap truncates; fetch full text yourself for the tail (risk section) |
| Goodreturns | `goodreturns.in/ipo/<slug>/` | Quick basics: dates, price band, lot size, min investment |
| MSN / NDTV Profit / IndiaTV / Outlook Business / IIFL | via Bing News RSS `bing.com/news/search?q="<company>"+IPO&format=rss` | News headlines, day-wise subscription snapshots, anchor investor names, "should you subscribe" articles |

Discovery pattern:
- Chittorgarh slugs are NOT guessable (`/ipo/ardee-industries-ipo/` → 404). Find the real URL from the dashboard:
  `curl -s https://www.chittorgarh.com/ipo/ipo_dashboard.asp -A <browser-UA> | grep -io 'href="[^"]*<company>[^"]*"'`
  → gives `/ipo/<slug>/<id>/` (main page) and `/ipo_review/<slug>/<id>/` (review page).
- Chittorgarh pages are nav-heavy: the real content sits deep in the stripped text. Search for anchors
  ("Issue Open", "Subscription Status", "Market Cap") rather than taking text[:4500].

## ipowatch GMP table — fastest live triage (verified Aug 10 2026)
- URL: `https://www.ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/` — REQUIRES `curl -L` (301 redirect without it → 0 bytes), browser UA, ~880KB page.
- Parse: strip `<script>`/`<style>`, regex `<tr[^>]*>(.*?)</tr>` then `<t[dh][^>]*>(.*?)</t[dh]>` per row, join cells with ` | `. Two tables on the page: (1) live list — columns `IPO Name | GMP | Trend emoji(🟢/🔴/🟡) | Price Band | Est. Listing | Date | Type(Mainboard/SME) | Status(Open/Upcoming/Closed) | Last Updated`; (2) recent listings — `IPO Price | GMP | Listing Price`. ONE fetch = full-market triage with mainboard-vs-SME + open/upcoming filters built in.
- Trend emoji = GMP direction: 🔴 on a hot IPO = cooling signal; 🟢 on an upcoming = momentum building.
- Chittorgarh IPO-page text extraction does NOT give subscription multiples: numbers that look like them (35/50/15) are CATEGORY RESERVATION %s + share counts, not subscription times. `chittorgarh.com/ipo/ipo_subscription_status.asp` is a 404. If day-wise multiples are needed, pull the dashboard's live subscription section or state the honest gap (user rule: never fabricate — snapshot-vs-final trap still applies, label clearly).
- Windows curl `-o` path trap: `/tmp/x` fails (no /tmp in git-bash) AND `-o ~/x.html` can land somewhere python can't open — always use an explicit `C:/Users/HP/<name>.html` in BOTH the curl -o and the python open() call.
- Review counts on chittorgarh dashboard rows (e.g. "Dhoot 8 Apply / 2 May Apply") are a quick sentiment signal worth quoting alongside GMP.

## Subscription numbers: snapshot vs FINAL (the trap)

Mid-issue headlines report DAILY snapshots (day-2: 14x, day-3 morning: 55x). The FINAL multiple is
published after close on the chittorgarh live subscription section (or BSE/NSE). Example (Ardee, closed
Aug 7 2026): final 138.83x = Retail 47.77x / QIB (ex-anchor) 202.26x / NII 266.75x, 41.2L applications.
Always label snapshot-vs-final; the verdict depends on the final number (allotment odds ~ 1/retail-x).

## GMP / Kostak handling

- GMP moves daily: always quote date + source (e.g. "GMP ₹15 on Aug 8 per ipowatch → est. listing ₹68 = +28.3%").
- Kostak / subject-to-sauda (STS) rates are NOT published on any website — grey-market WhatsApp channels only.
  Report as an honest gap, don't fabricate. Agents must say "no live evidence" (user rule).
- Anchor round before open tells the real demand signal (Rs cr raised, quality of names — Kacholia, MFs).
  Outlook Business / chittorgarh anchor section carry the names.

## Apply-verdict structure that worked

1. Window status FIRST (open/closed dates) — the answer to "should I apply" is often "window already closed, here's what to do instead".
2. Allotment odds from final retail subscription (≈ 1-in-retail-x for one demat; mainboard cap rules).
3. GMP/est. listing gain for the listing-day play.
4. Business one-liner + financials (revenue/profit CAGR, margins, capacity) + valuation vs peers (P/E, mcap).
5. Risk flags (customer concentration, D/E history, promoter dilution %, cyclical exposure like LME prices).
6. Exit strategy: high-subscription mainboard + positive GMP → standard play is sell-on-listing into the pop;
   long-term hold only if growth story + concentration risk justify it. Don't chase post-listing fade if not allotted.

## Post-listing HOLD-vs-SELL variant (SBIFUNDS run, Aug 2026)

Same swarm, different user ask: "got allotted, missed the listing pop, now near/below
issue price — what's the future?" Task template (10 dims x 5): ipo_recap, price_action,
q1_fy27, company_business, amc_industry, valuation, analyst_views, strengths_risks,
future_outlook, hold_sell. The hold_sell dimension must quote the USER's actual situation
(allotted at ₹X, current ₹Y, loss %).

Live price channels (curl-blocked ones marked):
- **Google Finance via BROWSER** `google.com/finance/quote/<TICKER>:NSE` — best single
  source: price, P/E, EPS, mcap, 52-wk high/low, AND a pre-written bull/bear summary
  paragraph + key bullet points (valuation cooling, peer comparison, catalysts).
  Curl returns an empty JS shell — must use browser_navigate + snapshot.
- NSE quote API blocks curl (Access Denied). Groww `groww.in/stocks/<slug>` is curl-able
  (price, P/E vs industry, ROE, 52-wk range, mcap). TradingView page carries analyst
  price-forecast min/max (e.g. ₹750 est).
- Beware Groww's "dividend yield" on fresh listings — often a one-time pre-IPO special
  dividend artifact (13.99% shown for SBIFUNDS), NOT recurring income. Flag it in the report.
- Post-IPO pattern to check: listing-day pop (all-time high = listing day), drift down
  to/near issue within weeks (valuation cooling + mixed first quarterly results vs peers),
  narrow 52-wk band since listing, anchor lock-in end dates as overhang.

Hold/sell verdict structure that worked:
1. Frame the REAL loss: near-issue price = noise, not a loss (SBIFUNDS: -0.4%).
2. Why it fell (post-IPO cooling vs Q1 miss vs sector) — from Google Finance summary +
   Q1 profit growth vs peers (SBI +3.7% vs ICICI Pru +23% / HDFC +12% = the flag).
3. Valuation reality check: P/E vs industry P/E (37.8x vs 20.6x → NOT cheap, don't average down).
4. Bull case (market leadership, AUM/share, SIP franchise, alternatives growth) vs bear
   (QAAUM sensitivity, redemption risk, premium multiple, slower profit growth than peers).
5. Concrete decision: hold (don't sell at the floor), no averaging at premium P/E, mental
   stop below the 52-wk low band, re-evaluate after the next quarterly print; analyst
   target as the upside reference (12-18 month horizon).
6. Honest gaps: broker targets beyond TradingView, exact post-OFS promoter stake, peer P/E
   table → point user to screener.in.

## Session artifacts (Ardee run, reusable as templates)
- `swarm/gen_tasks_ardee.py` — 10 dimensions x 5 questions IPO task generator (ipo_basics, gmp_market,
  company_profile, industry_sector, financials, valuation_peers, strengths_risks, use_of_funds,
  analyst_verdict, investor_verdict)
- `swarm/search_cache_ardee.py` — verified-cache example (dimension keys before catch-all "ardee industries")
- `swarm/synth_ardee.py` — report synthesizer with LIVE-VERIFIED FACTS + Gaps sections
- `swarm/report_ardee.md` — final 491-line report with per-question agent findings + citations
- SBI post-listing variant: `swarm/gen_tasks_sbi.py` / `search_cache_sbi.py` / `synth_sbi.py` /
  `report_sbi.md` — hold/sell dimension template + verified-cache with word-form-drift fixes
