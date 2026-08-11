# Indian equity / auto / EV market research — working evidence ladder (validated Aug 10, 2026)

Context: full market-environment report for Ola Electric (NSE: OLAELEC) built with every discovery backend down at once (DDG html captcha, Bing web poisoned, r.jina.ai 403, Google-News tokens dead 0/3, niftyindices/nseindia unreachable). Everything below was verified working that day.

## 1. Live quotes: Google Finance via browser (primary for prices)
- `https://www.google.com/finance/quote/NIFTY_50:INDEXNSE` → level, day %, day range, **52-wk high/low**, related indices (Sensex, Next 50, Nifty 500), news links. Redirects to `/beta/quote/` — renders fine in `browser_navigate`.
- `https://www.google.com/finance/quote/NIFTY_AUTO:INDEXNSE`, `.../quote/OLAELEC:NSE` — same shape. Sector sidebar ("Equity sectors") = NIFTY sector indices live % (breadth snapshot in one page).
- **Stock pages carry a TipRanks "Outlook" panel** (bull/bear bullets) with hard earnings facts — OLAELEC Q1 FY27: revenue ₹455cr (-45% YoY vs ₹820cr+), net loss ₹336cr (-21%), automotive revenue +71% QoQ, deliveries ~39,200 (2x QoQ), 9th straight negative-FCF quarter (~₹350cr outflow), ₹57cr PLI-penalty reversal flagged by auditors (MHI waiver not granted at quarter end), QIP ₹780cr+ oversubscribed (Jun 2026), Axis Energy BESS target 20 GWh by 2032. Also mkt cap, EPS, prev close, 52-wk range, dated news links. Cite as "Google Finance (TipRanks summary)".
- News link click may stay on GF (target=_blank/JS) — hrefs are extractable via `browser_console` if needed.

## 2. RBI primary source via curl (no browser)
- List page (curl-friendly): `https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx` — current-month rows incl. "Monetary Policy Statement, 2026-27 Resolution of the Monetary Policy Committee <dates>" with a `?prid=<id>` HTML link and a PDF link on rbidocs.rbi.org.in.
- **The rbidocs PDF is bot-challenged** (curl returns an HTML challenge page, exit 56; not a real PDF). Skip it — fetch `https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=<id>` and grep for `repo rate`, `standing deposit facility`, `stance`, `GDP growth`, `inflation`, `5.25`.
- Aug 5 2026 resolution verified this way: repo 5.25% (unanimous), SDF 5.00%, MSF/Bank Rate 5.50%, neutral stance, GDP FY27 6.7% (Q1 7.0/Q2 6.4/Q3 6.5/Q4 6.8), CPI 4.4% June 2026 (first breach after 16 months below target; food+fuel on energy spike).

## 3. Article URLs when SERPs are dead: WordPress `?s=` search
- `https://<site>/?s=<query>` then parse `<h2 ...><a href="...">title</a>` blocks. Worked: rushlane.com (found `electric-2w-retail-sales-july-2026-ev-share-crosses-11-12552825.html`), evreporter.com. Fails/junk: financialexpress.com, telanganatoday.com (search ignored). Business-standard.com 403s curl.
- Outlet-native search beats external engines (matches existing skill guidance).

## 4. Headline-level evidence when token bodies 400
- Google News RSS (`https://news.google.com/rss/search?q=<q>&hl=en-IN&gl=IN&ceid=IN:en`) titles carry the numbers: "Net Loss Narrows 21% to ₹336 Cr", "Nifty at 24,571", "Repo rate unchanged at 5.25%". Quote title + publisher + pubDate, and state the body wasn't fetched. Works for direction/magnitude claims (market-environment reports).
- Token redirects (`news.google.com/rss/articles/...?oc=5`) returned empty page / HTTP 400 / "Access Denied" — 0/3 browser resolves this session; do not burn turns.

