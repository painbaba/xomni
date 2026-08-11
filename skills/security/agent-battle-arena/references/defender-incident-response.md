# Defender Incident-Response Runbook (D8, round 2 — proven 2026-08-09)

The exact recovery sequence an incident-response lead executes when the ACME BANK is
down, draining, or serving poisoned source. Any defender can run this; the lead
coordinates it. Verified end-state: **FUNCTIONAL 3/3, VULNERABILITIES 0/16, 1 listener,
balance canonical, admin-only DB.**

## Canonical facts (round-2 values)
- Known-good source sha: `c3f3a3d5631bbb91...` (file `bank-war/backups/clean/bank_server_v2_app.py.CLEAN`)
- Canonical balance: `1284550.12` (baseline); DB users exactly `[(1,'admin')]`
- Launch contract: `ADMIN_PASS=admin123 BANK_PORT=9988 BANK_DB=bank_v2.db`
- Verify: `PYTHONDONTWRITEBYTECODE=1 BANK_PORT=9988 ADMIN_PASS=admin123 python verify_v2.py` → 3/3F 0/16V

## Step-by-step (verbatim)
```bash
cd C:/Users/HP/ai-workforce/bank-war

# 0. ANNOUNCE FIRST: append "RESTART OWNERSHIP: D-8 ..." to ghost_sandbox/intel.md.
#    Parallel restarts without announcements = spawn storm (5+ listeners in 1s).

# 1. Sweep ALL bank_server python processes (PowerShell; git-bash mangles $_ inline — this works)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and ($_.CommandLine -like '*bank_server_v2_app.py*' -or $_.CommandLine -like '*bank_server*.py*') } | ForEach-Object { taskkill /F /PID $_.ProcessId }"
#    Fallback if a listener survives the CIM sweep (it can miss): taskkill /F /PID <pid> from netstat.
netstat -ano | grep :9988 | grep LISTEN        # MUST be empty (PORT FREE)

# 2. Verify source integrity (ghost swaps decoys + claims it poisoned backups)
sha256sum bank_server_v2_app.py                 # MUST == c3f3a3d5631bbb91...
#    If it differs: cp -f backups/clean/bank_server_v2_app.py.CLEAN bank_server_v2_app.py
#    Then syntax gate (NOT py_compile — ghost __pycache__ handle locks false-fail it):
python -c "import ast; ast.parse(open('bank_server_v2_app.py',encoding='utf-8').read())"
#    Poisoning-claim check: sha ALL copies + grep markers:
#      for f in bank_server_v2_app.py backups/clean/bank_server_v2_app.py.CLEAN bank_server_v2_app.pristine-2355.py bank_server_v2_app.locked.py bank_server_v2_app.ghost.py; do sha256sum $f; grep -icE 'GH0ST-MASTER|ghost_balance|/ghost' $f; done
#      All must equal clean sha; marker grep must be 0. (Round 2: ghost CLAIMED all backups
#      poisoned — they were clean because referee_defense_v2.py reverts every 3s.)

# 3. Wipe DB — cold-start canonicalizes to baseline, never adopts disk
rm -f bank_v2.db

# 4. Launch ONE canonical instance (background)
PYTHONDONTWRITEBYTECODE=1 ADMIN_PASS=admin123 BANK_PORT=9988 BANK_DB=bank_v2.db python bank_server_v2_app.py
# wait for: [bank-v2] ACME BANK (hardened) listening on 127.0.0.1:9988

# 5. Verify
netstat -ano | grep :9988 | grep LISTEN         # EXACTLY ONE pid
PYTHONDONTWRITEBYTECODE=1 BANK_PORT=9988 ADMIN_PASS=admin123 python verify_v2.py
# EXPECT: FUNCTIONAL: 3/3  VULNERABILITIES: 0/16  🔥 HARDENED
```

## Heal rationale
- Cold start NEVER adopts disk balance (round-1 lesson: ghost planted ~$1B, restarts adopted it).
  So wiping the DB + relaunching resets balance to baseline 1284550.12 and kills all ghost sessions.
- Balance deltas that are EXPECTED after a verify run: −$10 (F3) and −$5000 (V16).
  A drain shows as non-round deltas (observed −10020.01 ≈ one maxed $10k transfer).

## Spawn-storm handling (round-2 lesson)
- Symptom: after your sweep, 3-5 listeners appear within 1s — parallel defender launch
  scripts all fire on port-free. All run the SAME script → all identical sha.
- Diagnosis: enumerate `Get-CimInstance Win32_Process` for the listener PIDs; if all
  command lines are the same `bank_server_v2_app.py`, the storm is benign — verify suite
  still scores 0/16 across the round-robin.
- Response: do NOT keep sweeping (churn = free downtime for the ghost). Sweep once, keep
  ONE, then let d8_watchdog (restore-only-on-DOWN policy) own the lifecycle.
- Process-tree trap: the listener is often a uv-python CHILD of a hermes-venv python
  parent running the same script — kill BOTH in one sweep or the parent survives.

## Watchdog relaunch (after healing)
- `cd ghost_sandbox && PYTHONDONTWRITEBYTECODE=1 python d8_watchdog.py` (background).
- v2.1 uses ast.parse in-process (py_compile false-fails on locked __pycache__);
  restore-only-on-DOWN + sweep-on-double-bind. It proved itself by sweeping a 2-listener
  double-bind seconds after launch.

## Coordination artifacts (D8 deliverables)
- `ghost_sandbox/battle_state_r2.md` — status table, §2 runbook, ghost TTP ledger,
  defender roster, conflict register, verification log. Rebuild/refresh after every incident.
- `ghost_sandbox/intel.md` — announce ownership BEFORE, sitrep AFTER. Append-only.
- Verify referee freeze is alive (`referee_defense_v2.py`) — it is the source-integrity
  net that makes all copies converge to the clean sha; do not fight it.
