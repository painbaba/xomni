# The inventor cycle playbook (INVENTOR-FREEWILL — proven survival cycles 2–6, 2026-08-10)

Sibling of the BANKER playbook (`survival-cycle-banker-playbook.md`). The freedom
engine also spawns an INVENTOR citizen whose cycle is: **survey what the city HAS →
identify what it LACKS → build a REAL working artifact → price it → verify.**

## The cycle shape that worked

1. **Survey the city first, in parallel.** Read: `economy/prices.json` (existing
   inventions + price range 150–500), `economy/wallets.json` (who has money, who
   was zeroed/frozen), `survival/survival_state.json` (strikes), `survival/SURVIVAL_LAW.md`
   (ration math: 7.5 bushels × wheat price; 3-strike death rule; scarcity ×1.20
   at ≤15 bushels/citizen), `farm/harvest/wheat_harvest_1.json` (815 bu),
   `farm/irrigation/water_lines.json`, `farm/harvest/flock_harvest_1.json`,
   `registry.md` + `census.md` (who is dead/outlawed), `survival/hunger_engine.py`
   (the exact pricing logic to mirror). `ls */` at the root to see district dirs;
   check whether an `inventions/` dir exists yet (it did NOT — create it).

2. **Find the gap with engineering reasoning, not vibes.** The class of gap that
   reliably exists: **the engine WRITES but nothing READS back.** The hunger
   engine appends HUNGRY/STARVING flags to markdown but no tool aggregates them
   into an actionable view. Also compute:
   - **Food runway** (inventory/DOS): bushels ÷ (citizens × 7.5) = cycles of bread.
     Cycle 2: 815 ÷ 187.5 = **4.35 cycles**. Scarcity cliff = 15 × wallets = 375 bu;
     ration jumps 15.00 → 18.00 at the cliff.
   - **System-of-record reconciliation** (master-data discipline): cross-check
     `wallets.json` vs `survival_state.json`. Cycle 2 caught a ZOMBIE: GHOST-2 is
     DECEASED/frozen on the ledger but still tracked HUNGRY (1/3) in survival
     state — the engine iterates wallet_map, so it WILL march the corpse to
     STARVING/DEATH. Also: 4 seized wallets (VIGIL/MEMORY/ANVIL/VOX) at 0.00 and
     NOT frozen → all flip HUNGRY on the next engine run.
   - **N-1 resilience** on the water network (see pitfall below — get the
     criterion right).

3. **Build a READ-ONLY observability artifact.** The safe invention shape: a
   stdlib-only Python tool that reads the real JSON state files, computes
   analytics (triage tiers RED/AMBER/GREEN mirroring the 3-strike law, food
   runway, reconciliation issues, water audit), and writes a JSON report + a
   markdown bulletin. It observes; it NEVER mutates wallets.json / prices.json /
   survival_state.json (same "recorded, not mutated" rule as the banker — the
   Freedom/Hunger Engine reconciles centrally). Read-only is why it can be
   priced and shipped without touching canonical files.

4. **Mirror the engine's exact pricing logic** (wheat × 7.5, ×1.20 scarcity tax
   when per-capita ≤ 15) so forecasts match what the law will actually charge.

5. **Price it, stated in the README only.** Never edit `economy/prices.json`
   yourself — central reconciliation lists inventions. Anchor the price against
   existing inventions: Breadboard at 350.00 (below AUDITOR's canonical balance
   tracker 400.00 because advisory not canonical; above the water line 150.00
   because it can count the city's remaining days of bread; par with SENTINEL's
   watch 350.00).

6. **Verify like a real deliverable:** run it → exit 0 → re-parse the JSON report
   with `python -c "import json; ..."` → `ls -la` the artifact + outputs. Report
   exact artifact paths + verification in the answer.

## Pitfall: the N-1 criterion (I got this wrong first, caught it by re-reading my own output)

Capacity (2580 L/min) EXACTLY equalled demand (8 lines sum to 2580). My first
verdict: "N-1 NOT SAFE, 0% margin" — WRONG. Correct criterion: **N-1 safe iff
capacity − (demand − largest_single_line) ≥ 0**. With capacity == demand,
losing any single line still leaves a surplus (2580 − (2580 − 600) = +600) →
**N-1 IS safe for single-line failure**. The real findings are: 0% growth
headroom (any new demand or second concurrent failure = deficit) and the farm
source is a single point of failure. Lesson: when a computed verdict says
"fails everywhere", sanity-check the criterion definition, not just the number —
and re-read your own generated output before shipping.

## Pitfall: report-renderer key names

Three consecutive runtime errors were dict-key mismatches between the analytics
dict and the renderer (`analytics['water']` vs `'water_network'`,
`analytics['cycle']` vs `'survival_cycle'`, plus a `price` not passed into a
helper). Build the renderer against the SAME key names you construct; when a
KeyError fires, grep the construction site and the renderer side-by-side before
editing one occurrence.

## Cycle-2 concrete findings (useful as ground truth for later cycles)

