# verify-runner

One command runs a project's tests + linter and returns a compact
PASS/FAIL verdict — the "verify after every change" loop (Aider P4 port).

**What it does:** discovers the test command (`pytest` when a marker file
exists or pytest is on PATH, else `python -m unittest discover`) and the
lint command (`ruff check .` when configured/available, else
`python -m py_compile` on changed `.py` files — a zero-dependency syntax
check). Runs both with a 180 s timeout, captures stdout/stderr capped to
the last 3000 chars, and never lets a hung process outlive the timeout.
Returns `TEST PASS|FAIL`, `LINT PASS|FAIL`, the failing tail, and a final
`VERDICT: PASS|FAIL`.

**Commands/tools:** slash command `/verify [--coverage] [dir]` (defaults to
cwd) plus model tool `verify_project(dir, coverage=False)` — read-only,
never edits files, never raises on a bad directory. With `--coverage`
(or `coverage=True`), the tests run under `python -m trace --count --missing`
— pure stdlib, no pytest-cov dependency — and the report shows per-file
covered/total line counts with percentages plus a project total. The test
command runs once plainly for the authoritative exit code (`python -m trace`
swallows the child's exit status), then again under tracing for the counts.

**Speed posture:** no hooks; subprocesses only when invoked (tests + lint),
each bounded by timeout with tail-truncated output.

**Config:** none (constants in `core.py`: `DEFAULT_TIMEOUT=180`,
`TAIL_LEN=3000`, `MAX_COMPILE_FILES=120`).

```bash
cd plugins/verify-runner && python -m unittest tests.test_core -v
```

For the worked example project and a full walkthrough, see
[`docs/VERIFY-RUNNER.md`](../../docs/VERIFY-RUNNER.md).
