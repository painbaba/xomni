# India government research — PIB recipe + EV policy knowledge bank (verified Aug 10, 2026)

Companion to the "Indian government / regulatory research" section in SKILL.md. All facts below were
live-fetched on Aug 10, 2026; PRIDs are the canonical pib.gov.in release IDs.

## PIB fetch recipe (what works / what doesn't)
- Direct `curl pib.gov.in` → JS shell / 0 bytes; `www.pib.gov.in/index.aspx` 301s around; PIB site search = JS-only (jina returns ~300B). Skip all of these.
- WORKING: (1) jina-DDG site-search → `r.jina.ai/https://duckduckgo.com/html/?q=site:pib.gov.in+<topic>` ; (2) decode `uddg=` params to get `https://pib.gov.in/PressReleasePage.aspx?PRID=NNNNNNN`; (3) read via `r.jina.ai/<PRID URL>` — full text incl. posted-date line "प्रविष्टि तिथि: DD MMM YYYY by PIB Delhi".
- URL variants that all render via jina: `PressReleasePage.aspx?PRID=`, `Pressreleaseshare.aspx?PRID=`, `PressReleaseIframePage.aspx?PRID=` (append `&reg=3&lang=1` for English where a page comes back Hindi).
- Ministerial written replies (Lok Sabha/Rajya Sabha) carry the best aggregate numbers — e.g. "as on 31.12.2024", "till date no beneficiary firm has claimed any incentive".
- `heavyindustries.gov.in` (MHI) curls cleanly (200) for scheme pages.

## India EV-policy verified facts (as of Aug 10, 2026 — point-in-time)

### FAME-II (ended)
- ₹11,500 cr budget, ran 1 Apr 2019 – 31 Mar 2024 (PIB PRID 2102782, Rajya Sabha reply 13 Feb 2025). e-2Ws supported: 14,28,009 as of 31.12.2024 (same release).
- e-2W rate cut ₹15,000/kWh → ₹10,000/kWh from Jun 2023 (TOI articleshow/100427048).
- Dues: TVS/Ather/Tata still waiting 2 years on; SIAM cites portal glitches; funds risk lapsing (Business Standard via Rediff, 16 Apr 2026).
- SPMEPCI (EV import policy) notified 15 Mar 2024: min investment ₹4,150 cr, DVA 25% yr-3 / 50% yr-5 (PIB PRID 2102782).

### EMPS 2024 (bridge scheme)
- ₹500 cr fund-limited, 1 Apr – 31 Jul 2024 (PIB PRID 2014366), actually implemented 6 months to 30 Sep 2024, then subsumed into PM E-DRIVE (PIB PRID 2117294).
- Sub-split (PIB PRID 2035765): e-2W 3,33,387 veh / ₹333.39 cr; e-rickshaw/e-cart 13,590 / ₹33.97 cr; e-3W L5 25,238 / ₹126.19 cr.

### PM E-DRIVE (₹10,900 cr) — timeline
- Notified 29 Sep 2024, effective 1 Oct 2024, original window 01.04.2024–31.03.2026 (PIB PRID 2117294; Fortune 118587).
- e-2W incentive: FY25 ₹5,000/kWh cap ₹10,000/veh + 15% ex-factory cap; FY26 ₹2,500/kWh cap ₹5,000/veh (Fortune 118587 — note: ₹10,000/kWh was FAME-II's rate, NOT PM E-DRIVE's).
- e-3W L5: FY25 ₹5,000/kWh cap ₹50,000 → FY26 ₹2,500/kWh cap ₹25,000 (Fortune 118587).
- Targets: 24.79 lakh e-2W; 3.2 lakh e-3W (commercial only); ₹500 cr e-ambulances (PIB PRID 2070937, 5 Nov 2024).
- 7-8 Aug 2025: extended to 31 Mar 2028 within same outlay for e-buses (₹4,391 cr / 14,028 units), e-trucks, testing agencies; 2W/3W terminal date stayed 31 Mar 2026 (PIB PRID 2154408; The Hindu 69911230).
- Nov 2025: e-3W L5 subsidy ended after target met (TOI articleshow/126261898).
- Gazette 27 Mar 2026 amendment: fund-limited, total payout ≤ ₹10,900 cr, runs to 31 Mar 2028 or funds exhausted; e-2W window extended to 31 Jul 2026 (₹5,000/kWh cap ₹10,000 until FY25; ₹2,500/kWh cap ₹5,000 from Apr 2025; e-2W ex-factory cap ₹1.5 lakh); e-rickshaw/e-cart to 31 Mar 2028 (₹5,000/kWh max ₹25,000 → ₹2,500/kWh max ₹12,500; ex-factory cap ₹2.5 lakh) (Zeebiz 392770).
- Status 22 Jul 2026 (MHI Lok Sabha reply via Fortune 151906): 26.54 lakh EVs — 23.79 lakh e-2W, 2.68 lakh L5 e-3W, 6,547 e-rickshaw/e-cart, 55 e-trucks; ₹2,322 cr released/utilised of ₹10,900 cr. State leaders: Maharashtra 4.28L, UP 2.78L, Karnataka 2.67L, TN 2.59L, MP 1.73L.
- Charging: 6,562 chargers approved worth ₹689 cr, none deployed (Business Standard 126080401097, 4 Aug 2026). 52,700+ public stations nationwide (ET Auto, Jul 2026).
- Budget 2026 allocated ₹1,500 cr to PM E-DRIVE (Moneycontrol 13958561, 1 Feb 2026). 21 Jul 2026: industry says deadline may extend again, scheme needs more funds (ET 132545678).

