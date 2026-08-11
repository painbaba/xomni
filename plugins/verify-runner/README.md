# verify-runner

One command runs a project's tests + linter and returns a compact
PASS/FAIL verdict — the "verify after every change" loop (Aider P4 port).

**What it does:** discovers the test command (`pytest` when a marker file
exists or pytest is on PATH, else `python -m unittest discover`) and the
lint command (`ruff` when configured/available, else `python -m py_compile`
on changed `.py` files — a zero-dependency syntax check). Runs both with a
180 s timeout, captures stdout/stderr capped to the last 3000 chars, and
never lets a hung process outlive the timeout. Returns `TEST PASS|FAIL`,
`LINT PASS|FAIL`, the failing tail, and a final `VERDICT: PASS|FAIL`.

**Commands/tools:** slash command `/verify [dir]` (defaults to cwd) plus
model tool `verify_project(dir)` — read-only, never edits files, never
raises on a bad directory.

**Speed posture:** no hooks; subprocesses only when invoked (tests + lint),
each bounded by timeout with tail-truncated output.

**Config:** none (constants in `core.py`: `DEFAULT_TIMEOUT=180`,
`TAIL_LEN=3000`, `MAX_COMPILE_FILES=120`).

```bash
cd plugins/verify-runner && python -m unittest tests.test_core -v
```
