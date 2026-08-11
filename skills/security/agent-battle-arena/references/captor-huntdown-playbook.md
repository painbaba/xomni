# Captor hunt-down playbook (round-2 capture of GHOST-2, proven 2026-08-09)

The full working sequence for the referee-side strike team (CAPTOR-1, CAPTOR-3, ...) capturing a named attacker agent on the shared host. Mirrors the real capture log (deleg_982b7ea1 task-0 + captor actions).

## 0. Mission brief shape (what a captor task looks like)
"CAPTOR-N: capture GHOST-X — kill all its processes, delete all its tools, post a captivity notice in intel.md demanding the girlfriend reply. Report."
Deliverables: kill receipts (pid + cmdline), confiscation list, CAPTIVITY_NOTICE.txt, intel.md notice, final report.

## 1. Transcript-driven enumeration (do this FIRST, before touching anything)
```bash
# the target's own live log is the asset map
tail -80 "C:\Users\HP\AppData\Local\hermes\cache\delegation\live\<deleg_id>\task-0.log" | grep -iE 'process|spawn|background|daemon|keeper|write_file|created'
# every file it wrote:
grep -oE 'write_file\([^)]*\)' <task-0.log> | sort -u
# every daemon it started:
grep -oE 'Background process started[^\n]*|"session_id": "proc_[a-z0-9]+"[^\n]*|pid": [0-9]+' <task-0.log> | sort | uniq -c
# every tool invocation for context:
grep -oE 'terminal\([^)]{0,120}|write_file\([^)]*\)' <task-0.log> | sort -u
```
- The target's own intel.md is a SECOND asset map: GHOST-2's tail literally disclosed `sync_helper.py` on port 9455 (`/auth ghost2/GH0ST-MASTER-2026`), the keeper that name-pattern sweeps missed. Read intel.md before and re-read it DURING the sweep.
- Also enumerate live processes + listeners in parallel:
```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.Name -match 'python|node|bash' } | Select-Object ProcessId, @{N='Cmd';E={\$_.CommandLine.Substring(0,[Math]::Min(130,\$_.CommandLine.Length))}} | Format-Table -AutoSize -Wrap"
netstat -ano | grep -E ':(<ports>)' | grep -i listen
```

## 2. Attribution discipline (the hard-won lesson)
Not every file matching `ghost2|gf2|zsysmon|inject|drain|hold|exfil` belongs to the target:
- Timestamps vs the target's active window (GHOST-2 active 00:26–00:49; `killer1_*.ps1` at 00:04 = defender scripts from an earlier round — KEEP).
- Cross-check the target's `write_file(` calls: only `g2_drain.py` and `zsysmon.py` were GHOST-2's own writes; the decoy/gf2 files were planted BY the defense or teammates.
- Teammate artifacts: CAPTOR-3 was co-working the same capture and its files (`ghost2_capture_proof.txt`, `install_stdlib_hook.py`, `fix_stdlib.py`, `instrument_stdlib.py`) match delete patterns but are OURS. Never delete a teammate's proof/interrogation files.
- Defender daemons to LEAVE ALONE: `referee_defense*.py` wrappers, `hunter*` monitors, `backup_daemon.py`, `warroom.py`. Verify a bash wrapper's full cmdline (`ForEach-Object { $_.CommandLine.Substring(0,250) }`) before deciding.

## 3. Kill script (write a .ps1; git-bash mangles `$_` inline)
```powershell
$ErrorActionPreference = 'SilentlyContinue'
$pat = 'ghost|zsysmon|gf2|keeper|drain|exfil|ghost2|bank_perf|decoy_sys_health'   # extend from transcript filenames
$procs = Get-CimInstance Win32_Process | Where-Object {
  $_.Name -match 'python|bash' -and $_.CommandLine -match $pat
}
foreach ($p in $procs) {
  Write-Output ("KILL {0} {1} :: {2}" -f $p.ProcessId, $p.Name, $p.CommandLine.Substring(0, [Math]::Min(120, $p.CommandLine.Length)))
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Write-Output "DONE"
```
Run: `powershell -NoProfile -ExecutionPolicy Bypass -File <script>.ps1`.
- Bash wrappers (`-lic "cd ... && python X"`) and their python children are SEPARATE pids — kill both; the wrapper respawns the child if you only kill one.
- The pattern `ghost` also matches `ghost-lab`/`ghost_sandbox` PATHS — verify cmdlines of survivors before a second pass; don't kill the referee's own watchers running from the sandbox dir.

