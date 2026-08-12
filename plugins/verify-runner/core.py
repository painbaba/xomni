"""verify-runner core — pure stdlib: command discovery, subprocess running, verdicts.

No Hermes imports. Unit-testable in isolation.

Discovery
---------
* Tests: prefer ``pytest`` (a marker file ``pytest.ini`` / ``pyproject.toml`` /
  ``setup.cfg`` in the directory, or ``pytest`` on PATH), else fall back to
  ``python -m unittest discover``.
* Lint: prefer ``ruff`` (``ruff.toml`` / ``.ruff.toml``, a ``[tool.ruff]``
  section in ``pyproject.toml``, or ``ruff`` on PATH), else fall back to
  ``python -m py_compile`` over the changed ``.py`` files (git diff vs HEAD
  plus untracked; whole-tree scan when not a git repo) — a zero-dependency
  syntax check.

Execution
---------
``run_command`` captures stdout/stderr, keeps only the last ``TAIL_LEN``
chars of each stream, and never lets a hung process outlive the timeout
(subprocess kills it) — a stuck test can never hang the agent.

Coverage
--------
``verify_coverage`` runs the same discovered test command twice: plainly
(for the authoritative exit code — ``python -m trace`` swallows the
child's status) and under ``python -m trace --count --missing --summary``,
parsing the per-file summary plus the ``.cover`` files into exact
covered/total line counts and percentages. Stdlib only; no pytest-cov.
"""
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

DEFAULT_TIMEOUT = 180
TAIL_LEN = 3000
MAX_COMPILE_FILES = 120

PYTEST_MARKERS = ("pytest.ini", "pyproject.toml", "setup.cfg")
RUFF_MARKERS = ("ruff.toml", ".ruff.toml")
SKIP_DIRS = frozenset({
    ".git", "__pycache__", ".venv", "venv", "env", "node_modules",
    "dist", "build", ".tox", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "site-packages",
})


def _tail(text: str, n: int = TAIL_LEN) -> str:
    """Last ``n`` characters of a stream; whole string when shorter."""
    if not text:
        return ""
    return text if len(text) <= n else text[-n:]


def _as_text(data) -> str:
    """Normalize bytes/None/str subprocess captures to str."""
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_test_command(dir: str) -> str:
    """Return the test command for a project directory.

    Prefers ``pytest`` when a pytest marker file exists in ``dir`` or
    ``pytest`` is on PATH; otherwise falls back to unittest discovery.
    """
    for marker in PYTEST_MARKERS:
        if os.path.exists(os.path.join(dir, marker)):
            return "pytest"
    if shutil.which("pytest"):
        return "pytest"
    return "python -m unittest discover"


def _pyproject_wants_ruff(dir: str) -> bool:
    """True when ``pyproject.toml`` carries a ``[tool.ruff]`` section."""
    try:
        with open(os.path.join(dir, "pyproject.toml"), encoding="utf-8") as fh:
            return "tool.ruff" in fh.read()
    except OSError:
        return False


