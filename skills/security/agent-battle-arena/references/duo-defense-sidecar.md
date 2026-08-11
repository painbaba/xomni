# Round-2 duo-defense sidecar (D10): d10_duo_guard.py — full battle detail

Session: DEFENDER-10 round 2 vs GHOST-2 + girlfriend (both spawn-capable), ACME BANK 127.0.0.1:9988, clean build `bank_server_v2_app.py` pinned to sha c3f3a3d5 (hunter1/referee freeze every 3-5s). All techniques below verified live or by test battery.

## Why a sidecar and not a patch
The referee freeze (hunter1_tail.sh, 5s loop) reverts `bank_server_v2_app.py` to c3f3a3d5 whenever it differs, so ANY in-app patch is reverted within seconds. Ship defense as a separate daemon. Corollary discovered mid-battle: hunter1 restores FROM `bank_server_v2_app.locked.py` — poison locked.py and the protector silently stops protecting. Vault `C:\Users\HP\.d10vault\bank_server_v2_app.CLEAN.v2` (outside the lab tree) and restore app.py/locked.py/.CLEAN/pristine-2355/ghost.py from it. Live save: the duo poisoned `backups/clean/*.CLEAN` at 00:42 — guard restored it from the vault <3s.

## Guard architecture (1.5s loop, pure stdlib)
1. source_check: sha-verify 5 watched files (app.py, locked.py, .CLEAN, pristine-2355, ghost.py) → restore from vault/locked.py; delete plant artifacts (ghost_balance.txt, sys_health_agent.py*); sweep BOTH interpreters' site-packages for `.pth` outside a whitelist (GHOST-2's declared .pth-hook play; deleted real ztest.pth + test evil_pwn.pth <3s).
2. db_check: users == exactly [(1,'admin',CANON_HASH,CANON_SALT_HEX)] where CANON_SALT_HEX = sha256("acme-bank-v2-canonical-salt:admin123")[:32], CANON_HASH = pbkdf2(admin123, salt, 200k).hex() (DETERMINISTIC — all instances agree; the duo's replant loop appending hex to the salt lost the war). Accounts == exactly ONE row (id=1,user_id=1) — preserve the balance VALUE on row-set repair (D2/D9/referee own the balance pin). Planted transfer rows (>60s old, no matching `transfer ok` log line) deleted.
3. Ledger: anchor `expected` to the log's LAST `new_balance=` at startup, cursor jumps to EOF (summing the whole battle log drives expected negative — saw -1,606,179). New `transfer ok` lines decrement. Reseed = fresh `server start` line AND salt change AND balance≈BASELINE; otherwise a salt change is a tamper → canonicalize salt, keep ledger.
4. listener_check (D10_NO_SPAWN=1 mode): NO kill/spawn ever (D1/D2/hunter1 own lifecycle — the round-1 port-war lesson). Alerts on /ghost response, balance-oracle mismatch (>$200k), duplicate listeners.
5. drain_check: >25 `transfer ok`/60s → ESCALATE alert (duo hit 387/min); phantom-drain = logged new_balance > ledger + $100k.
6. proc_check (every ~6s, PowerShell full cmdlines): basename-only ATTACK_MARKERS match (sys_health|gf2|hold|drain|inject|massdrain|exfil|...), DEFENDER_EXEMPT incl. ghost_sandbox/ghost-lab (path-based matching false-kills defenders running from the sandbox dir). Killed gf2_keeper + sys_health daemons. Transcript-readers → SRC_READ flag only.
7. companion_check: ≥2 of {SRC_HTTP, SRC_DB, SRC_FS, SRC_PROC, SRC_READ} active within 15s → DUO-ALERT (once/60s) to bank_defense.log + intel.md. Fired live: 3 sources at 00:47.
8. Balance = ALERT-ONLY (BAL_FIX_TOL = $100k): my original log-ledger balance pin fought D9's baseline pin (guard rewrote DB to the duo's drained 0.01 "because the log said so") — the ONE-OWNER-PER-STATE-VARIABLE rule. Never write a value another defender owns.

## Keeper (d10_guard_keep.sh) — the storm post-mortem
Three sequential bugs produced a 42-process guard storm and "guards die within seconds":
1. wmic truncates CommandLine at 80 chars → `grep -c "d10_duo_guard.py"` returned 0 for live guards (script basename + PID sit past char 80) → keeper respawned forever. Also: duplicate-kill parsed the truncated fragment's trailing digits as a "PID".
2. `tasklist //FI "PID eq X"` errors in git-bash → liveness check always failed → keeper taskkilled the LIVE guard (read stale PID from pid file) then respawned → kill/respawn loop.
3. `python /c/Users/.../guard.py` from bash → MSYS double-converts to `C:\c\Users\...` → "can't open file" (native python). Use `C:/Users/.../script.py`.
Final keeper: heartbeat freshness (stat -c %Y, <45s) as the ONLY liveness signal; NEVER taskkill on a fallible check; guard startup lock-file (write os.getpid(), exit if holder alive) so keeper storms converge to one instance. Note: editing a RUNNING bash script doesn't apply (bash re-reads incrementally) — restart keepers after edits.

## Test battery (all PASS)
- Source tamper (wrote garbage over app.py) → restored to c3f3a3d5 within 6s.
- DB plant (gf2_babe user + 999,999,999.99 + account row 77) → users canonicalized <2s, backdoor login impossible.
- Attacker process (sys_health_agent.py basename) → process killed + file deleted.
- .pth hook (evil_pwn.pth in uv site-packages) → deleted <3s.
- Companion alert: plant + artifact + drain burst → DUO-ALERT fired.
- Contract: verify_v2.py 3/3 F, 0/16 V — twice, mid-battle (first F3 fail was the duo's active drain-to-0.01 window, not a code fault; re-ran in a healthy window).

## Attack timeline observed (live, for the ledger)
00:33 gf2_babe user plant → reverted (first canonicalization). 00:36 ztest.pth real plant → deleted. 00:38 gf2_keeper daemon → killed. 00:39-00:40 guard bug storm (keeper respawns; NOT attacker). 00:40 balance drained to 0.01 via API (legit-looking receipts); D2 DRAIN-DETECTED restart-loop. 00:42 backups/clean/*.CLEAN poisoned → vault-restored. 00:45 499,990,000.00 balance plant + 387 transfers/60s drain → PHANTOM-DRAIN + ESCALATE alerts; D2 revert-to-baseline holds. 00:46-00:52 admin hash/salt replant loop every ~2s → canonicalized every 1.5s (watchdog war won).

## Files shipped
bank-war/d10_duo_guard.py · d10_guard_keep.sh · kill_duo_zombies.ps1 (PowerShell full-cmdline kill of guard/keeper storms — git-bash mangles `$_` inline, write a .ps1) · d10_test_plant.py (plant simulator) · C:\Users\HP\.d10vault\ (private clean-source vault).
