---
name: bug-bounty-hunting
description: Hunt bug bounties on disclosed programs like HackerOne.
---

# Bug Bounty Hunting (authorized programs only)

## Why this skill exists
User hunts bug bounties on HackerOne (started 2026-08, Meesho as first
target). Hard boundary established with user: authorized targets only —
programs that invite testing (HackerOne scope, CTFs, own labs). Never
help attack systems the user doesn't own or that lack a disclosed program.

## Workflow (ordered)

### 1. Target selection — optimize for a beginner's first payout
Load the HackerOne directory sorted by ACTIVITY (resolved reports = proof
they actually pay and triage), not by launch date (default):
`https://hackerone.com/directory/programs?offers_bounties=true&order_field=resolved_reports_count&order_direction=DESC`
- PROGRAM LISTING VIA API (CORRECTED 2026-08 — the search JSON API DOES
  work unauth, contrary to earlier measurements): curl
  `https://hackerone.com/programs/search.json?query=bounty&limit=100&offset=N`
  returns `{"total":438,"results":[{"id","url"(=handle, leading slash),
  "name","meta":{submission_state, resolved_report_count, minimum_bounty,
  average_bounty, offers_bounty, default_currency}}]}` — 438 bounty
  programs, sorted by resolved_report_count DESC by default. Python +
  urllib with a browser UA; filter `state=='open'` + `min_bounty` set,
  dedupe by handle. CAVEATS (measured): `offset` pagination returns
  DUPLICATED results in practice (5 pages → 500 rows ≈ 100 unique) — dedupe
  by handle and accept ~100 programs per query; try different query terms
  (`bounty`, `managed`, `retesting`) to widen the pool. The RENDERED
  directory table is the fallback (scrape `tr` rows via browser_console —
  `tr.innerText` → Program, Launch, Reports resolved, Bounties min/avg) and
  get REAL program handles from `tr a[href^="/"]` links (they carry
  `?type=team` suffixes; guessing handles 404s — e.g. `/abercrombie` is
  wrong, `/abercrombie_fitch_bbp` right). NOTE: the directory UI is FLAKY
  in camofox (virtualized list sometimes never renders, ~400-char page
  text) — prefer the JSON API over fighting the UI. Program-page stat to
  weight: "Reports received | 90 days" = triage VELOCITY (A&F: 866/90d
  with avg $750 → fast money; a program with 0 resolved and no velocity
  is a black hole).
- STALENESS signal: the "Last report resolved" date on the program page.
  Old (weeks-to-months) while reports keep arriving = backed-up triage —
  DROP the program even if resolved-count looks good (measured: CoinMate
  71 resolved but last resolved 2 months ago + $50 flat → dropped).
  "Resolved days ago" + high 90d reports = processing live right now.
Filter for: offers bounties + active. Beginner-friendly signals on the
program page:
- Accepts LOW severity (check rewards summary: % of resolved that are Low;
  most programs auto-close low-sev — ones that pay Low are gold for a first
  payout, e.g. Meesho 44.9% Low @ $100 avg)
- Provides TEST CREDENTIALS (huge: no account creation friction)
- High response efficiency (79%+), fast first-response time
- "Retesting" + "Collaboration" markers
- Local/India angle when the user is in India (local context, phone-OTP signup)
- Fresh assets with 0 resolved reports = untouched, best dup odds
- Check Stats: total paid, avg/top bounty, reports received per 90d

### 2. Read the FULL scope before touching anything
Program page sections that matter:
- In-Scope table (asset, type, max severity, bounty-eligible, resolved
  reports count per asset) — the report count per asset tells you where the
  competition is
- Out-of-Scope list (hard rules: enumeration, rate-limit, clickjacking,
  CSRF-on-unauth, self-XSS, missing headers, scanner-only reports, etc.)
- Known Issues list (will be closed as DUPLICATES — never report these)
- Test Plan & Credentials + account signup instructions
- Rules: required headers (e.g. X-Hackerone), no automated scanners, no
  rate-limit testing on money flows, stop-and-report on admin access
- Safe Harbor terms + jurisdiction

### 3. Recon (light touch — program rules forbid aggressive scanning)
- Fingerprint every in-scope web asset: HEAD/GET with browser headers,
  title, tech hints. ~1-2 requests each, manual curl, no fuzzers.
- WAF 403 from a datacenter/proxy IP does NOT mean the asset is down —
  note it and test from a residential browser instead.
- SPA recon: fetch the JS bundle(s) (find via index.html script src),
  grep for API paths (`"/api/..."`), base URLs, header names
  (`"x-..."`, Authorization, XSRF). This maps the API surface without
  touching it.
- Probe discovered API endpoints unauthenticated ONCE each, no IDs:
  200-with-data = potential unauth access finding; 400/401/404 = gated.
  Gated APIs usually need session cookie + CSRF token (X-XSRF-TOKEN) or
  Authorization — note the mechanism from the bundle.
- `curl --compressed` is mandatory — many APIs gzip by default and raw
  bodies look like binary garbage otherwise.
- GEO-BLOCK vs DOWN: `curl` exit 28 / `code=000` (connect timeout) while
  DNS RESOLVES (nslookup returns IPs) = CDN edge geo-blocking your region,
  not a dead host. Gambling/casino sites block India IPs outright
  (measured: 1win.com, 1w.cash resolve but never connect). Sibling domains
  of the same brand may still answer (1w.run worked) — probe all scoped
  hosts before concluding the target is unreachable.
- JS bundle API base discovery: endpoints are built from a base + template
  fragments. Grep `apiPath\(\)\{...\}` / `baseURL:` — the DEFAULT base and
  EXPLICIT per-call overrides can differ (1win: default `apiPath` = `/api`,
  overrides `/api/v3`, separate `/api/v5` gateway). Endpoint fragments:
  `` `.../${e.id}` `` template strings reveal routes that literal
  `"/api/..."` greps miss. Probe each base once.
- API error-code triage (structured JSON = a live API, read the codes):
  "Cannot GET/POST <path>" = route exists, wrong method → don't waste
  method probes; "Unauthorized" = auth-gated → stop, note it; "Entry point
  is not found" = gateway exists, wrong path base. Triage by code, not by
  HTTP status. Affiliate money surfaces: `/postbacks`, `/tracker`,
  `/stats` — usually gated (1win postbacks: PRST00 Unauthorized), but the
  check is 3 requests and the class pays big when it isn't.
- Record: which assets are reachable from the current network vs
  WAF-gated, endpoint maps, auth mechanisms, redirect quirks.

### 3.5 Shodan passive recon — legal exposure survey (no API key needed)
For exposure research ("what's out there") WITHOUT touching any device,
Shodan's public web search works with ZERO auth for basic queries
(verified Aug 2026):
- `https://www.shodan.io/search?query=webcam` → total-count heading
  (2,418 for "webcam") + TOP COUNTRIES / TOP PORTS / TOP PRODUCTS /
  TOP ORGANIZATIONS / TOP OS facet lists + first page of results with
  banners — all without login. Same for product queries ("Hikvision" →
  1.12M results, top ports 80/81/8080/82/88).
- FILTERS (country:IN, port:, net:) REQUIRE login — a filtered query
  returns "Please log in to use search filters." Basic keyword queries
  are the free tier.
- HONEYPOT REALITY CHECK (the lesson that makes this safe): a large
  share of "exposed webcam/camera" results are bait servers with fake
  banners (SQ-WEBCAM/SPIP composites, fake grafana cookies, "Loginip"
  headers) — banners are NOT proof of a real device. Many flagged
  results are labeled `honeypot` in the org column. Never treat a
  Shodan banner as a live target; it's research data only.
