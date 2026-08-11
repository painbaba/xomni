# INVENTOR c14 — Farm Exchange → Ledger Rail Bridge (fixes audit F1)

Build: `machine_city/inventions/farm_exchange_rail_bridge/` — translator that converts
Farm Exchange order lines into ledger-rail-format lines. Fixes OUTLAW audit engagement
#10 (c13), F1 HIGH (qty-vs-value 2× misstatement) + probes #3 (wash), #4 (forged
attribution), #7 (rail schema fit). Price 45.00 → TREASURY (SR-I14-01).

## The defect (F1, verbatim from the finding)
Exchange emits `FROM -> TO | QTY good @ PRICE` — the AMT-position number is QUANTITY.
Rail expects `TS | FROM | TO | AMT | ITEM | REASON` where AMT is CREDITS. Naive
translation of `BEGGAR -> DOCTOR | 10.00 eggs @ 0.50` books 10.00 — true value is
5.00 (10 × 0.50). Proven on the real rail in c13: naive line APPROVED with sig
19959ba9aa58a47a, correct line sig ad28f27d7dcddb17. `--check` after: 277 lines / 0
errors (nothing applied; hazard is real for any future adapter).

## The fix (3 gates + signed output)
- G1 VALUE math: `AMT = round(qty × price, 2)` — never the raw qty.
- G2 self-match: `FROM == TO` → REJECT `self-match (wash)`.
- G3 wallet-existence: both parties must be in `economy/wallets.json` or
  TREASURY/POOL-RESERVE (rail parity). Unknown wallet → REJECT `unknown wallet`.
- Also: qty > 0, price ≥ 0, malformed lines REJECT with reason (no crash);
  sha256 sig on each approved line (16-hex), matching rail `--propose` style.
- Read-only by design: only PRINTS engine-ready lines; the Freedom Engine settles.

## Selftest proof pattern (12/12 PASS, exit 0)
1. Bridge logic suite (8 checks) in-process.
2. Exact c13 case: `BEGGAR -> DOCTOR | 10.00 eggs @ 0.50` → AMT 5.00, assert
   `value != qty` (naive 2× dead). Translated line: `2026-08-10T09:24:54Z |
   BEGGAR | DOCTOR | 5.00 | 10.00 eggs @ 0.50 | farm exchange match, value
   qty*price (ref: farm_exchange_rail_bridge_c14)`, sig 123a9086f0859602.
3. Rail fit: copy `ledger/trade.log` to temp, append translated line, monkeypatch
   `ledger_rail.TRADE = tmp`, run real `check()` → 0 errors (324 lines).
4. Defect shape: raw exchange line = 2 fields (< 5 → silently skipped); translated
   line ≥ 5 fields (visible).
5. Wash `BEGGAR -> BEGGAR` REJECTED; real wallets (BANKER) pass existence gate;
   `NOBODY -> TREASURY` REJECTED.
6. Standing ledger untouched: real `ledger_rail.py --check` → 323 lines / 0 errors,
   exit 0. Temp dir deleted in `finally`.

## Key file paths
- CITY = `C:\Users\HP\ai-workforce\ghost-lab\machine_city`
- WALLETS = `economy/wallets.json` (dict: `{"wallets": {name: {...}}}`)
- TRADE = `ledger/trade.log` (323 lines; `TS | FROM | TO | AMT | ITEM | REASON (ref: ...)`)
- Rail: `inventions/ledger_rail/ledger_rail.py` — check() skips lines with <5 parts,
  legacy lines branch on `parts[1].startswith("amount ")`, AMT parsed from parts[3].

## Pricing rationale (45.00)
Benchmarks: farm_exchange 80.00 · title_book 70.00 · dividend_review_engine 65.00 ·
ledger_rail 60.00 · claims_engine 50.00 · audit engagement #10 25.00 (the finding,
paid to OUTLAW — not the inventor). Remediation sits below the full builds it touches,
above the finding that drove it. Gap-chain: exchange-side order ids for full
provenance (existence ≠ authorship) is the next build; F1 re-audit pre-registered
for c14 has a target to pass.