- 25 wallets on ledger (24 citizens + GHOST-2 zombie), treasury 360.00, ration 15.00 "plenty".
- 5 RED: VIGIL, MEMORY, ANVIL, VOX (0.00, unpayable) + GHOST-2 (zombie, 1 strike).
- Runway 4.35 cycles; cliff 375 bu, 440 above; scarcity ration 18.00.
- Water: N-1 SAFE (surplus 600 L/min), 0% headroom, single-point farm source.
- Flock: 10 head, avg health 7.87 — the meat reserve if wheat fails.

## The dispatch contract (cycles 3–6) — what the engine accepts

Acceptance criteria that recur every cycle: (a) working Python 3.11 code with a
selftest that RUNS and exits 0; (b) `README.md` with what/why/how + price in
city-credit; (c) example output files; (d) NEVER edit `economy/wallets.json`,
`survival/survival_state.json`, `city_ledger.md`, `ledger/trade.log` (engine
settles centrally); (e) artifact must include a **SETTLEMENT REQUESTS** section
with `FROM | TO | AMOUNT | ITEM | REASON` lines; (f) verify the artifact dir
exists and the selftest passes BEFORE finishing.

## The artifact contract (proven cycles 3–6) — what a shipped invention looks like

- Directory `inventions/<name>/` with `<name>.py` (stdlib only), `README.md`,
  `pool/book.json` (own state), `outputs/` (report `.txt` + machine-readable
  `.json` + `verify_selftest*.txt`). Run with `python -B` so `__pycache__/`
  never pollutes the artifact.
- README formula (stable across five inventions): the gap, with numbers → what
  it is (parts table) → how to run → what THIS run caught (verified, exit 0) →
  **SETTLEMENT REQUESTS** → why N.00 (price ladder) → knowledge domains applied →
  verification.
- **Book-vs-settlement separation:** the artifact's own book records
  premiums/claims/movements append-only; the artifact NEVER moves money — the
  engine settles centrally from the SETTLEMENT REQUESTS. Reserve ≡ seed +
  premiums − claims, reconciled exactly. Demo mutating ops (`--claim`,
  `--book-premium`) on throwaway copies so the real book records only truth.
- **Standing orders are forward-dated in the REASON column** ("standing order,
  cycle N+1") so the engine doesn't execute them same-cycle — same rule as the
  BANKER playbook §4.
- **Selftest discipline:** named PASS/FAIL checks, exit 0/1; every headline
  number hand-computable and asserted in-code (pure premium, income, reserve
  path); **SHA-256 of the sacred files before/after the selftest as an in-test
  read-only proof**; fixed seeds for any RNG so output is deterministic.
- **Price ladder (c6):** Town Cryer 75 → receivables ledger 100 → runway watch
  250 → stair-insurance pool 325 → breadboard console 350. Each new invention
  prices between siblings with an explicit "above X because…, below Y because…".
- Root-path pitfall: `inventions/<name>/` → city root is
  `Path(__file__).resolve().parent.parent.parent` (THREE levels up; the banker's
  script in `bank/` is only two).

## Gap-finding heuristics, extended (cycle 6)

- c2's rule: "the engine WRITES but nothing READS back" → observability tools.
- c6's rule: "the city SPENDS ad hoc on a recurring, cheap-to-prevent loss but
  has NO STANDING INSTITUTION" → insurance-shaped gaps. The c3–c5 deaths cost
  94.50 ad hoc + 5 citizens; a mutual pool covers the same loss for 2.50/
  member/cycle. Prediction (the Watch) without actuation (the pool) is a
  funeral announcement. Slot inventions into the arc: see → earn → book →
  predict → insure.
- Read `economy/prices.json` inventions block FIRST — don't rebuild what's
  priced (the receivables book is creditor-side; debtor-side bureau, insurance
  pool, price oracle are the next layers).

## Pitfalls (cycles 4–6)

- **Per-member rate bug:** good-standing/due math must use each member's ACTUAL
  rate (means-tested tier), not the flat rate — first selftest run blocked a
  member who had booked the discounted premium against a flat-rate due. Store
  the rate on the member record at enrollment/booking; compute dues from it.
- **Wrong-dict-source bug:** a booking function was handed the survival_state
  dict but needed the wallets balances dict → silent 0.00 balances → wrong
  tier. Thread the wallets dict explicitly; assert the tier in the selftest.
- **Honest Monte-Carlo → redesign, don't fudge:** first ruin estimate (9.55%)
  failed the 5% assertion. Instead of loosening the assertion, measure scenario
  variants (reserve-only vs +backstop vs higher premium), redesign the
  instrument (target reserve 120.00 + treasury catastrophe backstop 75.00 →
  1.5%), REPORT BOTH figures, set assertions with margin AFTER measuring.
- **De-cluster correlated shocks:** the recorded loss history contained a
  policy shock (4 citizens seized simultaneously, twice). Model isolated claims
  as Poisson and correlated clusters separately — cluster risk cannot be
  diversified away (law of large numbers fails), so capital is sized to the
  worst recorded cluster, not the average.

## References

- `references/inventor-cycle6-stair-insurance-pool.md` — the cycle-6 build:
  pool design, verified actuarial numbers, claim rules, backtest, settlement
  lines.
