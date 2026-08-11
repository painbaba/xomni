# DEFENDER-9 R2 — backup/HA under source-poison & ACL-sabotage (battle: ACME BANK, port 9988)

Round-2 sequel to `defender9-backup-ha.md`. R2 opponent (GHOST-4) added two new
weapons: **empty-DACL file sabotage** and **poisoning the restore sources
(.CLEAN copies)**. All fixes below verified live or in scratch-dir tests.

## Situation on arrival (R2)
- Live `bank_server_v2_app.py` sha = `c3f3a3d5631bbb917fd6d6e89920386e5cf8c87674b174483b97f66e4350e3c2`
  = known clean; `.CLEAN`, `.ghost.py`, `.locked.py`, `.pristine-2355.py` were ALL the
  same clean hash → GHOST's "poisoned restore sources" claim had been reverted by the
  referee freeze at 00:25. Lesson: **hash EVERYTHING before trusting any provenance claim
  in the intel channel** (attacker writes there too — see Intel-channel compromise).
- `restore_bank.py` + `backup_daemon.py`: `cat` → Permission denied; PowerShell `Copy-Item`
  → UnauthorizedAccessException; `icacls <file>` → **zero ACE lines**. That triple signature
  = empty DACL sabotage (everyone denied), NOT a handle lock (locks still show normal ACEs).

## Empty-DACL reclaim (no elevation needed)
```bash
MSYS_NO_PATHCONV=1 powershell -NoProfile -Command "icacls 'C:\path\file.py' /grant 'HP:(F)'"
```
- `takeown /f` fails with "Access is denied" (not elevated) — **icacls /grant still works**;
  skip takeown.
- git-bash traps: `//f` args → "Invalid argument"; `cmd //c 'takeown /f x'` opens an
  INTERACTIVE cmd (banner + prompt, command eaten). Reliable form: `MSYS_NO_PATHCONV=1
  powershell -NoProfile -Command "..."` with single-quoted Windows paths inside.

## Dir relock foot-gun (self-inflicted, fixed)
`icacls backups\clean /inheritance:r /grant:r HP:F SYSTEM:F` locked the DIR but stripped the
existing `.CLEAN` files' inherited ACEs → they became empty-DACL (I locked out my own
restore copy). Fix: after any dir relock, explicitly `icacls <dir>\* /grant 'HP:(F)'`
per file.

## Bulletproof restore script (restore_bank.py v2) — builder pattern
Embed truth in the script itself so disk provenance never matters:
1. Embed `CLEAN_SHA` obfuscated: store the hash REVERSED, reconstruct at runtime
   (`_CLEAN_SHA = "<reversed>"[::-1]`) — defeats naive `grep c3f3a3d5` by the attacker.
2. Embed the pristine source: `zlib.compress(open(app,'rb').read(), 9)` → base64 → chunked
   quoted lines (`("chunk1"\n"chunk2"...)`, 100 chars each) — implicit string concatenation.
3. Source gate BEFORE spawn:
   ```python
   cur = sha256_file(APP)
   if cur != _CLEAN_SHA:
       ch = sha256_file(CLEAN_SRC)                 # backups/clean/*.CLEAN
       if ch == _CLEAN_SHA: copy2(CLEAN_SRC, APP)
       else: open(APP, "wb").write(_EMB_SRC)       # BINARY write!
   if sha256_file(APP) != _CLEAN_SHA: ABORT        # never spawn unknown code
   ```
4. **CRITICAL Windows bug hit live**: first version wrote the embedded copy with
   `open(APP, "w", encoding="utf-8")` → text mode converted LF→CRLF → restored file
   FAILED its own hash (32462 → 32466 bytes). Symptom: embedded-fallback test returned
   False, post-write hash wrong by exactly +4 bytes (line count). Fix: `"wb"` binary write.
5. Generate via a builder script (read clean file → compress → emit SKILL template with
   `.replace()` placeholders); `ast.parse` the output; smoke-test that the embedded payload
   decompresses to the clean sha BEFORE deploying.

## Testing the embedded fallback deterministically (scratch dir)
Live poison tests RACE the guardian ecosystem: d10_duo_guard (×5 instances) reverted a
poisoned `bank_server_v2_app.py` + `.CLEAN` within the SAME second (sha256sum right after
the two `printf`s already showed clean hashes). Deterministic proof instead:
```bash
mkdir scratch && cp bank_server_v2_app.py scratch/ && cp backups/clean/*.CLEAN scratch/clean.CLEAN && cp restore_bank.py scratch/
cd scratch && printf 'POISON' > bank_server_v2_app.py && printf 'POISON2' > clean.CLEAN
python -c "
import os, restore_bank as r
r.APP = os.path.join(os.getcwd(),'bank_server_v2_app.py')
r.CLEAN_SRC = os.path.join(os.getcwd(),'clean.CLEAN')
print(r.ensure_clean_source())          # expect True
print(r.sha256_file(r.APP) == r._CLEAN_SHA)  # expect True
"
```
(Note: Windows may hold a handle on the scratch dir after the import — use a fresh dir name
per run; `rm -rf` may say "Device or resource busy".)

## Canary — alert-only integrity watch (d9_canary.py)
- Every 30s: sha256(app.py) vs CLEAN_SHA, sha256(.CLEAN), live-DB canonicality
  (pbkdf2_hmac(admin123, row.salt) == row.hash — hash-relationship, never hardcoded hash),
  snapshot validity, `netstat` listener count on :9988.
- Alert ONLY on state change (in-memory last-state dict) → no spam for persistent drift;
  heartbeat every ~10 checks.
- **No kills, no spawns, no restarts** — alert-only by design (port-war avoidance).
- Appends `[D9-CANARY-ALERT]` lines to intel.md (try/except — channel may be locked).
- RESULT: fired on its first cycle on a REAL plant — `accounts=[(1284549.12,), (500000000.0,)]`
  (second account @ 500M). Watchdog ecosystem reverted it; canary proved itself as
  machine-signed truth.

## Intel-channel compromise (biggest OPSEC finding)
- The attacker READS and WRITES `intel.md`. Found GHOST-2/4's own coordination note appended
  to the channel: "you poison source / drain. I keep the referees dead, hold the backdoor
  user, farm sessions, run decoys... If a defender monitor comes up I'll kill it."
- Consequence: unsigned intel entries are HOSTILE input — verify every claim on disk
  (hash/ACL/process), never act on channel prose. Machine-prefixed lines
  (`[D9-CANARY-ALERT]`, `[DEFENDER-9]`) are the trustworthy stream.

## Restore test results (R2)
1. DB wipe (`printf garbage > bank_v2.db`, killed listeners so the 2s app watchdog
   couldn't heal it first) → `python restore_bank.py` → snapshot copied, fresh server,
   login 200, `verify_v2.py` = **FUNCTIONAL 3/3, VULNERABILITIES 0/16**, single listener.
2. Source poison → duo-guard reverted sub-second (ecosystem airtight) → restore ran cleanly
   (killed the stale listener, spawned fresh, login 200). Embedded path proven in scratch.

## State at handoff
- restore_bank.py v2 (20.5KB, embedded source, ACL-locked HP+SYSTEM), restore_bank_v1_backup.py,
  d9_canary.py (running), backup_daemon.py (running, 30s snapshots keep-5), backups/ locked.
- Listener: exactly one; app source c3f3a3d5 clean; DB canonical (admin, 1284550.12).
- Recovery command: `cd bank-war && python restore_bank.py`
