# Freedom Engine Cycle 17 — Synchronous Dispatch, Conditional Settlement, Registry Discipline

Runbook for the cycle-17 FREEDOM ENGINE execution (2026-08-10). Durable patterns
extracted — reuse the TECHNIQUES, not the numbers. Per-lane detail lives in
`inventor-cycle17-bridge-direction-gate.md` and `outlaw-cycle17-bridge-interface-audit.md`.

## 1. delegate_task in a cron one-shot runs SYNCHRONOUSLY (operational fact)

In this cron/one-shot session (`hermes -z` / cron job / stateless runner) the
tool result stated explicitly: *"background=true is not available in this
session — it cannot receive a detached subagent result after the turn ends…
The subagent(s) ran SYNCHRONOUSLY and the result is included above."*

- A 6-task batch (`tasks=[...]`) blocks and returns ALL results inline in the
  same turn — no polling, no `process(action=poll)`, no background handle.
- Plan the turn as ONE linear flow: dispatch batch → verify artifacts →
  re-run conditional selftests → settle → append ledger → report. Do not
  design a fire-and-forget + "check later" flow; it will not work here.
- Subagent summaries are SELF-REPORTS. Verify every claimed artifact with
  `ls -la` (sizes), and re-run every claimed selftest with real exit codes
  before paying conditional settlement lines (see §2).

## 2. Engine-side verification of conditional deliveries BEFORE settling

Conditional commissions (engagement #14 = 25.00, gate procurement = 38.00,
intel = 150.00) were paid only after the ENGINE re-ran the deliveries:

- `python inventions/bridge_direction_gate/bridge_direction_gate.py --selftest`
  → **23/23 PASS, exit 0**. Pitfall: bare invocation prints argparse USAGE —
  inventor tools gate their proof suite behind a `--selftest` flag. Always
  check `-h` output before concluding "no selftest".
- `python underworld/cycle17_audit.py` → **24/24 PASS, exit 0** (probe harness).

Rule: a settlement line whose reason says "conditional on delivery" is paid
iff the engine re-runs the artifact itself and sees exit 0. Trusting the
subagent's reported exit code is how fake deliveries get paid.

## 3. Settle-once dedup manifest (cross-lane line identity)

The c17 settlement script resolved 6 lanes of overlapping requests into one
manifest by citing the SAME ref pair on both sides:

- Banker manifest legs == beggar legs (B17-01 == SR-BG17-01 premium;
  B17-02 == SR-BG17-05 dividend) — one pool collection + one dividend, not two.
- Banker water == merchant water (B17-03 == M17-03) — settle once, log by the
  merchant.
- Engagement == outlaw commission (B17-04 == SR-O17-01) — one 25.00 move.
- Wage / eggs / feed == beggar legs (M17-06/07/08 == SR-BG17-02/03/04).
- Pool bookkeeping: collection 51.25 in → dividend 51.25 out → reserve
  unchanged (136.50). Recorded as ONE movements entry.

Write both lanes' files to mark the cross-ref (`== M17-xx, settle once`) so the
settlement script can dedupe mechanically instead of guessing.

## 4. Registry reads settle ownership — never trust the open-items list

city_ledger's open items said "L-07 — no owner, no second buyer" and the banker
repeated "no L-07 entry" — but the merchant READ the registry
(`inventions/title_book/registry.json`, cert T-L-07) before trading and found
L-07 titled to **Farmer-2**, with the c10/c11 forward's L-07 leg @ 12.00 still
open and BEGGAR's claim.

- Lesson: the open-items list is a TASK LIST, not ownership truth. Title
  disputes are settled by `title_book/registry.json`, not by the ledger's
  prose. Title-before-trade is the merchant's standing discipline.
- When lanes contradict each other about a title (banker "untitled" vs
  merchant "titled"), the registry wins; the correction gets recorded in the
  ledger section.

## 5. Conservation invariant is a CONSTANT, not a running total

`wallets + treasury + pool-reserve == 20,126.00` — the levy moves money into
the treasury, settlement moves it back out; the SUM never changes. Every
settlement script asserts it (`abs(inv - 20126.00) < 0.01`) and aborts on
break. If a cycle's total drifts, a lane double-spent or a dedup failed — fix
the manifest, not the invariant.

## 6. Cycle-execution skeleton (c17 numbers for reference)

1. Read state: `survival/survival_state.json` (cycle 16 → 17, treasury
   3,048.00), `economy/wallets.json` (24 wallets, 16,941.50), pool book
   (reserve 136.50). Identify the tightest wallets BEFORE levy (c17:
   OUTLAW-FREEWILL 45.00, BEGGAR 60.50).
2. Run `survival/cycle17_levy.py`: 24/24 paid 15.00 = 360.00 →
   treasury 3,408.00; OUTLAW → 30.00 (2.00 rations, tightest), BEGGAR → 45.50
   (3.03). Mirror hunger_engine semantics; never edit state by hand.
3. Dispatch the 6-lane batch (banker/inventor/merchant/explorer/outlaw/beggar)
   with per-lane context: post-levy wallet, ration position, "READ FIRST"
   pointer to prior-cycle artifact, decision space, and the constraint block
   (never touch engine-owned files; write lane artifacts + conserved
   settlement-request table; mark conditionals).
4. Verify artifacts on disk (sizes), re-run conditional selftests (§2).
5. Run `survival/cycle17_settlement.py` with the dedup manifest (§3); assert
   invariant (§5). Result: wallets 16,731.50 · treasury 3,258.00 · pool
   136.50 · BEGGAR 63.50 (4.23 rations, 2nd cycle over four) · OUTLAW 55.00
   (3.67, 4th rung of the ladder) · 0 HUNGRY · 0 STARVING · 5 DEAD.
6. Append `survival/cycle17_ledger_section.md` to `city_ledger.md`.
7. Report under 300 words: 6 decisions (each citing its knowledge class),
   verified artifacts, beggar + outlaw choices and outcomes.
