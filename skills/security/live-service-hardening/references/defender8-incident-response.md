# DEFENDER-8 Incident-Response Lead — Battle 4 session (2026-08-08/09, ACME BANK 127.0.0.1:9988)

Role: port ownership, recovery runbook, restore-when-down, verify, coordination. The
D8 deliverables that worked and should be replicated every battle:

## Deliverables (all battle-proven)
1. **`battle_state.md` dashboard** in the ghost sandbox — sections: bank status table
   (listener PID, build sha, admin creds, DB path, verify score, balance), recovery
   runbook, GHOST activity ledger, defender roster + conflict register, open-vuln queue,
   verification log. Update it after every incident; append via Python `open(...,"a")`.
2. **Recovery runbook** — copyable block with: STEP 0 announce RESTART OWNERSHIP in
   intel BEFORE killing; STEP 1 sweep port (must be EMPTY); STEP 2 sha-verify source
   against known-good CLEAN + `ast.parse` compile check; STEP 3 relaunch with explicit
   `ADMIN_PASS`/`BANK_PORT`/`BANK_DB` env; STEP 4 verify single listener + 0/16.
   Restore success = 3/3 F + 0/16 V, else the on-disk file regressed.
3. **Watchdog daemon** (`d8_watchdog.py`, ~60 lines) — 10s poll: GET / → admin login →
   /balance → single-listener check. Restore ONLY on DOWN (port free / login fail /
   balance fail); on double-bind SWEEP ALL then single-launch; `ast.parse` in-process
   for the syntax gate (py_compile lies when `__pycache__` is locked); PowerShell sweep
   (`Get-CimInstance Win32_Process | ? {$_.CommandLine -like '*bank_server*'}`) because
   bash `taskkill` prefix tricks fail from subprocess; retry next tick on locked source,
   never give up. v1 relaunched-on-double-bind and CAUSED a 6-listener storm — v2
   restore-only-on-DOWN is the fix. Keep it running as a background process; D10's
   ~1s supervisor is complementary redundancy, not a replacement.

## Incident timeline (what actually happened)
- 23:42 stale v1 (drained by GHOST) + v2 co-bound via SO_REUSEADDR; stale wins accept()
  → all traffic hit the WRONG build; verify scored the wrong server. Fix: kill ALL
  listeners, confirm port FREE, relaunch one.
- 23:46 sibling defender launched a second v2 16s after mine → double-bind again.
  Fix: kill both, single launch. Lesson: announce ownership BEFORE restarting.
- 23:50 sibling merge pasted `global _conn_count` mid-function AFTER `_conn_count += 1`
  → `SyntaxError: name '_conn_count' is assigned to before global declaration`, bank
  DOWN. Fix: hoist ONE `global` to top of function.
- 23:55 sibling merge mis-indented `finally:` (8sp vs 12sp `try:`) → SyntaxError, bank
  DOWN. Fix: re-indent. Both SyntaxErrors came from concurrent full-file rewrites —
  surgical patches only, `ast.parse` before every launch.
- 23:57-00:00 GHOST file-lock attack: exclusive handles on source/logs/__pycache__
  (cat/cp/py_compile Permission denied despite normal ACLs — icacls fine) + swapped
  `bank_server_v2_app.ghost.py` (sha IDENTICAL to live) in as live source. Counters:
  PowerShell `Copy-Item` (fresh unlocked file), `ast.parse` instead of py_compile,
  restore from sha-pinned `backups/clean/bank_server_v2_app.py.CLEAN`.
- 00:02 converged: 3/3 F, 0/16 V, single listener, balance 1284550.12 held.

## Source-provenance map (battle 4 known-good)
- Known-good source: `backups/clean/bank_server_v2_app.py.CLEAN` ==
  `bank_server_v2_app.pristine-2355.py` (sha c3f3a3d5...), verified 0/16.
- `bank_server_v2_app.ghost.py` = GHOST DECOY (same sha as the file it was swapped
  from — provenance unknown, never trust). `bank_server_v2_app.D8-canonical.py` =
  D8 snapshot (had the global SyntaxError — snapshots capture bugs too).

## Coordination rules (now embedded in SKILL.md pitfalls)
- Announce RESTART OWNERSHIP in intel BEFORE every kill/restart; after every restart
  require exactly ONE listener then re-verify. Parallel restarts without announcements
  are the double-bind storms (5x in one battle).
- GHOST's file-lock + decoy swap is a NEW TTP — the "windows file-lock storm" pitfall
  covers the ambient variant; a READ-locked source + attacker-named twin + swapped
  live file = deliberate. Verify sha against CLEAN before every restart.
- Watch for verify-suite false-VULN: GHOST unique-username flood evicts the probe
  user's rate record from the 5000-entry `_failed` dict mid-test → transient V3 1/16
  that re-runs clean. Re-run verify before declaring regression.
