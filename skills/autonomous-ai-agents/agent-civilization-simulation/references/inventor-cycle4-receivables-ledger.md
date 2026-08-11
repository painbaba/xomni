# INVENTOR-FREEWILL cycle 4 — the Banker's Book (receivables & loan ledger)

Proven 2026-08-10, survival cycle 4. Builds on the cycle-2 inventor playbook;
this is the concrete cycle-4 instance. Artifact:
`machine_city/inventions/receivables_ledger/` (ledger.py, receivables.json,
README.md, outputs/{debtors_report.md, book_snapshot.json, receivables.log}),
registered in `economy/prices.json` at **100.00**.

## The gap (why this, not the other candidates)

Survey prior inventions BEFORE choosing a gap. Cycle 2's Breadboard
(`breadboard_survival_console`) already covers the death-clock (flags the 4
STARVING: VIGIL/MEMORY/ANVIL/VOX) and the ration cliff; cycle 3's Town Cryer
covers wages. The uncovered layer was CREDIT: the bank runs credit operations
with no structured book. All of this lived as prose notes in wallets.json:

- RB-001 Ration Bridge Loan — 8.00 to BEGGAR at 0%, labor-collateral,
  **due cycle 4 (= the build day)**, debtor balance 0.00
- RP-001 Poor Relief pledge — 5.00 granted (Article V), 2.00 repaid, 3.00 out
- PW-001 pawn — 4.00 vs BEGGAR's copper cup, redeem 5.00 by cycle 6
- RS-001 ration reserve — 25 bu wheat, 50.00 book value (treasury asset)
- FL-001 fraud write-off — 5.00, open

The only question a lender cares about — *what is owed, to whom, when, can the
debtor pay?* — had no answer anywhere.

## Book schema (receivables.json)

`schema: bankers-book-v1`, `bookkeeper`, `currency: city-credit`, `cycle`,
three arrays:
- `receivables[]`: id, type (ration_bridge_loan|poor_relief_pledge|pawn),
  debtor, creditor (wallet name OR institution string like "treasury"),
  principal, repaid, interest, collateral, due_cycle, status, note
- `assets[]`: id, type, holder, qty, unit, book_value, acquired, note
- `losses[]`: id, type, amount, status, booked, note
- `movements[]`: append-only repayment records (MOV-###)

## Tool mechanics (ledger.py, stdlib only, Python 3.11)

- Reads `economy/wallets.json`, `survival/survival_state.json`,
  `economy/prices.json`, `farm/harvest/wheat_harvest_1.json` — READ-ONLY.
  Ration price recomputed with the hunger engine's exact formula (wheat × 7.5,
  ×1.20 scarcity if per-capita ≤ 15 bu).
- Default run: aging buckets (DUE NOW ≤ cycle / NEXT CYCLE = cycle+1 / later),
  debtor exposure = debt due by cycle+1 + next ration (BEGGAR: 15.00 debt,
  **26.00 due by cycle 5**, wallet 0.00 → RED), asset mark-to-market, loss
  register, counterparty reconciliation (every debtor/creditor must be a
  wallet or an institution — else flag), survival cross-check (STARVING
  citizens are the stair's debtors, not the book's).
- `--repay <id> <amount>`: write-path that mutates ONLY the invention's own
  book + append-only `outputs/receivables.log`. Never touches city state.
- Writes `outputs/debtors_report.md` (gazette-ready), `outputs/book_snapshot.json`
  (machine-readable), `outputs/receivables.log` (append-only).

## Verified run (exit 0)

```
RB-001 ration_bridge_loan BEGGAR -> BANKER      8.00  DUE NOW
RP-001 poor_relief_pledge BEGGAR -> treasury    3.00  NEXT CYCLE
PW-001 pawn               BEGGAR -> MERCHANT    4.00  CYCLE 6
Outstanding 15.00  |  DUE NOW 8.00  |  next cycle 3.00
EXPOSURE BEGGAR: 15.00 debt, 26.00 due by cycle 5, wallet 0.00 -> RED
RECONCILIATION: 0 issues — every counterparty resolves
```

Headline finding: the Ration Bridge is due TODAY and the debtor holds 0.00 —
the city's first visible default. The 26.00 is COMPUTED from the book (debt +
ration), never hardcoded.

## Honest-bookkeeping discipline (the --repay demo)

The real book must record only truth: nothing was repaid in cycle 4, so the
book shows everything outstanding. To PROVE the `--repay` code path without
falsifying the city's books: copy the invention dir to
`inventions/.tmp_repay_demo/` (INSIDE the project — see derived-path pitfall),
run `python ledger.py --repay RB-001 8.00` there (exit 0, RB-001 → settled,
MOV-001 movement logged), then delete the copy and verify the real book still
shows RB-001 outstanding with movements [].

## Registration in prices.json (python, structure-preserving)

The cycle-4 task explicitly requires direct registration (cycles 2–3 priced in
README only). Recipe that worked:

```python
prices = json.load(open("economy/prices.json", encoding="utf-8"))
inv = prices["categories"]["inventions"]
entry = {"receivables_ledger": {"price": 100.0, "seller": "INVENTOR-FREEWILL",
         "unit": "ledger", "note": "..."}}
new_inv = {}
for k, v in inv.items():
    new_inv[k] = v
    if k == "town_cryer_labor_exchange":      # anchor key: insert right after
        new_inv.update(entry)
prices["categories"]["inventions"] = new_inv  # dict preserves insertion order
json.dump(prices, open("economy/prices.json", "w", encoding="utf-8"),
          indent=2, ensure_ascii=False)
# verify: json.load again + assert all pre-existing invention keys still present
```

Never a blind `prices["categories"]["inventions"]["receivables_ledger"] = ...`
append at the end — inserting after the related anchor (next to the Town Cryer)
keeps the book readable, and the anchor assertions prove nothing broke.

## Pricing logic

100.00: below AUDITOR's balance tracker (400.00 — that is one ledger; this is
one book), below the water line (150.00 — the treasury funds the relief this
book tracks), above the Town Cryer (75.00 — the Cryer creates wages, this
guards the city's credit). Sold to the bank/treasury, not the poor.

## Verification checklist (all passed)

run → exit 0 · re-run → exit 0 (idempotent; log appends, report regenerates) ·
`json.load` on every output · read back all 5 files · prices.json still valid
JSON · wallets untouched (BEGGAR 0.00 / BANKER 905.00 / 25 wallets before AND
after).
