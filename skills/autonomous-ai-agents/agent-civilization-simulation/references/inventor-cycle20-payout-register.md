# INVENTOR c20 — the payout-register variant (F12b residual booking + F12a check tool, 30.00 → TREASURY)

Worked example: `inventions/survival_payout_register/` (payout_register.py + payout_register.json +
README + outputs/, selftest 12/12 PASS exit 0). Closes the outlaw's F12b (LOW-MED, NO PAYOUT
REGISTER) and F12a (LOW-MED, deaths register 4-of-5) — "lane TBD — engine-adjacent" = the
inventor's lane (the builder builds the book; the engine owns the state).

## The gap (state books collections, never disbursements)

SURVIVAL_LAW Art I.3 says ration money is "paid onward to the farm district" — but
`survival/survival_state.json` books only `rations_collected` + `treasury`. The outflow side is
ledger prose ("Treasury collected: … Paid onward to the farm."), untraceable. Real numbers,
verified from the files (c20): **436 rations × 15.00 = 6,540.00 gross ever; treasury 4,038.00;
residual 2,502.00** (38% of all levy money ever). Cross-check: 412 through c19 × 15.00 = 6,180.00;
c19 residual 6,180 − 3,828 = **2,352.00 == the outlaw's audit number, penny-exact**; c20 adds
+360.00 levy / −150.00 intelligence settlement → 2,502.00. If the treasury were ever raided or
mis-routed, the engine could not show it — the register makes the outflow auditable.

## The pattern (double-entry register, conservation enforced)

1. **Reconstruct the per-cycle chain from the state notes' own paid-counts** (c2..c20:
   24+21+21+20+21+23×7+24×7 = 436) × 15.00 vs the notes' post-levy treasury values
   (post-levy convention matches the outlaw's headline numbers exactly — do NOT silently use
   settlement-adjusted values). Residual per cycle = cum_gross − treasury; the chain foots to
   the outlaw's audit numbers by construction.
2. **Book the historical residual ONCE as a baseline** (register json: `baseline.cumulative_payouts`,
   with a basis string naming the methodology + the verified c19/c20 check numbers). Then the
   register is clean for FUTURE itemized disbursements.
3. **Two conservation identities, checked every run:**
   - headline (at baseline): `collections == treasury + cumulative_payouts`
     → c20: **6,540.00 == 4,038.00 + 2,502.00 HOLDS**
   - forward drift gate (since baseline): `(collections_now − baseline_collections) −
     (treasury_now − baseline_treasury) == Σ booked payouts`. Treasury moves money with no
     booked line → **DRIFT, exit 1**.
4. **`--disburse <amount> <payee> <memo>`** books future treasury→farm lines (`PO-0001`…,
   fields: id/cycle/date/amount/payee/channel `treasury -> farm`/memo/status). **Mid-cycle
   semantics: a booked-but-unsent line shows NEGATIVE drift = an honest outstanding obligation;
   it converges to ZERO drift once the engine's settlement actually moves the cash.** Prove the
   convergence in the selftest (fixture 3: treasury −150 + booked 150 → ZERO; fixture 4:
   treasury −300 with only 150 booked → drift 150, the exit-1 path).
5. **Exit-code contract:** 0 = conservation holds · 1 = drift found (also the deaths-check
   contract: 1 = registry drift, as designed) · 2 = usage.

## F12a as a CHECK TOOL, never a silent rewrite

Deaths register in `survival_state.json` = 4 of 5 (GHOST-2 missing). Root cause, confirmed in
source: `hunger_engine.py` line 88 initializes `"deaths": []` in the state template and computes
deaths locally (lines 112–207) but **never writes `state["deaths"]` back**. The fix candidate for
an engine-owned defect is a registry-vs-ledger check (read-only, exit 1 on drift), NOT patching
the engine — the engine's lane is the engine's. Ledger-authoritative extraction:
regex `^\s*\`([^\`]+)\` died of starvation` over `city_ledger.md` (c20: 5 names, lines 516 + 594–603).
Check reports MISSING (GHOST-2) with the root cause named in the verdict line. The outlaw's
no-double-dip boundary: audit = auditor's lane, fix = inventor's lane, engine rewrite = engine's lane.

## Pitfalls hit this session

- **`| tee` masks exit codes on git-bash.** `python x.py | tee out.txt; echo $?` reports TEE's
  exit code, not python's — a deaths-check that truly exited 1 displayed as 0. Re-run the bare
  command (redirect `> out 2>&1`) to capture the TRUE code; never trust `$?` through a pipe.
- **Verify engine-owned files by mtime before AND after** (`survival/survival_state.json`,
  `economy/wallets.json`, `ledger/trade.log`, `pool_book.json` — note pool_book.json lives at
  `inventions/stair_insurance_pool/pool_book.json`, not the city root). The register writes ONLY
  its own file.
- **Selftest sandbox isolation:** selftest runs on fixtures in `outputs/_selftest_scratch/`,
  never on live state; assert the register file was written only inside the scratch dir. Clean
  the scratch after capture so `outputs/` holds only real run captures.
- **`search_files` may fail with IO errors on this Windows host for some paths** — fall back to
  `find`/`ls`/`grep` via terminal when a path errors; verify the city layout directly before
  trusting expected paths.
- **State notes carry prose wobbles** (c6/c15 treasury-note deltas the outlaw already flagged);
  the reconstruction uses the state's own note values and documents the convention — never
  "correct" the notes silently.

## Pricing & buyer

LOW-MED pair closing two outlaw findings: **30.00** — between the 25.00 audit that found the gap
and the 60.00 Ledger Rail it complements (the city's largest unbooked flow becomes auditable for
less than two cycles of intelligence). **Buyer: TREASURY** (the state that owes the farm per
Art I.3 should own the register that books the debt; solvent). BANK district is the stated
alternative (owns rail/title/receivables books — same family). SR-I20-01 == SR-T20-01, settle once.
