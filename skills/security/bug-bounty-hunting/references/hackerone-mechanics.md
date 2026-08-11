# HackerOne mechanics (verified 2026-08-07)

## Directory URL params (the sort trap)
Default sort is LAUNCH DATE — useless for finding active targets. Sort by
activity (resolved reports) instead:

```
https://hackerone.com/directory/programs?offers_bounties=true&order_field=resolved_reports_count&order_direction=DESC
```

Other params: `order_field=launched_at`, checkboxes map to
`offers_bounties=true`. The "Offers bounties" checkbox click sets these
params in the URL — replicate via URL, don't fight the UI.

## Scope tab is SPA-only
`https://hackerone.com/<program>/scope` returns a 404 page
("looks like this page evaded detection"). Scope lives in a tab on the
program page. The treeitem has no ref in the compact snapshot — click via
JS evaluation:

```js
[...document.querySelectorAll('[role="treeitem"]')].find(e => e.textContent.trim() === 'Scope').click()
```

Then snapshot. The scope table includes: asset name, type (Domain/API/
Android/iOS), coverage (In scope / Out of scope), max severity, bounty
eligibility, last update, and RESOLVED REPORTS count per asset — the
resolved count is the competition gauge (0 = untouched).

## Program page section map (what to extract)
- Rewards summary: severity → avg bounty + % of resolved submissions
  (e.g. "Low $100, 44.9% of submissions" = they PAY low-sev → beginner gold)
- Stats: total paid, avg bounty range, top bounty, reports/90d, response
  efficiency, assets in scope
- Test Plan & Credentials: provided test accounts (OTP-based logins often
  use fixed OTP like 999999), supplier/panel creds, required request
  headers (e.g. `X-Hackerone: <username>` on EVERY test request)
- Known Issues: closed-as-duplicate list — do not report these
- Out of Scope: enumeration, rate limits, clickjacking, cache deception,
  CSRF-on-unauth, self-XSS, open redirects (unless chained), missing
  headers, scanner-only reports; per-asset extras (e.g. supplier panels
  exclude IDOR/SSRF/file-upload without demonstrated impact)
- Rules: no automated scanners, no rate-limit testing on money flows,
  stop-and-report on admin/system access, cancel time-limited test orders,
  no real transactions, all communication on-platform

## Recon notes from the Meesho session (patterns that generalize)
- WAF 403 (370-375 byte block page) on HEAD/GET from a datacenter IP while
  the asset loads fine from residential — don't declare assets dead; defer
  to the user's browser session.
- SPA bundle endpoint mining: index.html → script src → fetch bundle →
  `grep -oE '"/[a-zA-Z0-9_./-]{3,60}"'` for API paths, plus base-URL and
  header-name greps. React apps leak the whole API map this way.
- Auth-gated APIs return 400 "Unexpected Error" (not 401) when headers
  missing — check the bundle for Authorization / X-XSRF-TOKEN / custom
  header names before assuming the endpoint is dead.
- `curl --compressed` — gzip'd JSON bodies look like binary garbage
  without it; this misled initial probing for a full round.
- Meesho reference doc (full recon, creds, attack plan, asset table):
  C:\Users\HP\recon\meesho-recon.md (session artifact, not part of skill)