### PLI Auto (₹25,938 cr)
- Ola Electric Technologies Pvt Ltd approved under Champion OEM Incentive Scheme — 20 approved of 115 applicants (PIB PRID 1797610, Feb 2022; scheme notified 23 Sep 2021).
- 82 approved applicants as of 30.11.2025; ₹1,350.83 cr disbursed to five applicants; eligible sales ₹32,879 cr vs ₹2,31,500 cr target by Mar 2028 (PIB PRID 2200845, 9 Dec 2025). FY26 disbursement ~₹4,000 cr expected (Moneycontrol 13994228).
- Ola Gen-3 scooters secured PLI (AAT) certification Aug 2025, stock +5% (Business Today 491075).

### PLI ACC — 'National Programme on ACC Battery Storage' (₹18,100 cr, 50 GWh)
- Program Agreement signed 28 Jul 2022 by only 3 firms: Reliance New Energy, Ola Electric Mobility, Rajesh Exports (PIB PRID 1846078).
- Allocations: Ola 20 GWh, Reliance 15 GWh, Rajesh 5 GWh; 40 GWh awarded to 4 firms (BusinessLine 70552114, 26 Jan 2026).
- As of Oct 2025: only 2.8% (1.4 GWh) of 50 GWh commissioned in-timeline — entirely Ola; 8.6 GWh delayed; remaining 20 GWh no progress; jobs 1,118 vs ~1.03M est. (BusinessLine 70552114).
- As of 31.12.2025 (PIB PRID 2224542, 6 Feb 2026): cumulative investment ₹3,237 cr, employment 1,118, and "no beneficiary firm has claimed any incentive under the PLI ACC" — ZERO payouts 4 years in.
- Final 10 GWh being tendered for grid-scale stationary storage (GSSS): bidding initiated 3 Feb 2025 (BusinessLine 69176434); MHI pre-bid meeting 29 Jul 2026 (Business Standard).
- Ola-specific: mandated ₹225 cr/GWh investment within 2 years — missed; MHI notice Mar 2025; ₹57 cr penalty provision created then REVERSED before waiver → BSR & Co (KPMG India) qualified opinion on Q1 FY27, first since listing; shares −5% (Livemint 11786256685594, 10 Aug 2026; CNBC-TV18 19965235, 9 Aug 2026).
- Ola cell pivot 2026: talks to sell 6.5 GWh cells to global automakers (Financial Express, 14 May 2026); board approved ₹2,000 cr into EV + cell subsidiaries (BusinessLine 70983338, Mar 2026). Expansion beyond 5 GWh delayed ("may miss PLI timeline" — Autocar Professional, 14 Jul 2025).

### Budget 2025/2026 customs (EV/battery inputs)
- Budget 2025 (1 Feb 2025): customs duty exemption on lithium-ion battery scrap, 35 critical minerals, and 28 capital goods for EV manufacturing (Livemint 11738391206757).
- Budget 2026 (1 Feb 2026): FM extended BCD exemption on capital goods for Li-ion cell manufacturing to cells for BESS ("I propose to extend the basic customs duty exemption given to capital goods used for manufacturing Lithium-Ion Cells for batteries, to those used for manufacturing Lithium-Ion Cells for battery energy storage systems too" — Business Today 513949); Li oxide/hydroxide/carbonates now 0% BCD vs 7.5% earlier (YourStory).
- NOT re-verified: current BCD % on imported lithium-ion cells (FY27 tariff) — check CBIC/Finance Bill before quoting.

### State policies
- Tamil Nadu EV Policy 2023: incentives ₹5,000–₹10 lakh (commercial vehicles), SGST reimbursement, investment + turnover subsidy, ACC (cell) subsidy, 100% electricity-tax exemption 5 yrs, 6 EV cities (Autocar 427330, 16 Feb 2023; official: spc.tn.gov.in/policy/electric-vehicles-policy-2023/). Ola: ₹7,614 cr investment Krishnagiri (Deccan Herald 1194651, Feb 2023); 1-millionth vehicle Sep 2025 (YourStory).
- Karnataka (NEGATIVE turn): bill passed to amend Karnataka Motor Vehicles Taxation Act → lifetime road tax on EVs priced < ₹25 lakh (previously exempt; > ₹25 lakh taxed since 2024; e-bikes exempt) (Autocar 439474, 15 Apr 2026).

