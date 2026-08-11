# VERIFY-RUNNER

`verify-runner` is a Hermes plugin that closes the "verify after every
change" loop: one command runs a project's tests **and** linter, then
prints a compact `PASS`/`FAIL` verdict with the failing output tail.

- Plugin: `plugins/verify-runner/`
  - `core.py` — pure-stdlib engine (discovery, subprocess runner, verdicts)
  - `__init__.py` — Hermes wiring: `/verify` command + `verify_project` tool
  - `tests/test_core.py` — 38 unit + end-to-end tests
- Docs: this file
- Example project: `plugins/verify-runner/examples/`

---

## 1. How it works

### Test command discovery (`discover_test_command`)

1. `pytest` if a marker file exists in the directory:
   `pytest.ini`, `pyproject.toml`, or `setup.cfg`.
2. `pytest` if `pytest` is on PATH.
3. Otherwise `python -m unittest discover`.

### Lint command discovery (`discover_lint_command`)

1. `ruff check .` if `ruff.toml` / `.ruff.toml` exists in the directory.
2. `ruff check .` if `pyproject.toml` contains a `[tool.ruff]` section.
3. `ruff check .` if `ruff` is on PATH.
4. Otherwise `python -m py_compile <changed .py files>` — a
   zero-dependency syntax check over git-changed + untracked `.py` files
   (whole-tree scan capped at 120 files when not a git repo).

> **Why `ruff check .` and not bare `ruff`?** Modern ruff (≥ 0.6) prints
> help and exits 2 when invoked without a subcommand. `ruff check .` works
> on every ruff version.

### Execution (`run_command`)

- 180 s timeout (`DEFAULT_TIMEOUT`); a hung process is killed — it can
  never hang the agent.
- stdout/stderr captured, each truncated to the **last 3000 chars**
  (`TAIL_LEN`).
- Windows note: file paths in the `py_compile` fallback are `shlex.quote`d,
  which preserves backslash paths through `shlex.split` (single quotes keep
  backslashes literal).

### Verdict (`verify_project`)

```
VERIFY <dir>
TEST PASS (exit 0) | TEST FAIL (exit N) | TEST TIMEOUT
LINT PASS (exit 0) | LINT FAIL (exit N) | LINT TIMEOUT
--- <TEST|LINT> failing tail ---   (only when failing)
<last 3000 chars of the failing stream>
VERDICT: PASS | FAIL
```

`VERDICT` is `PASS` only when tests and lint both pass. It never raises on
a bad directory — it returns an error line instead.

---

## 2. How to use it

### Slash command

```bash
/verify                # verify the current working directory
/verify plugins/verify-runner/examples
```

### Model tool

`verify_project(dir)` — registered in the `file` toolset; read-only.

### From Python (same loading hermes uses)

```python
import importlib.util, os, sys

PLUGIN = os.path.abspath("plugins/verify-runner")

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

core = _load("verify_runner.core", os.path.join(PLUGIN, "core.py"))
sys.modules["verify_runner.core"] = core

spec = importlib.util.spec_from_file_location(
    "verify_runner", os.path.join(PLUGIN, "__init__.py"),
    submodule_search_locations=[PLUGIN],
)
mod = importlib.util.module_from_spec(spec)
mod.__package__ = "verify_runner"
mod.__path__ = [PLUGIN]
sys.modules["verify_runner"] = mod
spec.loader.exec_module(mod)

print(mod.verify_project("plugins/verify-runner/examples"))
```

---

## 3. The example project (`plugins/verify-runner/examples/`)

A deliberately tiny, stdlib-only, ruff-clean project:

| File                    | Purpose                                            |
| ----------------------- | -------------------------------------------------- |
| `example_math.py`       | Module with 2 functions: `add()` and `is_even()`   |
| `test_example_math.py`  | 4 passing unittest tests (also pytest-compatible)  |
| `clean_script.py`       | Standalone ruff-clean script                       |
| `README.md`             | In-project readme                                  |

It is its own git repository (no commits) so the `py_compile` fallback
scopes "changed files" to exactly these three `.py` files.

### Verified via the real runner

Environment: pytest 9.1.1 + ruff 0.16.2 on PATH, Python 3.11.

```
TEST CMD : pytest
LINT CMD : ruff check .
============================================================
VERIFY C:\Users\HP\xomni\plugins\verify-runner\examples
TEST PASS (exit 0)
LINT PASS (exit 0)
VERDICT: PASS
```

- `pytest` collects and passes 4 tests (`test_example_math.py`).
- `ruff check .` passes — all three files are ruff-clean (note: ruff's
  isort rule wants **two** blank lines before a top-level class; the
  example files follow that).

### Re-verify it yourself

```bash
cd plugins/verify-runner/examples
/verify
```

---

## 4. Maintenance notes

- Plugin tests: `python -m unittest tests.test_core -v` from
  `plugins/verify-runner/` — 38 tests, all green.
- The end-to-end tests generate tiny projects in temp dirs and assert
  `VERDICT: PASS` / `VERDICT: FAIL` — they exercise the real subprocess
  path (pytest or unittest, ruff or py_compile, whichever is discovered).
- When ruff 0.16+ is installed, lint discovery returns `ruff check .`
  (bare `ruff` exits 2). When ruff is absent, the `py_compile` fallback
  keeps verification zero-dependency.
