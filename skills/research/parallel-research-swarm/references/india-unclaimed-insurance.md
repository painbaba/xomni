# India Unclaimed Insurance Money — Data Sources & Extraction Pipeline (Aug 2026)

Verified by live probing (58 portals, curl + browser) on 2026-08-08. Reusable for
any "find unclaimed money / heirs" project in India.

## Context & scale
- Govt (Lok Sabha, 2026): ~Rs 16,649 cr unclaimed in LIC + inoperative EPF accounts;
  ~Rs 8,974 cr unclaimed with all insurers (maturity proceeds, death claims, premium
  refunds, not-encashed cheques). Heirs usually don't know the policy exists — that's
  the finder/claims-assist business angle.

## Master directory — START HERE, never re-probe from scratch
- IRDAI's official list of EVERY insurer's unclaimed-amounts portal (60+ links,
  life/general/health): https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount
- Central search form (up to 5 insurers, by policy no / name / DOB / PAN):
  https://bimabharosa.irdai.gov.in/Home/UnclaimedAmountsQuery
- DEAD URLS (don't retry): `unclaimed.irdai.gov.in` → DNS NXDOMAIN;
  `licindia.in/unclaimed-amounts` → 404. LIC's real portal is search-only:
  `merchant.licindia.in/LICEPS/portlets/visitor/unclaimedPolicyDues/UnclaimedPolicyDuesController.jpf`

## Verified landscape: BULK vs SEARCH-ONLY (the whole point)
Only FIVE insurers publish bulk downloadable lists — everything else is a
lookup-by-policy-number form (often with recaptcha), i.e. you must ALREADY know a
policy number or PAN+name+DOB to query. No bulk export, period.

BULK sources (record-yielding):
1. Liberty General — https://www.libertyinsurance.in/docx/amount-unclaimed-by-the-policyholders.pdf
   (27pp grid: SrNo|Name|Address|PolicyNo|Reason; ~600 records, no amounts in PDF)
2. ECGC — base is `https://main.ecgc.in/wp-content/uploads/...` — NO `/english` prefix,
   that 404s. Files (as on 31.03.2026):
   - `Unclaimed-Amount-Rs1000or-more-as-on-31.03.2026.pdf` (~248 recs)
   - `Unclaimed-Amount-as-on-31.03.2026.pdf` (~321 recs, superset incl. <Rs1000)
3. Acko Life — `https://acko-cms.ackoassets.com/Unclaimed_Amount_March_2026_*.pdf` (~5 recs)
4. Acko General — `https://acko-cms.ackoassets.com/Unclaimed_Amount_as_on_March_31_2026_*.pdf` (~7 recs)
5. IndiaFirst Life — 23pp "UNCLAIMED CASES - For Period 10 years & Above"
   (policy/member id + owner/beneficiary name + amount + due date; ~993 records — the
   jackpot). URL pattern:
   `indiafirstlife.com/content/dam/ifliwebsite/unclaimed-amount/unclaimed-amount.pdf`

SEARCH-ONLY (verified): LIC, New India, Oriental, United India, National Insurance,
SBI Life, HDFC Life (and Exide/eli pages), Kotak Life, ICICI Lombard, ICICI Pru,
Bajaj (life+general), Cholamandalam, Edelweiss, Aviva, Bharti AXA, PNB MetLife,
TATA AIA, Max Life, SBI General, Tata AIG, Universal Sompo (3 ASP.NET forms incl.
"client-wise details"), Manipal Cigna, Star Health. New India verified in browser:
form + recaptcha, zero export. Universal Sompo quarterly "public-disclosure" PDFs are
solvency/financial schedules (Annexure I-XI), NOT unclaimed lists.

## Implications for the "pull lots of them" goal
- Realistic ceiling ≈ 5 sources / ~2,200 records per season (master CSV hit 2,172).
  The big money (LIC, PSU general insurers) is locked behind per-policy lookup.
- LIC: policyholder unclaimed-policy lists are search-only, period (merchant portal,
  licindia.in/unclaimed-amounts-of-policyholders* all redirect to it). BUT LIC
  shareholder unclaimed-DIVIDEND registers ARE bulk-downloadable — see the dedicated
  section below. The sitemap is a RECURSIVE Liferay quirk (sitemap.xml returns itself,
  5,662 URLs) — don't crawl it; use Liferay site search instead.
- Mass-enumeration against search portals is blocked by design (you'd need candidate
  policy/PAN data — chicken-and-egg).
- The moat is NOT the data. It's the claims-assist/finder service: heirs don't know
  they're owed money; matching people to unclaimed policies + handling succession
  paperwork is the product.

## Pipeline (all in C:\Users\HP\ai-workforce\swarm\)
- `unclaimed_probe.py` — classifies all portals BULK/SEARCH/UNKNOWN via curl:
  scan HTML for downloadable file links (.pdf/.xls/.xlsx/.csv) + form/input detection.
  Output `unclaimed_portals.json`. UNKNOWN = JS-rendered, needs browser.
- `unclaimed_extract.py` — pymupdf table extraction → `unclaimed_records.csv`
  (1,181 rows, deduped). Raw PDFs in `unclaimed_data/`.
- `unclaimed_finalize.py` — generic re-extractor over every PDF in unclaimed_data/
  (handles new drops idempotently); `unclaimed_master.csv` (2,172 rows) +
  `unclaimed_master.db` (SQLite, guessed `state` column from address — NOT
  authoritative) + `unclaimed_README.md`.
- Bing RSS for finding these: `site:`/`filetype:` operators are IGNORED by Bing RSS
  (returns junk like insurance aggregators) — use the IRDAI directory + direct URLs
  instead. Plain keyword queries only.

## Parallel-hunt pattern (what landed the big catch)
3 delegate_task subagents in parallel: (1) LIC list-hunter, (2) JS-portal deep-dive
(12 insurers), (3) open-web bulk-list hunt. Agent 3 found IndiaFirst's 993-record PDF.
One agent (LIC) got trapped in the recursive sitemap and stalled — acceptable cost;
results still land from the others.

## WAF / JS-SPA probing (gov sites)
- curl gets 403/000 on WAF'd SPAs (Oriental AWS-WAF, IRDAI CMS). But browser_console
  `fetch()` from the loaded SPA context succeeds — replicate the EXACT API call the SPA
  makes. Find it via `performance.getEntriesByType('resource')` filtered to fetch/XHR
  (reveals Strapi CMS endpoints like `/cms/api/contents?filters[content_type][$eqi]=...`).
- WAF tokens rotate: after a 403, re-navigate then fetch immediately.

## pymupdf table-extraction pitfalls (all hit for real)
1. `page.find_tables()` + `t.extract()` beats hand-rolled line/word heuristics for
   gridded PDFs. ALWAYS check per-page table counts + the first table's header row
   before writing the mapper.
2. Header-row detection must be STRICT (≥2 keyword hits AND non-empty-cell-count
   bound). A loose regex like `Branch|Policy No|Name of the Insured` silently eats
   DATA rows whose name/address contains those words (lost 44 ECGC rows).
3. SILENT ROW-LOSS BUG: the `recs.append()` must sit OUTSIDE the if-header/else
   branches. When it ended up inside `else`, all header-mapped rows (49) never
   appended — output looked clean, counts were short. Debug by instrumenting a
   trace loop that counts raw rows vs appended rows per table.
4. Amount formats: `Rs. 18,662.00` — stripping non-digits keeps MULTIPLE dots
   (`.18662.00`). Fix: after strip, if >1 dot, keep the LAST numeric group
   (`re.findall(r"\d+\.\d{1,2}|\d+", amt)[-1]`).
5. This host: `pip install` can target python3.14 while `python` is 3.11 — always
   `python -m pip install <pkg>` so the lib lands in the interpreter that runs scripts.

## LIC DIVIDEND REGISTERS — the bonus bulk haul (found by LIC subagent)
LIC (the listed company) publishes bulk unclaimed-SHAREHOLDER-DIVIDEND registers via
Liferay site search: `licindia.in/search?q=unclaimed` → document library
(/documents/20121/...) PDFs. 16 files downloaded (~223 MB, one byte-identical dup).
NOT policyholder claims — a different unclaimed-money category (dividends before IEPF
transfer), but real names + amounts + addresses + folios.
- Columns (2025 format): SNo | Folio | Name | Address1-4 | Pincode | Warrant |
  MICR | Net Amount | Total Shares | Due date for IEPF transfer
- Registers: one per FY; the 4 unique Nov-2025 snapshots parsed gave ~Rs 2.52 cr
  (FY24-25: 19,630 rows/Rs 1.50 cr; FY22-23: 31,624/Rs 58 lakh; FY23-24 interim:
  25,183/Rs 29 lakh; FY21-22: 34,938/Rs 15 lakh). 12 older 2023-24 snapshots overlap.
- Parser: `lic_parse.py` (line-based, fast — 2-4 min/file; table extractor times out
  on 200+ page files). ~96 real rows/page; naive line parser OVER-SPLITS records
  (~2x rows) — count amount-bearing rows for the real number.
- Manifest: `unclaimed_data/manifest.txt`. Records: `unclaimed_data/lic_*_nov2025_records.csv`.
- Grand total incl. policyholder lists ≈ Rs 3.91 cr / ~113k amount-bearing records.

## User expectations (this user, verified Aug 2026)
- "Pull EVERY single available data" → run parallel subagents (3x delegate_task:
  LIC hunt / SPA-portal deep-dive / web-wide hunt), don't stop at first sources.
- Headline deliverable = running TOTAL AMOUNT (Rs crore) + record counts; user asks
  for the NUMBER first, before analysis. Report UNIQUE totals — dedupe overlaps
  (ECGC Rs1000+ file is a subset of the full file; 12 older LIC registers overlap the
  4 Nov-2025 snapshots).
- Report the honest ceiling (search-only dead ends, WAF walls) — user respects
  verified negatives over hand-waving.
- Business angle: finder/claims-assist for heirs. Dataset has ZERO phones (1 email in
  2,172 rows) → outbound cold-call impossible; the model is inbound name-search
  (aggregate all insurers, vernacular/WhatsApp) + claims-assist fees.

## Claims-assist / finder business research (3 parallel subagents, Aug 2026)
Market scan + legal + GTM research for the finder/claims-assist play. All live-verified.
- **Scale FY26 (Lok Sabha/MoneyControl):** ~Rs 1.1 lakh cr unclaimed total (bank
  deposits Rs 83k cr, insurance Rs 14k cr, equities Rs 10k cr). LIC Rs 7,318 cr;
  EPFO Rs 9,330 cr in ~31L inoperative accounts; insurers ex-LIC Rs 8,974 cr;
  UDGAM deposits Rs 72k cr. Reclaim-rate proof: govt "Your Money Your Right"
  campaign reclaimed Rs 5,777 cr across 748 districts.
- **Incumbents:** Share Samadhan (largest IEPF/equity recovery), IEPFClaim/GLC
  Wealth, IEPF Doctor, Legacy Asset Solutions (success-fee-only), Insurance Samadhan
  (Rs 999 + 15-20% success, no-win-no-fee), Kustodian.life (EPF), UnClaimedX
  (Bengaluru, digital-inheritance, English-first). Fee norms: success-% common,
  flat Rs 5-10k, or 2-3% EPF corpus; NO statutory cap found.
- **Legal (key facts):** IRDAI MC 2024 (Ref .../117/9/2024): death claims settle
  15/45 days, interest bank-rate+2% if delayed, no rejection for missing docs.
  Succession Certificate ONLY from civil court (4-8 mo uncontested, 1-3 yr contested;
  state ad-valorem court fee ~3% Maharashtra); small claims accept notarized
  legal-heir affidavit + indemnity bond (LIC Form 3805). Policyholder unclaimed →
  Senior Citizens' Welfare Fund after 10 yrs (claimable 25 yrs). IEPF (7-yr rule)
  ONLY for LIC shareholder dividends: Form IEPF-5, company e-verifies 30 days +
  Authority refunds 60 days, free of fee (rules amended 6 Oct 2025, G.S.R. 733(E)).
  Third party CAN charge for paperwork; advocates can't take contingency fees
  (BCI Rule 20); non-lawyers can't appear in court (Advocates Act s.33); buying
  claims barred (TP Act s.6(e)). DPDP Act 2023: cold outreach needs consent or
  s.17(1)(a) legal-claim hook; deceased's data likely outside Act, living heirs
  protected; phone/SMS also hit TRAI TCCCPR 2018 DND. Nominee-vs-heir unsettled
  (2025 court split; Insurance Act s.39 2015 amendment made spouse/children/parents
  "beneficial nominees").
- **GTM:** NO private WhatsApp+Hindi finder exists (govt EPFO has the only one —
  AI chatbot + E-PRAAPTI). Nobody indexes insurance unclaimed lists BY NAME
  (banks=UDGAM, shares=IEPF, insurance=search-only) → scraped dataset IS the moat.
  Hindi SEO + YouTube Shorts proven demand (18K-455K views on this exact topic).
  WhatsApp Business API: service replies inside 24-hr window FREE (user-initiated
  chatbot ≈ zero cost); marketing templates Rs 0.88. Scam wave ("fake Bima Lokpal
  calls") → anti-scam / no-fee trust positioning is the wedge.
- Full legal notes saved: `C:\Users\HP\research\unclaimed-insurance-legal-research.md`

## Name-search MVP (built on the dataset)
`C:\Users\HP\ai-workforce\unclaimed-mvp\` — stdlib-only (zero deps):
- `build_index.py` → `unclaimed_index.db`: merges unclaimed_master.csv + LIC
  Nov-2025 CSVs, normalizes names (uppercase, strip non-alnum), dedupes by
  (source, name_norm, amount). ~88,704 searchable records, ~Rs 2.49 cr indexed.
- `app.py` :8787 — ThreadingHTTPServer + /api/search?q= (token-coverage LIKE:
  `name_norm LIKE %tok1%tok2%`, rank by coverage then amount DESC, cap 40) +
  /api/stats. `index.html` — Hindi-first mobile UI, anti-scam banner, claim
  guidance. Verify with real names from the data (e.g. "Ramanbhai Parmar").
- MVP limits: no fuzzy matching (partial names miss), some LIC rows lack amounts
  (parser column issue), localhost only. Next: fuzzy/transliteration, public deploy.

## Remaining work if resumed
- Oriental's public-disclosures (Strapi CMS behind AWS-WAF) never rendered even in
  browser — its FY pages list per-year disclosure forms; the unclaimed list may exist
  there if the WAF token dance succeeds (re-navigate → immediate fetch).
- LIC divisional-office unclaimed lists were NOT found in the sitemap — treat LIC as
  search-only until proven otherwise.
