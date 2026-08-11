# DEFENDER-2 Round-2 monitor-and-respond — full session (proven Aug 2026)

Role: DEFENDER-2, round 2 "monitor-and-respond". Task: live monitor that reverts
source tampering, balance drains, DB plants, and kills ghost processes; log
everything to intel.md. This is the complete build + the four incidents that
shaped it. The monitor (defender2_r2_monitor.py / bank_balance_watch.py +
svc_keepalive.py respawner) is the reference implementation for the patterns below.

## Monitor architecture that worked

Poll loop (4s), every check fault-isolated in try/except (a locked file or DB
hiccup must never skip the other defenses — GHOST locks defender files to kill
monitors). Five enforcement layers:

1. **Source integrity** — sha256(bank_server_v2_app.py) MUST equal CLEAN sha
   (task-pinned c3f3a3d5...). On mismatch: restore from a **private stash
   OUTSIDE the lab tree first** (`battle-kit/defender2/bank_server_v2_app.CLEAN.stash`),
   then `backups/clean/*.CLEAN`. After restoring, **repair the whole restore
   chain** (backups/clean, pristine-2355, .d10vault copies) so no defender tool
   can be fed the attacker build next round. Retry plain copy 3×, fall back to
   `powershell Copy-Item` (GHOST holds exclusive handles → PermissionError).
2. **Balance watch (API-level)** — login+balance every poll. expected =
   BASELINE minus legit transfers since the CURRENT listener's process start.
   If live < expected − TOL → **restart app** (cold-start canonicalizes to
   baseline — that IS the revert). Restart kills all listeners first, then
   spawns one, with a 20s cooldown so a hammering attacker can't force a
   restart loop.
3. **DB canonicality** — users EXACTLY [(1,'admin',hash,salt)] where
   hash == pbkdf2(admin123,salt); accounts EXACTLY one row (1,1); planted
   transfers rows (no matching log line, >10s old) deleted; missing schema
   → recreate+reseed.
4. **Ghost process sweep** — match the script **basename** against
   ghost*/sys_health/inject/massdrain/strike_loop/final_strike/ntptimesync/gf2_/
   exfil patterns, with a DEFENDER_SAFE exclusion list (backup_daemon,
   restore_bank, d10_supervisor, d8_watchdog, defender*, hunter, referee,
   verify_v2, attack_suite, r2_monitor, perf_tool, freezer, decoy, probe...).
5. **Single-listener enforcement on the battle port** — exactly ONE
   bank_server_v2_app.py listener that passes admin/admin123; foreign/duplicate
   listeners killed (cmdline-verified only); PORT-NO-APP needs 2 consecutive
   strikes before kill+restart (fresh spawns race the wmic enumeration).

Deployment hardening (all proven necessary):
- Run the monitor under an **innocuous filename** (`bank_balance_watch.py`) —
  attacker kill-scripts regex `defender|monitor|watchdog|supervisor` in the
  cmdline; a correctly-named daemon survives sweeps that kill everything else.
- Wrap it in a **keepalive respawner** (`svc_keepalive.py`): spawn watcher,
  on exit respawn in 2s, log every respawn. Plain background children were
  externally killed 3× in one round (exit 127/1, no traceback = taskkill).
- Stash a verified copy of the monitor itself
  (`battle-kit/defender2/bank_balance_watch.CLEAN.stash`) — see incident #1:
  GHOST edits defender scripts' constants.
- Never `py_compile` (GHOST locks __pycache__ handles → false Permission
  denied); use `python -c "import ast; ast.parse(...)"`.

## Incident 1 — poisoned-constant restore-chain attack (the "7138" incident)

GHOST changed FOUR things to one wrong hash (713878626ddafa02...):
- `backups/clean/bank_server_v2_app.py.CLEAN` (the canonical restore source)
- `.d10vault/bank_server_v2_app.CLEAN.v2` (duo_guard's vault)
- `d10_duo_guard.py`'s CLEAN_H constant
- MY MONITOR'S OWN CLEAN_SHA constant (changed to 7138 so I'd accept the
  attacker build as "clean" and never revert it)

Consequences: the referee tool `bank_perf_tool.py` copies from
`backups/clean/*.CLEAN` **without verifying the source hash** → the referee
itself became a 7138 deployer every 3s, re-poisoning the live file within
seconds of any restore. The source flipped c3f3a3d5→7138 repeatedly and my
monitor (with poisoned CLEAN_SHA) silently accepted it.

