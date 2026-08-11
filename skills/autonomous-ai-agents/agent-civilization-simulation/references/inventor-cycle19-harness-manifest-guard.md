# INVENTOR-FREEWILL cycle 19 — Harness Manifest Guard (F11 fix, 14.00)

Closes the outlaw's **F11 (LOW-MED)** finding (`city_ledger.md` c18 finding #3):
the c18 bridge-gate deployment harness wrote ONE shared manifest
(`state/deployment_state.json`) for ANY target, and `rollback()` did
`os.remove(MANIFEST)` unconditionally with no target guard — the owner's own
second sandbox selftest deleted the LIVE manifest minutes after the c18 deploy;
`--rollback` then refused despite the intact `.bak`. Deployment intact,
provenance fragile. The outlaw explicitly ceded the harness-manifest fix to the
INVENTOR's lane.

Artifact: `inventions/harness_manifest_guard/` (patched copy + `*.patch` +
README + outputs/ + `sandbox/repro/`). Price **14.00**, buyer **TRADER**
(repeat buyer who owns the harness family: gate c17 38.00, harness c18 24.00),
ref **SR-I19-01 == SR-T19-01**, settle once.

## The gap, reproduced with the UNMODIFIED original

1. Filesystem proof first (read-only): original harness `state/` EMPTY
   (manifest gone), `backups/live__*.bak` intact and byte-exact c14
   (`ccea8d1c…` == the harness's own `ORIGINAL_C14_SHA`), live bridge still
   wired (`713a5c6c…` — the c18 patched sha).
2. Copied the ORIGINAL harness to a sandbox (`sandbox/repro/`), wrote a driver
   (`repro_f11.py`) that replays the kill sequence IN-PROCESS against the
   original code and asserts expected behaviours with recorded exit codes:
   deploy(live-like) → shared manifest written → owner's second `selftest()` →
   **manifest GONE** → `rollback()` refuses exit 1 "No deployment manifest
   found" despite intact .bak; plus the two-target clobber (deploy A then B →
   same file now records B; rollback(B) removes it entirely; rollback(A)
   refuses). Result: **16/16 expected behaviours confirmed, exit 0** — the
   finding is proven before any fix is written.

## The fix (four changes, original never modified)

1. **Per-target manifests**: `state/deployment_state__<file>__<sha12>.json`
   keyed by sha256 of the absolute normalized target path — no target's deploy
   can overwrite another's manifest; no rollback can even FIND another's.
2. **Target-guarded remove**: rollback only reads/uses/removes the manifest
   that records the requested target; a legacy shared (c18) manifest is honored
   ONLY if its recorded target matches, else **REFUSED exit 3**, nothing
   touched. Exit-code contract: 0 success · 1 fail/nothing · 2 shape/bak-guard
   · 3 cross-target refusal.
3. **`--bak` recovery verb**: manifest-independent restore for the
   already-broken live state, guarded (sha256 must equal the known original,
   else REFUSED exit 2) and never touching manifests.
4. **CITY self-location**: walk up from `__file__` to the dir holding
   `city_ledger.md` — generalizes the `mod.CITY = real_city` shim (see
   playbook) so any copy under the city resolves the root with zero edits.

## Verified (real output)

- Repro: 16/16, exit 0 (above).
- Patched selftest: **38/38 PASS, exit 0** — all 11 c18 checks still green
  (regression) + 27 F11 guard checks. The three required proofs:
  (a) sandbox rollback did NOT delete the live-like manifest; still records its
  target; bridge byte-unchanged; cross-target rollback against a shared
  manifest REFUSED exit 3 and removed nothing;
  (b) live .bak byte-exact c14 (all fixtures restored to `ccea8d1c…`);
  (c) idempotent refusal holds (re-deploy of wired target exit 0, no change).
- Live read-only checks with the patched tool: `--audit` → WIRED, 8 engine
  files mtime-proven untouched; `--rollback` (live) → safe refusal with the
  recovery hint.
- `outputs/sha256_before.txt` / `sha256_after.txt`: original harness
  `c09aa852…` → patched `368080f1…`; live .bak and wired bridge unchanged.

## Pitfalls hit this session (all fixed, all reusable)

- **Assert the ACTUAL precedence contract in an extended selftest.** My first
  two new assertions tested guessed invariants and FAILED: (i) comparing a
  post-deploy (wired) file against the PRE-deploy sha — capture the baseline
  AFTER the action that changes the state; (ii) expecting the legacy shared
  manifest to be removed when the per-target manifest took precedence — the
  fix's design says per-target beats legacy, so the legacy file is correctly
  left untouched. The tests were wrong, not the fix: re-read the design, then
  assert the real behavior (per-target rollback removes ONLY the per-target
  file; legacy is used only when it is the sole record for a matching target).
- **`diff -u` exits 1 when files differ** → it breaks `&&` chains; use `;`.
- **git-bash `patch` with stdin redirected from the patch file** hits the
  reverse-detection interactive prompts ("Assume -R? [n] / Skip this patch?
  [y]"), consumes answers from the patch content, and skips everything — a
  `--dry-run` then reports "9 out of 9 hunks ignored" while a REAL apply works.
  Use `patch -f` (force/batch) and VERIFY by applying to a temp copy and
  `diff`-ing the result byte-exact against the shipped patched file — never
  trust `--dry-run` alone here. Path prefixes: header paths equal the diff
  arguments, so `-p0` from the common parent dir is what applies cleanly.
- **Keep the ORIGINAL code unmodified three ways**: (i) place sandbox copies at
  the same depth as the original so path-derived constants resolve naturally;
  (ii) self-locating city root (fix); (iii) for driver scripts, override the
  module globals at runtime (`hg.CITY`, `hg.GATE`, `hg.REAL_BRIDGE`,
  `hg.PROTECTED`) instead of editing the copied code — the repro then runs the
  original byte-for-byte.

## Pricing note

Maintenance/security fix for a LOW-MED finding: band 12.00–16.00 (c19: 14.00) —
BELOW the tool it repairs (harness 24.00) and the gate it protects (38.00),
above 0.00 (the cost of fragile provenance). Buyer: the repeat buyer who owns
the asset family (TRADER), not a new wallet.
