# Freedom Engine Cycle 18 — Deployment-Audit Loop, Sibling-Cron Attribution, Grep-Based SR Extraction

Runbook for the cycle-18 FREEDOM ENGINE execution (2026-08-10). Reuse the
TECHNIQUES, not the numbers. Per-lane detail lives in
`outlaw-cycle18-deployment-audit.md`. Supersedes nothing in the c17 runbook —
extends it with what c18 proved new.

## 1. NEW — the deployment-verification loop (a reusable engagement class)

c18's engagement #15 created a three-lane loop worth reusing every time a lane
ships a fix TOOL (vs a fix already in the live path):
inventor BUILDS a deployment harness → outlaw ADVERSARIALLY VERIFIES the
deployment (is the fix actually wired into the live path?) → banker COMMISSIONS
it conditional on engine re-verification. The banker's scoping question for
"what is the next engagement" after any tool-shipment: *audit the deployment,
not the code.* Open item "the seam is sewn at the tool; the deployment is the
buyer's" is the standing trigger — the next engagement should be the
verification of whoever wired it.

## 2. NEW — verify with TWO independent re-runs (one per lane involved)

c17 verified one conditional artifact (outlaw audit). c18's commission was
conditional on BOTH sides of the seam, so the engine re-ran BOTH, read-only:
- `python underworld/cycle18_audit.py` → **48/48 PASS, exit 0**
- `python inventions/bridge_gate_deployment_harness/bridge_gate_deployment_harness.py --audit` → **WIRED**, direction DOCTOR→BEGGAR correct, read-only proven

Rule extension: when a settlement line references two lanes' deliverables
(commission == audit result == inventor's deployment), re-run each deliverable
independently before paying. One re-run is not enough when two pens signed.

## 3. NEW — sibling-cron attribution (city_ledger.md is SHARED)

During c18 verification, `city_ledger.md` showed an mtime INSIDE the subagent
window — looked like a lane violated the engine-owned-files rule. It was the
STUDY-CYCLE cron (school academy job, every 10 min) appending graduations to
the same ledger. Attribution rule:
- Engine-owned files whose untouched-mtime proves lane discipline:
  `economy/wallets.json`, `survival/survival_state.json`, `ledger/trade.log`,
  `inventions/stair_insurance_pool/pool_book.json` (plus registry/census).
- `city_ledger.md` is NOT a lane-integrity signal — two crons append it.
  If its tail shows a GRADUATION block, it was the school cron; a lane section
  means a lane. Check the tail before accusing anyone.

## 4. NEW — extract settlement tables with grep, not regex

A `^\|\s*(REF)\s*\|...` row regex matched only the banker's and outlaw's tables;
the merchant/inventor/explorer/beggar tables failed because amounts are SIGNED
(`+16.00`) and use the UNICODE minus (`−10.00`), which a `[0-9.]+` pattern
rejects. Reliable extraction: `grep -A 12 "SETTLEMENT REQUESTS" <lane file>` per
file. Cross-check refs between lanes by grepping the ref names (`B18-03`,
`SR-M18-03`) — the dedup manifest is built from the `== <other-ref>, settle once`
annotations both lanes were told to write.

## 5. Settle-once dedup manifest (c18)

- B18-01 == SR-BG18-01 (pool 12th collection 51.25) · B18-02 == SR-BG18-05
  (7th dividend 51.25 full pass-through) — one pool cycle.
- B18-03 == SR-M18-03 (water 4.00) · B18-04 == SR-O18-01 (commission 25.00).
- SR-M18-05 == SR-BG18-03 (L-04 eggs 5.00) · SR-M18-07 == SR-BG18-02 (wage
  19.00) · SR-M18-08 == SR-BG18-04 (feed 6.00).
- SR-M18-09 (garrison pitch) = **0.00 NOT BOOKED** — an open offer rows into
  the table for the record but must NOT move money; the settlement script
  skips zero rows. New pattern: unbooked offers are still filed so the ledger
  narrative can cite them.

## 6. Ladder termination condition — trip it and the narrative changes

The banker's covenant: the ladder ends when the redeemed holds **≥ 4 rations
with no commission in flight**. c18 tripped it: OUTLAW 40.00 → 65.00 = 4.33
rations, B18-04 settled. c19+ banker narrative must NOT simply renew a "next
rung" — the standing-rate commission relationship needs re-framing (or a new
covenant), and the open item "OUTLAW citizenship" becomes the natural next
step. Watch for the banker re-inventing the ladder instead of ending it.

## 7. Cycle-execution skeleton (c18 numbers for reference)

1. State read: survival_state cycle 17 → 18, treasury 3,258.00; wallets 24 /
   16,731.50; pool reserve 136.50.
2. `survival/cycle18_levy.py`: 24/24 paid 15.00 = 360.00 → treasury 3,618.00;
   OUTLAW → 40.00 (2.67 rations, tightest 3rd cycle), BEGGAR → 48.50 (3.23 —
   first time under 50.00 since c5, the poverty lane turns real).
3. 6-lane batch dispatch (same context recipe as c17: post-levy wallet, ration
   position, READ-FIRST pointer to prior-cycle artifact, decision space,
   constraint block). All 6 ran SYNCHRONOUSLY; results inline.
4. Verify: `ls -la` all artifacts; re-run conditional deliverables (§2); mtime
   check engine-owned files (§3); VM state (`VBoxManage showvminfo` → RUNNING —
   seeded windows left running per three-state policy: OFF kills / SAVED
   freezes / RUNNING hosts).
5. `survival/cycle18_settlement.py` with the §5 manifest; assert invariant
   20,126.00 (wallets + treasury + pool). Result: wallets 16,521.50 · treasury
   3,468.00 · pool 136.50 · BEGGAR 66.50 (4.43) · OUTLAW 65.00 (4.33) ·
   INVENTOR-FREEWILL 799.00 · EXPLORER-FREEWILL 1,770.00 · 0 HUNGRY · 0
   STARVING · 5 DEAD (13th clean cycle). trade.log 514 → 567 lines.
6. Append `survival/cycle18_ledger_section.md` to `city_ledger.md`.
7. Report < 300 words with the 6 decisions, verified artifacts, beggar +
   outlaw choices/outcomes.

## 8. Environment ops notes (host, not city)

- Localhost port **:3000 = Hermes WhatsApp bridge** (bridge.js) — when the
  explorer's host scan finds a new open port, check for Hermes infra before
  reporting "city drift". Identified and dispositioned as host infra in c18.
- VM fuzz windows seeded as `fuzz_avc_asan6` / `fuzz_hevc_asan6` /
  `fuzz_avc_patched_asan4` / `fuzz_jpeg4`; corpora intact across cycles
  (2778/1724/4746/5090); crash queue 52/9/0 unchanged — a stable baseline.
- `pgrep -af libFuzzer` self-matches its own wrapper; the explorer's guard uses
  a bracket trick, and a double-seed guard (exit 5) proved itself live.
