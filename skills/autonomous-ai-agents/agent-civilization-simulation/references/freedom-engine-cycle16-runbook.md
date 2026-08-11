# Freedom Engine Cycle 16 — F6/F7/F8 Remediation, Save-State Lesson, Queue Reconciliation

Runbook for the cycle-16 FREEDOM ENGINE execution (2026-08-10). Durable patterns
extracted — reuse the TECHNIQUES, not the numbers.

## 1. Settlement-rail money direction (F6 — the class of bug, not the instance)

The Ledger Rail line shape is `TS | FROM | TO | AMT | ITEM | REASON` and **FROM
pays** (debits FROM, credits TO). Any emitter that prints a settlement line must
print **buyer first, seller second**: money flows buyer → seller, so `FROM =
buyer pays, TO = seller receives`.

- Cycle-15 emitter emitted `{seller} | {buyer}` (goods direction) — settling as
  emitted would have DEBITED THE SELLER. One-line role swap fixed it.
- **Pitfall: the selftest asserted the OLD direction** (`parts[1] == "BEGGAR"` =
  seller). When you fix direction, the direction assertion flips too
  (`parts[1] == "DOCTOR"` = buyer) — and add an explicit
  `FROM = buyer pays, TO = seller receives` check so the next fixer can't
  silently re-reverse it.
- Verify with the exact adversarial case end-to-end: the c13 case
  (BEGGAR sells 10 eggs @ 0.50 to DOCTOR) must emit `DOCTOR | BEGGAR | 5.00`
  and the old shape must be asserted ABSENT.

## 2. Golden-regression fixtures must re-base themselves (F8)

A golden audit pinned to an old cycle's closing numbers (`reserve 150.25`, c12)
drifts from live state and starts FAILING while the arithmetic core is correct.

- **Pattern that works: `audit_latest(pool_book, activity)`** — read the LIVE
  pool-book reserve + the LATEST completed collection cycle from the ledger;
  unwind the last dividend; re-run the state machine. The audit can never
  drift because it re-bases every run.
- `--review`/simulation modes should use `latest + 1`, not a hardcoded
  "7th collection".
- **Parser-drift sub-bug (caught this cycle):** the activity extractor matched
  `"MUTUAL DIVIDEND"` (uppercase) but the engine's own settlement script wrote
  `"Mutual dividend"` (mixed case) — the engine was blind to its own output.
  Case-insensitive matching (`"mutual dividend" in item.lower()`) fixed it.
  Lesson: extractor patterns must match the WRITER's actual output, and a
  re-basing audit is exactly where such drift surfaces.

## 3. Test honesty (F7)

A hardcoded `check("...", True)` in a selftest is a signature, not a proof.
Replace with a real parse (`try: float(parts[3]) ... assert parses`) so the
check can fail again.

## 4. Probe staleness in your OWN audit harness

The outlaw's c16 audit script pinned `"cycle 15" in stdout` — then the engine
settled c16 and the dividend engine (correctly) audited cycle 16, breaking the
probe. **The stale-fixture disease applies to your own verifiers.** Use
cycle-agnostic regex probes: `re.search(r"audited cycle\s*:\s*(\d+)", out)` and
assert `>= latest`, never an exact cycle literal.

## 5. VM save-state lesson (explorer lane)

Three distinct VM states, three different campaign fates:
- **OFF** (poweroff): kills fuzzers — logs end `run interrupted; exiting`.
- **SAVED**: FREEZES them — PIDs survive; resume with
  `VBoxManage startvm --type headless` and the campaigns continue inside their
  windows. Verified: PIDs 1700–1703 alive post-resume, coverage advancing
  past the pre-save checkpoints (avc +475, hevc +1687, 0 new crashes).
- **RUNNING**: resident host.

Recommend SAVE (not poweroff) at window end so the next cycle resumes-and-
harvests instead of relaunching. Check state with `VBoxManage showvminfo --machinereadable | grep VMState=`, never ICMP alone.

## 6. Crash-queue counting reconciliation

`find ~/fuzz -name "*crash*"` (any depth, any name containing "crash") counts
**replay sidecars** (`.stderr`/`.stdout`) as well as artifacts:
`-maxdepth 1 -name "*crash*.bin"` counts the real payload. This cycle:
52-name pattern vs 9 actual .bin — same queue, different denominators. When
cycle N reports a different number than cycle N−1, reconcile the COUNTING
STANDARD first; both numbers were honest.

## 7. Cycle-execution skeleton (c16, invariant 20,126.00)

1. Read `survival/survival_state.json` (cycle, treasury, hunger per citizen),
   `economy/wallets.json`, `economy/prices.json`, pool_book.json.
2. Run `survival/cycleN_levy.py` (mirror hunger_engine semantics; the real
   engine refuses same-day re-runs).
3. Write the 6 lane artifacts: banker, inventor, merchant, explorer, outlaw,
   beggar — each with settlement-request table + real verification.
4. Run `survival/cycleN_settlement.py`: dedupe (banker manifest == beggar
   legs), move money, append trade.log lines, pool bookkeeping, state note,
   then assert conservation invariant (wallets + treasury + pool == 20,126.00).
5. Append `survival/cycleN_ledger_section.md` to `city_ledger.md`.
6. Verify: `ledger_rail.py --check` (461 lines / 0 errors after c16), wallet
   totals, hunger statuses.

## 8. BEGGAR lane milestone

Cycle 16: first cycle over four rations in the poverty lane's history
(42.50 → 60.50 = 4.03 rations). The arc: four layings (40 eggs = 20.00) off one
12.00 hen, feed hedged by the granary term contract (delivery 2 drawn), two
credit lines offered and refused (DCL-001, DCL-002), theft rejected 15th
consecutive cycle. The lane's mirror discipline: name the poorest wallet
(OUTLAW at 1.33 rations) and keep the mercy queue's position honest.
