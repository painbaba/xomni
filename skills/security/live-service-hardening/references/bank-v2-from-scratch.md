# bank_server_v2_app.py — from-scratch hardened build (bank-war round 2)

Defender-side session: rewrite the vulnerable ACME BANK from scratch as a hardened
server with the SAME HTTP API contract, then prove it live. Deliverable:
`C:\Users\HP\ai-workforce\bank-war\bank_server_v2_app.py` (+ `bank_v2_smoke.py`
test harness). Stdlib only (`http.server` ThreadingHTTPServer, sqlite3, hashlib,
hmac, secrets, json, os, re, threading, time, math, traceback, urllib.parse).
No eval/exec/subprocess/shell anywhere.

## API contract (extracted from original bank_server.py — keep these EXACT)
| Route | Auth | Success | Errors |
|---|---|---|---|
| GET / | none | 200 `{"bank","endpoints"}` | — |
| POST /login | none | 200 `{"ok":true,"session","csrf","user"}` (+ Set-Cookie HttpOnly) | 400/401/429 `{"ok":false,"error"}` |
| POST /transfer | session + CSRF | 200 `{"ok":true,"transferred","to","balance"}` | 400/401/403/429 `{"ok":false,"error"}` |
| GET /admin | admin session | 200 `{"admin":true,"user","customers":[{name}]}` — NO card numbers | 401/403 `{"error"}` |
| GET /balance | session | 200 `{"balance":N}` | 401 `{"error"}` |
| PUT /upload/<file> | session + CSRF | 200 `{"uploaded":true,"file","path","bytes"}` (raw body = content) | 400/401/403/413 |
| GET /upload/<name> | none | 200 file bytes (inline) | 400/404 `{"error"}` |
| GET /api/keys | none | 403 always | — |

Auth transport quirks kept for suite compat: session token accepted as `Cookie:
session=<token>`, as raw whole-Cookie value (original used the ENTIRE Cookie
string as the session key), or as `SESSION:` header. CSRF accepted from JSON
body `csrf` field or `X-CSRF` header (constant-time compare).

## Hardening checklist as implemented
1. Parameterized SQL everywhere; check-and-deduct = single atomic
   `UPDATE accounts SET balance = balance - ? WHERE user_id = ? AND balance >= ?`
   + `cur.rowcount != 1` → insufficient funds (no TOCTOU).
2. Strict JSON schema: allowed-key sets per endpoint, wrong types rejected,
   generic messages ("invalid request body"). Bool rejection: `isinstance(amount, bool)`.
   `math.isfinite` check BEFORE `round(amount, 2)` (round(inf) raises).
3. Uploads: ALLOWED_EXT {.jpg,.png,.pdf,.txt}; 64KB cap → 413 decided from
   Content-Length before reading; magic sniff bound to ext (jpg FF D8 FF,
   png 89PNG\r\n\x1a\n, pdf %PDF-, txt = printable-ASCII heuristic);
   stored under `secrets.token_hex(16)+ext` in `bank_uploads/` (outside web root);
   containment via `os.path.realpath` + startswith(base+os.sep); name validation
   = single unquote + `^[A-Za-z0-9._-]{1,128}$` + no "..".
4. Generic errors: catch-all per method logs traceback server-side, sends
   `{"error":"internal error"}`; no paths/versions/exceptions in responses.
5. Server header stripped by overriding `send_header` to drop the `Server`
   keyword (http.server emits it from send_response_only). Security headers on
   every response: X-Content-Type-Options nosniff, CSP default-src 'none',
   X-Frame-Options DENY, Cache-Control no-store, Pragma no-cache, Referrer-Policy.
6. Auth: PBKDF2-SHA256 200k iters + per-user salt; hmac.compare_digest; session
   TTL 3600 + background sweeper; login rate limit 5 fails/60s per username;
   per-session transfer caps (30/60s + cumulative 100k).
7. `Handler.timeout = 15` (slowloris); do_HEAD/OPTIONS/DELETE/PATCH/TRACE → 405
   (TRACE blocked); size caps on JSON bodies (64KB).

## Debug path: the stale-schema 500 (worth remembering)
Symptom: login → `500 {"ok":false,"error":"internal error"}`; server log shows
`sqlite3.OperationalError: no such column: password_hash` at the users SELECT.
Cause: a pre-existing `bank.db` from the ORIGINAL vulnerable server sat in the
dir; `CREATE TABLE IF NOT EXISTS` silently kept its OLD schema (users had
`password` not `password_hash`/`salt`). `IF NOT EXISTS` does NOT validate columns.
Fix (both, do not skip either):
- give the rewrite its own default DB filename (`bank_v2.db` via env BANK_DB),
  so it never inherits the original's file;
- startup schema guard: `PRAGMA table_info(users)` → if expected columns missing,
  DROP TABLEs and recreate, then seed admin/account. Log "schema mismatch".
Test-design lesson from the same run: a smoke assertion expecting a `%PDF-` body
uploaded as `.txt` to be REJECTED failed — PDF bytes are printable ASCII and
legitimately pass the txt heuristic. Text has no magic bytes; assert the sniff
rejects payloads with genuine control chars (NUL, ESC) instead.

## Smoke-test recipe (48 assertions, all passed)
Standalone urllib script hitting the LIVE server (no framework):
1. Retry-on-start loop (40 × 0.5s) for GET /.
2. Header assertions: nosniff, CSP, XFO, no-store, NO Server header.
3. login ok (session+csrf), Set-Cookie HttpOnly+SameSite; bad login 401;
   unknown-key 400; wrong-type 400.
4. transfer: no-session 401; bad CSRF 403; valid 100.5 → balance delta exact;
   rejects: "abc", -5, 0, 100.005, True, unknown key, over-cap → 400.
5. balance with cookie, with RAW token as whole Cookie (legacy), without → 401.
6. admin: ok, NO "card" key, no-session 401; /api/keys → 403.
7. upload: .php 400; `..%2f..%2fetc%2fpasswd.jpg` 400; magic mismatch 400;
   PNG round-trip byte-exact + Content-Type + inline; txt ok; NUL/ESC txt 400;
   70KB → 413; missing file 404; GET traversal + double-encode 400; no session 401;
   bad/missing CSRF 403.
8. unknown route 404; DELETE → 405; error bodies contain no "Traceback"/'File "'.
Run with a dedicated port (BANK_PORT=9999) to avoid clashing with the suite's 9988;
kill server + `rm -rf bank_v2.db bank_uploads bank_v2.log __pycache__` afterward.

## Known stdlib limits (documented, accepted)
- Python 3.11 http.server: no built-in header-size cap → socket timeout only.
- Windows: os.chmod can't enforce 0600 semantics; perms are ACL-based, best-effort.
- DB/upload permissions on Windows are same-user-enforced; watchdog-style
  re-sync is the real defense against a filesystem-level attacker.
