---
name: indian-insurer-unclaimed-data
description: Hunt bulk unclaimed-amounts lists from Indian insurers.
---

# Indian Insurer Unclaimed-Amounts Data Collection

Collect bulk downloadable unclaimed-amounts lists published by Indian insurers under IRDAI's policyholder-protection disclosure regime. The governing instrument for unclaimed-amount disclosures is the **Master Circular on Protection of Policyholders' Interests, 2024 (Ref IRDAI/PP&GR/CIR/MISC/117/9/2024, 5 Sep 2024)**: an "unclaimed amount" is unpaid >12 months from due date (non-contactability); **after 10 years it transfers to the Senior Citizens' Welfare Fund (SCWF)**; it stays claimable **up to 25 years after SCWF transfer via the insurer**, then escheats to the Central Government. (Do NOT confuse with IEPF — the 7-year Companies Act s.124 rule applies to listed-company dividends/shares, e.g. LIC shareholders, not policyholder money.) For the full legal/claim process behind this data: `web-research` skill → `references/india-unclaimed-money-legal-2026.md`. Most insurers only offer search portals; a handful publish bulk files. Save real downloads under the swarm project dir (e.g. `C:\Users\HP\ai-workforce\swarm\unclaimed_data\`).

## Canonical index — start here

IRDAI Bima Bharosa master directory: `https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount`
Lists EVERY insurer's unclaimed page in three tables (Life / General / Health). This is the authoritative registry. Prefer it over search engines, which return junk for these highly-specific queries (see Pitfalls).

## Workflow

1. Fetch the IRDAI master directory (browser snapshot or curl) → extract all insurer unclaimed URLs. The page is static HTML with `<table>` rows, easy to parse.
2. Batch-probe every URL with urllib + Chrome browser UA; collect hrefs matching `pdf|xlsx?|csv|zip|download|unclaimed|disclos`. Use `scripts/probe_insurers.py`.
3. High-value signal: pages whose visible text says "list" / "disclosure" / "as on 31st March" — grep ~300-char context windows around the word `unclaimed` for nearby hrefs. IndiaFirst's bulk PDF was found exactly this way.
4. Browser-verify JS-heavy or Akamai-403 pages (real browser rendering often gets through where curl gets 403).
5. Download candidates → verify magic bytes (`%PDF` for pdf, `PK\x03\x04` for xlsx) → extract with pymupdf → count records.

## Confirmed bulk-list publishers (as of Aug 2026)

| Insurer | Where | Notes |
|---|---|---|
| LIC | merchant.licindia.in .../UnclaimedPolicyDues | search portal (already collected) |
| ECGC | main.ecgc.in/english/public-disclosures | bulk (already collected) |
| Acko Life / Acko GI | acko.com/life/unclaimed-amount, acko.com/gi/unclaimed-amount | bulk (already collected) |
| Liberty GI | libertyinsurance.in/products/irdai/irdaiindex | bulk (already collected) |
| **IndiaFirst Life** | indiafirstlife.com/unclaimed-amount → `/content/dam/ifliwebsite/unclaimed-amount/unclaimed-amount.pdf` | **bulk PDF, ~992 records** (10 years & above period) |
| **LIC unclaimed DIVIDEND registers** | licindia.in site search `licindia.in/search?q=unclaimed` → Liferay doc-library PDFs (`/documents/20121/...`) | **16 PDFs, ~223 MB total — the biggest haul.** Shareholder unclaimed dividends (LIC the listed company; NOT policyholder claims — those stay search-only at merchant.licindia.in). Newest FY2024-25 register (Nov 2025): ~19.6k amount rows, ~Rs 1.5 cr. 4 unique FY registers + 12 older snapshots (trend data only). Columns: SNo | Folio | Name | Address1-4 | Pincode | Warrant | MICR | Shares | Net Amount | IEPF due date. Parse with `lic_parse.py` (line-based, below). |

## Archive snapshots = trend data, NOT new money (reconciliation rule)
When a source publishes the SAME register at multiple dates (LIC dividend registers do: Mar/May/Jun/Jul 2023 → Nov 2025), the older files are EARLIER SNAPSHOTS of the same pools. They show how the pool shrinks as people claim (LIC FY2021-22 pool fell 53% over 2.5 yrs) but they must NOT be summed into the unique total. Unique total = newest snapshot per FY + policyholder lists only. The trend itself is a business signal (fresh pools = most actionable).

## Search-only (verified — no bulk file)