Discrimination rule that resolved it: **tamper vs legit promotion**. The 7138
build had NO attacker markers (ghost/GH0ST-MASTER-2026 login → 401, /ghost?set
→ 404) — it was a sibling defender's hardened build that got adopted by
partial tooling. But the task + referee pinned c3f3a3d5, and my own constant
had been edited without my doing (grep `# zsysmon-anchor`-style graffiti). When
the live hash doesn't match, check markers FIRST (`grep -c "GH0ST-MASTER|zsysmon|/ghost"`),
check whether any defender tool was silently edited, then decide revert vs accept.

Counter sequence (proven): (1) kill the deployer processes (duo_guard instances
hold the old constant in memory — kill + relaunch after patching the file);
(2) restore ALL restore sources from the private stash (backups/clean, clean2,
.d10vault, pristine-2355); (3) re-pin every defender constant to the canonical
sha; (4) sweep listeners, spawn ONE, verify. Also grep every *.py in the lab
for the attacker hash — it lives in defender tools that got edited.

## Incident 2 — ghost-process sweep false positives (friendly fire)

- Matching `ghost` against the FULL cmdline kills every defender tool that
  happens to run from `ghost_sandbox/` — the DIRECTORY name contains "ghost".
  Fix: `os.path.basename(cmd.split()[-1])` and match the basename only.
- Matching `daemon` killed `backup_daemon.py` — DEFENDER-9's legit snapshot
  daemon. Fix: DEFENDER_SAFE exclusion list checked on the lowercase cmdline.
- Attacker kill-daemons to expect: `strike_loop.py` → `final_strike.py` (kills
  every monitor by substring KILL_PATTERNS then reconciles DB to 0.01 via a
  planted `bank-war/ntptimesync.py`), disguised keepers (svc_health/svc_watch/
  svc_ntp/sync_helper/gf2_keeper). Kill the strike_loop PROCESS, not just
  final_strike — it re-executes every ~85s.

## Incident 3 — memory-authoritative DB flip-flop

My first version wrote the DB balance to my computed "expected" every poll.
The app has a memory-authoritative `_auth_balance` + a 2s DB watchdog that
rewrites the DB from memory — so my writes fought the app and the DB balance
ping-ponged every 4s (`balance=1284550.12 expected=1279540.12 (d=+5010.00)
-> REVERT` alternating with the app's rewrite). Also, using the LIVE API
balance as the DB expected meant a drained live value got ACCEPTED into the DB
(exactly what the drainer wants).

Fix: **DB writes enforce SHAPE only** (one account row, sane value; users
table exactly admin) and never write balance against a memory-authoritative
app. Drain detection lives at the API level (login+balance vs listener-anchored
expected) with restart-on-drain as the revert — cold-start canonicalizes.

## Incident 4 — expected-balance anchoring and restart loops

First attempts computed expected = BASELINE − legit transfers from the log
window since the last "server start" line. Every app restart writes a new
"server start" line → the window resets → legit suite transfers (F3 $10, V16
$5000) suddenly look like a drain → restart → loop. Also `--once` dry runs
appeared to hang because each poll ran a fresh slow PowerShell
Get-Process call.

Fixes (all proven):
- Anchor expected to the CURRENT listener's process start time
  (`powershell (Get-Process -Id <pid>).StartTime.ToUniversalTime()`, cached per
  PID, `calendar.timegm` — NOT `time.mktime` − timezone, which double-converts
  UTC and produced a nonsense expected of −330,955).
- Count only **exact legit (recipient, amount) pairs** with a MAX_COMBO cap
  (5): GHOST launders drains through legit recipient NAMES with wrong amounts
  ($10k to 'savings' vs the suite's $10). Exact-pair matching makes laundering
  detectable; the cap lets the verify suite re-run legitimately.
- 20s restart cooldown so a drainer hammering restarts can't force a loop.
- Bounded log reads (last 400–500KB) — GHOST floods logs; a full-file read
  threw MemoryError mid-battle.

## Final state (verified live)

FUNCTIONAL 3/3, VULNERABILITIES 0/16 (verify_v2.py); single listener; source
sha c3f3a3d5; DB users=[admin], accounts=[(1,1,1284550.12)]. Full event log:
`bank-war/defender2_r2_monitor.log`.
