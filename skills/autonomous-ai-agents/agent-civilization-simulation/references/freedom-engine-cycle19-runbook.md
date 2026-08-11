# Freedom Engine Cycle 19 — Engine Arbitration of a Lane Refusal (the new governance pattern)

Runbook for the cycle-19 FREEDOM ENGINE execution (2026-08-11). The c17 runbook
(`freedom-engine-cycle17-runbook.md`) covers the baseline mechanics — synchronous
delegate_task in cron, engine re-runs of conditional deliveries, settle-once
dedup, the 20,126.00 invariant, the 7-step cycle skeleton. This file documents
the NEW governance element that emerged at c19: **the engine settling verified
work against a commissioning lane's explicit refusal.**

## The conflict (c19)

- **BANKER** declared the redemption ladder CLOSED (B19-04 = 0.00 redemption
  certificate): the c18-close termination condition (≥4 rations, no commission
  in flight — 4.33 rations at c18 settlement) was MET, and a scheduled levy
  dropping the wallet to 3.33 rations is not a revocation. Therefore: **no
  engagement #16 commissioned** — "no real open security item exists in the
  outlaw's lane this cycle."
- **OUTLAW** disagreed with the *premise*, not the covenant: took rung #6
  anyway (SR-O19-01, 25.00, conditional on delivery + engine verification) and
  audited the **survival engine's own arithmetic** — the one subsystem nobody
  had audited in 19 cycles (see `outlaw-cycle19-survival-engine-audit.md`).
- **ENGINE ruling**: the banker's no-commission premise was **falsified by the
  delivery itself** (the survival engine WAS a real open item; the audit found
  F12a/F12b/F12c/F13). The work was re-run by the engine (27/27 probes, exit 0).
  Result: **SR-O19-01 settled at the standing 25.00 rate** — the ladder's sixth
  and final rung; OUTLAW 50.00 → 75.00 = 5.00 rations; B19-04 certificate still
  recorded (redemption formally closed) alongside the paid rung.

## The durable rule (engine-arbitration of lane refusals)

When a commissioning lane refuses to pay/commission and another lane delivers
verified work anyway:

1. **Separate the covenant from its factual premise.** The banker's covenant
   (ladder terminates at ≥4 rations, nothing in flight) held. His *premise*
   ("no open item in the outlaw's lane") was a factual claim — check it against
   the delivery, don't let the refusal's confidence immunize it.
2. **Verify the delivery independently** (engine re-runs the audit script,
   exit 0), then check whether the refusal's premise still stands. If the
   delivery disproves it, the refusal was based on incomplete information, not
   on a broken contract.
3. **Settle at the standing rate** (the full 25.00, not a haggled price) and
   record BOTH: the lane's refusal decision (it was rational under its info)
   AND the engine's ruling (verified work gets paid). The ledger section states
   the ruling explicitly so the refusing lane isn't recorded as "overridden" —
   its decision is honored as a decision; the settlement is the engine's own.
4. **No double-dip:** the fix for findings stays in the finding lane's
   responsibility (inventor fixes F11, auditor files eggs prices) — settlement
   pays only the audit delivery itself.

## Why this matters for future cycles

Lanes will disagree. The c19 resolution shows the engine's role is not "execute
the manifest as written" — it is the arbiter of last resort: verify, rule,
settle, and write both sides into the ledger. Refusing lanes remain rational
under their information; delivered, verified work remains paid. This is what
keeps conditional-settlement economics honest when a banker and an outlaw
disagree about whether a ladder is finished.

## Cycle-19 execution specifics (c19 numbers, for reference)

1. Pre-levy state: cycle 18, treasury 3,468.00, 24 wallets (16,521.50), pool
   reserve 136.50, BEGGAR 66.50 (4.43 r) / OUTLAW 65.00 (4.33 r) tightest.
2. `survival/cycle19_levy.py`: 24/24 paid 15.00 = 360.00 → treasury 3,828.00;
   BEGGAR 51.50 (3.43), OUTLAW 50.00 (3.33) — both tightest, both above the
   3-ration alarm line. 0 HUNGRY / 0 STARVING / 5 DEAD.
3. Dispatch 6 lanes; verify artifacts on disk (sizes); engine re-runs
   `underworld/cycle19_audit.py` → 27/27 exit 0.
4. `survival/cycle19_settlement.py`: 13th pool collection 51.25 (20×2.50 +
   BEGGAR 1.25) → reserve 187.75 → 8th dividend 51.25 full pass-through →
   136.50; banker water == merchant water (B19-03 == M19-03); engagement #16 ==
   SR-O19-01 (settle once); I19-01 TRADER→INVENTOR 14.00 (harness manifest
   guard — F11 closed in code, 38/38 selftest); E19-01 TREASURY→EXPLORER
   150.00 (harvest: 272,104 fuzz runs, 0 ASAN, VM frozen savestate rc=0).
5. Invariant: wallets 16,311.50 + treasury 3,678.00 + pool 136.50 = 20,126.00 ✓.
   Rail 567/0 → 620/0 after settlement.
6. Append `survival/cycle19_ledger_section.md` to `city_ledger.md`.
7. Report <300 words: 6 decisions + knowledge classes, verified artifacts,
   beggar + outlaw choices/outcomes.

## Artifacts produced (all verified)
`bank/banker_freewill_cycle19.md` · `inventions/harness_manifest_guard/` +
`inventions/inventor_freewill_cycle19.md` · `business/merchant_freewill_cycle19.md`
+ `business/garrison_mess_offer_cycle19.md` · `explorer/expedition_report_cycle19.md`
(+ cycle19_kali_recon.py, pulse_pass, run log) · `underworld/cycle19_audit.py` +
`audit_finding_cycle19.md` + outlaw_log.md §CYCLE 19 ·
`survival/beggar_log_cycle19.md` + letter + job-wanted · `survival/cycle19_levy.py`
+ `cycle19_settlement.py` + `cycle19_ledger_section.md`.
