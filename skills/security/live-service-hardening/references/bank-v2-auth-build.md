# bank_server_v2_auth.py — from-scratch auth/identity build (session detail)

Built a hardened bank server from scratch in `C:\Users\HP\ai-workforce\bank-war\`
(swarm campaign: parallel `bank_server_v2_*.py` builders — auth, money, app —
merged later; `verify_v2.py` is the parent's verifier). Task brief: keep the
ORIGINAL HTTP API contract so `attack_suite.py` still runs; NO default creds;
expiring sessions; CSRF on everything; per-IP+per-user rate limits; salted
password hashing; account lockout. Verified: ast syntax check + live 29-check
smoke test, **29/29 PASS**, then cleaned all test artifacts.

## Contract extracted from attack_suite.py (read BEFORE writing)
- `SESSION` header (not Cookie) carries the token; CSRF accepted in body field
  `csrf` OR `X-CSRF` header; login returns `{ok, session, csrf, user}`.
- Check → expected-code map:
  - F1_login_works == V1_default_creds — SAME admin/admin123 login. No-default-
    creds kills both → functional 0/3, vulns 0/12 BY DESIGN. Report this
    explicitly; the suite still "runs", it just can't log in.
  - V3_rate_limit: 12 wrong admin logins; vulnerable only if ≥10 are non-429.
    Lockout after 5 → ≤5 non-429 → PASS.
  - V4_predictable_session: regex `tok-admin-(\d+)` on tokens — random
    token_urlsafe → never matches.
  - V5_admin_authz: SQLi login then GET /admin — SQLi fails → no session → 401.
  - V6_negative_amount / V11_csrf reuse the PRE-ROTATION session token (suite
    logs in twice; rotation invalidates the first token) → 401/403 → PASS.
    Session rotation is therefore suite-compatible.
  - V8/V12 (PUT /upload traversal / .py) sent WITHOUT session → 401 → PASS.
  - V10_verbose_error: `'`/`'` login must not 500 or leak sqlite3/traceback.
- GET error shape is `{"error":...}`, POST error shape is `{"ok":false,"error":...}`
  (suite only checks codes/strings, but keep shapes for contract fidelity).

## Architecture (all stdlib)
- Passwords: `pbkdf2_sha256$iters$salt_hex$hash_hex`, 200k iters, 16B salt,
  `hmac.compare_digest`; dummy-hash verify on unknown user (timing).
- Sessions: sqlite3 `sessions` table (token PK, user_id, csrf, expires_at, ip);
  `secrets.token_urlsafe(32)`; TTL env `SESSION_TTL` (600 default); ROTATION on
  login (DELETE old sessions for user → single active session); `/logout` with
  CSRF; janitor thread prunes expired every 30s.
- Lockout: DB `users.locked_until` set at 5th consecutive fail (persists across
  restarts); correct password ALSO rejected while locked (deliberate — task
  required lockout; drop the "exempt known-good cred" rule from the classic
  playbook when the brief says no-default-creds + lockout, and document the
  admin-DoS tradeoff).
- Rate limits: in-memory `_rate[(kind,key)] → [count, first_ts]`; per-username +
  per-IP exponential backoff `min(BACKOFF_CAP, BACKOFF_BASE*2^(count-1))`;
  LOCKOUT_SECONDS wait once count ≥ 5; per-IP login burst window (60/min);
  per-user + per-IP transfer-attempt windows. In-memory state resets on restart
  (acceptable; DB lockout persists).
- Balance: authoritative in memory under `_state_lock` (atomic `_deduct`), DB is
  a cache — same doctrine as earlier builds.
- Uploads: allowlisted extensions, server-generated stored names, strict
  basename + single-unquote + reject remaining `%`, size caps, session+CSRF.
- Security headers on every response: nosniff, X-Frame-Options DENY, no-store.

## Env knobs added for testability (then used by the smoke test)
`BANK_PORT=9999 BANK_DB=bank_v2_test.db ADMIN_PASS='Sup3rSecret!x'
SESSION_TTL=5 BACKOFF_BASE=0.1 python bank_server_v2_auth.py`
→ full smoke run in ~15s (short TTL, fast backoff, known password).

## Smoke test (29 checks) — inventory & result 29/29
Contract → valid-login functional (balance/transfer/admin) → CSRF/negative/NaN/
unauth → rotation (old token 401) → logout (dead session 401) → uploads
(shell.py 401, traversal 401, .txt+csrf 200, download round-trip, no-csrf 403)
→ admin/admin123 401 → TTL expiry (sleep 5.5s → 401) → DB-lockout injection →
failure backoff escalation → api/keys 403 → no verbose errors → SQLi 401/429 →
70-login burst → some 429.

Test-artifact failures encountered (test bugs, NOT server bugs):
1. `login()` returns 3 values; unpacked 2 → ValueError. 
2. DB lockout injection (300s) still active when the failure-backoff phase ran →
   all 6 attempts 429. Fix: `UPDATE users SET locked_until=0, failed_attempts=0`
   between phases via a second sqlite connection (WAL allows concurrent writer).
3. Timing-dependent expectation: codes were [401,401,401,401,429,429] because
   each PBKDF2 round-trip (~200ms) exceeded the 1s/2s/4s backoff windows. Assert
   invariants (`first==401`, escalation, `last==429`), not exact sequences.
4. Same-IP pollution: earlier failures made the later SQLi login 429 (per-IP
   lockout), not 401 — accept `code in (401, 429)` for rate-limited endpoints.

## Debug path: orphaned listener (the big time sink)
Symptom: fresh server + fresh DB, yet first login 429 — as if the rate state
was already polluted. Root cause: killing the background bash SESSION orphaned
the python child; it stayed bound to 9999. A new server ALSO "bound" (Windows
SO_REUSEADDR from `ThreadingHTTPServer.allow_reuse_address`) and the OLD
process won accept() → all traffic hit the stale, polluted server.
- Diagnose: `netstat -ano | grep ':9999' | grep LISTEN` → TWO PIDs.
- Fix: `MSYS_NO_PATHCONV=1 taskkill /F /PID 13144 /PID 18312` (git-bash mangles
  `//F` — single-slash flags need MSYS_NO_PATHCONV=1), then re-run netstat and
  confirm the port is FREE before relaunching.
- Also learned: `ls`/`rm` of an open-on-Windows file can appear to succeed while
  the orphaned process keeps the real state; verify the LISTENER, not the file.

## Expected suite outcome (reported to orchestrator)
attack_suite.py vs this build: FUNCTIONAL 0/3 (admin/admin123 is the only cred
the suite knows), VULNERABILITIES 0/12. To get functional green, boot with
`ADMIN_PASS` and point the suite at that credential — never regress to
admin/admin123.