## 5. Indian auto/EV data — three series, never agree, present both
| Series | What | Cadence | Where covered |
|---|---|---|---|
| SIAM | wholesale/domestic dispatches | monthly ~15th | ET Auto, BusinessLine, The Hindu |
| FADA | retail registrations | monthly ~7th | The Hindu, DD India; e-2W brand detail via RushLane |
| Vahan | RTO registrations | ~2-3 days after month end | EVreporter "India ICE vs EV Sales", Autocar Professional, Moneycontrol |
- Worked example July 2026 e-2W: FADA 204,362 units (+88.32% YoY, +4.82% MoM, record 11.24% of 2W retail; petrol 88.67%) vs Vahan ~192,000 (+77%, 11.2%). Brand ranking (FADA/RushLane): TVS 55,499 (+135%) > Bajaj 45,613 (+122%) > Ather 30,357 (+70%) > Hero Vida 22,900 (+111%) > Ola 14,106 (-23.5% YoY, -13.2% MoM). Vahan (EVreporter): Honda 469,466 (0.2% EV), Hero 440,537 (5.2% EV), Bajaj 25% EV, TVS 14.8% EV; EV penetration by segment: 2W 11.2%, 3W L5 52.6%, cargo 3W 31.6%, 4W 7.9%.
- Company-reported vs Vahan market share differ (Ola 8.4% company-reported Q1 vs ~7% Vahan) — quote both with labels.
- Milestones: e-2W crossed 1M units in record 7 months of 2026 (BS Jul 30); total EV retail Jul 2026 3.28L (+66% YoY, FADA).

## 6. Index valuation (Nifty P/E) fallback
- niftyindices.com (dashboard + index pages) and nseindia.com were unreachable from this host (connection timeout / reset / HTTP2 protocol error). upstox/1nvest.in/1stock1 PE pages 404 or DNS-fail. Don't retry blindly.
- Use dated media reference points and label UNVERIFIED: "Nifty PE below 5-year median" (Financial Express, May 20 2026); "valuations could fall to 18x as crude >$115/bbl" (Moneycontrol, Mar 9 2026); Reuters Nov 26 2025 "scale new highs... easing valuations".
- YTD math: Nifty closed CY2025 at 26,129 (Dec 31 2025 wrap; CY25 +10.5% per ANI/NSE Jan 1 2026) → YTD = current/26,129 − 1 (≈ -5.9% at 24,600).

## 7. Worked reference dataset — OLAELEC (all verified Aug 10, 2026)
- Price ₹40.48 (-1.44%) / ₹40.52 (-1.34%) intraday; prev close ₹41.07; 52-wk ₹22.25–₹71.25; mkt cap ₹169.3B (~₹16,931cr); EPS -₹4.16 (Google Finance).
- Price arc: IPO band ₹72-76 (opens Aug 2 2024; raised >₹6,100cr), listed Aug 9 2024 +20% day 1, day-2 ~₹107 (+41% over issue); ATH ₹157.53 (late 2024); ₹38 Dec 5 2025 (all-time low, half of IPO price, NDTV); ₹25 Feb 27 2026 (-84% from peak); March 2026 low ₹22.25; +91% from March low by Aug 5 2026 (Axis Energy pact); Q1 results Aug 7-9 2026 → -5-6% (Emkay 27% downside; brokerages up to 51% downside).
- Structural story: #1 at IPO (~30-40% share) → #5 (~7% share, July 2026); revenue -45% YoY; 9 straight negative-FCF quarters; ₹780cr QIP (Jun 2026); dealer-pivot announced Aug 6 2026 ("targets Diwali 2026 expansion").
- IPO-era anchors for comparison tables: repo 6.50% (first cut only Feb 7 2025, Groww/The Hindu); Nifty in record zone Aug 2024 but first new highs only Nov 26 2025 (Reuters); lithium ~¥90-100k mid-2024 (May-2026 ¥200k+ peak was explicitly a "two-year high", MINING.COM); e-2W penetration ~5-6% vs 11.24% now; BNEF pack $115/kWh (2024) → $108/kWh (2025, record low, -8%).

## 8. Blocked at fetch time (Aug 10, 2026) — context, not durable claims
- niftyindices.com, nseindia.com (timeout/reset/HTTP2 error); r.jina.ai 403; DDG html captcha; Bing web SERP Cloudflare-challenged AND poisoned (typingmaster junk) even with setmkt=en-IN; Google-News tokens 400/empty/Access-Denied; financialexpress.com ?s= junk; business-standard.com 403; pdftotext not on Windows-Python PATH (do fetch+extract in terminal, or use HTML versions).
- Left UNVERIFIED this session: Nifty live P/E; India-specific battery pack $/kWh; e-2W consumer loan rate %; urban/rural 2W demand split; lithium spot on Aug 10 (latest verified: ¥143,000 Jul 22 mining.com; ¥142,750 Aug 8 Brave New Coin headline).
