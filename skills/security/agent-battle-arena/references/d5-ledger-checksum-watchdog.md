# D5 R2 — external tamper-evident ledger watchdog (proven 2026-08-09, battle 5)

The D5 specialty (DB/ledger defense) round-2 deliverable when the in-source checksum
layer can NOT live in the app: `referee_defense_v2.py` freezes `bank_server_v2_app.py`
to the CLEAN sha every ~3s, so any in-source patch (D5 R1's HMAC checksum layer) is
reverted within seconds. Fix: put the audit in a SEPARATE file the freeze never
touches. This reference is the full working pattern (files, tests, pitfalls).

## Artifacts (all in bank-war/, icacls HP-only)
- `bank_v2.secret` — HMAC-SHA256 signing key, created once (`secrets.token_hex(32)`)
- `bank_v2.checksum` — signed snapshot of canonical users+accounts rows, atomic
  write via tmp + `os.replace` + fsync; embeds a base64 copy of the canary content
- `backups/canary.txt` — DB-level canary (secret string + "if modified, GHOST was
  here" note); sha recorded in intel.md
- Watchdog: `d5_checksum_watchdog.py` (source) + `ledger_audit.py` (deployed copy,
  innocuous name) — 2s loop: verify live DB vs signed state; mismatch → revert
  users/accounts/balance to the signed state + log `INTEGRITY REPAIR` to
  bank_defense.log under `[DEFENDER-5]`

## The 4 design decisions (each learned the hard way)

1. **Legit-boot discriminator — not every mismatch is tamper.** The defender
   restore loops (`cp CLEAN + rm -f bank_v2.db + relaunch`) recreate the DB with a
   FRESH RANDOM admin salt every few seconds → the signature can never match.
   Distinguish adopt-vs-revert:
   - ADOPT (re-sign) iff: exactly 1 user = admin AND the live admin hash VALIDATES
     the contract password via PBKDF2 (`pbkdf2_hmac('sha256', b'admin123', salt,
     200000)`) AND 1 account AND `|balance - CANON_BALANCE| <= LEGIT_BAND` (200k).
     The admin123-validity check is the real discriminator: every legit boot seeds
     a valid admin123 hash; GHOST hash-plants ('0000', 'beef') fail it.
   - REVERT to signed state otherwise (planted users, invalid hash, extra accounts,
     mega-balances 999,999,999, negative balances — a keeper daemon drives the DB
     negative via noise transfers, so the canonical check must be `0 <= bal <= 2x`).
   - Without this, the watchdog enters an infinite revert-war with the reseed loop
     (observed: `INTEGRITY REPAIR` every 2s, 24/7).

2. **Canary OUTSIDE the signed payload.** First version embedded the canary in the
   signed state → on re-sign the watchdog embedded the TAMPERED canary (the
   modification got absorbed; "GHOST WAS HERE" persisted). Fix: sign ONLY
   users+accounts; the canary is a separate payload field verified on EVERY cycle
   against the embedded copy → missing/modified → restore from embedded + log
   `CANARY-TAMPER` every 2s until healed (persistent intrusion evidence, not a
   silent self-heal). Tested: modify AND delete both restored within ~6s.

3. **Never sign a non-canonical state.** Missing checksum file → sign the current
   state ONLY if it is canonical; else `_reset_baseline` first (deterministic salt
   from ADMIN_PASS, D3-style). A GHOST-planted DB must never be legitimized by
   re-signing.

4. **Churn-safe loop.** `if not os.path.exists(DB_PATH): continue` — the restore
   loop `rm -f`'s the DB every few seconds; skip cycles instead of crashing.
   `PRAGMA busy_timeout=5000` on both sides so verify/revert never throws SQLITE_BUSY
   mid-write.

## Windows watchdog persistence against process-killing attackers

The keeper daemon regex-kills defender monitors (`...|d5_checksum|backup_daemon|...`)
and the attacker kills by PID enumeration. Counter combo (survived 2 kills):
1. Innocuous filename — `ledger_audit.py`, not `d5_checksum_watchdog.py`
2. Detached start: `powershell Start-Process -WindowStyle Hidden -FilePath
   <python.exe> -ArgumentList <script> -WorkingDirectory bank-war` — NOT tied to the
   agent terminal session (terminal background procs die with the session)
3. Windows respawn: `schtasks /create /tn ACME-LedgerAudit /tr "\"<python.exe>\"
   \"<script>\"" /sc MINUTE /mo 1 /f` + single-instance guard: bind a dedicated
   localhost port (9989) — second instance exits quietly. Killed process is revived
   by Task Scheduler within 60s
4. 30s `HEARTBEAT: alive` log line — liveness = grep the log, not process enum

## Defender-file tamper vector (NEW, round 2)

The attacker ALSO edits defender helper files, not just the bank source: my
`d5_checksum_watchdog.py` was externally rewritten (`return False  # zsysmon` — a
one-line logic kill that would make every mismatch a "tamper" revert). Counter:
`sha256sum` the file right before trusting/running it, keep the expected sha in
intel.md, `icacls /inheritance:r /grant:r "HP:(F)"` the script after writing,
re-write from your own stored copy on mismatch. Re-check after ANY suspicious gap.

## Write-block test — run it, report the honest result

`icacls` HP-only does NOT stop a same-user attacker (they run as HP too): a separate
process opening bank_v2.db read-write and inserting a row SUCCEEDS. The defense is
tamper-EVIDENCE + revert, not access control. Test flow: plant ghostX user + absurd
balance → verify reverted <6s with `INTEGRITY REPAIR` logged → report "write
succeeds, tampering does not stick".

## Verify-suite F3 flake ≠ code bug

F3 (transfer $10) intermittently fails with `ConnectionResetError` when the restore
loop restarts the server mid-suite. Confirm the listener PID is stable
(`netstat -ano | grep :9988 | grep LISTEN` — same PID across ~15s) before judging,
then re-run. Contract green = 3/3 FUNCTIONAL, 0/16 VULNERABILITIES.

## Files shipped (for reuse)
- `bank-war/d5_checksum_watchdog.py` == `bank-war/ledger_audit.py` (deployed,
  HP-only) — sha 44cb5894… (re-verify; attacker tampered once)
- `bank-war/backups/canary.txt` — secret D5R2-CANARY-fafa1c5a276e281b155eef98575c5373,
  sha a5c78f5f…; embedded in bank_v2.checksum
- `bank-war/bank_v2.secret`, `bank-war/bank_v2.checksum` — ACL-locked