- BOUNDARY (state it plainly): reading Shodan's stored banners =
  passive research, legal. Clicking through to any listed IP, viewing
  feeds, or testing = unauthorized access (IT Act 43/66 in India) even
  if the device is exposed. The legal active-testing path is bug-bounty
  scope; Shodan is for understanding the exposure landscape.

### 4. Attack plan (priority order for a beginner)
1. Untouched assets (0 resolved reports, Critical-eligible) — admin
   panels, fresh domains. Best dup odds.
2. Cross-account authorization with PROVIDED test accounts (account A
   reading B's data) — classic, pays, and only IDOR *with demonstrated
   impact* counts (bare IDOR often out of scope).
3. Business logic on money flows (payouts, bank details, order confirm)
   — always check the program's known-dups list first.
4. Fresh low-severity-cap assets (max Low) — zero dup risk, easiest
   $50-250.
5. Mobile apps: static analysis only, secrets need demonstrated impact.

### 5. Report quality = 50% of the game
Template in `templates/bounty-report-template.md`. One issue per report,
numbered repro steps with exact requests (including required headers),
business impact (not just CVSS text), screenshot/video proof.

### 6. Hunt tooling & automation — MANDATORY for this user
The user demands FULL end-to-end automation: "build it everything for
once, I'm not going to keep doing steps." Never hand off a step that can
be automated from the agent side (browser launch via CLI flags, config
pre-seeding, CDP verification). Irreducible user inputs only — account
usernames/creds — asked ONCE and pre-seeded into a config file.
- Programs that require a custom header (e.g. X-Hackerone) → build an MV3
  extension that injects it via declarativeNetRequest on scoped domains;
  seed the username from a config.json the launcher can write. Full
  recipe + CDP verification: `references/extension-automation.md`
  (working code: C:\Users\HP\meesho-hunter).
- One-command launcher (hunt.sh): Edge/Chrome with --load-extension +
  custom --user-data-dir + --remote-debugging-port, opens first target.
- Deterministic test suite (node test.js) for the tooling + live
  verification via CDP (rule installed in the browser, not just in code).
- Pitfalls: MV3 SWs sleep ~30s — verify rules right after launch; Edge
  built-in SWs pollute /json/list (filter endsWith('background.js'));
  kill only the debug instance via CDP Browser.close, never taskkill.

### 7. WAF / bot-detection walls & pivoting (measured Aug 2026)
- Akamai bot manager 403s even the APP'S OWN auth-API calls on CDP-driven
  sessions (meesho.com `/api/v1/user/login/request-otp` → 403 edgesuite.net)
  while pages/products/cart/phone-entry all work. Prove it with an XHR hook
  (wrap `XMLHttpRequest.prototype.open/send`, capture status) — fetch() hooks
  MISS XHR traffic (axios apps).
- Page-level bot checks DO pass (Camoufox, `navigator.webdriver` spoof,
  `--disable-blink-features=AutomationControlled`) — but API-level auth
  endpoints still 403. One probe per wall, then PIVOT; don't burn turns.
- Username+password panels dodge the OTP wall, but program test creds can be
  invalid on the web panel — verify once, then pivot.
- Shape Security (retail majors: A&F, hollister): fingerprint = custom
  status line like `HTTP/1.1 767 Help Me` on some routes + challenge shell
  HTML with `_fs-ch-*` asset paths + strict CSP. curl gets the challenge
  shell, NOT the app — page-level bot wall; a real browser (Camoufox)
  passes. Legacy paths from robots.txt (`/shop/*` etc.) then just serve
  the SPA shell (200, 0-3KB, CSP header) — check content-type/body, never
  trust a 200 before calling a route "live".
- Cross-program reality (measured): every major retail/travel/crypto
  target is bot-walled at the page or API level; unauth curl probing
  dead-ends fast. The money paths left are post-auth testing (needs ONE
  self-registration + email verification) or a single human OTP for a
  known lead — quantify these honestly instead of grinding dead surfaces.
- CAPTCHA-LEVEL WALLS (third measured class, 2026-08 — Expedia Group BBP:
  expedia.com/vrbo.com/hotels.com all 429 for curl; the browser gets
  "Bot or Not" = Akamai bot-manager + INTERACTIVE CAPTCHA: routes
  `/botOrNot/initial-validate`, `/cgp/simple/challenge.*`,
  `/akam/13/<pixel>` + a captcha-pwa GraphQL bundle). Camoufox is
  challenged too — this wall needs a HUMAN captcha solve, not JS
  execution, so it closes the automation path entirely. Wall taxonomy so
 far: API-level (Akamai 403 on the app's own XHR — Meesho), page-level
 JS challenge (Shape Security "767 Help Me" — A&F), captcha-level
 (Expedia "Bot or Not"), CLOUDFLARE JS challenge (passable — Quora,
 measured 2026-08: curl gets 403 "Just a moment...", but Camoufox
 SOLVES it and the real page loads; then call the target's API from
 INSIDE the page context — same-origin fetch in an evaluate — which
 carries the cf_clearance and bypasses Cloudflare entirely; verify the
 pass via `document.title` after 15-25s, and read the API surface from
 `performance.getEntriesByType('resource')`). One probe each, then
 PIVOT — captcha walls are not beatable with the current toolset.
- PIVOT RULE (user preference): on a hard wall, switch programs AUTONOMOUSLY —
  never stop to ask. OSS-scope programs (e.g. Vercel Open Source) are ideal:
  shallow-clone in-scope repos, audit high-risk surfaces (input parsing,
  URL/fetch, shell exec, tokens, rendering) with an LLM CLI, verify each
  claim against the code, draft findings only. Nightly cron pattern
  (clone → audit → append findings.md; never submit externally; human
  reviews drafts) — live job: `vercel-oss-nightly-audit`, 1 AM IST.
- Measured detail + tool recipes: `references/waf-bot-walls.md`

### 8. Candidate findings: PoC or it didn't happen
- Every candidate finding gets an assert-based PoC (hypothesis → install the
  dependency → deterministic test with exit code → verdict). Write it as a
  regression test so it documents the SECURITY PROPERTY, not just today's
  attempt: exit 0 = defense holds, exit 1 = escape/leak confirmed.
- PAYLOAD-DEVELOPMENT LAB (built 2026-08-08, authorized localhost-only):
  `C:\Users\HP\ai-workforce\swarm\lab\lab.py` (WAF-vs-origin sim: encoding-depth
  + HPP bypass classes), `lab2.py` (per-class sinks: sqli/xss/ssti/rce/xxe/
  deser/ssrf/idor/auth/proto/path), `lab3.py` (ZERO-TOUCH parser surfaces:
  image/font/doc/XML/archive/email/deeplink/media/vcard/QR), `lab4.py`
  (ANDROID ZERO-CLICK parsers: parcel/ims/nfc/bt/sms/mp4/quic/bundle/audio/rcs —
  50-agent campaign produced ~119 NOVEL payload families, e.g. LF-only SIP line
  endings, MP4 size=0 box family, SMS UDL=0 overflow, RCS file:-URI canonicalization).
  Drive them with tool-using agent harnesses (`lab_agent.py`, `lab_agent_zt.py`,
  `lab_agent_android.py`, reasoning_effort=high on OpenCode Go) to develop +
  lab-VERIFY payloads BEFORE touching an in-scope target — dev in the sim,
  validate on the authorized asset. Recipe + NOVEL payload families:
  parallel-research-swarm skill, references/zero-touch-lab.md +
  llm-api-key-pools skill, references/lab-agent-swarm.md.
- REFUTE honestly and mark it: the just-bash `allowSymlinks: true` +
  absolute-path-passthrough + full-egress chain LOOKED like a sandbox
  escape; a 20-line PoC proved just-bash's ReadWriteFs blocks
  outside-root symlinks (EACCES "resolves outside sandbox"). Marked REFUTED
  in findings.md so neither the user nor the nightly cron re-chases it. A
  killed candidate is a win; a fabricated finding is a reputation kill.
- Recipe + worked example: `references/poc-verification.md`

### 9. Reverse-audit the target's own security fixes (highest-yield move)
In actively-hardened programs (Vercel fixes reported bugs within days),
the team's OWN recent security commits are a map of weak spots. Method:
1. Shallow clones hide history — `git fetch --depth 60 origin main`, then
   `git log --oneline -30`. Commit messages like "fix(teams,slack):
   follow-up hardening for html and url parsing" are gold.
2. `git show <sha>` the hardening commits; audit the FIX for incomplete
   coverage. "Follow-up" commits mark a prior INCOMPLETE fix — hunt the
   regression/edge case.
3. Proven examples (all held, Aug 2026): teams `stripHtmlTags` do-while
   stable loop + `new URL(href)` scheme allowlist {http,https,mailto} (no
   bypass — quote edge cases degrade to inert text); slack length-bounded
   unfurl parse that NEVER fetches the URL (no SSRF); read-tool scope
   guard with per-adapter strict thread-id decoders (no crafted-id channel
   confusion; fail-open default documented by design); X CRC token
   constraint to base64 alphabet closing a signing oracle (informational
   edge: >=16-digit numeric bodies match the pattern AND are valid JSON,
   but X events are objects -> nothing forgable; logged, not reported).
4. Now ALSO running on Matomo (H1 /matomo, open bounty): the same-week
   security commits (2FA preconditions, SSRF-safe fetch opt-in, Overlay
   JS-encode, token_auth URL exclusion) were reverse-audited — three
   fixes complete, one INCOMPLETE (token_auth exclusion covers tracked
   page URLs only, NOT the referrer urlref param → stored raw → view-
   user readable token = API-access chain; conditional/low, queued for
   verification in the nightly cron). When ALL fresh fixes hold, WIDEN
   the sweep — the deepest dig then found a HIGH stored XSS in the
   the Annotations plugin (`{{ note|raw }}` + truncation-only storage +
   view-access write + admin-viewer read + CSP `'unsafe-inline'`) — the
   first confirmed High of the campaign, chain + PoC + duplicate-risk
   check in the dossier; full H1 report draft ready for review at
   C:\Users\HP\recon\matomo_xss_report.md (duplicate-check at submission;
   optional live PoC = Matomo Cloud free-trial self-registration — the
   one human step, no money). Full dossier incl. defused chains, do-not-re-
   walk list, and the PHP authz-scan heuristic:
   `references/matomo-oss-audit.md`.
5. THIRD PROGRAM (Mozilla — TWO handles: `/mozilla` for sites, and
   `/mozilla_core_services` for the AUTH STACK = Firefox Accounts — the
   money surface; the split is discoverable from the `/mozilla` safe-
   harbor link): fxa monorepo first pass came back CLEAN — oauth v2
   consent purge on account delete (both v1+v2 tables cleared, bounded
   credential-safe logging), request→native-fetch migration (added a
   status check = improvement), passkeys ceremony SOLID (server-stored
   single-use consumed challenge, credential→uid binding, signCount
   rollback, UV required). The reusable WebAuthn/passkey audit checklist
   (the 5 things to verify in ANY passkey login flow) + program-split
   note + cron coverage: `references/mozilla-fxa-audit.md`.
6. FOURTH PROGRAM (Zulip, H1 /zulip) — the OPTIMIZATION-REGRESSION
   class (new lesson, measured 2026-08): reverse-audit ALL fresh commits
   touching access-control code, not just "fix/security" ones. An
   "optimize computing inaccessible users" commit REMOVED the
   is_user_active=True filter from get_inaccessible_users_queryset →
   limited guests could access DEACTIVATED users (shared-stream
   subscriptions) in Zulip Cloud for ~10 days; the fix (2bf3bd2)
   re-added it. Found-and-fixed = NOT reportable — but two durable
   outputs: (a) the SIBLING-HELPER HUNT: check every access function in
   the same file (check_can_access_user had the filter pre-existing;
   read the full logic incl. user_access_restricted_in_realm
   early-returns before concluding); (b) the AUTHOR PATTERN: the same
   author's optimization cluster (4 commits that week, one broke
   security) — feed names into the nightly cron as a watch-list.
   Also validated: webhook handlers authenticated via the framework
   decorator (validate_api_key + bot API key) are safe; event-
   notification "optimizations" that skip events are NOT findings
   (events ≠ access control). Full dossier:
   `references/zulip-oss-audit.md`. Cron now covers FOUR repos
   (vercel + matomo + fxa + zulip), nightly 1 AM IST.
5. STORED-XSS-IN-CODE VERIFICATION CHAIN (the order that pays, when a
   `|raw`/unescaped-output sink is found in an OSS codebase): sink →
   storage sanitization (truncation-only = the signature of a FAILED
   mitigation attempt — the fix is incomplete by definition) → WRITE
   authz (view-access = attacker bar) → READ authz (any viewer incl.
   admins = victim bar) → CSP (read the POLICY CONSTANTS, not the
   header — `'unsafe-inline'` in script-src = inline scripts execute,
   no bypass needed) → git history (old pattern = duplicate-risk flag,
   still reportable if unpatched). Impact framing for the report:
   low-priv XSS → admin session → token_auth theft → (Matomo admins can
   upload plugins) → RCE on server.
   SYSTEMIC-SINK SCAN before concluding: regex ALL templates for the sink
   pattern (twig: `\{\{\s*[\w.\[\]'"0-9]+\s*\|raw\s*\}\}`), classify each
   hit server-set vs user-content (translations, generated messages,
   admin config = safe; tracker/DB-derived = candidate), verify ONLY the
   user-content ones. Measured on Matomo: 97 `|raw` outputs →
   annotation.note was the SOLE exploitable one (custom-dimension tooltips:
   name=admin-set + value=escaped → safe; SMS/email labels: weak
   email-client impact → safe; login messages: server-set → safe). The
   singular confirmed sink IS the finding — don't pad the report with
   defused ones.

### 10. GraphQL API hunting (schema oracle + header discovery)
GraphQL endpoints are prime unauth surface on booking/e-commerce flows
(measured: Agoda `/api/activities/graphql` backs the in-scope `/book/`
flow — the API serving a scoped URL is in scope even if the path differs).
Method, in order:
1. Find the endpoint: grep bundles for `graphql` literals and
   `operation=...` params; probe `/graphql`, `/api/*/graphql` with GET and
   POST. `curl --compressed` always (gzip responses look like binary).
2. "Missing required headers" = server-side gate. Discover the header set
   by grepping the request-client bundle for brand-prefixed header names
   (`"AG-CID"` found → pattern is `AG-*`; also `x-*`). Test each plausible
   header until the error message CHANGES (Agoda: adding `AG-CID` +
   `AG-PLATFORM-ID` shrank the error to just "LanguageId"; adding
   `AG-LANGUAGE-ID: 1` unlocked full query validation). The error text
   names exactly which context pieces are still missing — iterate on it,
   don't guess blind.
3. Method/param variants matter: GET-with-query-param can bypass a
   POST-only header gate; an `operation=` param can switch the gateway to
   a REST-envelope parser ("Unable to deserialize request" on GraphQL
   bodies) — DROP the operation param to reach the GraphQL-validating
   backend.
4. Introspection blocked ≠ schema closed. Validation error messages are a
   full schema oracle: "Did you mean 'X'?", "Cannot query field 'X' on
   type 'Y'", "Field 'X' of required type 'Y!' must have a sub selection",
   "Field 'X' argument 'Y' of type 'Z!' is required but not provided".
   Drill the input shape by sending `{}` and reading the
   "was not provided" chain level by level.
5. MULTI-FIELD-ONE-QUERY trick: the validator reports ALL violations in
   one response — include N guessed field names in a single query; the
   valid ones are the names ABSENT from the violation list. Parse with
   regex `Cannot query field '(...)'`, diff against your guesses.
6. Load-balancer roulette: identical queries alternate between
   "Unable to deserialize request" (envelope backend) and "Query does not
   pass validation" (GraphQL backend). Loop with retries until the
   validating backend answers; confirm consistency by repeating the same
   query 3x.
7. Real identifiers for required args (e.g. `activityToken`) can come from
   public pages (activity detail URLs carry `activityId=`); response field
   names may live in lazy-loaded chunks — pull the chunk list from
   `performance.getEntriesByType('resource')` on the live page and grep
   the unfetched chunks before blind-guessing fields.
8. EMPTY-TYPE / DECOY RECOGNITION (the stop rule): when every plausible
   field name fails validation — human guesses, an LLM-generated batch
   (feed schema facts + error corpus to the glm CLI, oracle-test its
   candidates in one multi-field query), PascalCase variants, AND
   object-shape probes ("must have a sub selection" leaks valid object
   fields + their types) — the type is an empty/redacted placeholder in
   the public schema. Real data then lives behind the REST-envelope
   variant (the `operation=` param) which needs full identity context
   (measured on Agoda: 45+ candidates incl. 20 LLM ones all dead;
   AvailabilityResponse = { result, errors } only; both types empty).
   Conclude "decoy surface", verify the availability of the envelope's
   required context, rate the disclosure (type names via errors =
   informational, below payout), and PIVOT — don't spend a session on a
   stripped schema.
9. OPERATION-PARAM SCHEMA VARIANTS: an `?operation=` value can select a
   DIFFERENT GraphQL schema on the SAME endpoint. Enumerate enum values
   from the bundle (`A.Ni.details` style → grep `\.Ni\.[a-z]+`), then
   probe each — the SAME query text validates on one operation and 404s
   the root field on another (Agoda: `{ details }` → root `details:
   DetailsResponse!` ONLY on `operation=details`; on `availability` the
   root is `availability: AvailabilityResponse!`). The availability
   schema's data types were redacted decoys while the details schema had
   REAL fields (`result.activity.activityRepresentativeInfo.
   {activityToken, activityId}` all validate) — always check sibling
   operations before declaring the whole surface stripped.
10. "not defined by type" oracle for INPUT types: feed a batch of guessed
    fields into a required input object — the validator flags each
    invalid one with `Field 'X' is not defined by type 'Foo'`; fields NOT
    flagged are real. This enumerated InternalContext down to EXACTLY
    {currency, memberId, experimentInfo{forcedExperiments,
    forceUserVariant}} — and adding anything else to the context later
    breaks backend deserialization. Input types are strict: extra or
    wrong-typed fields flip responses from validation errors to
    "Unable to deserialize request".
11. EXECUTION PROBE + IDENTITY WALL: after validation passes, a response
    of `{"data":null,"errors":[{"message":"Internal server error","path":[...]}]}`
    proves the query EXECUTED and reached a real backend (not just
    validation). Then sweep inputs: if EVERY value (activityId 1, 100,
    99999999, real ID) returns the same 500, the backend is missing an
    identity/context it can't be forged from outside — the ONE irreducible
    human step is an authenticated session (register + login, then the
    data path opens for IDOR/price-manipulation testing). State that step
    once, clearly ("where I need you: one logged-in account"), and stop —
    do not keep probing a wall that already answered.
12. CAPTURE-AND-REPLAY — the move that beats the identity wall (verified
    Aug 2026, Agoda). Even WITH a valid authenticated session (cookies +
    memberId in context + the harvested identity token), hand-built curl
    requests can still 500 on EVERY input while the logged-in browser
    loads the same data fine. The 500s are usually a WRONG REQUEST
    FORMAT, not auth. Two unlocks:
    a. REQUEST ENVELOPE: the app may POST a non-standard body, e.g.
       `{"queryString":"?operation=details&activityId=1563604","query":"query details(...)","variables":{...}}`
       (queryString carries the operation+params, NOT the URL alone).
       Plain `{"query":...}` bodies 500 on such gateways. Read the
       captured body before assuming the shape.
    b. STANDALONE REQUEST CAPTURE (the reliable way to learn the exact
       working request): do NOT fight browser_console hook-resets —
       write a standalone Playwright/camoufox-js script that launches a
       browser, seeds the session cookies via `context.addCookies([...])`,
       and logs EVERY request with headers+postData via
       `page.on('request')`. Run the real page flow, dump to JSON, then
       REPLAY verbatim (python urllib with captured headers+body, gzip
       handling) → real data. This converts "the app works, I can't"
       into "I have the exact request". Reusable harness:
       `scripts/request-capture.cjs` (camoufox-js API note: module exports
       `{Camoufox, launchOptions, NewBrowser, launchServer}`; `Camoufox()`
       is CALLABLE (not `new`), returns a Playwright-like browser).
    c. HEADER SET beyond the obvious: capture revealed ag-language-group-
       id, ag-origin, ag-platform-id:1 (NOT 0), ag-whitelabel-id,
       ag-whitelabel-token (a UUID that IS the `wlt` claim of the user
       JWT — decode the JWT payload to find it), ag-activities-client-
       context-id. Grep the captured headers, don't guess.
    d. PER-SERVICE IDENTITY TOKEN harvest: the token that authenticates
       the GraphQL service is NOT the session cookie. It's minted per
       client into the LOGGED-IN page's SSR bootstrap: regex the page
       HTML for `identityTokens":{"<client-id>":"([^"]+)"` (e.g.
       activities-web) — present only when session cookies are set.
    e. ISOLATION MATRIX (determine the true auth boundary): replay the
       captured request, then strip ONE thing at a time — identity
       token, cookies, xsrf — and read the delta. Measured: identity
       token REQUIRED (absent → VALIDATION_ERROR BAD_REQUEST), cookies
       NOT required (token alone authenticates). That tells you whether
       "authenticated" means session-bound or token-bound, and whether
       any token can be reused across sessions (the finding class).
    f. SIGNED-TOKEN TAMPER TEST (before writing any price-manipulation
       finding): prices are embedded client-side in the product token.
       Decode (base64url, mixed binary/JSON, price as ASCII), same-length
       tamper, replay WITH a control. Measured (Agoda): tampered → 6/6
       HTTP 400 deserialize; control → 200 + data. Tokens are
       server-signed — mark refuted, move to the mutation-based vectors.
       Full recipe: references/graphql-capture-replay.md §Signed tokens.
13. HANG TRIAGE — turning a hanging endpoint into a DoS candidate
    (verified Aug 2026, Agoda). After the identity wall: when
    auth-related ops (booking/create/reserve/checkout) HANG — read
    timeout, no response, no 401/403 — while known-good ops (details/
    search) answer in 0.2-0.7s, evaluate methodically:
    a. CONTROL BASELINE first: replay a known-good captured request. If
       IT also hangs, the session token expired — the hang is
       meaningless, re-harvest, don't report.
    b. UNAUTH REPRODUCIBILITY: replay the hanging op with NO cookies, NO
       identity token, NO xsrf. Still hangs past 60s = the backend
       accepts and holds connections from anyone (no auth check before
       the hold) — that's the candidate.
    c. BOUNDED vs UNBOUNDED: a 15s timeout tells you nothing — test 60s.
       Response at 30-60s = bounded (backend errors eventually) = weak.
       Zero response past 60s = unbounded hold per request.
    d. RATE LIMIT (the multiplier): 10 rapid VALID calls to a known-good
       op; all 200 in 0.2-0.4s with no 429 = no rate limiting on the
       gateway → parallel unauth connection-holds = resource exhaustion.
    e. Honest report framing: you may NOT load-test (program rules), so
       impact = "N parallel unauth connections held indefinitely, no rate
       limit" WITHOUT measured server impact — some triagers N/A
       slow-request findings. Document the observation, rate LOW, move
       on. (Agoda: getBooking/createBooking held 60s+ unauth, search
       baseline 0.7s, 10/10 rapid calls all 200 — documented as a
       low-sev candidate, not submitted.)
    Full worked transcript: `references/graphql-capture-replay.md`
14. PRELOADED-SSR / HOOK-BLIND pages + in-page probing (measured 2026-08,
    Quora): when a page SSR-preloads all data, scrolling/button clicks
    fire ZERO new requests — fetch/XHR hooks capture nothing (also: the
    app's fetch wrapper is bound at module load, so a late hook misses
    calls even when they fire). What still works:
    a. `performance.getEntriesByType('resource')` reveals the REAL query
       names/URLs the page called during load (e.g.
       `.../gql_para_POST?q=QuestionPagedListPaginationQuery`) — that
       list IS your endpoint map even with no body capture.
    b. Probe formats from INSIDE the page with same-origin SYNCHRONOUS
       XHR (carries the cf_clearance session, returns
       `status|responseText` directly). Async fetch in evaluate breaks
       with "Promise rejection value is a non-unwrappable cross-compartment
       wrapper" — sync XHR only.
    c. Evaluate output is truncated ~400 chars — run regex/extraction
       INSIDE the page and return only matches; keep expressions small
       (multi-line probes 500 the evaluate endpoint).
    d. Silent identical 400s across ALL body/header variants + the app
       bundle loaded dynamically (absent from document.scripts AND
       resource entries) = the transport format is not reachable
       statically; if the session is anonymous (m-uid=None, no state
       globals), the unauth surface is public data only → the money
       classes need auth; ask for the ONE free registration and stop
       grinding the format. Full matrix: `references/quora-dossier.md`
Worked example + transcript: `references/graphql-schema-oracle.md`

### 10.14 Authenticated web-app surface assessment (org-scoped IDOR testing)
For a logged-in SaaS with org-scoped resources (measured: Anthropic /
claude.ai — open-scope program, $190 Low / $1,104 Med / $3,563 High /
$8,000 Crit, 8h first response, 390 resolved):
1. Map the API surface by CAPTURE (§10.12 pipeline): a fresh logged-in
   session fires 20-40 `/api/*` calls on load; that endpoint list IS the
   surface (`/api/account_profile`, `/api/organizations/{uuid}/*`,
   `/api/billing/{uuid}/*`, `/api/team-trial/*`...). Session cookies +
   cf_clearance work for curl IF the clearance matches the fingerprint.
2. AUTHZ BOUNDARY TEST (the core move): replay each org-scoped endpoint
   with (a) YOUR org UUID → expect 200 + real data; (b) a RANDOM v4 UUID
   (`str(uuid.uuid4())`) → 404 not_found with no existence leak = authz
   enforced; 200-with-data = IDOR. Consistent 404-for-foreign across ALL
   endpoints = the org boundary holds — stop proving it, move on.
3. Numeric IDs in UUID paths → 400 validation ("Input should be a valid
   UUID") = no sequential-enumeration angle (org IDs are sequential
   numbers but the API only accepts UUIDs).
4. Conversation/project/share UUIDs are all v4 — unguessable. Without a
   SECOND account to cross-test, a fresh single-account web surface is
   thin; state that honestly instead of grinding it.
5. Claude Code CLI = PAID WALL (measured 2026-08): `claude auth login`
   → OAuth authorize page renders "Claude Max or Pro is required to
   connect to Claude Code — Sign up for a Max or Pro subscription... or
   use your API key." Free accounts CANNOT authorize. For a no-money
   user, don't install/setup the CLI at all — check the plan tier before
   building the harness. (The authorize flow IS drivable in camoufox
   with the session cookies: claude.com authorize → bounce to
   claude.ai/login?selectAccount → inject .claude.ai cookies → reload →
   authorize page — but the paid wall stops it regardless.)
6. cf_clearance COOKIE TRANSFER pitfall: a cf_clearance pasted from the
   user's real browser is FINGERPRINT-BOUND. A different browser
   (camoufox) gets re-challenged (jsd/oneshot challenge requests appear
   in the capture). The page still loads AFTER the challenge resolves —
   wait 15-25s, verify via `document.title` (e.g. "New chat - Claude"),
   don't kill the run or assume the session is dead.
Full dossier: `references/anthropic-claude-ai.md`

### 10.15 Pre-submission duplicate & program-health check (measured 2026-08, Matomo)
Before submitting an OSS/self-hosted finding, run this cheap external
duplicate screen — it materially moves the payout odds and costs minutes:
1. GITHUB ADVISORIES API (the strongest signal for OSS): 
   `curl "https://api.github.com/advisories?affects=<owner>/<repo>&per_page=100"`
   — zero results = no published GHSA/CVE for that repo's issues. A prior
   report that got FIXED almost always leaves an advisory trace; absence
   leans "never reported/fixed". The global `?q=<name>` search is NOISE
   (matches any advisory mentioning the string — routers, unrelated CVEs) —
   use the `affects=` repo-scoped query, not q=.
2. PROGRAM HACKTIVITY as a HEALTH read: Matomo's page showed bounties
   $222/$333/$555/$777/$1,333/$1,777 all resolved within the last 10 days
   → live triage + real payouts. A page with "last report resolved" weeks
   ago = stale (drop). The compact hacktivity view HIDES report titles to
   logged-out viewers (all `aria-label="upvote the report titled: \"\""`
   empty) — you CANNOT scan titles for prior reports from outside; say so
   honestly and price that residual risk into the odds.
3. PROGRAM/FAQ SECURITY PAGES: grep for the sink class ("annotation",
   "stored xss", "escaping") — e.g. Matomo's FAQ "annotation" hits were
   MCP/AI prompt-injection guidance, not a prior vuln. Absence of any
   advisory/CVE for the class = favorable.
4. GIT HISTORY of the sink: `git log -L <lines>` on the sink file, or
   `-- <path>` — "|raw unchanged across N commits" = old-and-unpatched =
   reportable but flags duplicate risk; a RECENT fix nearby = your variant
   may be the incomplete-patch angle (stronger finding).
5. ODDS FRAMING for the user (they ask "whats the probab of our payout" —
   give a calibrated number + the two levers): start ~50% for an old
   unpatched sink dominated by private-dup risk; clean advisory record +
   demonstrably paying program (recent bounty velocity) + airtight chain +
   no CSP objection → ~60-65%. Levers that shift it: live PoC on the
   vendor's free trial (one human registration) and the H1 auto-dup check
   at submit (instant, no penalty). Never quote odds without naming the
   dominant uncertainty.

### 10.16 LLM analysis-channel degradation mid-hunt (measured 2026-08)
The GLM-5.2 co-pilot channels die at the worst times; the audit must not
stop: Puter free tier exhausts mid-session ("GLM via Puter failed: No
usage left for request." — daily quota, resumes next day), and the NIM
gateway can 503/axum-error ("Missing request extension: Authorization" —
platform-side outage affecting ALL keys, not the key). Fallback ladder:
audit SOLO immediately (the code-level work — sink scan, authz trace,
chain verification — is fully doable without the LLM), re-probe the
channel at the next natural boundary (a file read, a repo operation),
and if the user offers a new-account login to refresh quota, keep the
deep-GLM question set PRE-BUILT so the moment auth refreshes the consult
fires in one call. Never block a hunt on an analysis channel; the channel
the channel is an accelerator, not a gate.

### 10.17 Local lab / CTF web-app exploitation — source-first methodology (measured 2026-08, ACME BANK)
For own-lab / sandbox targets (a "bank" on localhost with a harness running it),
the source and harness are ON DISK — read them before black-boxing:
1. SOURCE-FIRST RECON: find the server file (`bank_server.py` etc.), the live
   process (`netstat -ano | grep <port>` → PID → `Get-CimInstance Win32_Process`
   for command line), and identify which DB the running PID actually uses
   (live `bank.db` vs decoy copies — match observed balances to the file).
   Read the source: default creds, rate-limit mechanics, session/CSRF handling,
   and DB schema fall out in minutes instead of hours of probing.
2. READ THE HARNESS/TEST SUITE (`attack_suite.py`, `harden_state.json`): it
   lists exactly what was already tested (SQLi, rate limit, CSRF, traversal…).
   Anything it checks that PASSES = hardened, don't re-test. The gold is the
   classes the suite does NOT cover: concurrency, multi-row accounting,
   non-finite floats, direct-DB access.
3. AUTH LADDER: (a) default/seed creds from source; (b) rate-limiter bypass —
   per-username counters only, wait out the lockout window or PLANT YOUR OWN
   USER via the DB (bypasses app-layer auth entirely); (c) session quirks —
   old sessions stay valid after re-login, `Cookie` header accepted, token not
   boundary-validated (trailing `; foo=bar` still authenticates).
   (d) LOCKOUT-TRAP (measured: 429 on the CORRECT creds right after running
   the suite): the scoring harness's OWN checks (V3-style loops fire 10+ bad
   logins per username) and sibling agents sharing the same username keep the
   60s window rolling — treat 429 as "window active", not "creds wrong"; poll
   login every ~5-8s, move on. Never brute-force a working limiter.
   (e) VERIFY SESSION CLAIMS YOURSELF: `Cookie: <tok>; foo=bar` authenticated
   in one run and 401'd in another (boundary-splitting inconsistent) —
   sibling intel about session semantics is a hypothesis; test it once.
4. BUSINESS-LOGIC FLAW CHECKLIST (what hardening swarms consistently miss):
   - TOCTOU race on check-then-act: SELECT balance → UPDATE balance as separate
     statements = double-spend. Fire N barrier-synced concurrent transfers of
     the full balance; count 200s > 1 = confirmed (measured: 25 threads → 2
     wins → balance −$1B). SQLite serializes writes but NOT the check-before-
     update on separate connections. MECHANIC (measured): each winning UPDATE
     subtracts from the LIVE balance, not the stale read → N winners leaves
     balance = initial − N×amount (receipts show 0.0 → −1.28M → −2.57M). Yield
     is GIL-tight: expect ~1–3 winners per 100-thread burst (1/40 naive, 3/100
     barrier-synced, 2.07s), not 20. Widening option if you need more: trickle
     request BODIES to park every server thread in body-read, then release the
     tail simultaneously so all SELECTs run before the first COMMIT.
   - Multi-row UPDATE mismatch: check reads `WHERE user_id=1` first row only,
     UPDATE `WHERE user_id=1` hits ALL rows → single transfer debits 3× the
     checked balance.
   - float() non-finite bypass: `float("nan")` passes `amount <= 0` (False)
     AND `balance < amount` (False — NaN comparisons are always False) →
     `balance-nan` = NULL → account destroyed (DoS). `"Infinity"` → blocked by
     the `< amount` check. Python's `json.loads` accepts bare `NaN` tokens.
     PAYMENT-ABUSE NUANCE (measured): the transfer RESPONDS 200
     `{"ok":true,"transferred":NaN,...}` — a payment is ACCEPTED with a
     non-numeric amount, so it is a fake-payment-record vector too, and it
     works even on negative balances (NaN < anything is False).
   - Per-endpoint CSRF/rate-limit verification: CSRF may be enforced on the
     PRIMARY money endpoint (transfer → 403 without token) but MISSING on
     sibling endpoints (PUT /upload → 200 with session only, no csrf) — and
     the GET sibling may need NO session at all. Check each state-changing
     endpoint individually; don't extrapolate from one. Same for rate limits:
     login had a per-username limiter while /transfer had ZERO (100 req/2s, no
     429s) — the money endpoint is the unprotected one, and per-username-only
     + in-memory means unlimited password spray across usernames.
   - Upload ext blocklist bypass: trailing-dot `shell.py.` (ext becomes
     ".py."), double-extension `shell.php.png`, unknown ext `shell.python` all
     pass a splitext-based blocklist; traversal (`..`/`%2e`) is usually still
     blocked. Echo-only storage → low impact, but the filter is bypassable.
   - Negative/zero amounts, missing CSRF, unauth transfer — usually already
     covered by the suite; verify once, move on.
5. DIRECT DB = TOTAL AUTH BYPASS: plant backdoor users (`INSERT ... sha256`),
   override the admin password hash, inflate balances. SQLite tolerates short
   concurrent writes from the live server (new connection per request, no
   long-held locks). Keep one seed login working so partners aren't locked out.
   BACK UP the DB file (plain copy into the sandbox) BEFORE the first tamper —
   it gives a pre-state diff for the report and a restore point if a sibling's
   NaN/race wrecks the balances mid-run. Verify partner-planted hashes by
   sha256-testing candidate passwords against the stored hex; recognize the
   classic seed hashes instantly (MD5(admin123)=0192023a7bbd73250516f069df18b500,
   SHA256(admin123)=240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9).
6. VERIFICATION-FIRST REPORT: before writing the report, re-login with the
   planted creds and re-check /admin + /balance + raw DB state — the report
   must reflect the FINAL state (partners may have nulled balances mid-run).
   Keep a loot manifest (what/amount/how) alongside the report.
7. PARTNER COORDINATION (multi-agent): the shared intel file is
   LAST-WRITER-WINS — a concurrent sibling write gets clobbered. Read the file
   immediately before writing and re-merge after; recover partner findings
   from their on-disk scripts/artifacts when the channel is missing them.
   LIVE-FIRE OPS (measured round 2): (a) the channel may be DELETED outright
   by partners — rebuild it from their loot manifests and keep YOUR loot
   manifest in a separate file so it survives; (b) a sibling's brute-force
   can 429-lock the SHARED admin creds — the planted backdoor user is exactly
   the fallback that still authenticates (money endpoints accept any valid
   session); (c) a sibling may ZERO the DB file mid-session — the server keeps
   running but every request 400/500s ("no such table"); recover by re-seeding
   schema + seed rows (mirror the server's init_db: CREATE TABLEs + INSERT OR
   IGNORE admin/seed account) and restore balances; verify F1-F3-style
   functional checks before the final report so the lab stays usable.
   Worked example + exact findings: `references/local-lab-bank-ctf.md`

### 10.18 AOSP decoder findings — upstream fix-status verification (disclosure readiness)
Before reporting any AOSP `external/*` library finding, verify fix status at THREE
layers — AOSP main, AOSP release branches, canonical upstream — and produce a
disclosure table (finding | audited AOSP copy version/date | AOSP main fixed? |
branches affected | upstream fixed?). Worked example (giflib/libhevc/libavc,
Aug 2026) + full recipe + measured branch tips:
`references/aosp-upstream-fix-status.md`. Reusable VM runner (paramiko, executes
a local bash script via stdin on the Kali VM): `scripts/run_script_on_vm.py`.
1. Identify the EXACT audited AOSP copy: `git -C <clone> log -1 --format='%H %cd %s'`
   + `git describe --tags`. AOSP rarely upgrades codecs (libhevc/libavc both still
   at the v1.6.0 upgrade, Aug/Nov 2024) — the fuzzed copy is usually STILL AOSP
   `main` HEAD, which makes the finding trivially current.
2. Check AOSP `main` AND the release branches: `refs/heads/android13-release`,
   `android14-release`, `android15-release` (BRANCH names, not tags). Grep the bug
   lines in each branch tip's file version. Release-branch tips are FROZEN
   snapshots (last commit can be years old) — absence of a fix there is
   authoritative; do not trust "latest tag" for the shipped state.
3. Check the CANONICAL upstream — often NOT the GitHub repo in old notes:
   - libhevc / libavc → `github.com/ittiam-systems/*` (active; AOSP only mirrors
     their code, so a fix must land there first)
   - giflib → SourceForge `git.code.sf.net/p/giflib/code` — `TeamHypersomnia/giflib`
     and `gitlab.com/limx/giflib` are DEAD (404); AOSP giflib is still 5.2 while
     upstream is 6.x
4. Per-file last-touch: `git log -1 --format='%H %cd %s' <branch> -- <path>` — a
   file untouched since 2019 (common for codecs) = the fix was never ported.
5. Disclosure routing: AOSP findings → Android Security Rewards
   (`g.co/androidsecurityreport`) + AOSP Issue Tracker; codec fixes must land at
   Ittiam first; if upstream already fixed (e.g. giflib 6.1.3 `ImageCount <= 0`
   guard), the report becomes a backport/sync ask, not a new-CVE hunt.
PITFALLS (all measured Aug 2026):
- googlesource `?format=TEXT` (base64 file fetch) RATE-LIMITS bursts: rapid
  sequential fetches start returning **404 (not 429)** — looks like a bad URL but
  is throttling. A single spaced request (~20s) returns 200. Prefer one full
  `git clone --filter=blob:none <repo>` (small, e.g. 24MB for libhevc) and
  `git show <branch>:<path>` for everything.
- ALWAYS `git -C <repo>` for greps across multiple clones — a bare `cd` into one
  clone makes subsequent `git show`/`git log` run against the WRONG repo and
  silently produce bogus zero counts (cost a re-verify round).
- Distinguish "fixed upstream" from "fixed in AOSP": Ittiam partially fixed one
  libhevc shift-UB (added `(UWORD32)` cast, commit `5ad6b713`) but AOSP main is
  untouched — "upstream fixed" ≠ "Android fixed"; the table needs both columns.

### 11. User directive: keep going (embedded preference)
When the user orders "keep going / don't stop / do it manually / till
u got worthy" — continue grinding autonomously: pick the next untouched
surface, work it, append results to the findings ledger. Do NOT pause to
deliver status updates or summaries mid-grind — the user reads those as
stopping. Deliver state only when a surface is exhausted, a finding lands
(confirmed OR refuted-by-PoC), or the turn budget forces it. The ledger
(findings.md) + audit map (covered/refuted lists) IS the output channel;
keep it current so the nightly cron never re-walks a surface.
- DECISION PARALYSIS (measured: "i dont kknow" after a wash day): when the
  user is overwhelmed, do NOT re-present the menu of options — make the
  call yourself, keep the autonomous paths running, park the manual paths
  with one-line labels ("say Valmo for the 3-minute OTP walkthrough") and
  STOP pushing. A short, warm close that states what's running and what's
  parked beats another decision request every time.
- USE THE TOOLS YOU BUILD (measured: user asked "is puter glm5.22 help
  u" after the glm CLI sat idle for the whole grind): any analysis tool
  built for the user (glm CLI, nim_rotate, cdp.js) must be DEPLOYED in
  the active workflow, not just exist and pass tests. The GLM+oracle
  loop is the pattern: dump the verified facts + error corpus to GLM,
  get candidate field names, oracle-test them in one multi-field query —
  the tool earns its place even when its candidates are wrong (that's
  what the oracle is for). Don't let the user have to nudge.
- FLIP-FLOP DIRECTIVES (measured: "no switch" → cron removed → hours later
  "switch to vercel" → cron recreated): this user reverses course fast and
  without explanation. On an ambiguous directive, PAUSE infrastructure
  (cron pause, park the branch) instead of DELETING it — recreation costs
  turns and can lose state. Only delete on a clear, repeated directive.
- FILING vs HUNTING (measured: "no move on to other" after the Agoda low
  candidate): this user rejects filing weak/low candidates. A conditional,
  low-sev, or unproven-impact finding gets documented in the ledger, NOT
  submitted. Keep hunting fresh targets instead; only a confirmed
  High-class chain earns the "want the report drafted?" question.
- DECLINING OFFERED STEPS (measured: "no u alone go in hunt" after offering
  a Puter re-login to refresh the exhausted GLM quota): when the user
  offers a manual step then withdraws it, proceed SOLO immediately — never
  block the hunt waiting for a login they said they'd do. Re-check the
  auth state once at the next natural boundary, then continue.
- REPLY LANGUAGE (corrected 2026-08: "why the fuckk u talk in hindi"):
  the user writes Hinglish but wants AGENT replies in plain English.
  Never mirror the Hinglish in your own replies — clean English, casual
  and short. (This is global, not hunt-only; the hunt workflow is where
  it surfaces most.)

## Pitfalls
- Private H1 programs: directory handles with a `_private` suffix (e.g.
  `/box_private`) show as "Page not found | HackerOne" for non-members —
  that 404 IS the private signal. Filter them out of the shortlist BEFORE
  spending recon turns; you can't hunt them without an invite.
- CDP + React SPA automation: JS-synthesized `el.click()` fails on hover
  menus and some buttons — use trusted `Input.dispatchMouseEvent`; 
  `Input.insertText` can bypass React onChange (submit silently no-ops —
  verify the input value AND hook XHR to confirm the request actually
  fires); ALWAYS `scrollIntoView({block:'center'})` before computing click
  coords (off-viewport clicks miss silently); per-char
  `Input.dispatchKeyEvent` (typekey) is the React-safe typing path. Add a
  hard watchdog (`setTimeout(...).unref()`) to every CDP script — hangs
  cost the session. (scripts/cdp.js modes: goto/eval/fetch/clickat/type/
  typekey/rules/wake/close/tabs.)
- HackerOne `/program/scope` direct URL 404s — scope is an SPA tab. Click
  the `treeitem "Scope"` via JS: `[...document.querySelectorAll('[role="treeitem"]')].find(e => e.textContent.trim()==='Scope').click()` (browser_console evaluate).
- Directory default sort is launch date — always re-sort by resolved count.
- Known-duplicates list is the difference between a payout and a wasted
  report. Read it before every test session.
- Test credentials are shared/finite: don't lock accounts, cancel
  time-limited test orders (e.g. grocery 30-min rule), no real transactions.
- Do NOT submit reports for out-of-scope assets — repeat violations = ban.
- Never run scanners/fuzzers against program assets (explicit rule in most
  programs; also generates spam that destroys reputation).
- Capturing the app's real API requests via `window.fetch` hook: full page
  navigation RESETS the JS context and silently kills the hook (measured:
  hook installed, then browser_navigate → hook-lost). Install hooks only
  when the triggering action happens in the SAME context (SPA navigation,
  clicks), or reinstall after every navigate before the target request
  fires. Also: the app's own request stuck in "Loading" inside an
  anti-detect browser is itself diagnostic — the API is failing for that
  fingerprint, not necessarily down for everyone.
- Driving Camoufox directly via REST when browser_console loses its
  session: POST /tabs needs `userId` AND `sessionKey`; evaluate needs a
  JSON body `{"userId":..., "expression":...}` (raw JS body → 400);
  nested quotes in shell curl break — build the JSON with Python
  (json.dumps) and POST that.
- Camoufox infra stability (measured 2026-08): standalone camoufox-js
  launches crash under memory/disk pressure (Juggler NS_ERROR_FAILURE,
  "Target page, context or browser has been closed") — prefer the
  `npx camofox-browser` SERVER instance (port 9377), which is far more
  stable. Server gotchas: tabs are REAPED after ~300s idle (session
  closes — always create a fresh tab with a NEW userId/sessionKey rather
  than reusing stale tab IDs); tab creation can 500 "tab create timed out
  after 30000ms" when the browser is mid-reap — restart the server
  (`process kill` + relaunch, wait for
  `{"browserConnected":true}` on /health) and retry; C: drive at 100%
  causes both launch paths to fail — free space (Temp, npm/pip caches,
  ms-playwright) BEFORE retrying browser work.
- A "lead" (e.g. an unauthenticated endpoint) is NOT a finding until impact
  is demonstrated — programs close speculative reports as N/A. Document the
  ONE missing identifier (real AWB, second test account, placed test order)
  and the legitimate way to obtain it; stop there for the session.
- When the user pastes a browser COOKIE DUMP to unlock a session: it will
  contain unrelated personal sessions (Google SID/SSID, Bing, Snapchat —
  high-value account cookies). Use ONLY the target domain's cookies
  (build the request cookie-string from those), never store/echo the
  others, and tell the user to clear/rotate the personal ones. Test the
  target cookies are actually valid (a logged-in page echo, e.g. the
  memberId appearing in /trips) before building the harness on them.

## Support files
- `references/hackerone-mechanics.md` — verified HackerOne navigation
  (directory URL params, SPA tab clicking, program page section map)
- `references/extension-automation.md` — MV3 header-injection extension
  (declarativeNetRequest), config.json username seeding, Edge launch with
  --load-extension + CDP verification, SW-dormancy/builtin-pollution traps
- `references/meesho-program.md` — Meesho BBP dossier: assets + report
  counts, test creds, known dups, out-of-scope, recon findings, attack
  priorities, tooling paths
- `references/multi-program-pipeline.md` — cross-program sweep: directory
  scraping without login (API auth-gated → scrape rendered table), ranked
  shortlist with bounty math, A&F probe dossier (Shape Security wall,
  dead SPA-fallback routes), 1win dossier (geo-block, affiliate panel API
  mapping, auth-gate verification), Agoda dossier (single-URL scope,
  GraphQL gateway), honest probability ranking of money
  paths
- `references/graphql-schema-oracle.md` — Agoda worked example: AG- header
  discovery from error deltas, operation-param parser switch, schema
  enumeration via validation errors, multi-field leak trick, load-balancer
  roulette, in-scope-API-behind-scoped-URL rule
- `references/graphql-schema-oracle-v2-details-schema.md` — SAME-DAY
  follow-up: operation-enum schema variants (each `operation=` value serves
  its own schema; the details backend has REAL fields where availability
  was redacted), "not defined by type" input oracle, exact InternalContext
  shape, execution probe → identity wall (universal 500s = needs an
  authenticated session — the ONE human step)
- `references/graphql-capture-replay.md` — capture-and-replay breakthrough:
  request envelope {queryString, query, variables}, full AG header set
  (incl. ag-whitelabel-token = JWT `wlt` claim, ag-platform-id:1),
  per-service identity-token harvest from SSR bootstrap HTML, isolation
  matrix (identity token required, cookies NOT), camoufox-js capture
  pipeline
- `references/waf-bot-walls.md` — measured Akamai auth-API block (XHR hook
  proof), what does NOT bypass it, Valmo unauth tracking API notes, pivot
  playbook
- `references/bot-bypass-playbook.md` — condensed Cloudflare/Akamai/AWS
  bypass techniques from a 350-agent research swarm (2026-08-08): origin-IP
  discovery checklist (DNS history, grey-cloud subdomains, CT logs, favicon
  hash), direct-origin access + verification, WAF evasion classes, Akamai
  G2G/True-Client-IP + CVE-2020-9295, CloudFront direct-origin/OAC, AWS WAF
  inspection limits, TLS/JA4 fingerprint evasion, honest wall taxonomy
  (beatable vs human-only), reporting reality for CDN-bypass findings.
  Full report: C:\Users\HP\ai-workforce\swarm\report_botbypass.md
- `references/wolt-dossier.md` — Wolt (fresh program, launched Jul 2026):
  full unauth API-surface map (consumer-api / restaurant-api /
  gift-card-shop-http-api / DoorDash risk gateway), gift-card `validate`
  endpoint (405→POST→"Not authenticated" = auth-gated money surface),
  config leaks (per-country gift-card venue ObjectIds, card-only payment
  matrix), the one free unlock step (register account — no payment)
- `references/anthropic-claude-ai.md` — Anthropic open-scope program +
  claude.ai dossier: 23-endpoint API map, org-scoped authz boundary test
  (random-v4-UUID vs own → 404/200 = boundary holds), numeric-ID
  validation, Claude Code paid-plan wall (free accounts can't
  authorize), cf_clearance fingerprint-binding pitfall
- `references/vercel-oss-audit.md` — OSS-scope autonomous audit campaign:
  method (shallow clone → high-risk grep → LLM audit with code inline —
  glm CLI reads ARGV not stdin — → verify claims), target selection
  (0-report fresh repos), verified-clean pass results for ms/chat/eve,
  second-pass reverse-audit of recent security commits (teams/slack HTML,
  X CRC oracle, read-scope guard) with already-covered surface list
- `references/matomo-oss-audit.md` — Matomo OSS dossier (same playbook,
  second program): 4 same-week security commits reverse-audited (2FA,
  SSRF-safe fetch, Overlay JS-encode — complete; token_auth URL exclusion
  — INCOMPLETE: referrer urlref not cleaned = token-exposure candidate,
  conditional/low), defused chains (language-XSS via strict validation),
  verified-clean do-not-re-walk list, method notes for PHP codebases
- `references/mozilla-fxa-audit.md` — Mozilla core-services dossier
  (third program): /mozilla vs /mozilla_core_services program split,
  fxa monorepo first-pass results (consent purge complete, fetch
  migration clean, passkeys solid), the reusable WebAuthn/passkey auth
  audit checklist (challenge storage/consumption, credential→uid
  binding, signCount rollback, UV, post-verify session), cron coverage
- `references/quora-dossier.md` — Quora GraphQL surface (gql_para_POST
  endpoint + real query names from resource entries), the full 400
  dead-end format matrix, preloaded-SSR hook-blindness + in-page sync-XHR
  probing technique, anonymous-session verdict (public data only) and the
  one free-registration unlock
- `references/zulip-oss-audit.md` — Zulip dossier: the
  optimization-commit regression (is_user_active filter removed →
  limited guest → deactivated user access; fixed 10 days later, NOT
  reportable), sibling access-helper audit method, author-pattern watch
  list, webhook-auth validation
- `references/poc-verification.md` — PoC-first discipline: the
  symlink-escape worked example (hypothesis → evidence chain → assert test
  → REFUTED verdict) and the general recipe for proving/refuting
  candidate findings
- `templates/bounty-report-template.md` — report skeleton used for
  submissions
- `scripts/cdp.js` — CDP control for the hunt browser: goto/fetch/rules/
  tabs/close/wake (works with any Edge/Chrome launched with
  --remote-debugging-port)
- `scripts/request-capture.cjs` — standalone camoufox-js/Playwright
  request-capture harness: seed session cookies, log every API request
  (headers+body) on a real page flow, dump JSON for verbatim replay
  (the capture-and-replay technique, §10.12)
- `references/local-lab-bank-ctf.md` — ACME BANK own-lab worked example
  (§10.17): source-first recon, harness-read, live-vs-decoy DB, default-creds
  login, TOCTOU race + multi-row over-drain + NaN-null evidence, direct-DB
  backdoors, partner intel-channel merge
- `references/aosp-upstream-fix-status.md` — AOSP disclosure-readiness recipe
  (§10.18): googlesource fetch patterns + rate-limit trap, release-branch
  naming, canonical-upstream locations (Ittiam, giflib SourceForge), measured
  branch tips for libhevc/libavc/giflib, disclosure-table template
- `scripts/run_script_on_vm.py` — paramiko runner that executes a local bash
  script via stdin (`bash -s`) on the Kali VM; used for all remote AOSP/upstream
  verification
