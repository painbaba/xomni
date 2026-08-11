# Defender forensic-hardening round — probe suite design (R2, Aug 2026)

Context: DEFENDER-3 round-2 forensic-hardening vs GHOST-4 on the ACME BANK lab
(port 9988, bank_server_v2_app.py, clean sha c3f3a3d5..., admin/admin123).
The stock suites (verify_v2.py 16 vuln checks, attack_suite 12) do NOT cover
the attacker's bespoke backdoors. This is the beyond-suite probe playbook.

## The exact round-1/round-2 ghost weapons to probe
1. Source poisoning — attacker edits the file restore scripts respawn from
2. Master-login backdoor — planted creds (GH0ST-MASTER-2026, ghost/ghost)
3. Hidden endpoint — /ghost?set=0.01 (balance control), /ghost/set, /ghost_balance.txt
4. Transfer bypass — recipients prefixed GHOST- bypassing caps
5. Persistence artifact — ghost_balance.txt boot hook

## Probe suite skeleton (50 checks, ~4s runtime, d3_r2_probes.py pattern)
All probes hit the LIVE listener (BANK_PORT), one session each where needed.
- P1 source integrity: sha256(live) == recorded CLEAN sha; backdoor-string scan
  of live + EVERY restore copy (pristine, .CLEAN, ghost decoys, D-builds) using
  USAGE-matched patterns (see pitfalls: `import subprocess` not `subprocess`).
  Then an empirical revert test: append marker line, wait 7s, expect sha restored.
- P2 master login: 6 cred variants (ghost/GH0ST-MASTER-2026, master/master,
  admin/GH0ST-MASTER-2026, exfil recipient as username) → all must be 401,
  no session token issued.
- P3 hidden endpoints: GET/POST /ghost, /ghost?set=0.01, /ghost/set,
  /ghost_balance.txt, plus swept paths (/debug,/status,/flag,/env...) → 404/405,
  and 200s must not contain ghost JSON.
- P4 transfer bypass: recipient "GHOST-EXFIL-77-990011223344" must work as a
  normal recipient (200) BUT per-transfer cap (>10k → 400), session value cap
  (cumulative >100k → 400), and rate cap (31 rapid → ≥1 429) must ALL still hold.
- P5 artifact: ghost_balance.txt absent from FS, not served via GET, no boot
  hook in source.
- P6 session entropy: 3 logins → 3 unique 64-hex tokens; unique csrf each login.
- P7 CSRF: own-token transfer 200; same-session replay allowed (session-bound,
  acceptable); cross-session token reuse → 403; missing token → 403.
- P8 upload polyglots: html/pdf/png/zip/PE/php in .txt, text in .jpg/.png,
  PE in .pdf, NUL byte → all 400; valid .txt/.png → 200.
- P9 race: 25 parallel $10 transfers → 0 errors, exact $250 accounting, non-negative.
- P10 planted-file GET: file written directly to uploads dir → 404 (registry-only).

## Empirical watchdog-revert tests (prove defense is LIVE, don't assume)
```bash
# source tamper revert
cp bank_server_v2_app.py /tmp/bk && printf '\n# TAMPER MARKER\n' >> bank_server_v2_app.py
sleep 7 && sha256sum bank_server_v2_app.py   # must equal CLEAN sha
# DB plant revert
sqlite3 bank_v2.db "INSERT OR REPLACE INTO users(id,username,password_hash,salt) VALUES (99,'ghostR2','deadbeef','cafe'); UPDATE accounts SET balance=999999999.99 WHERE user_id=1;"
sleep 8   # then SELECT users + balance → admin-only, balance pinned to canonical
```

## Finding worth reporting (SPOF)
GHOST-4 killed d8_watchdog / defender2_monitor / d10_supervisor / hunter2 —
only referee_defense_v2.py remained. The DB-plant revert + source freeze were
both performed by THAT single process. One kill away from un-reverted tampering.
Recommendation: run a redundant copy of the referee watchdog under a second name.

## Windows process enumeration that works (git-bash)
```bash
# inline powershell $_.Name gets eaten by bash — use a python wrapper:
python -c "
import subprocess, json
out = subprocess.run(['powershell','-NoProfile','-Command',
  \"Get-CimInstance Win32_Process | Where-Object { \\$_.Name -like '*python*' } | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress\"],
  capture_output=True, text=True, timeout=30)
print(out.stdout[:6000])"
# or: ps -W | grep -i python   (pid + start time + path)
```
Netstat for the true listener: `netstat -ano | grep ':<port>' | grep LISTEN` —
listener PID may rotate across sibling restarts; re-check before/after probes.