### Safety & battery regulations
- AIS-156 / AIS-038 (Rev 2): Amendment 2 effective 1 Oct 2022; Amendment 3 in two phases — 1 Dec 2022 and 31 Mar 2023 (MoRTH, PIB PRID 1862596, 27 Sep 2022). Phase-2 (Amd III) ICAT certifications from Mar-Apr 2023 (ET Auto 99111566).
- BIS Li-ion standards: IS 16893 (P2/P3 EV-propulsion cells), IS 18237:2023 (transport), IS 16805:2018 (PIB PRID 2202970).
- QCO: Lithium-Ion Cells and Batteries (Quality Control) Order, 2023, S.O. 5113(E) (tradeprep.in). Effective/extension dates NOT re-verified.
- Battery Waste Management Rules 2022 (notified 24 Aug 2022, MoEF&CC): EPR for ALL batteries incl. EV; landfill/incineration banned; central EPR-certificate portal (PIB PRID 1854433). Status Aug 2025: 3,664 producers, 442 recyclers; EPR certs 7.29 lakh MT vs 10.96 lakh MT target; minimum recycled-content mandate in new batteries from FY 2027-28 (PIB PRID 2159301).
- E-waste (Management) Rules 2022: EV batteries governed by battery-waste regime, not e-waste rules.

### Ola legal/regulatory (verified)
- CCPA probe: 10,000+ consumer complaints; Karnataka HC refused to quash CCPA notice, directed compliance (CNBC-TV18 19536054, 7 Jan 2025; MediaNama, 8 Jan 2025); later 6-week extension to answer CCPA data request (ET Legal 117043337).
- Charger refund: Ola/Ather/TVS refunded ~₹300 cr (Ola ~₹130 cr) for separately-billed chargers after govt direction (Autocar 428064, May 2023; overdrive Oct 2023).
- Consumer forum: full refund ordered for defective S1 X Plus (Business Today 537133, 16 Jun 2026).
- PLI-ACC penalty/qualified audit — see PLI ACC section above.

### GST
- EVs retained at 5% GST by Sep 2025 Council (ET, 3 Sep 2025; Business Standard, 4 Sep 2025). GST 2.0 from 22 Sep 2025: small cars + bikes ≤350cc to 18% slab, 3-wheelers cheaper, SUVs higher (Cardekho 34973). GST on lithium-ion cells (18%) NOT re-verified.

## Key PIB PRID index
| PRID | Subject |
|---|---|
| 2014366 | EMPS 2024 announcement (13 Mar 2024) |
| 2035765 | EMPS 2024 guidelines / sub-component split |
| 2070937 | PM E-DRIVE targets (5 Nov 2024) |
| 2102782 | FAME-II status + SPMEPCI (13 Feb 2025) |
| 2117294 | PM E-DRIVE status, EMPS subsumption (~Mar 2025) |
| 2154408 | PM E-DRIVE extension to 2028 (8 Aug 2025) |
| 1846078 | PLI ACC Program Agreement (29 Jul 2022) |
| 2224542 | PLI ACC status (6 Feb 2026) — no incentives claimed |
| 1797610 | PLI Auto Champion OEM 20 approved (Feb 2022) |
| 2200845 | PLI Auto status (9 Dec 2025) |
| 1854433 | Battery Waste Management Rules 2022 (25 Aug 2022) |
| 2159301 | Battery-waste EPR status (21 Aug 2025) |
| 1862596 | AIS-156/AIS-038 amendments (27 Sep 2022) |
| 2202970 | BIS Li-ion battery standards (Feb 2026) |

## Blocked / flaky at fetch time (Aug 2026) — don't burn retries
- financialexpress.com — 403 CloudFront (curl, jina AND browser timeout) → find the same story on another outlet.
- TOI / ET (articleshow + auto.et) — 403 for jina, browser timeout → cite headline+URL from RSS instead of body.
- news18.com — blocked (DNS-hijack landing page via jina).
- thehindubusinessline.com — jina sometimes returns "404 Not Found" wrapper + nav-only shell; RETRY once (worked on 2nd attempt for article70552114).
- pib.gov.in direct curl/browser — JS shell; use jina on PRID URLs (works).
- DDG html via browser — anomaly/captcha challenge page (checkboxes); jina-DDG works instead.
- zeebiz.com — browser times out, jina works.
- business-standard.com, fortuneindia.com, livemint.com, autocarindia.com, thehindu.com, medianama.com, cnbctv18.com, businesstoday.in, yourstory.com, rediff.com, deccanherald.com — all fetched OK via jina.

## Workflow notes
- Print jina content as keyword-windows (±400 chars) to keep context small on 40+ page sweeps; batch 6-8 pages per execute_code call with ~5-7s sleeps (jina anonymous tier tolerates this).
- Bing News RSS `real_url` decode: html.unescape FIRST (see SKILL.md pitfall), then `[?&]url=` regex, then filter `apiclick` remnants.
- For "as of <date>" status numbers, prefer ministerial written replies (PIB) over media; cross-check one media outlet for the headline interpretation.
