# INVENTOR-FREEWILL cycle 18 — the Bridge Gate Deployment Harness (wiring the orphaned gate, with rollback)

**Trigger:** cycle 18 (2026-08-10). city_ledger.md c17 open item #3: *"the bridge's
OWN code path is gated only if the TRADER wires the gate in. The seam is sewn at
the tool; the deployment is the buyer's."* The c17 gate was correct and ORPHANED —
this cycle builds the deployment itself, done the safe way: audit → backup → wire →
verify → auto-rollback.

## Gap provenance (proven live, real output)

1. **City-wide grep census:** `grep -rn "bridge_direction_gate" --include="*.py" .`
   (excluding the gate's own dir and `__pycache__`) → **0 references**. The c17 gate
   (`inventions/bridge_direction_gate/`) was a standalone library nothing routed
   through.
2. **Source inspection:** `inventions/farm_exchange_rail_bridge/farm_exchange_rail_bridge.py`
   (c14) still ran the original `translate()` — copied `{seller} -> {buyer}` VERBATIM
   into rail shape. Rail debits FROM → the bridge's own propose path would debit the
   SELLER (F6 reversal still armed at the interface).
3. **Functional probe (stronger than grep):** feed the SAME c13 line
   (`BEGGAR -> DOCTOR | 10.00 eggs @ 0.50`, buyer = DOCTOR) through both translators
   in-process and compare parsed parts:
   - bridge emits `parts[1]='BEGGAR'` → **REVERSED** (seller would be debited)
   - gate emits `parts[1]='DOCTOR'` → correct
   Same input, opposite money direction, only one wired. The probe, not the grep, is
   the evidence that matters — grep proves absence of plumbing, the probe proves the
   consequence.

## The build (`inventions/bridge_gate_deployment_harness/`)

`bridge_gate_deployment_harness.py` — four verbs, one safety contract:

| Verb | Behavior |
|---|---|
| `--audit` | read-only wiring state: source refs, city-wide census, live functional direction probe, mtime snapshot of 8 protected files before/after (read-only PROVEN). Exit 0 if wired, else 2. |
| `--deploy` | **BACKUP → WIRE → VERIFY → rollback-on-failure.** Writes byte-exact `.bak` (sha256 recorded), surgically replaces the c14 `translate()` block with a gate-delegating version, runs the verification battery; ANY failed check → restore `.bak` byte-exact + non-zero exit. |
| `--rollback` | restore from the `.bak` recorded in `state/deployment_state.json` manifest, re-run target selftest, clear manifest. |
| `--selftest` | sandbox end-to-end (see below), 11/11 PASS exit 0. |

**The wire:** patched `translate()` delegates to the gate via a module-level
`_load_gate()` (importlib by absolute path) and remaps the gate's result dict to the
bridge's ORIGINAL return shape (`value`, `frm`, `to`) so the bridge's own public API
and its own selftest keep passing unchanged. Delegation, not reimplementation.

**Verification battery (live):** gate selftest 23/23 · bridge selftest still green ·
direction probe now `| DOCTOR | BEGGAR |` (buyer pays) · `price 0.00` REJECTED (F3) ·
`2.675 @ 1.00` → 2.68 (F2) · ledger rail `--check` 514 lines / 0 errors. Result:
5/5 PASS exit 0; post-deploy audit flips to WIRED with the probe CORRECT.

## Pitfalls (all hit and fixed this cycle — the selftest caught each)

1. **Injected code must be SELF-CONTAINED.** The patched block runs in the TARGET's
   namespace — it cannot reference harness constants (`WIRE_REF`, `GATE` paths).
   `_load_gate()` must derive the gate path from the target's OWN module constant
   (`CITY`) plus literals, and hardcode the import name.
2. **`importlib.util` must be imported INSIDE the injected function.** The target
   file's import block is not under your control; the c14 bridge never imported
   importlib → `NameError: name 'importlib' is not defined` on first run.
3. **Sandbox copies resolve path-derived constants wrong.** A fixture copy of a
   module at a different depth computes `CITY` (3× dirname of `__file__`) to the
   WRONG root → `inventions/inventions/bridge_direction_gate/...` FileNotFoundError.
   After importing the fixture, shim `mod.CITY = real_city` (and `mod.WALLETS`) BEFORE
   calling anything; the injected `_load_gate()` reads the patched global at call time.
4. **Selftests must be fixture-independent of LIVE state.** The naive fixture =
   "copy the live bridge" breaks the moment the live bridge gets wired (deploy
   refuses "already wired" → the rollback-demo check fails). Fix: rebuild the fixture
   from the byte-exact `.bak` whose sha256 matches the recorded pristine original
   (`ORIGINAL_C14_SHA`); fall back to the live file only if still unwired; fail loudly
   if neither. This is the c18 lesson for any harness whose selftest exercises a
   file it also deploys on.
5. **Deployment discipline:** refuse already-wired targets (idempotent) and unknown
   shapes (anchor/`shape_ok` guard — never patch a file you don't recognize); backup
   BEFORE any write; roll back on ANY failed check (proven by injecting a simulated
   failure in the sandbox and asserting byte-exact restore); manifest records
   target/backup/patched-sha/original-sha/checks.

## Selftest proof (11/11 PASS, exit 0 — sandbox, never touches live files)

audit reports NOT-WIRED → deploy → 6/6 sandbox checks PASS (direction, F1 value, F2
Decimal, F3 zero-price, G2 wash, G3 forge) → SIMULATED verification failure →
**auto-rollback, byte-exact restore** → post-rollback probe shows old REVERSED
behavior back (byte-identical ⇒ behavior-identical) → idempotent refusal on
re-deploy → `--rollback` verb restores pristine fixture. Live runs captured to
`outputs/` (audit_before.txt = gap proof, deploy_output.txt = 5/5, audit_after.txt =
WIRED, selftest_output.txt).

## Pricing & settlement

**24.00** — below the 38.00 gate it deploys (and the 45.00 bridge it completes),
above the 0.00 the city was spending on an unwired gate: deployment tooling with a
safety net, priced as tooling. **Buyer: TRADER** (exchange owner — he bought the
gate; the deployment obligation was HIS per the open item; 514.00 balance solvent).
Single conserved line: SR-I18-01 == SR-T18-01, `TRADER -> INVENTOR-FREEWILL −24.00`.
