# XOMNI CI Gate

The CI gate is a single self-contained script that enforces the two speed rules
the XOMNI plugin suite must never regress on:

1. **Import latency < 90 ms** — no plugin may make the agent loop pay a heavy
   one-time import cost.
2. **Zero hooks** — per [CONTRIBUTING.md §3](../CONTRIBUTING.md) ("The
   zero-hooks speed rule"), plugins must introduce **no hooks**. The 100x speed
   incident (see [PERFORMANCE.md](PERFORMANCE.md)) was driven by hook-triggered
   LLM calls and per-event I/O piling up across many enabled plugins; the rule
   now is: registration is pure bookkeeping, all work happens lazily inside
   tool/command handlers.

## How to run

```bash
python .bench/ci_gate.py            # full plugin sweep, 90 ms import limit
python .bench/ci_gate.py --limit-ms 120     # custom import ceiling
python .bench/ci_gate.py --json             # machine-readable summary line
```

Requires only the Python stdlib; it never imports or touches a live Hermes
install (same isolated FakeCtx harness as `.bench/bench.py`).

## What it checks

| # | Check | Rule | How it is enforced |
|---|-------|------|--------------------|
| 1 | **Import gate** | Every plugin in `plugins/<name>/__init__.py` cold-imports in **< 90 ms** | Each plugin is imported once in-process (bench.py methodology) and timed; import **failure** also fails the gate |
| 2 | **Zero hooks** | **No `register_hook` anywhere** in plugin code | Two independent detectors: (a) static scan for `register_hook(` in every `*.py` under `plugins/`, (b) runtime — call `register(ctx)` on a FakeCtx and require **zero** hooks registered |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | **PASS** — all plugins import under the limit, no hooks registered |
| 1 | Import-time violation — ≥ 1 plugin imported in ≥ 90 ms or failed to import |
| 2 | Hook violation — ≥ 1 plugin registers hooks |
| 3 | Both violations |

Any non-zero exit means the change must not merge.

## Example output

```
XOMNI CI GATE  (plugins dir: ...\plugins, import limit: 90 ms)
==============================================================================
PLUGIN               IMPORT(ms)  HOOKS   VERDICT
------------------------------------------------------------------------------
context-compact          15.4   pre_llm_callx1  FAIL
    ! hook registration: plugins/context-compact/__init__.py:276
gh-ops                    4.8   none    PASS
...
==============================================================================
IMPORT CHECK  : PASS — all 22 plugins < 90 ms
ZERO-HOOKS    : FAIL — 6 plugin(s) register hooks (CONTRIBUTING.md §3)
GATE VERDICT: FAIL (exit 2)
```

## Integrating into CI

`.bench/` is gitignored (scratch), so CI cannot read the gate from the repo
tree directly. Pick one:

- **Recommended: copy the gate into the workflow.** It is self-contained
  (stdlib only, no bench.py dependency). Copy `.bench/ci_gate.py` into the
  workflow (e.g. as a step that writes it to a temp path) and run it:

  ```yaml
  # .github/workflows/ci.yml (example step)
  - name: XOMNI speed gate (import <90ms, zero hooks)
    run: |
      python .bench/ci_gate.py --json
    shell: bash
  ```

- Or commit a copy of the gate at e.g. `ci/ci_gate.py` and run
  `python ci/ci_gate.py`; keep it in sync with `.bench/ci_gate.py`.

Treat a non-zero exit as merge-blocking. The gate is fast (< 10 s for the full
16-plugin sweep) and runs the whole suite in a single process, so it slots into
any job.

## Current status

As of the speed-fix workstream (see `docs/PERFORMANCE.md`), **imports pass
marginally** but the **zero-hooks check is RED**: 6 plugins still register
hooks (`context-compact`, `omni-memory`, `perkline`, `sandbox-gate`,
`title-statusline`, `waitperk`). These are the pre-rule plugins whose hooks
were made cheap (sub-ms, no LLM/network/subprocess) rather than removed; they
predate CONTRIBUTING.md §3. The gate intentionally reports them as violations
— resolving the RED state means either migrating those features to
command/tool handlers (the rule's preferred path) or an explicit maintainer
decision to grandfather them. New plugins must pass the gate green.

**Watch item — `context-loader` import time.** It sits right on the 90 ms
ceiling: ~82 ms in the recorded after-run, observed 75–97 ms in-process and
~95–120 ms when imported in a fully cold process (stdlib included in the
timer). Expect occasional borderline failures on loaded machines; if it is
consistently ≥ 90 ms in-process, that is a real regression to fix.

**Static-scan scope:** `register_hook` is scanned in plugin **production**
sources only — `tests/` directories are excluded, because test scaffolding
registers hooks against a FakeCtx. The runtime check (zero hooks actually
registered by `register(ctx)`) is the authoritative detector and covers all
code paths.
