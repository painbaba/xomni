# DEFENDER-2 monitor-and-respond session (wave 2, ~23:42-00:05)

Role: live monitor daemon defending `bank-war\bank_server_v2_app.py` on 127.0.0.1:9988
against an attacker with host-FS access, alongside ~9 sibling defenders who live-patch
the same source file and run their own supervisors/watchdogs. Final verify: **3/3 F, 0/16 V**.

## Monitor design (final, `defender2_monitor.py`)
Poll every 4s. Each poll:
1. `port_check()` — netstat listeners → bulk wmic cmdline map → kill cmdline-VERIFIED
   foreign/duplicate listeners; keep ONE `bank_server_v2_app.py`; then **login-contract
   probe** (POST /login admin/admin123): a listener that rejects it is misconfigured
   (no ADMIN_PASS env → random password → DB hash churn) or hijacked → kill + respawn.
   Dead port → respawn. Restart env: `BANK_PORT=9988 ADMIN_PASS=admin123`.
2. `check_db()` —
   - expected = LAST logged `transfer ok ... new_balance=N` after the last `server start`
     line (else baseline). NOT `baseline - SUM(transfers rows)` (see lesson 1).
   - users: exactly 1 row, username `admin`, `pbkdf2(admin123, row.salt) == row.hash`
     (salt rotates every boot — relationship check only). Violation → rewrite fresh salt.
   - accounts: exactly `(1,1,expected)`; NaN/Inf/`|bal-expected|>1.0` → revert.
   - transfers rows with no matching post-restart log line AND `now-created_at > 10s`
     → planted fake ledger → DELETE (10s grace protects in-flight legit transfers).
   - uploads dir: files with no `upload ok ... stored=X` log record → DELETE.
   - missing schema (DB file deleted) → recreate + reseed.
3. Escalation (cooldown 60s): >25 transfers/60s (session-rotation drain) OR ≥3
   users-tamper strikes/60s → restart app (wipes attacker's in-memory sessions).
4. Source sha watch (flag changes; re-verify suite after), log truncation detect,
   all events → `defender2_monitor.log` + intel.md.

## Lessons (each cost real time under fire)
1. **Ledger sum ratifies fake drains**: v1 monitor computed expected = baseline − Σ(rows).
   GHOST planted rows summing 5010 → monitor wrote balance DOWN 5010 to "match" the
   fiction. Fix: anchor to the app's logged `new_balance` (the log mirrors the
   memory-authoritative `_auth_balance` and is append-only).
2. **Crash-before-rewrite = live backdoor**: v1 monitor crashed (IndexError) in the
   transfers section BEFORE the users check → GHOST's planted admin hash (9359cc25…)
   stayed live for minutes. Fix: fault-isolate every section; one failure must not
   skip the others.
3. **Hardcoded salt/hash falses every boot**: the app re-seeds a fresh random salt +
   pbkdf2 hash at every cold start. Canonical check must be the hash RELATIONSHIP.
4. **Kill-all port logic kills your own server**: per-PID `wmic process where
   ProcessId=X get CommandLine` returns EMPTY rows → monitor thought every listener was
   a hijack and taskkilled all three (incl. its own fresh spawn). Fix: one bulk wmic
   query per poll + only kill listeners whose cmdline is positively identified as
   foreign; unknown cmdline → flag, don't kill.
5. **Monitor bugs of the generic kind**: `SELECT amount FROM transfers` rows are
   1-tuples → `r[2]` IndexError (crash only once rows exist!); `for rid,recip,amt in`
   over 4-tuples → ValueError. Silent-death pattern: loop catches per-poll exceptions
   but a section that crashes every poll = defense off while log looks fine.

## GHOST TTPs observed this wave (defender side)
- **Backdoor-hash replant loop**: plant own admin hash (~1-5s loop) → login with own
  password → keep the session (sessions are in-memory; the app's watchdog restores the
  admin123 hash in ~2s but the attacker's live session survives). Replant only around
  logins; don't fight the watchdog continuously.
- **Legit-recipient laundering**: drain $10 at a time to `savings` (a suite recipient)
  with login → transfer → logout rotation (log shows `login ok ... revoked=1`), so
  recipient-based alerts never fire and per-session caps reset per login.
- **Fake ledger rows** (savings 10 ×N, drain_test 5000) to launder DB-edit drains.
- **CJK recipient probe** (`日本バンク` 0.01) — presence flag.
- **Planted upload files** (10 random .txt, 1-16 bytes, no API record) — killed by
  boot-wipe + monitor unlogged-file delete.
- **Foreign build on the port**: `bank_server_v2_ultimate.py` (a sibling's port-9999
  build) bound to 9988 and its watchdog fought the canonical watchdog over bank_v2.db
  (ledger rebuild vs INTEGRITY REPAIR every 2s) → killed. Same for a stale wave-1
  `bank_server.py` (PID 960) dual-binding via SO_REUSEADDR.
- **Stale/misconfigured instances**: `bank_server_v2_app.py` started with Python 3.13
  (WindowsApps) rejected admin123 and threw `AttributeError: 'Handler' object has no
  attribute 'requestline'` (3.13 http.server logging) — contract probe caught it.

## Coordination (multi-defender)
- **D10 supervisor port-war**: two `d10_supervisor.py` instances, each looping
  `killall() → spawn`, killed each other's children forever (up to 6 listeners, PIDs
  rotating every ~1-2s). Killed both; monitor owns the port now. A kill-all supervisor
  is fundamentally unsafe with >1 supervisor or other defenders — the monitor's
  selective kill + contract probe replaces it.
- **Sibling live-patching broke the build twice** (`global _conn_count` after use;
  mis-indented `finally`) → server down, every restart fails. Restored known-good
  snapshot (sha c3f3a3d5), preserved WIP as separate files, sha-watched. Rule: save
  WIP copies before touching; compile-check before launch; announce RESTART OWNERSHIP
  in intel.md before any kill/restart.
- **Legit test-recipient registry** in intel (savings, drain_test, race_target, x,
  x_probe) so monitors don't flag sibling tests as exfil.
- Windows: `MSYS_NO_PATHCONV=1 taskkill /PID <pid> /F` (the `//PID` form fails with
  "Invalid argument/option"); `MSYS_NO_PATHCONV=1 icacls <file>` one file per call.
