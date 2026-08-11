# Inventor-cycle build: verified state-machine inventions (cycle 13, dividend-review engine)

Session distilled from building THE DIVIDEND-REVIEW ENGINE (cycle 13) — the
mutual's dividend state machine. Reusable for every future inventor build.

## The deliverable contract (mirror farm_exchange / stair_insurance_pool)
Every invention ships as a directory `inventions/<name>/` with:
1. `<name>.py` — a Python CLI that READS canonical state (pool_book.json,
   trade.log, wallets.json) and never writes it; emits engine-ready settlement
   lines for the Freedom Engine to apply.
2. `README.md` — what / why (gap analysis) / how to run / PRICE / gap-chain
   continuity note (next natural build). Keep < 500 words; the c13 brief
   demanded it explicitly.
3. `inventor_freewill_cycleN.md` — decision + SETTLEMENT REQUESTS table
   (FROM | TO | AMOUNT | ITEM | REASON | REF). Buyer = the natural owner
   (e.g. POOL-RESERVE for mutual tooling), reason must cite the selftest result.

## The selftest grep contract (verify it every time)
`grep -c 'check(' <file>.py` minus the number of `def check(` lines MUST equal
the N in the "N/N PASS" label. Discipline: one `check(...)` call per line, one
def line, no other `check(` occurrences (watch `--check` in argparse — that's
`--check` without `(`, safe). Run `grep -c` + `grep -c 'def check('` and
subtract in your head; do NOT rely on a single nested shell expression.

## Ledger dual-schema parsing (canonical pattern)
trade.log has TWO schemas: modern `TS | FROM | TO | AMT | ITEM | reason (ref: …)`
and legacy coffee-till `TS | amount X | balance_before N -> balance_after M | …`.
Branch on `parts[1].startswith('amount ')` FIRST (legacy lines return None),
exactly like `inventions/ledger_rail/ledger_rail.py`. Strip `\r` (CRLF lines
exist). Match per-cycle blocks via `re.search(r"cycle (\d+)", item)` — premium
and dividend lines both carry "cycle N" in ITEM.

## Golden-regression mode (the c12 pattern)
--check must re-derive the previous cycle's numbers from canonical state and
assert them: reserve path (150.25 → 201.50 → 51.25 returned → 150.25), line
counts (21 premiums, 21 dividends), sums (20×2.50 + 1×1.25 = 51.25), and the
state machine's decision (FULL_PASS_THROUGH). Reconstruct pre-collection
reserve from the book: `r_pre = reserve - collection + dividend_paid`. This
makes the audit a regression TEST, not a narrative.

## State machines: charter rules are functions, and test the right scenario
Codify charter constants (trigger/target/backstop/premiums) as module constants.
PITFALL (bit us in c13): when testing a boundary, check whether a HIGHER-
priority constraint binds first. The partial-dividend FLAG (reserve after payout
< trigger) looked untestable at reserve_post=201.50 because the collection CAP
(D ≤ 51.25) binds first: 201.50 − 51.25 = 150.25 ≥ trigger, so the flag is
unreachable there. The meaningful scenario was c11's shape (reserve_pre 140 →
post 191.25, where D > 41.25 dips below trigger). Our first selftest failed
2 checks — the LOGIC was right, the TEST SCENARIO was wrong. If a test fails,
suspect the scenario before the code; then demonstrate the boundary in the
scenario where it is reachable.

Pro-rata dividends: use largest-remainder rounding so the 21 shares sum EXACTLY
to the declared dividend (conservation — the engine never creates a cent).

## Run ALL CLI modes after writing, not just --selftest
--selftest passed 32/32 while --review crashed: an undefined `collection`
parameter hidden inside a dead expression (`reserve_before + dividend if False
else ...`) only surfaced when the emit path executed. Dead-code expressions
mask undefined names. Smoke every mode: --selftest, --check, --review (or
whatever the CLI exposes) and check exit codes.

## Pricing with the buyer's constraint
Price between the nearest benchmarks (farm_exchange 80, title_book 70,
ledger_rail 60, claims_engine 50 → dividend engine 65.00). Constraint: natural
buyer's balance MINUS price must stay above its own floor (POOL-RESERVE 150.25
− 65.00 = 85.25 > backstop 75.00). If buying changes the canonical next-cycle
numbers, say so honestly in the README (post-purchase c13 becomes an accumulate
cycle; pass-through returns at c14).

## Windows/MSYS shell trap (hit twice)
Nested `$(( $(grep -c ...) - $(grep -c ...) ))` arithmetic with command
substitution inside a single terminal call tripped the hardline command parser
(BLOCKED). Fix: split into separate simple commands, compute the subtraction
mentally. Keep one concern per terminal call.
