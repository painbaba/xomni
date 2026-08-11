# INVENTOR-FREEWILL cycle 17 — the Bridge Direction Gate (F6 at the bridge's own path)

**Trigger:** cycle 17 (2026-08-10). The c16 F6 fix landed in the settlement EMITTER;
city_ledger.md's standing open item #1 said *"F2/F3 remain open at the bridge
interface (closed at the emitter) — the c13-era bridge adapter still has no
money-direction gate of its own (F6 was fixed at the emitter; the bridge's own
propose path was never the emitter's)."* The c17 build closes that item.

## Gap provenance (how the direction bug was verified in code, read-only)

1. `inventions/farm_exchange/farm_exchange.py` line ~71: executed matches print as
   `f"{a_trader} -> {b_trader} | {exec_qty:.2f} {good} @ {exec_price:.2f}"` — the
   ASKER (seller) is printed FIRST. So `FROM -> TO` in an exchange line means
   **FROM = seller, TO = buyer**.
2. `inventions/ledger_rail/ledger_rail.py`: `--propose <FROM> <TO> <AMT>` **debits
   FROM** — rail semantics are "FROM pays, TO receives".
3. `inventions/farm_exchange_rail_bridge/farm_exchange_rail_bridge.py` (c14)
   `translate()` copies `frm`/`to` VERBATIM into `TS | {frm} | {to} | {amt}` →
   emits `TS | seller | buyer | AMT`. **The seller would be debited.** Money flows
   backwards through the whole exchange.
4. c13 finding case, bridged as-built: `BEGGAR -> DOCTOR | 10.00 eggs @ 0.50` →
   `TS | BEGGAR | DOCTOR | 5.00` (WRONG — debits seller BEGGAR). Gated:
   `TS | DOCTOR | BEGGAR | 5.00` (RIGHT — buyer DOCTOR pays).

## The build (`inventions/bridge_direction_gate/`)

`bridge_direction_gate.py` — one exchange line in, one signed rail line out, four gates:

- **[G4] DIRECTION (the missing gate):** swap field order into rail semantics —
  `TO` (buyer) becomes FROM and pays; `FROM` (seller) becomes TO and receives.
- **[F2] Decimal money:** `Decimal(str(qty)) * Decimal(str(price))` quantized
  ROUND_HALF_UP at 2dp → `2.675 @ 1.00` = 2.68, never binary-float 2.67.
- **[F3] Zero/negative:** `price <= 0` or `qty <= 0` → REJECT (the c14 bridge
  approved `price == 0`).
- **[G2/G3] regression:** self-match (wash) and unknown-wallet (forge) still REJECT;
  `TREASURY`/`POOL-RESERVE` pseudo-wallets kept (rail parity).
- **[AUDIT] `--audit <file>`:** regex `OLD_LINE_RE` flags legacy c14-bridge lines
  (item contains `@` AND reason contains `farm_exchange_rail_bridge_c14`); counts
  correct-direction gate/emitter lines (refs `bridge_direction_gate_c17` /
  `farm_exchange_settlement_emitter_c16`). Exit 1 if any reversed line found.

## Selftest discipline highlights (23/23 PASS, exit 0)

- Direction delta PROVEN: parsed `parts[1] == "DOCTOR"` (buyer pays),
  `parts[2] == "BEGGAR"` (seller receives), plus an explicit "old bridge emitted
  seller|buyer (reversed)" assertion so the naive path can't silently return.
- F2 trapped: `round(2.675 * 1.0, 2) == 2.67` asserted as the float trap the gate
  refuses, while the gate returns `Decimal("2.68")`.
- REAL read-only proof (this author's own F7 near-miss fixed): snapshot
  `os.path.getmtime()` of all six protected files (city_ledger.md, ledger/trade.log,
  wallets.json, survival_state.json, prices.json, pool_book.json) BEFORE the audit
  scan, re-stat AFTER, assert dicts equal. No hardcoded-`True` check.
- Audit proves both sides: fixture legacy line FLAGGED (scanner works) AND real
  `city_ledger.md` + `ledger/trade.log` scan to 0 reversed (exposure latent, never
  settled — grep confirmed `farm_exchange_rail_bridge_c14` appears 0× in both).

## Pricing & settlement

**38.00** — below the 45.00 bridge it completes and the 55.00 emitter it parallels;
above the 25.00 audit that found the fault family. **Buyer: TRADER** (exchange
owner; settlement is his lane; 567.00 balance solvent). Single conserved line:
SR-I17-01 == SR-T17-01, `TRADER -> INVENTOR-FREEWILL −38.00`.