HDFC Life, SBI Life, ICICI Prudential, Tata AIA, PNB MetLife, Aviva, Bharti AXA, Axis Max, Pramerica, Edelweiss, IndusInd Nippon, Ageas Federal, Canara HSBC, Kotak (commented-out UnclaimedReport.aspx errors without session), Universal Sompo (3 pages incl. an empty "Data Not Available" grid), IndusInd/Reliance GI, IFFCO Tokio, Magma, Navi, Zuno, Kshema, Go Digit, New India Assurance, Manipal Cigna, ICICI Lombard, Niva Bupa, ABSL Health, Chola MS. Full per-insurer probe matrix: `references/insurer-matrix-2026-08.md`.

## Pitfalls

- **Search engines are useless for this class**: Bing RSS (`&format=rss`) returned unrelated junk for every query tried (site: operators ignored); DDG HTML blocked after one query. Direct probing of the IRDAI registry wins.
- **Akamai 403s on curl**: SUD Life, Care Health, Royal Sundaram, Star Health return Akamai "Reference #18..." blocks — use browser navigation instead of fighting headers.
- **AEM coredownload URLs**: IndiaFirst and other AEM sites expose `/content/dam/...pdf.coredownload.inline.pdf` — both the inline and the clean path work.
- **Tabular PDF parsing trap**: naive line-split breaks when amounts are small integers (indistinguishable from Sl No columns). Detect row starts as `small-int line immediately followed by a 6–9 digit policy-id line`. Use `scripts/parse_unclaimed_pdf.py`.
- **Dense registers beat find_tables**: on huge multi-hundred-page registers (LIC dividend PDFs), pymupdf `find_tables()` is slow enough to time out (205 pages > 300s). Use LINE-BASED parsing instead (`lic_parse.py`): each record opens with a short SNo-only line; then scan up to ~12 lines classifying by regex — 14-17 digit folio, 6-digit pincode, 8-digit warrant, `\d+\.\d{2}` amount, date, else name-then-address. Split records on the next SNo line. Line parsers OVER-split (each record → 2-3 fragments) — treat amount-bearing rows as truth and dedupe by (source, name_norm, policy, amount). Also strip 14-17 digit folios glued to name starts ("1208880008342461 AKASH …" → folio + name).
- **Commented-out links are worth trying**: Kotak's 10+-year list link exists only as an HTML comment — fetching the URL directly still returns a page (errors without session, but try).
- **"List" wording ≠ bulk file**: IFFCO Tokio and IndusInd/Reliance GI pages say "Unclaimed Amount of Policyholder's list" but only expose search forms.
- **Health insurers** (Care, Star, Manipal Cigna, Niva Bupa, ABSL Health) are uniformly search-only as of this sweep.

## Name-search MVP (the demo deliverable — built Aug 2026)

The scraped lists become a product demo: a bilingual Hindi/English name-search page over the index. Pattern (all stdlib, zero deps):
- Build a SQLite index: merge all CSVs, `name_norm` column (upper, strip non A-Z0-9), dedupe by (source, name_norm, amount). LIC folio-glued names get folio stripped into policy_no.
- Search = `WHERE name_norm LIKE %token1%token2%` (every token must appear, order-free), rank by amount DESC. Match on ANY name part ("Parmar" finds "Ramanbhai Mavabhai Parmar").
- Server: stdlib `ThreadingHTTPServer` + `/api/search?q=` + `/api/stats`; HTML page mobile-first, Hindi-first labels, anti-scam banner (positioning: "verify with the insurer, beware unclaimed-money scam calls"), "next step" claim guidance on each match.
- Files live in `C:\Users\HP\ai-workforce\unclaimed-mvp\` (app.py, index.html, build_index.py, unclaimed_index.db).
- Business framing from the research: the moat is NAME-indexing (official portals are policy-number/PAN search only) + claim assistance (succession cert, legal-heir docs) at 15-20% success fee; inbound lead magnet = free name check. Govt is the EPF competitor (EPFO WhatsApp AI chatbot), insurance is open. DPDP: cold outreach needs consent; inbound avoids it.

## Support files

- `scripts/probe_insurers.py` — batch-probe insurer unclaimed URLs, dump file-ish links to JSON
- `scripts/parse_unclaimed_pdf.py` — robust row extraction from unclaimed-table PDFs
- `scripts/lic_parse.py` — line-based parser for dense multi-hundred-page registers (LIC dividends)
- `references/insurer-matrix-2026-08.md` — insurer-by-insurer probe matrix with URLs, HTTP status, links found
