# OUTLAW CYCLE 15 — BRIDGE-EMITTER AUDIT (engagement #12)

Outlaw lane runbook for the c15 audit of the INVENTOR's c15 build
(`inventions/farm_exchange_rail_bridge/emitter.py` — the F5 wiring that drains the
REAL `farm_exchange.OrderBook` and emits bridge-format rail lines). Verdict: F1
(c13 qty-vs-value 2× bug) **dead at the source** — the exact c13 case
`BEGGAR sells 10 eggs @ 0.50 → DOCTOR` emits `TS | BEGGAR | DOCTOR | 5.00 | …`
(was 10.00 naive). 20 real probes, exit 0, city cost 0.00. 15th clean cycle.

## Reusable techniques (the parts future audits should keep)

1. **Money-direction role check (the c15 lesson — HIGH value).**
   Ledger-rail lines are MONEY direction: `TS | FROM | TO | AMT`, and **FROM pays**
   (`--propose` enforces FROM's balance; every real ledger row has the buyer as FROM:
   `DOCTOR | MERCHANT | 4.00 | water`). Exchange settlement lines are GOODS direction:
   `SELLER -> BUYER | qty good @ price` (the exchange prints the asker first).
   Mapping the goods arrow 1:1 onto the money schema **reverses payer/payee** — the
   seller gets debited. The c13/c14 audits only checked the AMT (2× → correct) and
   never asked WHO pays; the bug survived two cycles in plain sight. **Always audit
   the payer role, not just the amount** — prove with real ledger rows, not the
   artifact's own "engine-ready" labels. Fix is a one-line role swap in
   `emit_trade` / `bridge.translate`.
2. **Selftest-label honesty check.** Docstring claimed "24 checks"; runtime
   registered 11. Two of the 11 were non-informative: a hardcoded-`True` check
   (cannot fail by construction) and a vacuous `all(t[2] <= 1000 for t in [])`
   (empty iterable = vacuous truth). Technique: count call sites
   (`grep -o 'ok(' | wc -l` minus `def ok(`), compare to the docstring claim, and
   eyeball each check for constants/vacuous predicates. A "proof" section that
   asserts instead of tests is a label, not a proof.
3. **Ledger-copy validation (never touch the real ledger).** `shutil.copy` the real
   `ledger/trade.log` to a temp file, append the line under test, then
   `sys.path.insert(0, <inventions/ledger_rail dir>)` BEFORE `import ledger_rail`
   (the module isn't on sys.path by default — forgetting the insert throws
   ModuleNotFoundError), monkeypatch `ledger_rail.TRADE = <copy>`, run
   `ledger_rail.check()`. Expect 0 errors + exactly base+1 lines.
4. **Absence vs latency.** A 3 s-timeout sweep misread the live shop (:8791) as ERR;
   a 6 s re-probe showed HTTP 200. Characterize every listener with BOTH a socket
   probe and an HTTP probe at a generous timeout. WinError 10061 = hard absence
   (the bank, 7th cycle). Timeout/URLError on an OPEN socket = slow or wedged —
   different class, log it honestly, don't call it absence.
5. **Concurrent lanes.** The real ledger grew 355 → 362 during the audit window from
   other agents' settlements. Prove your probes wrote nothing: your copy's count
   must equal the live base at copy time + exactly your appended lines (362+1=363).
6. **Append-only log staging.** Write the section to a `_tmp` file first, then
   append with the MINIMAL single-purpose command `cat tmp >> log && rm tmp` —
   longer verification chains in one command can trip the terminal parser's
   blocklist; run the `grep -c '^## CYCLE'` before/after check as separate calls.
   Verify the header count increments by exactly 1 and the tmp file is gone.

## Findings filed (engagement #12)

| # | Severity | Finding | Status |
|---|---|---|---|
| F1 | HIGH | qty-vs-value 2× misstatement | **CLOSED at source** (AMT 5.00 end-to-end via emitter; F5 wiring RESOLVED) |
| F2 | LOW | float money drift (2.675→2.67) | Closed at emitter (Decimal 2.68 ✓); still open at bridge `translate()` (float) |
| F3 | LOW | zero-price lines approved | Closed at emitter (REJECT ✓); still open at bridge (0.00 APPROVED) |
| F4 | MEDIUM | existence ≠ intent (1M spoof) | Residual CONFIRMED — real book API produces the trade, emitter APPROVES; `ledger_rail --check` has NO per-line balance gate (1M line → 0 errors on copy); intent gate = engine's settlement logic |
| F6 | MEDIUM-HIGH | **money-direction reversal** (seller booked as payer) | NEW — one-line role swap fixes |
| F7 | LOW-MED | selftest label: claims 24, runs 11; F4 "proof" tautological/vacuous | NEW — honest count + real F4 test needed |
| F8 | LOW-MED | dividend engine golden fixtures stale (selftest 31/32, c12 golden 9/13 vs live pool book reserve 136.50; hardcoded 150.25 fixtures; exit codes honest) | NEW — re-base fixtures; c15 dividend arithmetic itself engine-consistent (136.50+51.25=187.75≥150 → full pass-through 51.25 → 136.50, zero drift) |

## Standing surfaces (c15)

- Bank :9988/:9989 — WinError 10061 refused, **7th cycle of absence** (probe
  HTTP+socket, log every refusal; do not rationalize).
- Shop :8791 — socket OPEN, GET /,/price,/menu 200, /admin,/transfer,/%2e%2e/ 404,
  POST /price 501 — till live, vault absent (EV −∞).
- Rob EV: −∞ (no door / no rail). Forge EV: −∞ (intent gate = engine, unreachable).

## Settlement pattern

- Standing full-engagement rate **25.00**; engine pre-registers the commission in
  `survival_state.json` cycle note (c15: "engagement #12 (25.00, banker-commissioned)")
  — check the engine note BEFORE filing, cite it as the == match for the banker's B15-xx.
- No double-dip: the F1 bounty (25.00, inventor's lane) is never claimed by the
  auditor; verification work is engagement work.
- Deliverables: `underworld/audit_finding_cycle15.md`, `underworld/cycle15_audit.py`
  (20 probes, exit 0), append CYCLE 15 section to `underworld/outlaw_log.md`
  (APPEND-ONLY; header count 12→13 verified), reply in the four-part structure
  (rob-lane result · audit verdict · straight reasoning · settlement request).
