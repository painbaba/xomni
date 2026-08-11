# India Unclaimed-Money Data Collection (insurer disclosure lists)

Goal: pull bulk lists of unclaimed insurance money (names + amounts) that IRDAI
mandates insurers to publish. ~Rs 16,649 cr unclaimed in LIC+EPFO and ~Rs 8,974
cr with insurers (govt data, Aug 2026); heirs mostly don't know.

## The master map — IRDAI directory
`https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount` lists EVERY insurer's
unclaimed-amounts page (58+ portals, life/general/health). Crawl it first;
it is the source of truth for what exists. (Note: `unclaimed.irdai.gov.in`
does NOT resolve — the Bima Bharosa host is the real one.)

## BULK vs SEARCH-ONLY — the hard ceiling
Classify every portal with a probe script (fetch with browser UA, look for
downloadable .pdf/.xls/.csv links vs `<form>` + policy-number inputs). Reality
(Aug 2026, verified live):
- **BULK publishers found (5):** Liberty General (27-page PDF, names+addresses,
  no amounts), ECGC (2 lists: all + >=Rs1000, as-on-31.03.2026, 6-7 pages),
  Acko Life/General (small), IndiaFirst Life ("UNCLAIMED CASES 10 years & above",
  23 pages, ~990 records), LIC **shareholder dividend registers** (16 files,
  ~223 MB — see below).
- **SEARCH-ONLY (everything else):** LIC policyholder portal (merchant.licindia.in
  + licindia.in/unclaimed-amounts-of-policyholders*), SBI Life, HDFC Life, ICICI
  Pru, Kotak, Max Life, SBI General, Tata AIG, New India, National, United
  India, Universal Sompo, PNB MetLife, IRDAI central form
  (bimabharosa.../UnclaimedAmountsQuery — a REQUEST form, not a database).
  These need policy-no or PAN+name+DOB; no bulk export exists. Confirmed via
  browser, not assumed.
- **LIC dividend registers:** found via Liferay site search
  `licindia.in/search?q=unclaimed` → 19 doc-library files, 16 downloaded.
  These are LIC-the-listed-company's UNCLAIMED SHAREHOLDER DIVIDENDS (names +
  folio + amount + address + due date), NOT policyholder claims. Newest
  FY2024-25 register ~19,630 rows; older FVs are EARLIER SNAPSHOTS of the same
  pools (trend data, not new money — don't double-count in totals).

## Extraction recipe (pymupdf)
- `page.find_tables()` beats hand-rolled line parsers for grid PDFs. One table
  per page, ~96 rows/page for LIC registers.
- Header-row detection: require >=2 header keywords AND cell count <= column
  count, or data rows containing "branch"/"policy" in names get eaten.
- Amounts like `Rs. 18,662.00` mangle under `[^\d.]` strip (multi-dot) — keep
  only the last numeric token.
- Dedupe by (source, normalized name, policy_no, amount). Watch for the
  folio-number glued to name start in LIC rows (`1208880008342461 AKASH ...`).
- Search engines (Bing RSS) IGNORE filetype:/site: operators and return junk —
  direct portal probing is the only reliable discovery channel on this host.

## Business context (finder/claims-assist play)
- Opportunity: bank deposits ~Rs 83,000 cr, insurance ~Rs 14,000 cr, equities
  ~Rs 10,000 cr unclaimed (Lok Sabha FY26).
- No one indexes insurer unclaimed lists BY NAME (banks have UDGAM, shares have
  IEPF, insurance is search-by-policy-only) → a name-search service is the moat.
- Fee norms: IEPF/EPF consultants flat Rs 5-10k or 2-3%; insurance finders
  15-20% success fee (Insurance Samadhan model: Rs 999 + %, no-win-no-fee).
- Legal path: death claim settles 15-45 days (IRDAI MC 2024); succession cert
  civil-court 4-8 months, but small claims accept notarized heir affidavit +
  indemnity bond (LIC Form 3805); policyholder unclaimed goes to Senior
  Citizens' Welfare Fund after 10 yrs (NOT IEPF — IEPF 7-yr rule is only for
  LIC/dividends); DPDP 2023: cold outreach needs consent or s.17 legal-claim
  hook, TRAI DND for phone/SMS → inbound ("check your family name") is the
  compliant channel.
- Scam climate: fake "Bima Lokpal" unclaimed-refund calls are surging — the
  trusted no-upfront-fee brand is the wedge.

## Deliverables built (Aug 2026, `ai-workforce/swarm/` + `unclaimed-mvp/`)
- unclaimed_portals.json (58 portals classified) · unclaimed_master.csv /
  unclaimed_master.db (~2,172 policyholder records, ~Rs 1.39 cr unique) · LIC
  Nov-2025 registers (+~Rs 2.52 cr) · grand total ~Rs 3.91 cr unique
- MVP: stdlib SQLite name-search (app.py + index.html, bilingual Hindi/English,
  mobile-first) — build_index.py merges CSVs into unclaimed_index.db with
  normalized name column; token-LIKE matching sorted by amount desc.