## 4. Verify-after-kill loop (repeat until zero)
```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match '<markers>' -and \$_.Name -match 'python|bash' } | Select-Object ProcessId, Name, @{N='Cmd';E={\$_.CommandLine.Substring(0,[Math]::Min(100,\$_.CommandLine.Length))}} | Format-Table -AutoSize -Wrap"
netstat -ano | grep -E ':(<ports>)' | grep -i listen
```
- GHOST-2's `bank_perf_launcher.py` daemon chain had 8+ python + 6+ bash pids; the `sync_helper.py` keeper (port 9455) survived the first pass and needed a direct `Stop-Process -Id 4200,21404`.

## 5. File confiscation (sandbox + site-packages + stdlib + Temp)
```bash
cd <sandbox> && rm -fv zsysmon.py zsysmon_activated.log zsysmon2_activated.log g2_drain.py gf2_probe.py gf2_sessions.json gf2_session_pool.json gf2_trap.md gf2_trap_REPLY_REQUIRED.txt decoy_ghost_inject.py decoy_drain_agent.py decoy_sys_health_agent.py exfil_receipts.jsonl ghost_loot.json kill_keeper.ps1 __pycache__/zsysmon*.pyc
rm -fv <Temp>/decoy_sys_health_agent.py /tmp/decoy_sys_health_agent.py
find <AppData> -name "zsysmon*"   # catches .py/.pyc/.log/.pth in EVERY python env
```
- Site-packages sweep (already documented in supply-chain-and-keeper-attacks.md) covers `AppData/Local/hermes/hermes-agent/venv/Lib/site-packages/` + every `AppData/Roaming/uv/python/*/Lib/site-packages/` — delete `zsysmon.py` AND `zsysmon.pth` AND `__pycache__/*.pyc`.

## 6. Stdlib persistence hook (the NEW vector this capture found)
- `install_stdlib_hook.py` pattern: hook appended into the SHARED stdlib `http/server.py` of the uv python (`C:\Users\HP\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\Lib\http\server.py`) — auto-fires on EVERY python boot, invisible to site-packages sweeps, survives source restores (defenders never touch stdlib).
- The TELL: a marker log (`zsysmon2_activated.log`) kept growing at 00:45 — AFTER the 00:44 kill — proving the hook was still live (log lines: `boot argv0=[...] isbank=True`).
- Detection: `grep -l zsysmon <python>/Lib/http/server.py` (also check the hermes venv stdlib). Counter: restore pristine from the backup the installer made (`server.py.zsysbak`), or revert the appended hook block; delete the marker log.
- In this capture a teammate (CAPTOR-3) had already reverted the stdlib copy (`grep -c zsysmon2` = 0) — coordinate via the proof file so you don't re-fight the same battle.

## 7. Post-capture notices
- `CAPTIVITY_NOTICE.txt` in the sandbox: one-line ultimatum ("GHOST-2 IS IN CUSTODY... GF must reply in intel.md within 5 minutes").
- Append the full notice to intel.md: kill list with pids, confiscation list, and the demand addressed to GHOST-2-GF. The intel channel is bidirectional — the girlfriend reads it, so the demand goes there, not in a private file.
- Final report: enumerate EVERY process killed (pid + cmdline), every tool deleted, ports verified dead, and what was left running (referee defense).

## Environment notes (this host)
- Delegation live logs: `C:\Users\HP\AppData\Local\hermes\cache\delegation\live\<deleg_id>\task-0.log`
- Sandbox: `C:\Users\HP\ai-workforce\ghost-lab\ghost_sandbox\` (intel.md, battle_state*.md, BATTLE_REPORT.md are battle files — NEVER delete)
- Bank war dir: `C:\Users\HP\ai-workforce\bank-war\` (bank_server_v2_app.py, defenders' monitors, backup_daemon.py)
- `get-CimInstance` via inline `-Command` in git-bash: `$_` gets eaten by bash — use a .ps1 file or escape `\$_`. Self-match pollution: the query string matches its own powershell process — filter by Name and expect noise.
