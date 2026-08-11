# India Unclaimed-Money Data + Claims-Assist Venture (Aug 2026)

Session-proven source map, numbers, and business research. All verified live
Aug 8, 2026. Artifacts: C:\Users\HP\ai-workforce\swarm\ (data pipeline) and
C:\Users\HP\ai-workforce\unclaimed-mvp\ (working demo).

## The regulator master-directory trick (start here for ANY regulator-mandated disclosure)
IRDAI publishes a SINGLE page listing every insurer's unclaimed-amounts portal:
`https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount` (also the query form at
`/Home/UnclaimedAmountsQuery` — that one is a REQUEST form, not a database; it
forwards to insurers and needs policy numbers, so it is NOT bulk-pullable).
Curl returns empty (JS/WAF); use the browser. 58 portals total: ~25 life,
~27 general, ~6 health. Classify each BULK vs SEARCH-ONLY before scraping.

## Verdict: only ~6 sources publish BULK lists (the entire legal bulk universe)
Everything else is search-only by design (policy no / PAN / name / DOB form).
Bulk publishers found:
- **Liberty General** — 27-page PDF, 600 records, names+addresses, NO amounts.
  URL: libertyinsurance.in/docx/amount-unclaimed-by-the-policyholders.pdf
- **ECGC** (Export Credit Guarantee Corp) — 2 PDFs (all amounts + Rs1000+ subset),
  ~570 unique records, amounts present. On main.ecgc.in/wp-content/uploads/...
  NOTE the path is WITHOUT /english/ (with it → 404).
- **Acko Life / Acko General** — tiny PDFs, 12 records total.
- **IndiaFirst Life** — 23-page "Unclaimed cases 10 years & above" PDF, 993
  records (policy id + name + amount + due date). URL: indiafirstlife.com
  /content/dam/ifliwebsite/unclaimed-amount/unclaimed-amount.pdf
- **LIC** — NOT policyholder lists (those are search-only via merchant portal).
  BUT LIC publishes **shareholder dividend registers** (LIC is listed since
  2022): 16 PDFs, 223 MB, millions of rows, names+folio+address+pincode+amount
  +IEPF due date. These are "unclaimed dividend" lists, a DIFFERENT money
  category than policyholder claims — label honestly.

## LIC dividend registers — how they were found (reusable)
LIC's sitemap is a Liferay trap: sitemap.xml returns 5,649 self-referential
`?p_l_id=...` URLs (recursive; each fetch returns the same index). Do NOT crawl
it. The winning move: **Liferay site-search** `https://licindia.in/search?q=unclaimed`
surfaced all 19 doc-library files at once (under /documents/20121/...). Pattern:
when a govt/Liferay site's sitemap is garbage, use its own site search + grep
the results for .pdf links.
Register columns (2025 format): S.No | Folio Number | Name of Member | Address
1-4 | Pincode | Warrant No | MICR | Net Amount | Total Shares | IEPF due date.
4 unique Nov-2025 snapshots (per FY 2021-22 → 2024-25) + 11 older 2023-24
snapshots. Older snapshots = same pools at earlier dates → trend data only,
NOT new unique money (pools SHRINK over time as people claim: FY21-22 pool fell
53% from Mar-2023 to Nov-2025 — useful proof-of-demand stat for the pitch).

## PDF table extraction (pymupdf) — pitfalls hit this session
- `page.find_tables().tables[i].extract()` beats hand-rolled line parsing for
  grid PDFs (Liberty, ECGC, IndiaFirst all clean). Line parsing over-splits
  when records span multiple text lines.
- **max S.No ≠ record count.** The subagent's "854,318 records" was a cumulative
  serial number across registers; real count ≈ rows/page × pages (~19.6K).
  Always cross-check rows-per-page × pages.
- Header-row detection that matches keywords like "branch"/"policy" EATS data
  rows whose name/address contains those words. Fix: require ≥2 header keywords
  AND few non-empty cells before treating a row as a header.
- A patch that moved the record-append INSIDE the else-branch silently dropped
  every header-mapped row (252→203). Always re-run a known-count sanity check.
- Amount formats vary: "Rs. 18,662.00" → strip non-[0-9.], then if >1 dot keep
  the LAST numeric group (regex `\d+\.\d{1,2}|\d+`).
- Some LIC names have the 14-17-digit folio glued to the front — strip it into
  policy_no (`^(\d{14,17})\s+(.+)$`).
