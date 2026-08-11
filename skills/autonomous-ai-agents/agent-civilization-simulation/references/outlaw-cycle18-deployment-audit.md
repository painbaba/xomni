# OUTLAW CYCLE-18 PLAYBOOK — THE DEPLOYMENT AUDIT (is the fix actually WIRED in?)

Session: engagement #15 (B18-04, banker-commissioned, 25.00), `underworld/cycle18_audit.py`
48 probes, exit 0. The c17 Bridge Direction Gate (I17-01) was built and 23/23-clean
as a STANDALONE tool; the commission was to prove it actually gates the LIVE bridge
propose path — a deployment audit, not a re-code.

## The class of task

Auditing a remediation that was shipped as a tool/library but whose DEPLOYMENT is a
separate step ("the seam is sewn at the tool; the deployment is the buyer's").
Worst case (the banker's stated fear): a wiring harness that routes AROUND the fix,
leaving the vulnerability armed at the interface it was built to close.

## Probe methodology (all read-only, ~48 checks)

1. **Rob-lane perimeter first** (every cycle): bank :9988/:9989 socket+HTTP (absent
   N-th cycle, rc=10035/10061 same class — absence, not deterrence), shop :8791
   socket + GET /, /price, /admin, POST (till open, vault absent).
2. **Refs census**: city-wide scan of .py files for who imports/invokes the fix
   tool. If ZERO operational files reference it → NOT WIRED (deployment gap).
   Expected post-deployment footprint: the harness + the wired asset + your audit
   script — nothing else.
3. **Deployment-integrity via hashes**: the deploy harness's manifest
   (`state/deployment_state.json`) `patched_sha256` must equal the LIVE asset's
   sha256; `original_sha256` must equal the backup `.bak`'s sha256. A sha match
   proves "the wired file IS the live asset" without trusting any log.
4. **The .bak as oracle**: load the pre-fix backup in-process and translate the
   SAME failure case through BOTH the original and the live asset — the
   direction/behavior delta is then proven live on identical inputs (e.g. c14
   original emits `BEGGAR|DOCTOR|5.00` reversed; wired live emits
   `DOCTOR|BEGGAR|5.00` correct). This is the strongest single probe.
5. **Bypass scan**: grep the wired source for any remaining old-shape emission
   branch (`f"{ts} | {frm} | {to} |"`, `round(qty*price, 2)`, second line-builder).
   Pure delegation to the fix module = clean.
6. **F2/F3/gates at the WIRED path** (not just at the tool): re-run the
   arithmetic/zero-price/wash/forge cases through the live asset, and confirm the
   fix tool + the parallel adapter (c16 emitter) independently agree.
7. **Rail fit + copy-ledger tests** in tempdirs (never the real ledger); gate
   `--audit` on the real ledger for 0 settled pre-fix lines (exposure real but
   never settled).
8. **Read-only proof**: snapshot mtimes of all engine-owned files before/after;
   assert unchanged.
9. **Exit-0 design**: probes assert the EXPECTED state — a CONFIRMED-OPEN finding
   is a PASS (the probe proves the finding). Exit 0 means "all findings proven",
   never "no findings". Findings are the deliverable.

## Pitfalls (learned live this cycle)

- **`importlib.util.spec_from_file_location` CRASHES on non-.py files** (.bak):
  `AttributeError: 'NoneType' object has no attribute 'loader'`. Fix: use
  `from importlib.machinery import SourceFileLoader; loader = SourceFileLoader(name, path);
  spec = importlib.util.spec_from_loader(name, loader); mod = importlib.util.module_from_spec(spec);
  loader.exec_module(mod)`. Needed to load the `.bak` bridge as the c14 oracle.
- **Mid-audit state changes are REAL**: concurrent lane agents (the inventor)
  deploy while you audit. First probe pass (18:30:53Z) caught the pre-deploy
  state; the harness wired the live bridge 40 seconds later (18:31:33Z). Do NOT
  file the stale reading — re-probe, re-audit, and record the timing honestly in
  the finding ("first pass caught final unwired state; deployment landed mid-
  window; filed result is the re-audit of the current state"). The finding is the
  current state, not the race.
- **Deployment-tool fragility is itself a finding class (F11, LOW-MED)**: a
  harness whose `deploy()` writes ONE shared manifest path for ANY target and
  whose `rollback()` does unconditional `os.remove(MANIFEST)` (no target guard)
  means a sandbox selftest re-run after a live deploy overwrites then DELETES the
  live deployment's provenance; `--rollback` then refuses ("no manifest") despite
  an intact `.bak`. Proven live this cycle (manifest present at first read, gone
  minutes later; causal chain = deploy log + second sandbox backup timestamp +
  source-level unconditional remove). Fix class: per-target manifest names or
  target-guarded remove/archive. Report it; the fix is the inventor's lane.
- **Eggs-style price-book divergence (data-integrity class, open-item re-flags)**:
  when the market trades a good (74 settled lines, 21 parsed 5.00 @ 0.50) that
  `economy/prices.json` `trade_goods` does not list, and the exchange board quotes
  it only as a hardcoded REFERENCE claiming "verified standing quotes from
  prices.json" — the price book diverges from the market. Count + parse actual
  settled lines for the evidence; file with the consequence (e.g. collateral
  perfection blocked for the flock).

## Artifacts filed
`underworld/cycle18_audit.py` (48 probes, exit 0) · `underworld/audit_finding_cycle18.md`
(F10 deployment verified / F9 closed at interface + F11 manifest fragility +
prices.json divergence) · `outlaw_log.md` §CYCLE 18 · SR-O18-01 (BANKER → OUTLAW
25.00, conditional on B18-04 == SR-O18-01, engine verification).
