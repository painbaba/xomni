# Indian Listed-Company NEWS & EVENTS Research — Verified Recipe + Ola Electric Knowledge Bank
Validated Aug 10, 2026 on Ola Electric Mobility (NSE: OLAELEC). Pairs with the "Indian listed-company news dossiers" section in SKILL.md.

## Discovery: Bing News RSS
- Query pattern: `"<Company Name>" <event class>` — e.g. `"Ola Electric" QIP`, `"Ola Electric" CFO`, `"Ola Electric" "target price"`, `"Ola Electric" lawsuit consumer court`, `Bhavish Aggarwal sells Ola Electric shares bulk deal` (unquoted name variants surface more).
- **`OR` queries return ZERO items** (e.g. `"Ola Electric" NCLT OR tax dispute` → empty). Bing News RSS ≠ Google News RSS here. One topic per query, ~5-6 queries per batch with 1.5s sleeps.
- apiclick links decode via plain urlencoded `url=` param (`urllib.parse.unquote`), NOT the web-SERP `u=a1` base64 trick.
- **Print FULL decoded links** in any pass where you might fetch bodies later — truncated link output forces a wasteful re-query pass.

## Body fetching (r.jina.ai + keyword windows)
- Batch 6 articles per terminal call, 4s sleeps (anonymous jina tier throttles after ~a dozen rapid calls per domain).
- **Moneycontrol bodies are nav-heavy**: first-N-chars printing returns trending-stocks sidebar + logins. Correct pattern:
  ```python
  txt = fetch("https://r.jina.ai/<url>")           # Chrome UA
  txt = re.sub(r'\n{2,}', '\n', txt)
  for kw in ["revenue from operations", "Rs 336 crore", "EBITDA", "pledge"]:
      i = txt.find(kw)
      if i > 0: print(txt[max(0,i-200):i+900])
  ```
  This works on every Indian outlet that renders via jina — use it as default, not just for Moneycontrol.

## Per-outlet jina matrix (India, Aug 10, 2026)
| Renders clean via jina | Blocked / paywalled |
|---|---|
| Moneycontrol (keyword-windows), CNBC-TV18, Business Standard, Hindu BusinessLine, ET Auto, Entrackr, Deccan Herald, Outlook Business, News18, Free Press Journal, YourStory, Zeebiz, Rediff, BusinessWorld, New Indian Express | TOI (403), Financial Express (CloudFront 403), Livemint/Mint (paywall — but jina header still gives Title + Published Time, enough to cite headline+date+URL live) |

## NSE/BSE routing (both fully bot-walled from this host)
- Quote API (`nseindia.com/api/quote-equity?symbol=`) → Akamai 403 to curl, even with cookie-jar warmup.
- Corporate-filings page (`nseindia.com/companies-listing/corporate-filings-equity`) → `ERR_HTTP2_PROTOCOL_ERROR` in browser; curl 403. BSE similarly blocked.
- **Route around**: Indian press quotes exchange filings verbatim — Zeebiz ("according to a stock exchange filing"), Deccan Herald ("exchange data showed"), Hindu BusinessLine, Moneycontrol wire. QIP floors/allotments, preference allotments, board approvals all recoverable from press. Never burn turns retrying NSE.

## Price data without quote APIs
- Same-day market articles (BS/Moneycontrol "share price tanks X% after..." intraday pieces) carry: last close, intraday low/high, YTD%, 52-wk context. Dated same-day = live enough for a dossier.
- Derive total share count from promoter % disclosures: "Bhavish held 30.02% = 1,32,39,60,029 shares (Sep 2025)" → total ≈ 44.1 cr shares... **no: 132.4 cr / 0.3002 ≈ 441 cr shares** → market cap = 441 cr × price. Watch the cr-vs-absolute conversion carefully.
- 52-week range reconstruction: record-high articles ("crashed 80% from record high of ₹157.4 on Aug 20") + all-time-low articles pin the band.