- **Subset-overlap trap:** ECGC "Rs1000+" file is a SUBSET of the "all amounts"
  file. Summing both double-counts. Reconcile unique totals by summing only the
  superset + non-overlapping sources (and label it "unique, no double-count").

## Final dataset (unique, no double-count)
- Policyholder lists: ~Rs 1.39 cr (ECGC 1.09 cr + IndiaFirst 27.9L + Acko 2.4L;
  Liberty 600 records carry NO amounts).
- LIC dividends (4 Nov-2025 registers): Rs 2.52 cr.
- GRAND: ~Rs 3.91 cr across ~113K amount-bearing records (88.7K deduped rows in
  the search index). Government context for scale: Rs 1.1 LAKH crore total
  unclaimed in India FY26 (banks 83k cr, insurance 14k cr, equities 10k cr);
  LIC Rs 7,318 cr; EPFO Rs 9,330 cr / 31L accounts; insurers ex-LIC ~Rs 8,974 cr.

## Claims-assist business research (3 subagents, live-verified)
**Market/players:** Share Samadhan ("India's largest"), IEPFClaim/GLC Wealth,
IEPF Doctor, Legacy Asset Solutions, Insurance Samadhan (Rs 999 + 15-20%
success, no-win-no-fee), UnClaimedX (Bengaluru, digital inheritance), Kustodian.
life (EPF). Fee norms: success-% (common), flat Rs 5-10k, or 2-3% of EPF corpus;
no statutory cap found. Govt "Your Money Your Right" campaign reclaimed Rs 5,777 cr.

**Legal/regulatory:** death claim settles 15 days (no investigation) / 45 days
(investigation), else interest at bank rate+2% (IRDAI Master Circular 2024).
Succession Certificate = civil court only (4-8 months uncontested); small claims
accept notarized legal-heir affidavit + indemnity bond (LIC Form 3805) — no
court. Policyholder unclaimed money → Senior Citizens' Welfare Fund after 10
years (claimable ~25 yrs); IEPF 7-yr rule applies ONLY to LIC shareholder
dividends (Form IEPF-5, company verifies 30 days, Authority refunds 60 days,
free). Third party CAN charge for paperwork; but advocates can't take
contingency fees (BCI Rule 20), non-lawyers can't appear in court, buying
claims is barred (TP Act s.6(e)). DPDP: cold outreach needs consent or legal-
claim hook (s.17(1)(a)); deceased's data likely outside Act, living heirs
protected; TRAI DND applies to phone/SMS. Inbound (families come to you)
sidesteps everything.

**GTM / moat:** nobody indexes INSURANCE unclaimed lists by name (banks have
UDGAM, shares have IEPF — insurance has nothing). Our scraped index is the only
name-searchable insurance unclaimed dataset → free name-check is the lead
magnet. No private WhatsApp+Hindi finder exists (govt does EPF via EPFO
WhatsApp AI chatbot + E-PRAAPTI; insurance is open). Hindi YouTube Shorts on
this topic get 18K-455K views; Hindi SEO ranks (economictimes/hindi, tv9hindi,
zeebiz/hindi explainers). WhatsApp Business API since Jul-2025: marketing
template Rs 0.88, utility Rs 0.125, service replies in 24-hr window FREE —
inbound chatbot ≈ zero cost. Scam wave: fake "Bima Lokpal" unclaimed-refund
calls surging → position as trusted zero-upfront no-win-no-fee (anti-scam brand).

## MVP (built, working, localhost:8787)
C:\Users\HP\ai-workforce\unclaimed-mvp\ — stdlib-only Python (no deps):
- `build_index.py` — merges unclaimed_master.csv + lic_*_nov2025_records.csv →
  unclaimed_index.db (88,704 rows, name_norm column, idx on it).
- `app.py` — ThreadingHTTPServer, `/` serves index.html, `/api/search?q=`,
  `/api/stats`. Token-AND matching (every query token must appear in name),
  rank by amount DESC. Port arg: `python app.py 8787`.
- `index.html` — Hindi-first mobile UI, anti-scam banner, claim-path guidance.
Verified: "SYED SHAHED"→1, "Ramanbhai Parmar"→1, "RAM"→40 sorted by amount.
Limits: ~8.9K LIC rows lack amounts (parser column issue in 2 registers);
no fuzzy/transliteration (next: metaphone + Hindi→English for "राम"→RAM);
localhost only.
