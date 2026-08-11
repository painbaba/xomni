# Portal bulk-triage: 12 Indian insurer unclaimed-amount portals (Aug 2026)

Task: determine whether each portal offers a BULK downloadable list (PDF/XLS/CSV
of all policyholders) or is SEARCH-ONLY (form requiring policy no / PAN / name /
DOB). Method: batch curl probe → browser-render JS shells → static webpack
analysis when browser was down. Output dir: `C:\Users\HP\ai-workforce\swarm\unclaimed_data\`.

## Verdict table

| # | Portal | Verdict | Evidence |
|---|--------|---------|----------|
| 1 | maxlifeinsurance.com/cs/unclaimed-amount | SEARCH-ONLY | Browser: "enter any two fields" Name/DOB/Policy/PAN form; zero pdf/xls links in DOM |
| 2 | sbigeneral.in/unclaimed-policy-details | SEARCH-ONLY | Browser (after cookie-accept): Name/PAN/DOB/PolicyNo form; bundle analysis found only cp-api key/consent endpoints |
| 3 | tataaig.com/service/unclaimed-amount | SEARCH-ONLY | Browser: Insured Name/Birthdate/Policy No form + Search button |
| 4 | portal.uiic.in/CUSTOMERPORTAL/unclaimed_query.jsp | DOWN (search-only presumed) | TCP connects, GET times out → 503. Main site uiic.co.in links to the same jsp. JSP name implies query form |
| 5 | kotakgeneral.com/claims/unclaimed-amount | UNVERIFIED (likely search-only) | React shell "You need to enable JavaScript"; 5.6KB |
| 6 | aicofindia.com/regulatory-compliance | UNVERIFIED | "JavaScript is required" shell; 3KB |
| 7 | customerportal.pnbmetlife.com/unclaimed/amount/ | UNVERIFIED | 535-byte `<div id="root">` shell |
| 8 | myinsurance.tataaia.com/.../unclaimed-funds/authenticate | UNVERIFIED (auth gate in path) | "Loading..." SPA |
| 9 | lifeinsuranceservicing.adityabirlacapital.com/pre-unclaim | UNVERIFIED | 136KB "enable JavaScript" shell |
| 10 | generalicentrallife.com/customer-service/unclaimed-amount | UNVERIFIED | Next.js shell; only title "Unclaimed Amount" in curl text |
| 11 | navi.com/insurance/unclaimed-claims | SEARCH-ONLY-likely | Curl-rendered text shows "Search Now" tool; downloads page is generic, no unclaimed list |
| 12 | saharalife.com/vs/FrmDispUnclaimed.aspx | DEAD | Serves only ASP.NET precompilation marker file (86 bytes) |

**Outcome: 0 bulk lists found.** All confirmed pages are search forms. This is
the expected regulatory shape (IRDAI mandates per-claimant lookup, not bulk
disclosure).

## SBI General static bundle analysis (browser kept timing out)

Browser navigation failed repeatedly (`localhost:9377` read timeout + 500s), so
the React SPA was analyzed from its webpack bundles:

```bash
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0'
curl -s -A "$UA" -o sbi_main.js 'https://www.sbigeneral.in/webportal/static/js/main.55a6a509.chunk.js'
# 1. route → component mapping
grep -oE 'path:"/unclaimed-policy-details/",component:At' sbi_main.js
# 2. lazy chunk IDs for that component
grep -oE 'At=Object\(o\.lazy\)\(\(function\(\)\{return Promise\.all\(\[[^]]*\]\)' sbi_main.js
# → At=Object(o.lazy)((function(){return Promise.all([n.e(0),n.e(1),n.e(279)])...
# 3. API base URLs + endpoint calls
grep -oE '"https://[^"]*api[^"]*"' sbi_main.js
grep -oE '\.(get|post)\("[^"]*"\)' sbi_main.js
```

Findings: API base `https://www.sbigeneral.in/cp-api/api` (+`/key`, `/v2/key`,
`/cookie-consent`, `/captcha`); page component is lazy chunk 279 (module 3389).

**PITFALL — chunk hash map unfindable:** chunk files are
`{id}.{hash}.chunk.js` but the id→hash map was not present in `main.*.chunk.js`
or `100.*.chunk.js` (`re.findall(r'(\d+):"([a-f0-9]{8,})"', js)` → empty).
Guessing `279.0.chunk.js` returned the HTML shell (200, 17KB), not JS. Static
bundle analysis is therefore good for endpoint/route DISCOVERY, not for
reconstructing the full SPA render. Use the real browser when it's available.

## UIIC server-down diagnosis

- Plain curl: `HTTP 000` (timeout) — looked like a block, but `-v` showed TCP
  connect OK, then 0 bytes after GET → server accepts, never responds.
- Retry with 90s timeout: `HTTP 503 Service Unavailable` → server-side
  capacity/maintenance, not client-side blocking.
- Alternate-domain check: `uiic.co.in` main site returns 200 and links to the
  same `unclaimed_query.jsp` → URL is current, portal itself is down.
- Lesson: distinguish "blocked/anti-bot" (fast 403/202, challenge pages) from
  "down" (TCP-OK-then-hang, 503). Only the first is a scraping problem.

## IRDAI context (durable domain knowledge)

IRDAI circulars require life/general insurers to operate "unclaimed amount"
lookup portals where a claimant searches by policy number / PAN / name / DOB
and gets their own amount. There is no regulatory requirement to publish the
full list, and insurers do not. Any task asking to "download all unclaimed
policyholders" from these portals should expect 100% SEARCH-ONLY verdicts and
budget accordingly — the real data path (if any) is via Bima Bharosa
(bimabharosa.irdai.gov.in) or direct insurer contact, not portal scraping.
