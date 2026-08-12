# Windows support

Windows is a **first-class supported platform** for XOMNI. This document
covers the three known Windows failure modes (all hit in production), how CI
guards them, and the tooling that verifies them locally.

## The three known Windows bugs and their fixes

### 1. `npx` / `.cmd` shims not found by `subprocess`

**Symptom:** `subprocess.run(["npx", "--version"], shell=False)` raises
`FileNotFoundError` on Windows, even though `npx` works in a terminal.

**Root cause:** Node.js ships `npx` as `npx.CMD` (a batch shim). Python's
`subprocess` on Windows launches via `CreateProcess`, which does **no PATHEXT
search** — a bare `npx` is not found. `shutil.which("npx")` *does* honor
PATHEXT and returns `C:\Program Files\nodejs\npx.CMD`; passing that **full
path** with `shell=False` works. Plain `.exe` tools (`gh.exe`, `git.exe`,
`hermes.exe`) work bare, so only `.cmd`/`.bat` shims need substitution.

**Fix (applied in code):** every plugin/xomni_cli subprocess call that invokes
an external CLI resolves the binary first:

```python
def _resolve_exe(name: str) -> str:
    """Resolve *name* to its real executable, honoring .cmd/.bat shims (Windows)."""
    found = shutil.which(name)  # honors PATHEXT on Windows
    if found and os.path.splitext(found)[1].lower() in (".cmd", ".bat"):
        return found           # full path to the shim executes fine
    return name                # gh.exe / git.exe / hermes.exe work bare
```

Applied at: `plugins/gh-ops/core.py` (`run_gh`), `plugins/omni-skills/core.py`
(`_git_clone`), `plugins/codebase-index/core.py` (`_git_head`),
`plugins/verify-runner/core.py` (`_git_repo_root`, `changed_py_files`, generic
`run_command`), `xomni_cli/__init__.py` (`launch`).

**Rule for new code:** never hand a bare name to `subprocess` on Windows;
resolve via `shutil.which` first and pass the full path when it ends in
`.cmd`/`.bat`. Never fall back to `shell=True` — argv lists are safer.

### 2. `config.yaml` write-protected, direct edits fail

**Symptom:** opening `%LOCALAPPDATA%\hermes\config.yaml` for write raises
`PermissionError`, so config edits through code fail.

**Root causes (check in this order):**

1. **Read-only attribute** — `attrib +R` was set on the file.
   Fix: `attrib -R "C:\Users\<you>\AppData\Local\hermes\config.yaml"`
2. **ACL denies write** — the file/dir ACL was tightened.
   Fix (admin shell): `icacls "C:\Users\<you>\AppData\Local\hermes" /grant "%USERNAME%":(OI)(CI)M`
3. **Exclusive lock** — another process (hermes itself) holds the file open.
   Fix: stop hermes / close the editor before editing.

`python .bench/windows_checks.py` detects this state loudly (checks the
Read-only attribute via `GetFileAttributesW` and probes an actual temp-file +
append write in the config dir).

### 3. `/tmp` vs Windows path confusion

**Symptom:** Python code that writes to `/tmp` works in git-bash but breaks
(or silently writes to the wrong place) when run by native Windows Python.

**Root cause:** `/tmp` is a git-bash/MSYS fiction. Native Windows Python
resolves `/tmp` as an absolute path on the current drive — e.g. `C:\tmp` —
which usually does not exist. `tempfile.gettempdir()` on Windows returns
`%LOCALAPPDATA%\Temp`.

**Path policy (enforced by `windows_checks.py`):**

- Python: always `os.path` / `pathlib`. Repo-relative paths derive from
  `Path(__file__).resolve()`. Temp files use `tempfile.gettempdir()`.
  Never hardcode `/tmp`.
- Shell scripts that must run on Windows (via git-bash, e.g.
  `.bench/run_all_tests.sh`): use repo-relative temp dirs, not `/tmp`
  (`run_all_tests.sh` now logs to `.bench/.tmp/`).
- `os.path.normpath` handles both separators: `C:/Users/HP/xomni` and
  `C:\Users\HP\xomni` normalize to the same string.

## Local verification

```bash
python .bench/windows_checks.py          # human report; exit 0 = all OK
python .bench/windows_checks.py --json   # machine-readable report
```

Checks: (a) npx shim resolution — locates `npx` on PATH (PATHEXT), verifies
`subprocess` can launch the full `.cmd` path, and warns what breaks if you use
the bare name; (b) Hermes config write access — temp-file + `config.yaml`
append probes, flags the Read-only attribute loudly with the `attrib -R` fix;
(c) path sanity — repo root resolves identically via forward/back-slash
spellings, mixed separators normalize, `/tmp` policy scan over repo shell
scripts.

## CI: `windows-latest` job

`.github/workflows/tests.yml` runs a `test-windows` job on `windows-latest`
mirroring the Ubuntu matrix (Python 3.11, `actions/checkout@v4`,
`actions/setup-python@v5`):

1. `python .bench/windows_checks.py` — Windows env checks fail fast with a
   clear name if the runner's npx/config/path setup is broken.
2. `bash .bench/run_all_tests.sh` — the bash-only test matrix is driven
   through **git-bash**, which is preinstalled on windows-latest runners
   (`shell: bash`). Logs go to `.bench/.tmp/` (repo-relative), so no `/tmp`
   dependency.

## Testing on Windows

- Unit tests run per plugin: `cd plugins/<name> && python -m unittest discover -s tests -v`
- Full matrix: `bash .bench/run_all_tests.sh` (writes `docs/TEST-MATRIX.md`)
- The gh-ops/verify-runner suites assert exact argv (e.g. `["gh", ...]`); the
  `_resolve_exe` rule only substitutes `.cmd`/`.bat` shims, so `.exe` tools
  keep their bare names and those assertions stay valid on Windows too.
