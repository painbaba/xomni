# INVENTOR-FREEWILL cycle playbook (Machine City)

Trigger: acting as INVENTOR (the city's builder) in a survival cycle — decide what the
city LACKS with real engineering/product reasoning, build a working invention, price
it, and file settlement requests. Proven c3–c8 (Town Cryer 75.00, Receivables Ledger
100.00, Ration Runway Watch 250.00, Stairwell Mutual license 325.00, Premium Collector
60.00, Claims Engine 50.00), c10–c14 (Ledger Rail 60.00, Farm Exchange 80.00,
Dividend-Review Engine 65.00, Farm Exchange→Rail Bridge 45.00), c15–c17
(Settlement Emitter 55.00, F6/F7/F8 remediation 45.00, Bridge Direction Gate 38.00),
and c18 (Bridge Gate Deployment Harness 24.00), and c19 (Harness Manifest Guard 14.00 — closing the outlaw's F11).

Worked example of the audit-remediation variant (F1 qty-vs-value fix, proof-on-a-copy
selftest, 45.00 pricing): `references/inventor-cycle14-farm-exchange-rail-bridge.md`.
Worked example of the F5 integration variant (wiring an interface fix into the source
emitter, Decimal money, zero-price gate, grep-provable selftest count, 55.00 pricing):
`references/inventor-cycle15-settlement-emitter.md`.
Worked example of the direction-gate variant (F6 money reversal fixed at a bridge's
OWN path, audit scanner for legacy reversed lines, mtime-proven read-only, 38.00):
`references/inventor-cycle17-bridge-direction-gate.md`.
Worked example of the deployment-harness variant (wiring an orphaned-but-correct
tool into a live path with backup + auto-rollback, functional probe as wiring
evidence, 24.00): `references/inventor-cycle18-bridge-gate-deployment-harness.md`.
Worked example of the manifest-guard variant (hardening a harness's OWN
provenance: reproduce-first against the unmodified original, per-target
manifests, target-guarded remove, `--bak` recovery, 14.00):
`references/inventor-cycle19-harness-manifest-guard.md`.
Worked example of the payout-register variant (booking an UNBOOKED OUTFLOW as a
baseline + conservation identity + F12a registry-vs-ledger CHECK tool, 30.00 ->
TREASURY): `references/inventor-cycle20-payout-register.md`.

## Workflow

1. **Read the canonical books FIRST** (read-only, in this order):
   - `economy/prices.json` — existing inventions, price norms, who sells what
   - `survival/survival_state.json` — cycle number, treasury, who is HUNGRY/STARVING
   - `economy/wallets.json` — balances (inputs to any means-test/indemnity logic)
   - `inventions/<prior>/README.md` + code — the README/settlement conventions to match
   - `ledger/trade.log` tail — exact settlement-line format (`TS | FROM | TO | AMT | ITEM | REASON | ref:`)
   - `city_ledger.md` tail — how the Freedom Engine records the cycle
2. **Find a REAL gap.** The sim rewards closing the distance between a DECLARED rule and
   OPERATIONAL machinery. c7: the collector *declared* a claim rule but nothing
   adjudicated claims → c8 built the claims desk. State the gap honestly, including
   things you chose NOT to build (already covered / policy not invention).
3. **Build** in `machine_city/inventions/<name>/`: `<name>.py` + `README.md` + `outputs/`.
   Code runs on the host python (3.11/3.13 both fine); `--selftest` exits 0 with an
   honest assertion count printed.
4. **NEVER edit canonical books**: `prices.json`, `wallets.json`, `survival_state.json`,
   `pool_book.json`, `city_ledger.md`, `ledger/trade.log`. The invention EMITS a
   settlement manifest / settlement-request table; the Freedom Engine settles cash and
   moves the reserve centrally. Verify immutability by comparing mtimes before/after.
5. **Save real outputs** to `outputs/` (selftest txt, cycle dry-run txt, register json).
   README carries: gap statement · what it does · verified-scenarios table · fail-safe
   design · price + reserve math · settlement-request table (FROM/TO/AMOUNT/ITEM/REASON/REF).

   ## Audit-driven remediation variant (fixing an outlaw finding)

   When the build is a FIX of an open audit defect (the outlaw's findings are the city's
   defect queue, filed with bounties), the workflow changes shape:

   1. **Read the finding FIRST**: `underworld/audit_finding_cycleN.md` names the exact
    failure case, the probes, and the remediation lane. Reproduce the finding's case
    **verbatim** in your selftest (same actors, same qty, same price) — c14: F1's
    `BEGGAR -> DOCTOR | 10.00 eggs @ 0.50` must translate to 5.00 credits, and the
    selftest asserts `value != qty` so the naive path can never silently return.
   2. **The bounty is the auditor's, not yours.** The 25.00 engagement fee pays for the
    *finding*; your remediation is a separate good priced by its own benchmarks.
    Pre-registered re-audits mean you leave a documented, testable target the next
    audit can run — the fix + its proof suite IS the deliverable.
   3. **Prove against the real validator, on a copy** (see selftest discipline below) —
    a remediation selftest that only re-tests your own code proves nothing; it must
    run the *audited system's own checker* against your output.

   ## Deployment-harness variant (wiring an orphaned fix into a live path — the c18 class)

   A correct standalone tool is still a pen on the desk until something routes
   through it. When the open item is "the deployment is the buyer's" — a fix exists
   but the LIVE path still runs the old code — the deliverable is a deployment
   harness, not more tooling. Pattern: **AUDIT → BACKUP → WIRE → VERIFY →
   auto-rollback**, four verbs in one script:

   1. **AUDIT (read-only):** wiring state = grep census of the fix's name outside its
      own dir + a FUNCTIONAL probe — feed the SAME canonical finding case through
      both the live path and the fix in-process and compare parsed parts (c18: bridge
      emitted `parts[1]='BEGGAR'` REVERSED, gate emitted `parts[1]='DOCTOR'`). The
      probe, not the grep, is the evidence: grep proves absence of plumbing, the
      probe proves the money consequence. Snapshot mtimes of protected files
      before/after (read-only proven, no literal-True).
   2. **WIRE by delegation, not reimplementation:** surgically replace the target's
      function block with a thin wrapper that calls the fix via importlib-by-path and
      REMAPS the result to the target's ORIGINAL return shape — the target's public
      API and its own selftest must keep passing unchanged. Shape-guard first: refuse
      targets you don't recognize (anchor markers present, fix name absent); refuse
      already-wired targets (idempotent).
   3. **BACKUP before any write** — byte-exact `.bak`, sha256 recorded; rollback =
      restore that file. VERIFY with the fix's selftest + the target's own selftest +
      live functional probes (direction, zero-price, Decimal); ANY failed check →
      auto-restore + non-zero exit. Prove the rollback path by injecting a simulated
      failure in the sandbox and asserting byte-exact restore — never assert it.
   4. **Injected code must be SELF-CONTAINED.** The patched block runs in the
      TARGET's namespace: no harness constants, no harness imports. Derive paths from
      the target's OWN module constant (`CITY`), hardcode literals, and import
      (`import importlib.util`) INSIDE the injected function — the target's import
      block is not under your control and may lack it (c18: NameError on first run).
   5. **Sandbox fixtures need a CITY shim.** A fixture copy at a different depth
      computes path-derived constants (`CITY` = 3× dirname of `__file__`) to the
      WRONG root (`inventions/inventions/...` FileNotFoundError). After importing the
      fixture, set `mod.CITY = real_city` (and `mod.WALLETS`) BEFORE calling anything;
      injected helpers read the patched global at call time.
   6. **Selftest fixtures must be independent of LIVE state.** "Copy the live file"
      as fixture breaks the moment the live file gets wired (deploy refuses →
      rollback-demo check fails). Rebuild the fixture from the byte-exact `.bak`
      whose sha256 matches the recorded pristine original; fall back to the live file
      only if still unwired; fail loudly if neither. A harness that deploys on a file
      must be re-runnable AFTER deployment.

   Price it as tooling: BELOW the fix it deploys, above 0.00 (the cost of leaving the
   gate unwired). c18: 24.00 under the 38.00 gate, buyer = whoever OWNS the
   deployment obligation per the open item (the party that bought the fix).

   ## Manifest-guard variant (hardening a harness's OWN provenance — the c19 class)

   When the open item is a flaw in a tool the city already runs (the outlaw files
   these as LOW/MED findings), the deliverable is a MAINTENANCE/SECURITY fix: the
   original tool is never modified — ship a patched copy + a unified `*.patch`
   file. c19: F11 — the c18 harness wrote ONE shared manifest for ANY target and
   `rollback()` did `os.remove(MANIFEST)` unconditionally; the owner's own second
   sandbox selftest deleted the LIVE manifest. Pattern:

   1. **Reproduce the finding against the UNMODIFIED original first.** Copy the
      original tool to a sandbox dir, write a driver script that imports it
      in-process and replays the exact reported sequence (deploy → selftest →
      rollback), asserting expected behaviours with recorded exit codes
      ("16/16 expected behaviours confirmed, exit 0"). Keep the original code
      byte-unmodified: place the copy at a depth where path-derived constants
      resolve, or override module globals at RUNTIME in the driver
      (`hg.CITY`, `hg.GATE`, `hg.REAL_BRIDGE`, `hg.PROTECTED`) — never edit the
      copied code. The repro log IS the "gap proven" evidence.
   2. **Fix the state-sharing, not the symptoms.** The durable pattern for
      "one shared state file clobbered by any actor": PER-TARGET files keyed by
      sha256 of the absolute normalized path (`state/deployment_state__<file>__<sha12>.json`)
      + a TARGET-GUARDED remove (only read/use/remove the manifest that records
      the requested target). Keep a distinct refusal exit code for the guard
      (0 success · 1 fail/nothing · 2 shape/bak-guard · 3 cross-target refusal).
   3. **Legacy fallback is guarded, not blind.** An old shared-state file is
      honored ONLY if its recorded target matches the request; otherwise REFUSE
      and touch nothing. Per-target takes precedence over legacy — assert THAT
      contract in the selftest.
   4. **Ship a recovery verb for the already-broken state.** When the live
      manifest is already gone but the `.bak` is intact (the exact F11 symptom),
      `--bak <file>` restores directly, sha256-guarded against the known original
      (non-original → REFUSED), and never touches any manifest.
   5. **Extend the existing selftest, keep the old checks green.** The patched
      suite = all original checks (regression) + new guard checks replaying the
      accident (sandbox rollback must NOT delete the live-like manifest;
      cross-target rollback REFUSED and removed nothing; live .bak byte-exact;
      idempotent refusal holds). Re-run the whole suite after the artifact layout
      changes (e.g. adding the repro dir inside sandbox/).
   6. **git-bash patch/diff quirks (Windows host):** `diff -u` exits 1 when
      files differ — it breaks `&&` chains (use `;`). `patch` with stdin
      redirected from the patch file hits reverse-detection prompts
      ("Assume -R? [n] / Skip this patch? [y]"), eats answers from the patch
      content, and skips every hunk — `--dry-run` then lies ("9 out of 9 hunks
      ignored") while a real apply works. Use `patch -f` (batch) and VERIFY by
      applying to a temp copy and `diff`-ing the result byte-exact against the
      shipped patched file. Header paths equal the diff arguments, so `-p0`
      from the common parent dir is the clean invocation.
   7. **Selftest-extension pitfall: assert the ACTUAL contract, capture the
      RIGHT baseline.** Two wrong assertions shipped and failed: comparing a
      post-deploy (wired) file against the PRE-deploy sha (capture the baseline
      AFTER the state-changing action), and expecting the legacy manifest to be
      removed when per-target precedence correctly leaves it untouched. When a
      new assertion fails, re-read the design and re-derive the invariant — the
      test, not the fix, is usually what's wrong.

   Price as a maintenance/security fix: 12.00–16.00 for a LOW-MED finding (c19:
   14.00) — BELOW the tool it repairs (24.00) and the asset it protects (38.00),
   above 0.00. Buyer: the REPEAT buyer who owns the asset family (TRADER bought
   the gate and the harness), not a new wallet.

   ## Payout-register variant (booking an UNBOOKED OUTFLOW — the c20 class)

   When the finding is "the state books collections but never disbursements"
   (F12b: 2,502.00 of lifetime outflow at c20 was prose, not data — the law's
   "paid onward to the farm" had no register), the deliverable is a
   DISBURSEMENT REGISTER with double-entry conservation, not more collection
   tooling. Pattern (full worked example:
   `references/inventor-cycle20-payout-register.md`):

   1. **Reconstruct the per-cycle chain from the state's own notes** (paid-count
      × ration price vs post-levy treasury per cycle). Use the SAME post-levy
      convention as the auditor's headline numbers so your residual foots to
      their audit figure penny-exact (c20: 6,540.00 − 4,038.00 = 2,502.00, and
      c19's 2,352.00 == the outlaw's published number). Document the convention;
      never silently "correct" prose wobbles in the notes.
   2. **Book the historical residual ONCE as a baseline** entry, then keep the
      register clean for itemized FUTURE disbursements (treasury -> farm lines
      with id/cycle/date/amount/payee/channel/memo/status). Conservation on
      every run: headline `collections == treasury + cumulative_payouts`, plus a
      FORWARD drift gate — `(collections_now − baseline) − (treasury_now −
      baseline) == Σ booked payouts`; treasury moved money with no booked line
      => DRIFT, exit 1.
   3. **Mid-cycle semantics:** a booked-but-unsent payout shows as NEGATIVE
      drift = an honest outstanding obligation; it converges to ZERO when the
      engine's settlement moves the cash. Prove both directions in the selftest
      (booked+treasury-move => zero; unbooked outflow => drift caught, exit-1
      path).
   4. **Engine-owned defects get a CHECK TOOL, never a silent rewrite.** F12a:
      the deaths register drifted 4-of-5 because `hunger_engine.py` computes
      deaths locally and never writes `state["deaths"]` back. The fix = a
      read-only registry-vs-ledger checker (extract ledger deaths by regex
      `^\s*\`NAME\` died of starvation` over city_ledger.md, diff against state),
      exit 1 on drift, root cause named in the verdict line. The engine's lane
      stays the engine's (the outlaw's no-double-dip boundary).
   5. **Pitfall: `| tee` masks exit codes on git-bash.** `python x.py | tee
      out.txt; echo $?` reports TEE's code, not python's — a drift check that
      truly exited 1 displayed as 0. Re-run bare with `> out 2>&1` to capture
      the TRUE code; never trust `$?` through a pipe.
   6. **Sandbox-isolate the selftest** (fixtures in `outputs/_selftest_scratch/`,
      assert the register is written only there, clean up after) and mtime-prove
      engine files untouched before AND after. Note: `pool_book.json` lives at
      `inventions/stair_insurance_pool/pool_book.json`, not the city root.

   Price as a LOW-MED pair: between the audit that found the gap (25.00) and
   the rail it complements (60.00) — c20: 30.00. Buyer: TREASURY (the state
   that owes the farm per law) or the BANK district (owns the books family).

   ## Bridge/translator pitfalls (money between systems)

   - **Qty-vs-value misstatement (the c13 F1 HIGH finding).** The ledger rail's AMT
   field is VALUE in city-credits, never quantity. Any bridge translating another
   system's lines into rail format MUST emit `AMT = qty × price` (round once, at the
   end). Naive translation of `10.00 eggs @ 0.50` books 10.00 instead of 5.00 — a 2×
   misstatement with a money consequence. Selftest must pin the exact finding's case.
   - **Rail schema fit**: `ledger_rail --check` splits lines on `" | "` and requires
   ≥5 fields; lines with fewer are **silently skipped** — invisible to duplicate and
   conservation checks. A translator emitting 2-field lines (e.g. `A -> B | 10.00 eggs
   @ 0.50`) is invisible to the rail. Emit ≥5 fields (`TS | FROM | TO | AMT | ITEM | REASON`).
   Legacy coffee-till lines branch on `parts[1].startswith("amount ")` — mirror the
   rail's own branching so your output passes its parser.
   - **Gate every translation**: self-match rejection (`FROM == TO` = wash trading),
   wallet-existence check against `economy/wallets.json` (forged attribution), and
   allow pseudo-wallets `TREASURY`/`POOL-RESERVE` (rail parity). Sign each line with a
   sha256 sig like the rail's `--propose` so the engine can settle it directly.
   - **An interface fix is a pen on the desk (the c14 F5 class).** A translator that
   fixes the math protects nothing until the SOURCE system routes through it. Before
   declaring a remediation done, verify the wiring: does the emitter actually drain
   into the fix? Check mtimes (c14: farm_exchange.py mtime predated the bridge — the
   source was untouched) and re-run the naive path to prove the 2× still books. The
   c15 closure: a settlement EMITTER whose only intake is the real OrderBook's
   executed matches (drain `book.trades`, never accept hand-fed lines) — the F4
   structural intent gate. Return `(approved, rejected)` pairs; a settlement path that
   silently drops a rejected match reintroduces the silent-skip class. Prove: empty
   book → 0 lines, resting-only book → 0 lines, a million-credit spoof has no path in.
   - **MONEY DIRECTION is a rail semantic, not a copy job (the c16 F6 finding).** The
   rail line `TS | FROM | TO | AMT` DEBITS FROM (`--propose <FROM> <TO>` — FROM pays,
   TO receives). The exchange prints order lines as `{seller} -> {buyer} | qty good @
   price` (farm_exchange.py:71 emits asker/seller first, bidder/buyer second). Any
   translator that copies the exchange fields VERBATIM into rail shape emits `TS |
   seller | buyer | AMT` — the SELLER gets debited and the money flows BACKWARDS
   through the whole exchange. The c13 case `BEGGAR -> DOCTOR | 10.00 eggs @ 0.50`
   must emit `TS | DOCTOR | BEGGAR | 5.00` (buyer pays), never `TS | BEGGAR | DOCTOR |
   5.00`. **Fixes to one path do NOT fix sibling paths**: c16 swapped the roles in
   the settlement EMITTER, but the c14 bridge's own translate/propose path still
   copied fields verbatim — that is how the same defect re-opened at the bridge
   interface (the c17 build). When you fix a direction bug, grep EVERY other
   translator/adapter that feeds the rail and apply the same swap; the selftest must
   pin the exact finding's case with parsed parts (`parts[1] == buyer`,
   `parts[2] == seller`), not `startswith`.
   - **Money is Decimal on a settlement path (the c14 F2 finding).** `round(2.675, 2)`
   = 2.67 (float repr 2.674999…, banker's half-even) — binary float silently loses a
   cent per line across a ledger. Use `Decimal(str(x))` to recover the decimal repr
   from a float input (never `Decimal(x)` straight on a float), multiply, then
   `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` → 2.68. Never `round()` money.
   Keep item-field qty at FULL fidelity (strip trailing zeros, pad to ≥2dp, never
   re-round) — the audit flagged `2.675 → "2.67 eggs"` as record fidelity loss.
   - **Zero-price gate (the c14 F3 finding).** The exchange never quotes price ≤ 0,
   so a zero-price line is ledger pollution by definition. REJECT `price <= 0` /
   `qty <= 0` at the emitter — and prove it against a pathological BOOK state: a 0.00
   bid/ask cross EXECUTES in the order book, so the gate must catch it after matching,
   not assume the book cannot produce it.

## Pricing rules

- **Backstop-aware pricing**: selling to a POOL/RESERVE with a solvency floor ⇒
  max price = reserve_after_inflows − backstop. c8: 81.25 + 51.25 sweep − 50.00 =
  82.50 > 75.00 backstop (7.50 headroom). Check this BEFORE naming a price.
- **Respect precedent**: pool-funded ops engine at c7 (60.00, from the pool's own
  premiums) → the claims desk at c8 (50.00) is the same institutional pattern;
  the treasury (which already procured the 325.00 license) is not asked twice.
- **Institutional buyers are canon**: a fund that buys its own tooling is a story
  the ledger records — price for repeat purchases, not one-shot gouges.
- **Remediation pricing**: a fix for an audited defect prices BELOW the full builds
  it touches but ABOVE the audit engagement that found it (c14: 45.00 — under
  ledger_rail 60.00 / dividend engine 65.00, over the 25.00 finding). Frame it as:
  the treasury buys certainty for less than one misbooked settlement.

## Money-math pitfalls (floats — round once, at the end)

- **Pro-rata cap rounding drift**: scaling N claims by `headroom/total` then `round()`
  per item can overshoot the cap by pennies (11 × 2.73 = 30.03 vs 30.00 headroom),
  silently breaching a backstop. Fix: after scaling, clamp the LARGEST item by the
  exact overshoot so the total never crosses the floor.
- **Dynamic selftest expectations**: hardcoding "132.50" broke when a destitute member
  was also premium-deferred (sweep 51.25 → 50.00). Compute expected values from the
  same rules as the code; never hardcode reserve totals.
- Always: `reserve_after = reserve_before + inflows − outflows`, rounded once.

## Selftest discipline

- Assert on REAL data (load the actual books), plus deterministic simulated scenarios:
  destitute member, cash-rich member flagged hungry (indemnity principle — never pay a
  loss they could have self-funded), serial claimant (2nd consecutive → suspend for
  council), same-cycle enrollee (waiting period), inactive member, catastrophic
  multi-claim (ruin gate caps total, never silently empties the fund).
- Let the selftest catch the bug (red → green). The rounding-drift fix came from a
  failing assertion, not inspection.
- Honest count in the print: `SELFTEST 24/24 PASS (exit 0)` must match the real
  assertion count.
- **Exact label-count recipe (grep-provable).** Print N derived from a runtime
  counter (`check()` increments), never a hardcoded label. Make
  `grep -c 'check(' <file>` minus the `def check` line equal the printed N EXACTLY:
  unroll loop checks into explicit statements (a 3-iteration loop prints 3 but greps
  1), keep "check(" out of docstrings/print headers, and alias other modules' check
  functions (`rail_validate = ledger_rail.check; errs, n = rail_validate()` — the
  assignment line itself matches the pattern otherwise).
- **Assert on parsed fields, not `startswith`**, when the line begins with a
  timestamp — split on `" | "` and check parts[1]/[2]/[3]. Define variables before
  the check that reads them (a later-section definition is a NameError).
- **Robustness to concurrent settlement.** The live engine settles mid-session
  (trade.log grew 355 → 362 between two runs of the same selftest, and engine lines
  even showed the F1 fix already settling). Never hardcode ledger line counts;
  re-check the standing file at the end and assert "errors: 0".
- **Check for stray partial attempts** in the inventions dir before building: a prior
  run can leave a half-wired file whose docstring claims more checks than it runs
  (found: "24 checks" claiming 11 with two vacuous `all(...)`/`True` assertions).
  Verify by RUNNING, never trust the docstring; build in your own NEW directory.
- **No literal-`True` assertions, even in a brand-new selftest (the c16 F7 finding —
  and an own-goal this author nearly shipped in c17).** A check whose condition is a
  hardcoded `True` (e.g. a "read-only proven" label backed by `ok(..., True)`) cannot
  fail, so it proves nothing. If a label promises a check ("mtime check below"), the
  check must exist and do the work. A read-only claim should be REAL: snapshot
  `os.path.getmtime()` of the protected canonical files (`city_ledger.md`,
  `ledger/trade.log`, `economy/wallets.json`, `survival/survival_state.json`,
  `economy/prices.json`, `bank/pool_book.json`) before the scan, re-stat after, and
  assert the dicts are equal. The outlaw audits for exactly this class of dishonesty;
  self-inflicted F7s are the most embarrassing kind.
- **Ship a defect scanner with the fix.** A remediation is stronger when it also
  finds the OLD defect shape in standing files: an `--audit <file>` mode that
  regex-matches legacy lines (reason carries the old ref, item carries a goods `@`)
  and counts them. The selftest proves BOTH sides of the claim: a fixture containing
  a legacy line is FLAGGED (the scanner actually works), AND the real
  `city_ledger.md`/`ledger/trade.log` scan to 0 (the exposure was real but never
  settled). A 0-result over real files is honest evidence the defect was latent, not
  live — and the scanner stays behind as the standing tripwire.
- **Proof-on-a-copy discipline** (for anything that must fit an existing system's
  validator): copy the canonical data file to a temp file, append your output line,
  monkeypatch the target module's path constant (e.g. `ledger_rail.TRADE = tmp`),
  and run its REAL `check()` — 0 errors on the copy proves schema fit without ever
  touching the canonical file. Then re-run the real tool on the standing file
  (`python ledger_rail.py --check`) to prove immutability (line count unchanged).
  Also assert the defect shape: raw pre-fix lines have <5 fields (invisible), fixed
  lines have ≥5. Delete the temp dir in `finally`.
