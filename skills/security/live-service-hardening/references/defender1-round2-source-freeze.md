# DEFENDER-1 round 2 — source-integrity freeze session (battle 5, 2026-08-09 ~00:25-00:40)

Role: DEFENDER-1, round 2, against GHOST-4's "poison every restore source" playbook.
Canonical bank: `bank-war/bank_server_v2_app.py`, sha `c3f3a3d5631bbb91...`, port 9988,
`ADMIN_PASS=admin123`. Scoring: `verify_v2.py` → 3/3 F, 0/16 V.

## Situation on arrival
- Live source hash == clean hash (c3f3a3d5) — GHOST-4's claimed source backdoor
  (ghost/GH0ST-MASTER-2026, /ghost?set, ghost_balance.txt) was already reverted.
- BUT `referee_defense.py` (the sanctioned 3s source-integrity watchdog) was DOWN —
  GHOST-4's "hold daemon" had killed it and all defender monitors.
- DB already tampered: planted account (2,2,$500M) + balance nibble; no watchdog alive
  to revert it → the round-1 plant→login→drain chain was armed again.
- Port 9988 had 2-3 co-bound listeners (SO_REUSEADDR split-brain); verify untrustworthy.

## What was built
1. `ghost_sandbox/defender_freezer.py` — upgraded referee freeze (also copied as
   `referee_defense.py` v2):
   - WATCH set extended: `restore_bank.py` + `backup_daemon.py` (were unwatched /
     watch-only-with-no-restore-copy).
   - Self-healing restore sources: every loop, verify each `backups/clean/*.CLEAN`
     against `backups/freeze_mirror/` and repair from mirror FIRST (poisoned .CLEAN
     must never be deployed by the watchdog itself).
   - App restore fallback chain, hash-verified: freeze_mirror → pristine-2355 →
     ghost.py (decoy) → .CLEAN; CRITICAL alarm if none match c3f3a3d5.
   - DB pin upgraded: delete planted USERS **and planted ACCOUNT rows**
     (user_id != 1 OR id != 1), re-insert canonical row if missing, then pin balance.
   - Launched under an innocuous name via a bash respawn loop:
     `while true; do python defender_freezer.py >> log 2>&1; sleep 2; done`
     — survived 2 monitor-kills (GHOST kills by name/pid within ~10s of learning it).
2. Pristine stores: `backups/freeze_mirror/` + `backups/clean2/`, each copied
   separately; canonicalized restore_bank v2 (sha 0c907efa) into both.
3. Port consolidation: ran D9's `restore_bank.py` (kills ALL listeners → spawns ONE
   canonical) → exactly 1 listener; verify 3/3F 0/16V ×3.

## Live evidence (the attacker counters your intel)
- After the intel announcement named `backups/freeze_mirror/` as the fallback store,
  within ~5 min: `freeze_mirror/bank_server_v2_app.py` + `_ultimate.py` were DELETED
  and `backups/clean/restore_bank.py.CLEAN` + `backup_daemon.py.CLEAN` were
  handle-locked (`Permission denied` for bash AND PowerShell Copy-Item -Force —
  beyond the lock-storm case where Copy-Item works). Lesson: never announce the path
  of your only pristine copy; build redundancy before advertising.
- GHOST re-planted account (2,2,500000000.0) at 00:34:44; freezer logged
  `REMOVED planted account rows: [(2, 2, 500000000.0)]` on the same sweep.
- A sibling defender's `restore_bank.py` v2 (sha 0c907efa) arrived mid-wave with an
  embedded zlib+base64 pristine app copy + reversed-hex hash. Verification recipe:
  `importlib.util.spec_from_file_location('rb','restore_bank.py'); exec_module;
  hashlib.sha256(mod._EMB_SRC.encode())` == c3f3a3d5 → LEGIT (keep). A later sibling
  micro-fix switched the blob to bytes + binary `wb` write (hash both forms).
- `d10_duo_guard.py` respawned bank instances every ~12s → listener PID churned
  4× in 6 min; verify flapped until re-run on a single-listener window (ran twice
  back-to-back, both green).

## Key numbers
- verify_v2.py: FUNCTIONAL 3/3, VULNERABILITIES 0/16 (00:30, 00:35 ×2).
- Freezer removed 1 planted account row + pinned balance 3× in ~2 min of logs.
- Final state: source c3f3a3d5, users=[admin], accounts=[(1,1,1284550.12)],
  1 listener, freezer alive.

## Reusable snippets
- Verify embedded copy: `python -c "import importlib.util,hashlib;
  s=importlib.util.spec_from_file_location('rb','restore_bank.py'); m=importlib.util.module_from_spec(s);
  s.loader.exec_module(m); e=m._EMB_SRC; print(hashlib.sha256(e.encode() if isinstance(e,str) else e).hexdigest())"`
- Windows-python script arg from git-bash: use `C:/Users/...` forward-slash form —
  `/c/Users/...` becomes `C:\c\Users\...` → "can't open file".
- Hash identity check: explicit filenames, never globs (`backup_daemon` sorts before
  `bank_server` — glob output misattribution cost a false "files swapped" scare).
