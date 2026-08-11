# DEFENDER-9 — backup/HA & restore session (ACME BANK wave 2, 23:45-23:56)

Role: DEFENDER-9 (backup/HA). Deliverables: protected DB snapshots + restore
script, corruption-recovery test, periodic backups, restore-on-demand, contract
verify after restore. All learnings below are generic for "defender for backup/HA".

## Architecture built (both files live in bank-war/)
- `backups/` — icacls-locked dir: `MSYS_NO_PATHCONV=1 icacls backups /inheritance:r /grant:r "HP:(OI)(CI)F" "SYSTEM:F"` (flag args path-mangle without MSYS_NO_PATHCONV; git-bash converts `/inheritance:r` → `//inheritance:r` → `Invalid parameter`).
- `backups/bank_v2.snapshot.db` — CANONICAL restore target: pristine schema + admin + balance 1284550.12. NOT a copy of the live DB (live DB is mid-drain/poisoned at any given moment).
- `restore_bank.py` — pipeline: db_valid() → restore from snapshot / rebuild canonical from constants → kill ALL listeners on 9988 → spawn exactly ONE `bank_server_v2_app.py` with BANK_PORT + ADMIN_PASS=admin123 env → probe admin/admin123 login as the FINAL GATE.
- `backup_daemon.py` — every 30s: snapshot live DB ONLY if structurally valid (else skip+log); keep last 5 timestamped copies; rebuild canonical snapshot at start. Logs `[DEFENDER-9]` lines to bank_defense.log.

## db_valid() — structural, NOT hash comparison
```python
ok = integrity_check == "ok" and {"users","accounts"} <= tables
users == exactly [(1,'admin')] and accounts == exactly 1 row
0 < balance <= BASELINE + 0.01
```
Do NOT compare `password_hash` to a hardcoded constant: every server re-bootstrap
regenerates salt → fresh hash for the same password. A hash check falses after any
restart and triggers spurious rebuilds. Identity is verified LIVE (login probe), not statically.

## Identity poisoning — the subtle kill (core lesson of this session)
- A server started WITHOUT `ADMIN_PASS` env generates a random password at boot
  and BOOTSTRAPS the DB with it (overwrites users.password_hash when the users
  table is empty / tampered). admin123 stops working. DB looks structurally perfect.
- Symptom fingerprint: DB integrity ok + exactly admin + sane balance, but
  verify_v2 F1 FAILS (login 401). Culprit found via `wmic process where
  "ProcessId=<pid>" get CommandLine` → rogue instance running
  `bank_server_v2_ultimate.py` (a DIFFERENT file from the canonical app) with no env.
- Fix baked into restore_bank.py: after restore+spawn, probe login. If not 200:
  rebuild canonical DB with a FRESH salt + pbkdf2(admin123, salt, 200_000) hash
  (iter count must match the app), kill all listeners, respawn, re-probe.
- Lesson: a restore script that trusts "DB looks valid" is insufficient. The
  live-login gate is the real identity check.

## Split-brain elimination
- Observed: up to 6 listeners on 9988 at once — old round-1 `bank_server.py`
  serving bank.db, v2 app on bank_v2.db, duplicate v2 spawns, rogue ultimate.py.
  Windows SO_REUSEADDR allows the second bind; accept() routing is nondeterministic.
- Fix: restore script kills EVERY listener PID found on the port (identify via
  `wmic process where ProcessId=... get CommandLine`; only kill ones whose
  commandline mentions the bank server), then spawns exactly one with known-good env.
- Don't be clever about which listener to keep — kill all, spawn one.

## Verify-after-restore protocol (this session's exact run)
1. Build canonical snapshot (rebuild from constants — NOT a file copy).
2. Simulate GHOST wipe: `open('bank_v2.db','wb').truncate(0)`.
3. Run restore script → assert: live DB restored (integrity ok, admin only, 1284550.12), single listener, login 200.
4. `BANK_PORT=9988 ADMIN_PASS=admin123 python verify_v2.py` → must be FUNCTIONAL 3/3, VULNERABILITIES 0/16.
5. Result: PASS. Also re-verified after a second restore when sibling edits had churned the source.

## Coordination hazards observed
- **Concurrent multi-defender source editing**: bank_server_v2_app.py grew
  703 → 1010 → 1134 → 1295 → 1284 lines within minutes (DEFENDER-7/10 layers).
  Re-read the file before EVERY write; `patch` tool warns "modified by sibling
  subagent ... re-read before writing" — trust it, re-read, re-apply.
- **Running server = stale code**: a spawned server runs the file as of ITS boot.
  After any restore, spawn fresh so the current source (incl. sibling fixes like
  the 429-lockout fix) is live. Behavioral probe to confirm which build answers.
- **Single-instance guard appeared mid-wave**: newer app builds log
  "REFUSING START: port already served by another listener" — a second spawn
  exits harmlessly instead of double-binding. Restore scripts that assume they
  own the port may race a sibling's already-running instance: probe may return
  HTTP -1 (conn refused) transiently — re-probe after settle before declaring failure.
- **V3 regression from a sibling edit**: unknown users got 401 even when locked
  (lockout check only applied to existing users) → verify V3 (15 wrong logins on
  non-existent `rl_probe_user`) flagged VULN. Correct behavior: unknown-user path
  must ALSO return 429 once `_is_locked`. A sibling fixed it independently — the
  lesson is that V3 tests unknown-user throttling, and any login-lockout change
  must cover the unknown-user branch.
- **Intel channel discipline**: append timestamped `[DEFENDER-9]` entries to
  intel.md; announce restart ownership + split-brain findings so parallel
  defenders don't fight your listener consolidation.

## Environment-specific notes
- git-bash + PowerShell: `powershell -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='python3.exe'\" | Where-Object { $_.CommandLine -match 'bank_server' } | Select-Object ProcessId,CommandLine"` lists bank server PIDs + commandlines.
- netstat listener parse in Python: `parts[1]` is the local-address column, `parts[-1]` is the PID; filter `'LISTENING' in line and f':{PORT}' in parts[1]`.
- `subprocess.Popen(..., creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)` survives the restore script exiting (Windows).
- GHOST was draining via API in real time during the session (balance dropped 1284550 → 1269510 within minutes) and threw a massive TIME_WAIT connection flood on 9988 — expect live traffic to contaminate balance-delta assertions; attribute via defense log.
