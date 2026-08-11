# Multi-Program Pipeline — ranked shortlist + A&F dossier (2026-08-07)

Extends SKILL section 1 (target selection) and section 7 (bot walls) with
the first cross-program sweep's measured data. Strategy: volume across
beginner-friendly bounty programs; every candidate got a live probe before
being added to the ledger.

## Directory scraping without login (verified)
- `GET /programs/search?sort=resolved_reports_count&order=descending...`
  returns `[]` unauthenticated — curl AND in-page fetch (login-gated).
- Use the rendered table at `/directory/programs` in a real browser:
  `[...document.querySelectorAll('tr')].map(tr => tr.innerText...)` for
  stats; handles from `tr a[href]` — real links are like
  `/abercrombie_fitch_bbp?type=team` (guessable short handles 404).

## Ranked shortlist (live directory, sorted by resolved reports)
Program             | Handle                    | Resolved | Bounty      | Notes
Abercrombie & Fitch | /abercrombie_fitch_bbp    | 58       | $50-$750    | avg $750, 866 rpts/90d (fastest triage), self-reg allowed
Box BB              | /box_private              | 208      | $150-$500   | managed, huge SaaS surface
Agoda Public        | /agoda-public             | 0        | $50-$576    | retesting, travel
Wolt                | /wolt                     | 0        | $100        | fresh
CoinMate            | /coinmate                 | 71       | $50 flat    | crypto
1win                | /1win_com                 | 11       | $150-$300   | gambling (real money flows)
Anthropic           | /anthropic                | 390      | $50-$1k     | AI/jailbreak focus (different skillset)

## A&F probe results (live, 2026-08-07)
Scope: abercrombie.com (21 rpts), hollisterco.com (8), anfcorp.com (11),
corporate.abercrombie.com (2). OOS: nonmerchvendorprofile.anfcorp.com,
applications.abercrombie.com.
- .git/HEAD, .env, .git/config on all hosts: 403/404/000 — clean.
- CORS: no ACAO reflection on any host.
- robots.txt legacy paths (/shop/OrderCalculate, ANFCheckPromoCodes,
  OrderItemAdd, ANFCheckOrderItems, ShoppingBagDisplay, OrderItemDelete,
  OrderConfirmationDisplayView): ALL 200 = SPA shell fallback (0-3KB,
  CSP header) — dead routes, not live services.
- /sos → `HTTP/1.1 767 Help Me` (custom non-standard status) + `_fs-ch-*`
  challenge assets → Shape Security bot wall. Root page = challenge shell.
- /login?redirect= → 404 (auth route lives inside the SPA; unknown until
  browser-driven analysis).

## 1win probe results (live, 2026-08-07)
Scope: 1win.com/casino (0 rpts), 1w.run (0), 1w.cash (0). Avg $150-300,
top $1500-2250, 756 rpts/90d, $4,300 paid/90d, last resolved 17 days ago
= ACTIVE program, fresh untouched assets.
- GEO-BLOCK: 1win.com + 1w.cash resolve (nslookup OK) but curl times out
  (code=000) from India IP — gambling geo-block. Sibling 1w.run answers
  (Cloudflare). Probe all scoped hosts before concluding unreachable.
- robots.txt on 1w.run leaks /panel/* → "Affiliate Program 1win" Vue SPA.
- Bundle API mapping (request-CXkcAhza.js, main-rEvyXjsL.js):
  - DEFAULT apiPath = `/api` (grep `apiPath\(\)\{return``\}`); explicit
    per-call overrides: `/api/v3`; separate `/api/v5` gateway (APIGW2
    "Entry point is not found" = gateway live, wrong entry path).
  - Template-string fragments reveal routes: `/v2/postbacks/${id}`,
    `/v2/postbacks/config`, `/v2/postbacks/global`, `/v2/stats/recap`,
    `/v2/app-config/support-contacts`, `/api/web/v2/tracker` (POST-only).
  - Full URLs = apiPath() + fragment → /api/v2/postbacks/*.
- Auth verification: ALL postback routes return {"errorCode":"PRST00",
  "errorMessage":"Unauthorized"} unauth (GET+POST) — properly gated.
  PRST02 "Cannot GET/POST <path>" = route exists, wrong method.
- CORS: `access-control-allow-origin: *` on API responses (no credentials
  mode — noted, not exploitable alone).
- Public /api/v5/app-config/web-app-manifest = PWA manifest, no leak.
Verdict: API layer gated. Panel testing needs an affiliate account
(registration = manual step, parked). Affiliate money surface
(postbacks/tracker/stats) checked once — the class pays big when a
postback accepts unauth forged conversions.

## Honest probability ranking (what actually pays)
1. Valmo AWB lead (Meesho): ONE human OTP → $150-600 class. Best odds.
2. Vercel OSS fresh-commit delta hunting (nightly cron): low per-day,
   compounds over days.
3. Post-auth testing on self-registration programs (A&F): real odds, needs
   one email verification per program.
4. Unauth mass-probing of remaining majors: bot-walled, low yield.

Rule from this sweep: quantify the ONE irreducible manual step per path
(OTP / email verify / none) and present the honest ranking — the user
decides which 60 seconds to spend.

## Ledger
- This session's recon doc: C:\Users\HP\recon\multi-program-hunt.md
- A&F challenge shell captured: C:\Users\HP\recon\anf_shell.html
