# Meesho BBP dossier (verified 2026-08-07)

Program: hackerone.com/meesho_bbp — launched Feb 2026, response efficiency
79%, fast payment ~1mo, retesting+collaboration, avg first response 1.5d,
triage 4.5d. Total paid $17,390; avg bounty $150-200; top $900-1700.
44.9% of resolved = LOW severity ($100 avg) — low-sev findings ARE paid.

## Bounty table (web & platform)
Low $50-150 / Medium $150-600 / High $600-1200 / Critical $1200-2000.
Mobile (static analysis only): Low $100-250 / Med $250-800 / High
$800-1700 / Crit $1700-2500. CVSS-driven, team discretion.

## In-scope assets (bounty-eligible)
- www.meesho.com — Domain, Critical, 17 resolved (33%)
- supplier.meesho.com — Domain, Critical, 10 (20%) — supplier panel
- affiliate.meesho.com — Domain, Critical, 4 (8%) — affiliate panel SPA
- prod.meeshoapi.com — API, Critical, 5 (10%) — mobile app API
- admin.meeshosupply.com — Domain, Critical, 0 (0%) — ADMIN panel, untouched
- superstoreapp.meesho.com — Domain, HIGH max, 0 (0%) — grocery; PIN 440002
- www.valmo.in — Domain, Critical, 5 (10%) — logistics arm
- meesho.io — Domain, LOW max, 0 (0%) — NEW Apr 2026
- investor.meesho.com — Domain, LOW max, 0 (0%) — NEW Apr 2026
- com.meesho.supply / com.valmo.valmo (Android) / 1457958492 (iOS) — apps

## Test credentials (program-provided)
- Supplier: suppliertest-1@meeshoai.com / suppliertest-2@meeshoai.com —
  password Hackerone@123
- Consumer (web+mobile): phone 6666666661 / 6666666662 — OTP 999999
- REQUIRED header on ALL test requests: X-Hackerone: <h1-username>
  (auto-injected by the meesho-hunter extension)
- Grocery: set PIN 440002 (Nagpur); CANCEL grocery orders within 30 min
  or the test account locks.

## Known duplicates (never report)
- HTML injection in ticketing module, supplier.meesho.com
- Stored XSS via file upload, supplier.meesho.com
- Bank details update OTP bypass, supplier.meesho.com
- My Bank & UPI details OTP bypass, mobile apps
- Account deletion → first-order discount misuse (web + apps)

## Out of scope highlights
Enumeration, brute-force/rate-limit, clickjacking, cache deception,
CSRF-on-unauth, self-XSS, open redirects (unless chained), stack traces,
missing headers, scanner-only reports, collection-ID enumeration in
affiliate panel, account deletion in apps. Supplier panel extras: IDOR/
SSRF/file-upload WITHOUT demonstrated impact, MFA-missing, rate-limiting
alone. Third-party/vendor systems + listed exclusions (warehouse.meesho.com,
Rider App, agency/affiliate-c/grocery-supplier/farmiso/console/atlas/
di-prd-superset, log10-web-staging.valmo.in, com.valmo.ops).

## Recon findings (2026-08-07, light touch)
- www.meesho.com / supplier / admin.meeshosupply.com / investor.meesho.com:
  403 from datacenter network (WAF edge, TLS-fingerprint) — load fine in a
  real browser (Edge opened admin → redirected to /login?redirect=%2F).
- affiliate.meesho.com: React SPA. Surface from bundle: /api/affiliate/*,
  /api/v1/performance/perf, /oauth-bridge, /bank-details, /user/,
  /view-all-ordered-products. Unauth API probes 404 (routed elsewhere).
  Source maps NOT exposed (403).
- superstoreapp.meesho.com: React SPA. API map: /api/customer/{config,
  details, cart, order/confirm_order, order/cancel, fetch-payment-options,
  file/upload, fetch-nearby-pickup-points, app-offers, ...}. Auth =
  Authorization + X-XSRF-TOKEN (session+CSRF). Unauth = 400 "Unexpected
  Error" (gated).
- meesho.io: 301 → https://www.meesho.io:443/ (explicit :443 in Location —
  minor quirk). www.valmo.in: minimal React shell (1.5KB).

## Attack priorities (from session)
1. admin.meeshosupply.com — 0 reports, Critical; map login surface, pre-auth
   functionality, auth bypass.
2. supplier.meesho.com — cross-ACCOUNT authz between the two test accounts
   (IDOR with real impact: other supplier's orders/PII/financial docs).
3. affiliate.meesho.com — /bank-details + payout flows (OTP/authz),
   /oauth-bridge state issues.
4. superstoreapp.meesho.com — order/confirm_order logic (price/qty),
   file/upload restrictions, cancel flow (30-min rule).
5. meesho.io + investor.meesho.com — fresh, max Low, zero dup risk → $50-250.
6. Mobile static analysis: secrets with demonstrated impact.

## Tooling
C:\Users\HP\meesho-hunter — extension (X-Hackerone injection, target nav,
creds copy) + hunt.sh launcher + cdp.js verification. See
references/extension-automation.md. Recon report: C:\Users\HP\recon\meesho-recon.md.
