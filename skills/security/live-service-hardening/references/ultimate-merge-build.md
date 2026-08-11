# Ultimate three-way merge build (bank_server_v2_ultimate.py) — session detail

Task: merge three independently-verified hardened builds into ONE ultimate build, then
self-test with verify_v2.py (3/3 F, 0/16 V) and run attack_suite.py for comparison.
Base = bank_server_v2_app.py (web-app hardening); merge in money-integrity defenses
from bank_server_v2_money.py and auth defenses from bank_server_v2_auth.py.
Admin password from env ADMIN_PASS (random fallback printed once). All files in
C:\Users\HP\ai-workforce\bank-war\. Result: 51.7KB stdlib-only single file.

## Merge architecture (what the ultimate build looks like)
- BASE = app build's Handler: strict `_json_body(allowed_keys)` schema, `_clean_str`
  (no control chars), upload allowlist (.jpg/.png/.pdf/.txt) + magic-byte sniff bound
  to ext + random stored names + realpath containment + single-unquote regex,
  generic errors, security headers (nosniff/CSP none/XFO DENY/no-store), Server-header
  strip, parameterized SQL, minimal admin exposure, per-session transfer caps.
- DB layer swapped to money build's: `_money_connect()` (isolation_level=None,
  explicit BEGIN IMMEDIATE), ledger hash chain (`_chain_hash` includes rowid +
  fixed-cents amount + repr(ts); `_verify_chain` rehashes from GENESIS_HASH),
  `_do_transfer` = BEGIN IMMEDIATE → read balance in-tx → row-scoped
  `UPDATE accounts SET balance=balance-? WHERE id=? AND balance>=?` (rowcount==1)
  → in-tx hourly drain cap (SUM(amount) from ledger, 300k/h) → append ledger row with
  prev_hash, hash filled same tx → commit → mirror into `_canonical` + persist signed
  state. `_canonical = {"balance", "journal"}` is the source of truth; DB is a cache.
- Watchdog thread (2s): under `_tx_lock`, fix users table, revert balance column to
  canonical, verify chain vs canonical journal, rebuild ledger from journal on
  mismatch, persist state if changed, re-lockdown file perms.
- Signed cold-start state: `_persist_state_locked` writes balance/ledger_count/
  tail_hash/chain_root/ts + HMAC-SHA256 sig (code-constant STATE_KEY); `_load_state`
  verifies; `_cold_start` never adopts a tampered balance — signs off only when
  chain verifies AND count/tail/chain_root match the signed state AND debits
  reconcile; else resets to signed last-known-good or baseline.
- Auth layer: per-IP AND per-user failure lockout (5 fails → 60s, in-memory dicts),
  per-IP login burst cap (60/60s sliding window), session rotation at login
  (delete all sessions for uid → mint fresh → ONE active session), /logout
  (session + CSRF, tolerates empty body), 10-min session TTL, PBKDF2-SHA256 200k +
  salt + compare_digest, DUMMY hash timing equalization for unknown users.

## Adaptations required to merge (the non-obvious parts)
1. **Env password must be re-applied EVERY boot**, not just first boot: a pre-existing
   DB may hold a randomly-generated admin password from a previous no-env boot.
   Bootstrap canonicalizes: exactly one admin user + one account; if ADMIN_PASS env is
   set, rehash and UPDATE it (test contract: ADMIN_PASS=admin123 always works).
   Random `secrets.token_urlsafe(18)` fallback only when no env AND no admin exists —
   printed ONCE to stdout (banner) and to the 0600 log.
2. **Money build's code-constant ADMIN_HASH cannot work with env passwords** — the
   watchdog's users-table tamper repair needs an anchor. Fix: capture the canonical
   (hash, salt) at bootstrap into module globals (`_admin_hash_hex/_admin_salt_hex`);
   `_fix_users_table` enforces users == exactly `[(1, 'admin', hash, salt)]`, deleting
   anything else. Bootstrap also wipes users/accounts if a tampered DB has users but
   no admin row.
3. **Keep app's minimal admin exposure** (`customers: [{"name": "Alice Chen"}]`) over
   money/auth builds, which leaked card numbers in /admin — the leak was a genuine
   vuln regression the suites don't check but the contract shouldn't have.
4. **No FK constraints** in the schema: the watchdog deletes/reinserts users freely;
   an accounts→users FK would make `DELETE FROM users` raise.
5. **Hash-chained `ledger` replaces the `transfers` table** — the ledger IS the
   transfer record; chain payload separator is `|`, so sanitize the recipient label
   (`re.sub(r"[^A-Za-z0-9 _\-.@]", "", to)`) before it enters the chain.
6. **Session value cap ($100k) + MAX_TRANSFER ($10k) make V10's 30×$50k race
   irrelevant** — transfers are rejected before the DB op regardless of rotation
   timing; row-scoped guarded UPDATE is the second line.
7. **Rate-limit ordering**: verify_v2's V10 (30 concurrent) needs the per-session
   window ≥ 30/60s and per-IP transfer window ≥ 120/60s so the suite's own race burst
   isn't throttled into a false "vuln" reading.
8. **Separate runtime artifact names** per build generation (bank_v2_ultimate.db /
   _state.json / .log, default BANK_DB) so a stale DB with the old schema can't
   silently poison a new build (stale-schema trap).

## Observed scores (both suites, same build)
- Fresh instance, `BANK_PORT=9999 ADMIN_PASS=admin123`:
  - verify_v2.py → **FUNCTIONAL: 3/3  VULNERABILITIES: 0/16 🔥 HARDENED**
  - attack_suite.py → **FUNCTIONAL: 3/3  VULNERABILITIES: 1/12** (only
    V1_default_creds = the env-password false positive; see SKILL.md scoring section)
- Back-to-back on ONE instance (verify then attack, or attack then verify): second
  suite scores 0/3 functional — its F1 admin login 429s because the first suite's
  failed-login probes (15 + 12 wrong passwords) tripped the per-IP lockout on
  127.0.0.1. Artifact, not regression; fresh instance per suite fixes it.
- Suite order matters for repeated verify runs too: a verify run's OWN V3 probes lock
  the shared IP, so a second immediate verify run also 0/3s (all 16 V-checks still
  pass). Don't re-run a suite twice on one instance without a restart.

## Cold-start / signed-state evidence (proves the merge actually works)
Log transcript from the session:
```
COLD START: no signed state, DB self-consistent -> adopt balance=1284550.12 ledger=0
server init: balance=1284550.12 journal=0
... (verify run: F3 10.0 + V16 5000 -> balance 1279540.12, ledger=2, state signed)
COLD START: signed state + DB verified consistent -> adopt balance=1279540.12 ledger=2
```
i.e. the restart verified the HMAC signature + full hash chain and adopted the signed
balance — the money-integrity cold-start path exercised end-to-end.

## Windows verification notes (this host)
- ACL lockdown verify: `icacls bank_v2_ultimate.db` → `LAPTOP-XX\HP:(F)` with NO
  inheritance entry = lockdown good. ONE file per invocation; multi-file args from
  git-bash → `Invalid parameter`.
- Server lifecycle: launch `terminal(background=true)` + watch_patterns
  `["listening on 127.0.0.1:PORT"]`; poll to confirm env-password line; kill via
  process tool; confirm port free with `netstat -ano | grep :PORT | grep LISTEN`
  (an old suite's listener may still hold 9988 — pick an unused port like 9999).
- `python -m py_compile` before launch; verify suite reads ADMIN_PASS env itself.