## Dossier shape that worked (parent asked for)
- 15 numbered sections (products / monthly sales+share / management / fundraising / promoter-insider-pledge-ESOP / institutional / analyst TPs / suppliers / lawsuits / regulatory / factory / battery / partnerships / competitors / hidden negatives).
- Every item: WHAT happened → WHY it matters → estimated financial impact → probability → impact on valuation.
- Tables (quarterly financials, monthly registrations, analyst ratings) with each row URL-dated; explicitly label unverified cells.
- LIVE-VERIFIED FACTS section: every URL fetched + what was blocked + infra used.

---

# Ola Electric (NSE: OLAELEC) — verified knowledge bank (Aug 2025 → Aug 10, 2026)
All figures verified live Aug 10, 2026. Sources listed in the dossier at `C:\Users\HP\ola_research\OLA_ELECTRIC_NEWS_EVENTS_2026.md`.

## Price arc
- Record high ₹157.40 (Aug 20, 2025) → all-time low ₹27.36 (Feb 17, 2026) → last close ₹41.07 (Aug 7, 2026); ~₹40.37 Aug 10 intraday; +8% YTD. Market cap ≈ ₹18,000 cr (≈441 cr shares; QIP took it to ≈463 cr).
- Street: ZERO Buy ratings. Kotak Sell ₹20; Citi Sell ₹27 (cut 51% Feb 16, 2026); Emkay Sell ₹30 (3.5x EV/S); Goldman Neutral ₹40 (raised from ₹38.9). "Brokerages see up to 51% downside."

## Quarterly financials (consolidated)
| Qtr | Revenue | Net loss | Notes |
|---|---|---|---|
| Q1 FY26 (Jun 25) | ₹828 cr | ₹428 cr | pre-window |
| Q2 FY26 (Sep 25) | ₹690 cr (-43%) | ₹418 cr | first-ever Auto-segment EBITDA profit claimed |
| Q3 FY26 (Dec 25) | ~₹470 cr (-55%) | ₹487 cr | loss exceeded revenue; stock -7% → Citi downgrade |
| Q4 FY26 (Mar 26) | ₹265 cr (-57%) | ₹500 cr | |
| Q1 FY27 (Jun 26) | ₹455 cr (-45%) | ₹336 cr (7-qtr low) | EBITDA -₹165 cr; Auto GM 30.5%; regs +97% QoQ; share 5.1→8.4% |

