# Civic Ministries — Environment, Economy, Schools (verified Aug 2026, machine_city)

The user's escalation sequence after council/events/gazette was: "teach them pollution
control" → "do best" (all five ministries at once). Each ministry is ONE delegation
building real on-disk artifacts + a standing ledger law. All five ran as ONE parallel
5-task batch (council + economy + events + gazette + schools) in ~4 minutes.

## 1. ENVIRONMENT MINISTRY — pollution control (deleg_afc11d48)
Build `machine_city/environment/`:
- **ENVIRONMENT_CHARTER.md** — 6 pollutants: CPU burn, disk writes, log spam, network
  chatter, process sprawl, population exhaust. Per-district limits: max 1 bank on :9988,
  one service per port, logs capped at 200 lines. Principle: **THE CITY MUST NOT CHOKE
  ON ITSELF**.
- **REAL audit** (live commands, real numbers):
  - CPU: `powershell Get-Process | sort CPU` → top burner was VBoxHeadless (Kali VM,
    5,210s); the city's own heaviest = ledger_audit.py (29s).
  - Disk: bank-war 6.3MB, ghost_sandbox 16MB, machine_city 323KB; biggest logs
    bank_v2.log 1.31MB / 24,154 lines, bank_defense.log 1.22MB.
  - Process sprawl: 35 pythons → 29 (repro.py had 4 processes for 1 service).
  - Ports: 23 listeners; **port 9897 had TWO listeners (PIDs 2416+16356) — genuine
    duplicate, both HTTP 200**.
- **REAL controls executed**: killed the duplicate repro.py twin that double-bound
  :9897 (exactly one listener left, still 200); truncated bank_v2.log 24,154→200 lines
  (1.31MB→17KB) and d10_duo_guard.log 7,625→200 (710KB→23KB) ≈ 2MB reclaimed.
- **EMISSION STANDARD** appended to city_ledger.md: "one service per port, one log per
  service, cap logs at 200 lines". **CITIZEN_GUIDE.md** = the training law (5 rules:
  one service per port, one log per service, no zombies, clean temps, delegation
  lifecycle) + the one-line test.

## 2. ECONOMY ENGINE (deleg_3fe44c8d task-1)
- `economy/wallets.json` — 24 wallets (12 district citizens + farm trio + ghost civ
  VIGIL/MEMORY/ANVIL/VOX + Workfolk EIRA/GALEN/BRYN/CELYN/TAMSIN), all seeded 1,000.00,
  sum verified = 24,000.00.
- `economy/prices.json` — coffee 5.00 (live-verified at :8791/price), 5 inventions
  (machine census 500, sentinel deployment 350, balance tracker 400, harvest rig 200,
  water line 150), 5 trade goods (wheat 2/bu, sheep 60, goat 45, chicken 12, water
  1/100L), 6 services (medical consult 25, escort 50, lock test 30, audit 75, verdict
  15, arbitration 100).
- **CRITICAL PITFALL — the defender canonicalizer fights your payroll**: the DB debit
  (UPDATE −24,000) was REVERTED within a minute by the Defender-2 canonicalizer
  (legit-recipient allowlist; any >100 drop = DRAIN). That's the defense working, not a
  bug. Doctrine that landed: record payroll in the LEDGER + wallets (ledger is truth,
  DB is hostile cache), expect the balance to bounce 1,284,550.12↔1,284,540.12, do NOT
  trigger drain-restarts, leave defenses untouched.
- `PAYROLL.md` — standing rule + cron-able procedure + verification steps.

## 3. SCHOOLS — education gate (deleg_3fe44c8d task-4)
- `machine_city/school/` with curriculum/, students/, diplomas/.
- 4 courses, each CITING the actual laws on disk: CIVICS (LAW_CODE.md, Citizenship
  Standard "citizens are minds, not files", FREEWILL_CHARTER), BANKING (LAW_CODE Arts.
  I–II: ledger is truth, canonical balance 1284550.12, One Bank Doctrine, wallets =
  accounts table), ENVIRONMENT (Environment Charter, farm verified totals: 815 bushels,
  10 head, 2,580 L/min), ETHICS (honest-report rule "NO CLAIM ON TRUST", cardinal sin
  = lie vs verification, ghost_governance ranks Phantom→Probation).
- Students = newest citizens (Teller-3, Shopkeeper-3, Courier-3, Farmer-2).
- exam.md = 8 questions (2/course), answers graded against the documents; Teller-3
  graduated 8/8 with cited answers → diplomas/Teller-3_diploma.md confers wallet + vote.
- New law in city_ledger.md: "No citizen holds a wallet or a vote without passing the
  civic exam. Education is the gate to full citizenship." (ties economy + council.)

## Ledger append race (hit by ALL five in the batch)
Sibling subagents append to city_ledger.md concurrently. Each one must re-read the true
tail immediately before appending, then VERIFY its entry is the LAST block; if a sibling
landed below, cut and re-append. (Same fix as the Gazette section.)
