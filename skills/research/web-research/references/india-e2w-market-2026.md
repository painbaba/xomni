# India e-2W (electric two-wheeler) market data — verified bank (Aug 10, 2026)

Built during the Ola Electric vs TVS/Bajaj/Ather/Hero Vida competitive analysis. Every number below was live-fetched 2026-08-10 (per-URL audit trail in the session dossier `ola_electric_competitive_analysis_2026.md`).

## Recipe: monthly e-2W sales/share data fast
1. **Discovery**: Bing News RSS (`https://www.bing.com/news/search?q=<urlenc>&format=rss&setlang=en&cc=IN`) with queries like `electric two-wheeler sales <Month> <Year> Vahan market share`, `e-2W sales <Month> <Year> Ola TVS Bajaj Ather`, `<Brand> <model> price <Year> on road`. Monthly Vahan roundups publish days 1-8 of the following month (Jul data: entrackr Jul 31, BusinessLine Aug 8, DriveSpark Aug 9).
2. **Curl-friendly outlets** (curl + tag-strip works, no browser): entrackr.com (Vahan registrations + exact % shares, updates daily), thehindubusinessline.com (retail regs + penetration %), drivespark.com (full manufacturer table incl. YoY + MoM %), carbike360.com (top-10 table), autocarindia.com/industry (model-level: iQube vs Chetak vs Rizta; FY-end roundups carry capacity + strategy detail), auto.economictimes.indiatimes.com (CBO/CEO quotes, capacity numbers), rediff.com (syndicates FADA half-year consolidations), financialexpress.com, businesstoday.in, livemint.com (Mint Premium articles are giftable/fetchable).
3. **SCOPE CAVEAT — the same month has different totals per source** (as-of date; dispatch vs registration; high-speed-only vs all e-2W). Real example, Jul 2026: total 1,91,614 (BusinessLine, Vahan retail) vs 2,04,266 (carbike360, high-speed); Ola 13,085 (BL) / 13,170 (entrackr) / 14,106 (drivespark). Always quote source + scope per number; present ranges; entrackr/BusinessLine are the safest for market shares.
4. **Pricing**: ZigWheels `zigwheels.com/<brand>-bikes/<model>/on-road-price-<city>/` and Autocar `autocarindia.com/bikes/<brand>/<model>/price-in-<city>` are SSR'd — plain curl + tag-strip yields exact per-variant ex-showroom / insurance / on-road breakdown. On-road varies ₹2-5k by city; always state the city.
5. **IPO/stock facts**: chittorgarh.com/ipo/, investorgain.com/ipo/, ipogyani.com give consistent issue price / listing date / listing gain (cross-check ≥2). Daily closing price + mcap come from entrackr/moneycontrol result articles.
6. **Regulatory context to always check**: central subsidy status (PM E-Drive ₹5,000 e-2W subsidy extended to Jul 31, 2026, then ENDED — post-subsidy era from Aug 2026), state mandates (Delhi: only e-2W registrable from Apr 1, 2028, with tapering purchase subsidy), fuel-price shocks driving demand surges.

## Verified snapshot (as of 2026-08-10)
### July 2026 Vahan retail — total 1,91,614 (+76.6% YoY; e-2W penetration ~11%)
TVS 52,035 (27.2%) · Bajaj 43,137 (22.5%) · Ather 28,540 (14.9%) · Hero/Vida 20,913 (10.9%) · Ola 13,085 (6.8%; ONLY major OEM with YoY decline, −29.1%) · Greaves/Ampere 9,590 · River 5,554 (+254% YoY) · BGauss 5,324 · Simple 1,532 · Lectrix 1,335.