def _git_repo_root(dir: str) -> str:
    """Repo toplevel for ``dir``, or ``""`` when not inside a git repo."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=dir, capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return ""
    root = (r.stdout or "").strip()
    return root if r.returncode == 0 and root else ""


def _all_py_files(dir: str) -> list[str]:
    """Every ``.py`` file under ``dir`` (junk dirs skipped), capped."""
    files: list[str] = []
    for root, dirs, names in os.walk(dir):
        dirs[:] = [sub for sub in dirs if sub not in SKIP_DIRS]
        for name in names:
            if name.endswith(".py"):
                files.append(os.path.abspath(os.path.join(root, name)))
                if len(files) >= MAX_COMPILE_FILES:
                    return files
    return files


def changed_py_files(dir: str) -> list[str]:
    """Absolute paths of changed ``.py`` files vs HEAD (plus untracked).

    Uses git when ``dir`` sits inside a repository (diff vs HEAD +
    ``git ls-files --others``); otherwise falls back to scanning the tree.
    Deleted files are filtered out. Capped at ``MAX_COMPILE_FILES``.
    """
    root = _git_repo_root(dir)
    if root:
        try:
            diff = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                cwd=root, capture_output=True, text=True, timeout=10,
            )
            files: list[str] = []
            for line in (diff.stdout or "").splitlines() + (untracked.stdout or "").splitlines():
                name = line.strip()
                if name.endswith(".py"):
                    full = os.path.abspath(os.path.join(root, name))
                    if os.path.exists(full) and full not in files:
                        files.append(full)
                        if len(files) >= MAX_COMPILE_FILES:
                            return files
            if files:
                return files
        except Exception:
            pass
    return _all_py_files(dir)


def discover_lint_command(dir: str) -> str:
    """Return the lint command for a project directory.

    Prefers ``ruff`` when a ruff config exists or ``ruff`` is on PATH;
    otherwise falls back to ``python -m py_compile`` on the changed
    ``.py`` files (a zero-dependency syntax check).
    """
    for marker in RUFF_MARKERS:
        if os.path.exists(os.path.join(dir, marker)):
            return "ruff check ."
    if _pyproject_wants_ruff(dir):
        return "ruff check ."
    if shutil.which("ruff"):
        return "ruff check ."
    files = changed_py_files(dir)
    if not files:
        return "python -m py_compile"
    return "python -m py_compile " + " ".join(shlex.quote(f) for f in files)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_command(
    cmd: str, cwd: str, timeout: int = DEFAULT_TIMEOUT, tail_len: int | None = TAIL_LEN
) -> dict:
    """Run ``cmd`` (a shell-style command string) in ``cwd``.

    Returns ``{"ok", "exit_code", "stdout_tail", "stderr_tail", "timed_out"}``
    with each stream capped at the last ``TAIL_LEN`` chars (``tail_len=None``
    keeps the full stream — used when output must be parsed whole). A hung
    process is killed by subprocess once ``timeout`` elapses and reported via
    ``timed_out=True`` — it never hangs the caller.
    """

    def _crop(text: str) -> str:
        return text if tail_len is None else _tail(text, tail_len)

    if not os.path.isdir(cwd):
        return {
            "ok": False, "exit_code": None,
            "stdout_tail": "", "stderr_tail": f"working directory not found: {cwd}",
            "timed_out": False,
        }
    try:
        argv = shlex.split(cmd)
    except ValueError as exc:
        return {
            "ok": False, "exit_code": None,
            "stdout_tail": "", "stderr_tail": f"bad command: {exc}",
            "timed_out": False,
        }
    try:
        proc = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout_tail": _crop(_as_text(proc.stdout)),
            "stderr_tail": _crop(_as_text(proc.stderr)),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False, "exit_code": None,
            "stdout_tail": _crop(_as_text(getattr(exc, "output", None))),
            "stderr_tail": _crop(_as_text(getattr(exc, "stderr", None))),
            "timed_out": True,
        }
    except OSError as exc:
        return {
            "ok": False, "exit_code": None,
            "stdout_tail": "", "stderr_tail": f"command not found: {exc}",
            "timed_out": False,
        }


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

def summarize(result: dict, kind: str) -> str:
    """One-line verdict for a run result: ``<KIND> PASS|FAIL|TIMEOUT ...``."""
    kind = (kind or "RUN").upper()
    if result.get("timed_out"):
        return f"{kind} TIMEOUT"
    if result.get("ok"):
        return f"{kind} PASS (exit 0)"
    detail = ""
    tail = (result.get("stderr_tail") or "").strip() or (result.get("stdout_tail") or "").strip()
    if tail:
        lines = tail.splitlines()
        detail = " | " + (lines[-1].strip() if lines else tail)[:160]
    code = result.get("exit_code")
    if code is None:
        return f"{kind} FAIL{detail}"
    return f"{kind} FAIL (exit {code}){detail}"


# ---------------------------------------------------------------------------
# Coverage (stdlib only — python -m trace, no pytest-cov)
# ---------------------------------------------------------------------------

_TRACE_SUMMARY_RE = re.compile(r"^\s*(\d+)\s+(\d+)%\s+(.+?)\s+\((.+)\)\s*$")
_COVER_HIT_RE = re.compile(r"^\s*\d+: ")


def _trace_ignore_dirs() -> list[str]:
    """Directories the trace run should skip (stdlib + site-packages)."""
    dirs: list[str] = []
    for p in (sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix):
        if p and p not in dirs:
            dirs.append(p)
    try:
        import site

        for p in site.getsitepackages():
            if p and p not in dirs:
                dirs.append(p)
    except Exception:
        pass
    return dirs


def coverage_command(dir: str, coverdir: str) -> str:
    """Command that runs the project's tests under ``python -m trace``.

    Traces the same runner ``discover_test_command`` picks (pytest or
    ``python -m unittest discover``), writes ``.cover`` files into
    ``coverdir`` and prints the per-file summary to stdout. ``--missing``
    makes trace annotate never-executed lines, so covered/total is real
    coverage rather than always-100%. Stdlib+venv internals are ignored for
    speed. All paths are forward-slashed and shlex-quoted so the command
    round-trips through ``run_command``.
    """
    module = "pytest" if discover_test_command(dir) == "pytest" else "unittest discover"
    py = shlex.quote(sys.executable.replace(os.sep, "/"))
    ignore = " ".join(
        f"--ignore-dir {shlex.quote(p.replace(os.sep, '/'))}" for p in _trace_ignore_dirs()
    )
    return (
        f"{py} -m trace --count --missing --summary "
        f"--coverdir {shlex.quote(coverdir.replace(os.sep, '/'))} "
        f"{ignore} --module {module}"
    )


def parse_trace_summary(text: str, dir: str) -> list[dict]:
    """Parse ``python -m trace --summary`` stdout into per-file rows.

    Each row: ``{"file", "module", "total", "pct"}`` where ``total`` is the
    executable line count and ``pct`` is trace's integer percentage. Only
    files under ``dir`` are kept (stdlib/venv noise filtered out).
    """
    base = os.path.normcase(os.path.abspath(dir)) + os.sep
    rows: list[dict] = []
    for line in (text or "").splitlines():
        m = _TRACE_SUMMARY_RE.match(line)
        if not m:
            continue
        total, pct, module, path = (
            int(m.group(1)), int(m.group(2)), m.group(3).strip(), m.group(4).strip(),
        )
        full = os.path.abspath(path)
        if os.path.normcase(full).startswith(base):
            rows.append({"file": full, "module": module, "total": total, "pct": pct})
    return rows


def count_cover_file(path: str) -> tuple[int, int]:
    """``(covered, total)`` executable lines from a trace ``.cover`` file.

    Executed lines are written as ``%5d:``, executable-but-missing lines as
    ``>>>>>>``; everything else is non-executable padding.
    """
    covered = total = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if _COVER_HIT_RE.match(line):
                covered += 1
                total += 1
            elif line.startswith(">>>>>>"):
                total += 1
    return covered, total


def verify_coverage(dir: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Run the project's tests and report per-file line coverage (stdlib).

    Two subprocess runs: the plain test command first — its exit code is
    authoritative for the verdict because ``python -m trace`` swallows the
    child's exit status — then the same tests under
    ``python -m trace --count --missing --summary`` whose output is parsed
    into per-file rows. Both must succeed for ``ok`` (a broken trace run,
    e.g. pytest not importable by this interpreter, reports FAIL). Returns
    ``{"ok", "exit_code", "timed_out", "rows", "covered", "total", "pct",
    "stdout_tail", "stderr_tail"}`` with each row ``{"file", "module",
    "covered", "total", "pct"}``. Never raises.
    """
    empty = {
        "ok": False, "exit_code": None, "timed_out": False, "rows": [],
        "covered": 0, "total": 0, "pct": 0.0, "stdout_tail": "", "stderr_tail": "",
    }
    if not os.path.isdir(dir):
        return dict(empty, stderr_tail=f"working directory not found: {dir}")
    plain = run_command(discover_test_command(dir), dir, timeout=timeout)
    if plain.get("timed_out"):
        return dict(
            empty, ok=False, timed_out=True,
            stdout_tail=plain.get("stdout_tail", ""),
            stderr_tail=plain.get("stderr_tail", ""),
        )
    coverdir = tempfile.mkdtemp(prefix="verify_cov_")
    try:
        cov = run_command(coverage_command(dir, coverdir), dir, timeout=timeout, tail_len=None)
        rows = parse_trace_summary(cov.get("stdout_tail") or "", dir)
        for row in rows:
            cover_path = os.path.join(coverdir, row["module"] + ".cover")
            if os.path.exists(cover_path):
                covered, total = count_cover_file(cover_path)
                row["covered"] = covered
                row["total"] = total
                row["pct"] = int(100.0 * covered / total) if total else row["pct"]
    finally:
        shutil.rmtree(coverdir, ignore_errors=True)
    covered = sum(r.get("covered", 0) for r in rows)
    total = sum(r.get("total", 0) for r in rows)
    return {
        "ok": bool(plain.get("ok")) and bool(cov.get("ok")),
        "exit_code": plain.get("exit_code"),
        "timed_out": bool(cov.get("timed_out")),
        "rows": rows,
        "covered": covered,
        "total": total,
        "pct": round(100.0 * covered / total, 1) if total else 0.0,
        "stdout_tail": cov.get("stdout_tail") or "",
        "stderr_tail": _tail(
            ((plain.get("stderr_tail") or "") + "\n" + (cov.get("stderr_tail") or "")).strip()
        ),
    }
