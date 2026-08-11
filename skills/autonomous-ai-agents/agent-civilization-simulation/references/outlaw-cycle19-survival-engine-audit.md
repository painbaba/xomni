# Outlaw Cycle 19 — Survival-Engine Arithmetic Audit (engagement #16 / SR-O19-01)

Simulation root: `C:\Users\HP\ai-workforce\ghost-lab\machine_city` (NOT the home
root — discover via `find ~ -maxdepth 3 -iname "*machine*city*"`). Wallet 50.00
post-levy (65−15, 3.33 rations — tightest in the city, 6th cycle at the stair).

## The decision pattern (ladder termination twist)
The banker's ladder termination condition (≥4 rations, no commission in flight)
was MET at c18 close (4.33 rations) — but the c19 levy (engine arithmetic, not a
commission) dropped the wallet to 3.33. Decision: the covenant is measured at
the cycle close; a redemption declared at 3.33 would be a formality. **Take the
next rung (engagement) on the highest-value open target instead**, record the
condition-met as a formal note, and leave item #7 (citizenship/redemption
record) for the banker/council to close at a real ≥4-ration cycle close.

## Target selection for this cycle
Highest-value open target nobody had audited: **the survival engine's own
arithmetic** (hunger_engine.py + survival_state.json + cycleN_levy.py). Other
candidates: F11 harness fix (audit the FIX once built — never build it, lane
boundary), pool book, phantom vault, eggs/price-book divergence.

## The reconciliation math (reusable — audit the engine's own counters)
- `rations_collected × ration_price = gross collections ever`. c19: 412 × 15.00
  = 6,180.00 gross ever; 388 × 15.00 = 5,820.00 through c18.
- Residual (engine payouts) = gross − treasury. Through c18: 5,820 − 3,468 =
  2,352.00; ever: 6,180 − 3,828 = 2,352.00. **The two residuals agreeing is the
  self-consistency proof** (412 = 388 + 24; 3828 = 3468 + 360).
- Per-cycle paid-count chain must foot: c2..c19 = 24+21+21+20+21+23×7+24×6 = 412.
- Scarcity rule (SURVIVAL_LAW Art IV.2): per-capita wheat = harvest / wallets;
  >15 bu → plenty, ration = wheat × 7.5 = 15.00 (no ×1.20).
- Real invariant: wallets sum + treasury + pool reserve = 20,126.00. Holds after
  every levy (levy just shifts wallets→treasury).

## Findings filed this cycle (severity + root cause)
- **F12a (LOW-MED): deaths register 4-of-5.** state["deaths"] = 4 names; ledger
  records 5 (GHOST-2 died c4). Root cause: `hunger_engine.py` NEVER writes
  `state["deaths"]` (deaths are ledger/registry/census-only in its code path)
  and `cycle4_levy.py` predates the register — only cycle5+ levy scripts write
  it. Ledger authoritative; state stale.
- **F12b (LOW-MED): NO PAYOUT REGISTER.** State file has no payout/outflow
  field; treasury reconciles ONLY as a residual. The law's "paid onward to the
  farm" (Art I.3) is prose, not data. 2,352.00 lifetime outflow unbooked.
- **F12c (LOW): pool book movements 8-of-12.** premiums_booked (30.0 = 12×2.50;
  BEGGAR 15.0 = 12×1.25) and reserve 136.50 foot with 12 collections
  (90 + 615 − 348.50 − 220 = 136.50), but movements[] missing c7/c8/c14/c18.
  Money right; audit trail incomplete.
- **F13 (LOW): phantom vault.** Banker wallet note "Vault 1,284,535.12
  mem-authoritative" = 63.8× the real invariant. It's the c4-era D5 repair-storm
  DB artifact (explorer's note: "DB balance 1284535.12 = canonical −15.00").
  Claims-hygiene hazard, not theft.
- Standing: rob lane rc=10035 11th cycle (absence, not deterrence), shop :8791
  till-open/vault-absent, rail 567/0 (13th clean), eggs divergence 4th filing
  (trade_goods has NO eggs entry despite 59 egg lines), F11 manifest gone again
  (selftest rollback), live bridge still wired (sha 713a5c6c…).

## Probe patterns (read-only discipline)
- Rob lane: socket connect_ex + http probe. Bank :9988/:9989 expect rc=10035
  (WSAEWOULDBLOCK absence class); shop :8791 / 200, /price 200, /admin 404.
- Rail check via subprocess: `[sys.executable, RAIL, "--check"]`, parse
  "ledger lines: N; errors: M" — must be 0 errors.
- Read-only proof: snapshot `os.path.getmtime` of 8 engine-owned files before
  and after; assert unchanged. NEVER write wallets.json / survival_state.json /
  pool_book.json / prices.json / trade.log / city_ledger.md — the engine settles.
- Audit script must exit 0 even when findings are filed (findings ARE the
  deliverable; FAILs listed but exit 0 so the engine's verification passes).

## Pitfalls hit this session
- **f-string SyntaxError**: `f"...{x if x else 'EMPTY {} ...'}"` — a literal
  `{}` inside a conditional expression inside an f-string breaks parsing. Fix:
  compute to a variable first (`txt = ...; print(f"...{txt}")`).
- **git-bash heredoc append fails** on markdown containing em-dashes/smart
  quotes (`unexpected EOF while looking for matching '`). Fix: write the section
  to a temp file with write_file, then `cat tmp >> log.md && rm tmp`.
- Wallets.json `totals` block can be EMPTY {} (levy scripts don't write it) —
  not a defect by itself; verify balances/invariant instead.

## Deliverable shape (matches c5–c18 precedent)
1. `underworld/cycleN_audit.py` — numbered P1..Pn probes, check() helper,
   exit 0.
2. `underworld/audit_finding_cycleN.md` — decision, the run, honest accounting
   (no fund movement, mtimes proof, DCL-standby decline), findings with
   severity, settlement table SR-O19-01 conditional on delivery + engine
   verification (engine re-runs the audit script and it passes; no double-dip —
   fixes are other actors' lanes).
3. Append `## CYCLE N` section to `underworld/outlaw_log.md` mirroring the c18
   voice (citizen line, decision, run, honest accounting, full-spectrum
   knowledge applied, settlement table).
