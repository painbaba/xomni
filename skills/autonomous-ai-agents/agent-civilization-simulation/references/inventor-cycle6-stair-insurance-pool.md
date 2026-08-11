# INVENTOR cycle 6 — the stair-insurance pool (`inventions/stair_insurance_pool/`)

Companion to `inventor-survival-cycle-playbook.md`. Built 2026-08-10, price
**325.00**, selftest **25/25 PASS, exit 0** (Python 3.11.15, stdlib only).

## The gap

Every recorded death (GHOST-2 + VIGIL/MEMORY/ANVIL/VOX) was a ration death via
the 3-strike stair (Article II: HUNGRY 1/3 → STARVING 2/3 → DEAD 3/3) — fully
deterministic, therefore insurable. The city's response had always been ad hoc:
relief grants, custodian wages, an elemency petition that went **unanswered**.
Hunger spend cycles 2–6: 94.50 (60.00 lost levies + 21.50 BEGGAR rescue +
13.00 relief/wages) **plus five citizens**, with no institution left behind.

## Design

- Mutual aid society: 21 members pay a premium each cycle; the pool pays the
  15.00 ration to the treasury for any member who misses a levy → no strike
  ever accrues.
- **Premiums:** 2.50 full / 1.25 solidarity tier (balance < 1.5 rations =
  22.50). BEGGAR (19.40) pays half → pool income **51.25/cycle**. Solidarity
  cross-subsidy: the rich fund the poor; that is what a mutual is for.
- **Actuarial:** 10 recorded claims × 15.00 = 150.00 over 105 member-cycles →
  pure premium **1.43**; loading +1.07 (75%, conservative) → 2.50.
- **Capital:** opening reserve 90.00 escrowed from the license proceeds
  (a mutual with zero capital dies on its first cluster: the c3 shock alone
  leaves it −22.50); target reserve **120.00** (8 rations); treasury
  catastrophe backstop **75.00** (one recorded-worst layer).
- **Claim rules (anti-abuse, unit-tested):** 1-cycle waiting period,
  premiums-current good standing (per-member rate), pre-existing-hunger
  exclusion at join, once per member per cycle, claims pay the treasury
  directly (no member cash → no arbitrage).

## Verified numbers (from the actual run)

- Ruin probability (Monte-Carlo, 2000 seasons × 120 cycles, seed 20260810):
  **4.95% reserve-only → 1.5% with backstop**. (First honest estimate was
  9.55% — thin capital; redesign, not fudge.)
- Stress: two consecutive 75.00 shocks → reserve 96.25 → 72.50, survives.
- Backtest (pool opens c2 with 90.00 seed, premiums as today):
  141.25 → 117.50 (c3, −75.00) → 108.75 (c4, −60.00) → 145.00 (c5, −15.00) →
  **196.25 (c6)** — above the 120.00 target through the worst recorded famine;
  all five citizens alive, 60.00 of levies preserved.
- Counterfactual without the pool: 94.50 spent + 5 citizens dead.
- BEGGAR affordability: 19.40 − 1.25 = 18.15, ration untouched (ration is
  senior).

## Settlement requests shipped

```
FROM treasury           | TO INVENTOR-FREEWILL | 325.00 | stair_insurance_pool | license, cycle 6 (incl. 90.00 opening-reserve escrow)
FROM <each of 21 members> | TO INVENTOR-FREEWILL | 2.50/1.25 | pool premium | standing order, cycle 7 (member, full/solidarity tier)
FROM INVENTOR-FREEWILL  | TO treasury           |  15.00 | pool claim | standing rule: ration paid for any member who misses their levy
```

Standing orders are forward-dated in REASON so the engine won't execute them
same-cycle. The pool book (`pool_book.json`) records the 90.00 seed as
"pledged" until the license settles; reserve ≡ seed + premiums − claims.

## Domain knowledge applied (real, cited in the README)

Actuarial pure premium & loading · risk pooling / law of large numbers (and its
failure under correlated shocks) · Solvency-II-style capital sizing (target
capital = worst recorded cluster; minimum seed before writing business;
catastrophe layering via the backstop) · Monte-Carlo ruin theory with Poisson
frequency (isolated + cluster events) · mutual/friendly-society economics ·
solidarity pricing · contract mechanics (waiting period, good standing,
pre-existing exclusion) · append-only bookkeeping with exact reconciliation ·
read-only systems engineering proven by SHA-256 before/after in the selftest.