## Sales / share (Vahan registrations)
- CY2025: 1,96,767 (halved); Oct 2025: 16,034 (-61%, Goa suspension); Dec 2025: 9,020 (share 9.3%); Feb 2026: out of top-5; Mar 2026: 10,117 (+155% MoM, rank #5 behind TVS/Bajaj/Ather/Vida); Jul 2026: declined (TVS >50k/mo, segment >1.93L); H1 2026: rivals drove 96% of segment growth. 2026 dispatch declines YoY: Feb -54%, Mar -57%, Apr -38%, May -23%, Jun -21%.

## Capital & ownership events
- QIP Jun 1–4, 2026: floor ₹37.74, indicative ₹35.86, raised ₹780 cr (oversubscribed 56%); buyers: Goldman Sachs, BNP Climate Fund, Motilal Oswal/Mirae/Kotak/JM Financial/Baroda BNP Paribas MFs; Mirae among top allottees.
- Board approved ₹2,000 cr into subsidiaries (May 14–15, 2026): ₹1,500 cr Ola Electric Technologies + ₹500 cr Ola Cell Technologies. Earlier: OET preference raise ₹877.6 cr (Sep 30, 2025); ₹127.6 cr preference shares to cell arm (Apr 27, 2026). IPO proceeds reallocated + timeline extended (Aug 22, 2025). No debt/FCCB found.
- Promoter: Bhavish sold ~₹324 cr across 3 sessions Dec 16–18, 2025 (2.62 cr @ ₹34.99 = ₹91.9 cr; ₹142.3 cr; 2.83 cr @ ₹31.9 = ₹90.3 cr) to repay ₹260 cr loan; ALL pledges released Dec 23, 2025 (stock +10% upper circuit). Promoter group 36.78% / Bhavish 30.02% (Sep 2025). June-2026 post-QIP pattern NOT verified.
- SoftBank (SVF II Ostrich): 94.94M shares sold Sep 4, 2025 (stock fell below IPO ₹76); 15.6% → 13.53% (Jan 8–9, 2026). ~13% overhang remains.

## Management / governance
- CFO Harish Abichandani resigned; Deepak Rastogi appointed (Jan 19–20, 2026; stock -8%, 10-session losing streak).
- Livemint (Aug 19, 2025): Bhavish missed >3/4 of FY25 board meetings. "Lack of financial control sweeps across Ola Electric" (Livemint Sep 4, 2025). Bhavish admitted service challenges hurt brand trust (Feb 13, 2026).

## Legal / regulatory
- Employee-suicide FIR (Bengaluru, Oct 20, 2025): Bhavish + Subrath Kumar Das (Head of Vehicle Homologation) named; company challenged.
- Goa: Vasco trade licence cancelled, Margao suspended (Nov 12, 2025).
- Bailable arrest warrant (Goa consumer case) stayed by Bombay HC Feb 17, 2026 (stock +4–5%); HC later called the consumer order "perverse" (Apr 11, 2026).
- Consumer verdict: full refund for defective S1 X Plus (Jun 16, 2026).
- Q1 FY27: company moving to SETTLE a SEBI probe (Aug 7, 2026; subject paywalled). Auditors red-flagged PLI penalty provision REVERSAL without approval (Aug 9–10, 2026; stock -5%). PLI mandate: ₹225 cr/GWh investment within 2 years. First PLI certification in Roadster portfolio (Apr 2, 2026).

## Products / battery / capacity / partnerships
- Products: S1 Pro+ w/ 4680 Bharat Cells deliveries (Nov 4, 2025); Roadster X+ Bharat-Cell CMVR cert (Dec 29–30, 2025); Roadster 9.1 cut ₹60,000 (>30%, Apr 1–2, 2026); S1 X+ 5.2 kWh ₹1,29,999 intro (Apr 13, 2026); Roadster X ₹79,999 Holi promo (Mar 3, 2026); commercial e-scooter for gig workers (ARAI nod Feb 2026, announced May 27, 2026); 1M production milestone + special-edition Roadster X+ (Sep 15–16, 2025). NO electric-car program news in window.
- Battery: ARAI nod 4680 pack (Oct 28, 2025); LG tech-leak claims rebutted (Nov 9–10, 2025); Bharat Cell platform opened to enterprises/startups (Jan 14–15, 2026); in-house LFP 46100 ready (Apr 7, 2026) + BIS certified (Jun 24, 2026); cell-supply talks with global automakers (May 13–14, 2026).
- Capacity/strategy: dealer-network pivot (Aug 6–8, 2026; ~1,000 dealer enquiries, Diwali-2026 footprint target) — ends direct-sales-only model; 6 GWh cell ramp; gigafactory chasing BESS/drones/defence (NDTV Profit Aug 8, 2026).
- Partnerships: Axis Energy MoU for up to 20 GWh BESS by 2032 (Aug 4–5, 2026; 5 GWh/yr from 2028; no financial terms); Mahashakti BESS platform launches Aug 15, 2026; Ola Shakti residential ESS (Oct 16, 2025; first gigafactory unit Jan 12, 2026).

## Not found (verified absent in window)
Delisting rumors; insurance disputes; supplier disputes; FCCB/debt; electric-car program; Ola ESOP dilution events; June-2026 shareholding pattern (unverified).

## Monitoring triggers (next 90 days from Aug 10, 2026)
Aug 15 Mahashakti launch → Q2 FY27 cell-revenue disclosure → SEBI settlement outcome → Jul–Aug registration trend vs Q1's +97% QoQ → further SoftBank block sales.
