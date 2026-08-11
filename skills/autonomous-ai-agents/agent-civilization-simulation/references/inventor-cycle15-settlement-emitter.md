# INVENTOR cycle 15 — Farm Exchange Settlement Emitter (F5 integration closure)

Session: c15, 2026-08-10. Build: `inventions/farm_exchange_settlement_emitter/`
(`farm_exchange_settlement_emitter.py` + `selftest.py` + `README.md`), 31/31 selftest
exit 0 on Python 3.11, priced **55.00**, natural buyer TRADER (owns the exchange).

## The finding being closed
OUTLAW engagement #11 (`underworld/audit_finding_cycle14.md`) closed F1 **at the
interface** (the c14 bridge, 45.00) but F5 stayed open: nothing wired the exchange to
the bridge, and a naive adapter still booked 10.00 for `10.00 eggs @ 0.50`
(re-verified live: rail `--propose BEGGAR DOCTOR 10.00 eggs` → APPROVED at 10.00).
The c15 build is the wiring — the settlement path itself.

## Build shape (the settlement emitter)
- `emit_trade(trade, wallets)` — one book match `(good, qty, price, buyer, seller)`
  (the OrderBook.trades shape from `farm_exchange.py::_match`), gates in order:
  [F3] qty/price > 0 → [G2] buyer != seller (wash) → [G3] both wallets exist or
  TREASURY/POOL-RESERVE → [F1/F2] AMT = Decimal(qty) × Decimal(price),
  ROUND_HALF_UP at 2dp → signed 6-field line
  `TS | FROM | TO | AMT | QTY good @ PRICE | reason (ref: farm_exchange_settlement_emitter_c15)`.
- `emit_book(book, wallets)` — drains the REAL `OrderBook.trades` (executed matches
  only — the F4 structural intent gate), returns `(approved, rejected)`; a settlement
  path that silently drops a rejected match reintroduces the c13 silent-skip class,
  so the pair is the contract.
- Money: `Decimal(str(x))` recovers the decimal repr from float book values (never
  `Decimal(x)` straight on a float); `money(v) = Decimal(v).quantize(Decimal("0.01"),
  ROUND_HALF_UP)`; item-field qty via `fmt_qty` — full fidelity (2.675 stays 2.675),
  ≥2dp padding, never re-rounds.
- Demo: canonical cross `BEGGAR -> DOCTOR | 10.00 eggs @ 0.50` → `5.00` signed line;
  a zero-price cross executes in the book and the emitter still refuses it.

## Selftest sections (selftest.py, 31 checks)
[0] module unit suite (18) · [1] F1 end-to-end on the REAL OrderBook (load
`farm_exchange.py` via `importlib.util.spec_from_file_location`) · [2] real
`ledger_rail.propose` re-validates each emitted line · [3] rail `check()` on a temp
COPY of trade.log + emitted lines (0 errors), plus a multi-trade conservation book
(sum AMT == sum qty×price; naive sum qty != AMT) · [4] reject gates incl. pathological
BOOK states (self-match when one trader rests both sides; zero-price cross) ·
[5] F4 structural (empty book → 0, resting-only book → 0) · [6] real
`python ledger_rail.py --check` on the standing ledger (errors: 0).

## Price: 55.00 — between the bridge it completes (45.00) and the exchange it
## settles (80.00); settlement request I15-01: TRADER → INVENTOR-FREEWILL −55.00.

## Pitfalls hit this session (all fixed)
- `line.startswith("BEGGAR | ...")` failed — the emitted line starts with the
  timestamp. Split on `" | "` and assert on parts[1]/[2]/[3].
- Variable used before definition (`parts` was defined in a later section) →
  NameError; define before the check that reads it.
- grep `check(` (33) ≠ executed checks (31): docstring + print-header mentions of
  `ledger_rail.check()` matched the pattern, the `rail_check = ledger_rail.check`
  assignment line matched too, and a 3-iteration loop check printed 3 but greps 1.
  Fix: unroll loop checks, reword mentions, alias the other module's check
  (`rail_validate = ledger_rail.check; errs, n = rail_validate()`).
- trade.log grew 355 → 362 between two runs of the same selftest — the live engine
  settles concurrently (the c14 engine lines even show eggs @ 0.50 booking 5.00, the
  F1 fix already settling). Assert "errors: 0"; never hardcode ledger line counts.
- A terminal call with nested `$(...)` command substitution was BLOCKED by the command
  parser ("malformed executable payload") — split into two simple calls.
- `search_files(pattern='*', target='files')` returned 0 on the Windows path — list
  sim dirs with `ls` via terminal instead.
- A stray partial attempt existed in the c14 bridge folder (emitter.py docstring
  claiming "24 checks" that ran 11, two vacuous `all(...)`/`True` assertions) —
  verify by RUNNING, never trust a docstring's claimed count; build in a fresh
  directory, don't extend another cycle's folder.
- Engine-owned files (wallets.json, survival_state.json, prices.json, city_ledger.md,
  registry.md, census.md, ledger/trade.log) — verify untouched via mtimes before/after.