### Monthly trajectory 2026 (Vahan/industry totals)
Jan ~1.24L · Feb 1.12L (TVS 28.3% @31,601, Bajaj 22.7%, Ather 18%, Hero 11.2%, Ola 4% rank #7 @3,968) · Mar ~1.92L (TVS 49,304 + Ather 35,688 records; penetration >9%) · Apr ~1.51L · May ~1.65L · Jun >1.74L (penetration >10%; TVS 25%+ @~44k, Bajaj 22%+ @>39k, Ather 16.5% capacity-capped, Ola 8%+ @~15k) · Jul 1,91,614.

### FY26 (Apr 2025–Mar 2026) retail
TVS 341,471 (24%) · Bajaj 289,323 (21%) · Ather 239,124 (17%) · Ola 164,294 (12%, −52%). FY26 e-2W total ~1.4M = 57% of India EV market; FADA FY26 penetration 6.5%.
### CY2025 (Vahan)
Ola 196,767 (share 36.7% → 16.1%) · TVS 295,315 (24.2%, #1) · Bajaj 21.9%.
### H1 CY2026 (FADA)
970,993 (+53.3%); TVS 251,438 (25.9%), Ather 169,020 (17.4%, +91.1%), Ola 65,999 (−44.1%, 6.8%); TVS+Bajaj+Ather+Hero = 95.6% of incremental registrations (market consolidating).

### Key financials
- **Ola (OLAELEC)**: FY26 rev ₹2,253 cr (−50.1%), net loss ₹1,833 cr; Q1 FY27 rev ₹455 cr (−45%), loss ₹336 cr — 7th straight revenue-decline quarter, SEBI probe settlement underway; Q4 FY26 GM 38.5% (industry-best), first positive CFO ₹91 cr; stock ₹41.07 (Aug 7, 2026), mcap ₹19,185 cr; IPO Aug 2024 @ ₹76 (raised ₹6,145 cr), peak ~₹150; break-even needs ~15k units/mo; QIP ₹780 cr (Jun 2026).
- **Ather (ATHERENERG)**: IPO ₹321 (Apr 28-30, 2025; size ₹2,980.76 cr; listed May 6, 2025 @ ₹328, +2.2%; day-1 close ₹302.30; subscribed 1.43x); Q1 FY27 rev ₹1,217 cr (+89%), loss ₹51 cr (−71%), EBITDA-positive first time; stock ₹1,280 (Aug 3, 2026), mcap ₹50,448 cr (2.6× Ola); ₹1,200 cr preferential (Hero MotoCorp ₹960 cr) + QIP + planned $200M sale; Hosur capped 35k/mo → new plant Nov-Dec 2026 (+42k) → 1.42M/annum ambition.
- **TVS**: Q4 FY26 NP ₹819-820 cr (+17-18%), quarterly rev >₹15,000 cr; Q1 FY27 NP +67% YoY; capacity +1.5M units; BaaS across EV portfolio (Mar 2026).
- **Bajaj**: Q1 FY27 NP ₹3,226 cr (+46%), record revenue; Chetak 289,323 FY26.

### Aug 2026 pricing snapshot (ex-showroom → on-road)
- Ola S1 X ₹84,999 / 98,999 / 1,14,999 (2/3/4 kWh; on-road ₹89,761–1,20,286 Guwahati) · S1 Pro ₹1,29,999–1,75,000 (on-road ₹1.40–1.89L) · Roadster ₹1,04,999–1,39,999 (on-road ₹1.23–1.61L) · Mar-26 promos: S1 X 2kWh & Roadster X at ₹49,999; 8-yr warranty standard, Service Trust Guarantee, buyback ≤60%.
- TVS iQube ₹1,15,822 (2.2) / ₹1,38,943 (3.5) / ₹1,72,384 (ST 5.3) — after Aug 1, 2026 hike; Orbiter V1 ₹95,250 / V2 ₹1,18,480; iQube on-road ₹1.20–1.75L.
- Bajaj Chetak C2501 ₹91,399 (Jan-26 launch, ex-sh BLR; now ~₹96,399–1,04,802); 3501 top ₹1.34L ex-sh; on-road ₹1.04–1.45L.
- Ather Rizta S ₹1,21,499 ex-sh (on-road ₹1.31L; S-on-BaaS ₹76,000 upfront); 450S from ₹1,00,812 (on-road ₹1.06–1.78L).
- Hero Vida V2 Plus ₹1,04,990 ex-sh (on-road ₹1.13L) · V2 Pro on-road ₹1.19L · VX2 Go ₹99,490 · DIRT.E K3 ₹69,990.

### Network / strategy facts
- Ola: retail cut ~4,000 → ~700 stores (Feb 2026, "structural reset"); **Aug 5-6, 2026 pivot to dealer-led retail** (first dealerships by Janmashtami 2026, Diwali scale; ~1,000 dealer enquiries); 4680 NMC "Bharat Cell" ARAI-approved (Oct 2025), Gigafactory 6 GWh commissioned by Sept 2026, Axis Energy 20 GWh BESS MoU; Ola Shakti BESS line; earnings-call pivot toward drones/defence.
- Ather: 700 experience centres (FY26-end, doubled); Rizta ≈ 70% of sales; Rizta wait times 45-60 days (demand > supply).

## Pitfalls (this session)
- **Bing News RSS `<link>` is complete, but printing/truncating it loses the URL** — re-run the query printing the full link (or resolve via r.jina.ai). Do not hand-guess truncated slugs.
- **MSN syndication pages (msn.com/en-in/...) return a ~42KB JS shell to curl** — fetch the publisher directly (BusinessLine/Livemint/etc.) instead.
- **TOI slug-only URLs 404** (e.g. e-scooter reliability study) — headline-verify via RSS and mark URL as truncated rather than fabricating.
- **DDG html via urllib returns empty where curl succeeds** (UA handling); both rate-limit after ~4-6 queries — pace ≥2.5s, then escalate to Bing News RSS or r.jina.ai.
- **r.jina.ai → DDG html** (`https://r.jina.ai/https://duckduckgo.com/html/?q=...`) is the reliable niche-facts path (worked for Ather IPO details via IPO-tracker sites); parse `## [title](uddg-link)` headings.
- India market caps in ₹ crore; convert to USD for the reader (~₹95-96/USD context, but always state the mcap in both as quoted).
