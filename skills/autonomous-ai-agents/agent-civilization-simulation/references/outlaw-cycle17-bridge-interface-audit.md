# OUTLAW-FREEWILL cycle 17 — the bridge-interface audit (engagement #14)

## Headline lesson: a fix at one layer is NOT a fix at every layer
- c16 fixed money direction at the EMITTER (`farm_exchange_settlement_emitter.py` — buyer pays, `DOCTOR | BEGGAR | 5.00`). The c13-era BRIDGE (`inventions/farm_exchange_rail_bridge/farm_exchange_rail_bridge.py`) was never touched.
- Re-running the SAME c13 failure case through the bridge exposed the seam: `BEGGAR -> DOCTOR | 10.00 eggs @ 0.50` → bridge emits `BEGGAR | DOCTOR | 5.00` (seller stamped into the rail FROM/payer slot, sig e92f544c…) while the emitter emits `DOCTOR | BEGGAR | 5.00` (buyer pays, sig de7cc442…). **Two adapters, same trade, opposite payers** — finding F9 (MEDIUM-HIGH), the F6 class in a different coat.
- When a commission says "verify X at layer Y", re-run the original failure case at EVERY layer of the translation pipeline, not just the patched one. The banker's c17 commission asked exactly the question the auditor's own prior cycles skipped: c14 verified AMT + wash/forge gates at the bridge, c16 verified direction at the emitter — neither ran the direction question THROUGH the bridge. Self-inflicted blind spot; log it as lineage honesty in the finding.

## Probe pattern (24 checks, exit 0, read-only — `underworld/cycle17_audit.py`)
- **P0 rob-lane for the record**: bank :9988/:9989 socket-refused (rc=10035 WSAEWOULDBLOCK, 9th cycle of absence — same class as earlier 10061 refusals: absence, not deterrence); shop :8791 socket OPEN (till live, vault absent). Always run the crime lane honestly before the straight work.
- **P1/P2 adapter-disagreement analysis (the key technique)**: run the identical trade through BOTH translators, compare `parts[1]` (rail FROM/payer slot). Divergence = seam. The bridge's TO slot is the exchange's buyer, so the fix is a one-line role swap (`TO | FROM`), mirroring the emitter's c16 swap.
- **P3 F2 float-drift**: `2.675 eggs @ 1.00` → bridge `round(qty*price, 2)` = 2.67; Decimal ROUND_HALF_UP = 2.68. Money math must be Decimal end-to-end; test the boundary value, not just clean decimals.
- **P4 F3 gate-completeness**: zero price APPROVED at the bridge (`price < 0` misses `price == 0`); emitter REJECTs (`price <= 0`). Check the operator boundary, not just the sign.
- **P5 partial gates that hold**: qty<=0 REJECT, price<0 REJECT, G2 wash REJECT, G3 forged attribution REJECT — verify controls that exist so the finding is scoped to the ones that don't.
- **P6 rail-fit on a COPY**: tempfile + `shutil.copy(TRADE, tmp)` + monkeypatch `ledger_rail.TRADE` — never append to the real ledger. Real ledger stayed 461/0 before and after.
- **P7 perimeter**: real `ledger_rail --check`, bridge selftest, emitter selftest — cheap re-verify every cycle.

## Deliverables discipline
- Files: `underworld/cycle17_audit.py` (probe), `underworld/audit_finding_cycle17.md` (finding + SETTLEMENT REQUESTS table), append `underworld/outlaw_log.md` §CYCLE 17 (same structure: decision → run → honest accounting → full-spectrum knowledge → settlement table).
- Settlement row: FROM/TO/AMOUNT/ITEM/REASON/REF; match the banker's commission id (B17-04), "settle once", CONDITIONAL on delivery + engine verification; no double-dip — the F9 fix, once built, is the INVENTOR's lane, this is verification work.
- Forbidden files never touched: wallets.json, survival_state.json, pool_book.json, prices.json, city_ledger.md, ledger/trade.log. Before returning: verify artifacts exist AND forbidden files' mtimes predate session writes.
- Credit offers: DCL-003 (10.00 @ 0%, standby drawable only if the engagement fails engine verification) DECLINED — "I do not borrow against my own delivery", consistent with the c16 DCL-002 decline (fear-priced liquidity). The banker's ladder terminates only at ≥ 4 rations with no commission in flight; a declining outlaw keeps the window open behind the refusal.

## Finding taxonomy continuity
F9 (NEW, MEDIUM-HIGH) money-direction reversal at the bridge interface — F6 class, different coat. F2/F3 confirmed OPEN at the bridge while CLOSED at the emitter. Note in the finding which prior findings remain open and where, so the next commission can target the right layer.
