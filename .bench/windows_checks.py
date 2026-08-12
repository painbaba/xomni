#!/usr/bin/env python3
"""XOMNI Windows first-class checks.

Runs on any dev machine (especially Windows) and verifies the three known
Windows failure modes, plus a few extras:

  (a) npx / .cmd shim resolution
      ``subprocess.run(["npx", ...], shell=False)`` raises FileNotFoundError on
      Windows because CreateProcess does no PATHEXT search. The fix is to
      resolve through ``shutil.which`` (honors PATHEXT -> returns ``npx.CMD``)
      and pass the FULL path with shell=False.
  (b) Hermes config dir write access
      A read-only config.yaml (attrib +R, or an ACL that denies write) makes
      direct config edits fail with PermissionError. Detected loudly here.
  (c) Path sanity
      /tmp is a git-bash/MSYS fiction on Windows; native Python has no /tmp.
      Repo code must use os.path/pathlib and tempfile.gettempdir(), never a
      hardcoded /tmp. This check also proves mixed-separator paths normalize
      to the same string.
  (d) Spaces-path launch
      ``python -m xomni_cli`` must work from a directory whose path contains
      spaces (classic Windows breakage: unquoted argv[0] / sys.path entries).
      The probe runs the real CLI ``--help`` from a temp dir with spaces.
  (e) Host-config writer (mcp-catalog)
      The mcp-catalog plugin edits the host config.yaml with surgical text
      appends. On Windows the file is typically CRLF and commands carry
      backslash paths (``C:\\Program Files\\...``); the writer must preserve
      the file's line endings, single-quote backslash scalars, keep every
      other top-level key, and produce YAML that still parses. When pyyaml
      is installed the round-trip is verified with ``yaml.safe_load``;
      otherwise quoting/CRLF are verified at string level.

Usage:
    python .bench/windows_checks.py          # human report, exit 0 = all OK
    python .bench/windows_checks.py --json   # machine-readable report

Exit code is 1 when any check FAILs, 0 otherwise (WARNs do not fail the run).
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK_NAMES = ("npx_shim", "config_write", "path_sanity", "spaces_path", "host_config_edit")

try:  # pyyaml is optional: full round-trip when present, string-level otherwise
    import yaml  # noqa: F401

    HAVE_YAML = True
except ImportError:  # pragma: no cover - exercised only on minimal interpreters
    HAVE_YAML = False

# --------------------------------------------------------------------------- #
# tiny check framework
# --------------------------------------------------------------------------- #


class Checker:
    def __init__(self) -> None:
        self.results: list[dict] = []

    def report(self, name: str, status: str, detail: str) -> None:
        self.results.append({"check": name, "status": status, "detail": detail})

    def fail(self, name: str, detail: str) -> None:
        self.report(name, "FAIL", detail)

    def warn(self, name: str, detail: str) -> None:
        self.report(name, "WARN", detail)

    def ok(self, name: str, detail: str) -> None:
        self.report(name, "PASS", detail)

    def has_fail(self) -> bool:
        return any(r["status"] == "FAIL" for r in self.results)


# --------------------------------------------------------------------------- #
# (a) npx shim resolution
# --------------------------------------------------------------------------- #

NPX_FIX = (
    "Fix: install Node.js (https://nodejs.org) and make sure the install dir "
    "(usually C:\\Program Files\\nodejs) is on PATH; then re-run. In code, "
    "always resolve before subprocess: `full = shutil.which('npx')` and pass "
    "`[full, ...]` with shell=False (full path to npx.CMD executes fine; the "
    "bare name raises FileNotFoundError on Windows)."
)


def check_npx_shim(c: Checker) -> None:
    found = shutil.which("npx")
    if not found:
        c.fail("npx_shim", f"npx is not on PATH (PATHEXT={os.environ.get('PATHEXT', '')!r}). {NPX_FIX}")
        return
    is_win = os.name == "nt"
    ext = os.path.splitext(found)[1].lower()
    if is_win and ext in (".cmd", ".bat"):
        # The shim case: bare 'npx' would FileNotFoundError; full path works.
        try:
            r = subprocess.run([found, "--version"], capture_output=True, text=True, timeout=30)
            ver = (r.stdout or r.stderr or "").strip()
            if r.returncode == 0 and ver:
                c.ok(
                    "npx_shim",
                    f"npx resolved to .cmd shim {found!r}; subprocess with full path works "
                    f"(npx {ver}). NOTE: bare 'npx' with shell=False FAILS on Windows — "
                    f"use shutil.which('npx') first, then pass the full path.",
                )
            else:
                c.fail("npx_shim", f"npx shim {found!r} ran but returned rc={r.returncode} out={r.stdout!r} err={r.stderr!r}")
        except FileNotFoundError:
            c.fail("npx_shim", f"npx shim found at {found!r} but subprocess could not launch it (unexpected). {NPX_FIX}")
        except subprocess.TimeoutExpired:
            c.fail("npx_shim", "npx --version timed out")
    else:
        # npx.exe or POSIX npx: bare name works.
        try:
            r = subprocess.run(["npx", "--version"], capture_output=True, text=True, timeout=30)
            ver = (r.stdout or r.stderr or "").strip()
            if r.returncode == 0 and ver:
                c.ok("npx_shim", f"npx on PATH as {found!r}; bare subprocess call works (npx {ver}).")
            else:
                c.fail("npx_shim", f"npx ran but rc={r.returncode} out={r.stdout!r} err={r.stderr!r}")
        except (FileNotFoundError, OSError):
            c.fail("npx_shim", f"npx found at {found!r} but bare subprocess call failed. {NPX_FIX}")


# --------------------------------------------------------------------------- #
# (b) Hermes config dir write access
# --------------------------------------------------------------------------- #

CONFIG_FIX = (
    "Fix: (1) `attrib -R <config.yaml>` if the Read-only attribute is set; "
    "(2) if that is not it, the file/dir ACL denies write — run your editor "
    "as Administrator, or `icacls <dir> /grant %USERNAME%:(OI)(CI)M` to grant "
    "modify; (3) make sure no other process (hermes itself) holds an exclusive "
    "lock while you edit."
)


def hermes_config_dir() -> Path:
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "hermes"
    return Path.home() / ".config" / "hermes"


def _readonly_attr(path: Path) -> bool:
    """True when the Windows Read-only attribute (FILE_ATTRIBUTE_READONLY) is set."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
        return attrs != 0xFFFFFFFF and bool(attrs & 0x1)
    except Exception:
        return False


def check_config_write(c: Checker) -> None:
    cfgdir = hermes_config_dir()
    if not cfgdir.exists():
        c.warn("config_write", f"hermes config dir {cfgdir} does not exist — nothing to write-protect. (HERMES_HOME={os.environ.get('HERMES_HOME', '(unset)')})")
        return
    # 1) temp file inside the config dir (the real "can hermes write here" test)
    try:
        with tempfile.NamedTemporaryFile(dir=str(cfgdir), delete=True) as tf:
            tf.write(b"xomni windows_checks probe")
            tmp_ok = True
    except (PermissionError, OSError) as exc:
        tmp_ok = False
        c.fail("config_write", f"cannot create temp file in hermes config dir {cfgdir}: {exc}. {CONFIG_FIX}")
    if tmp_ok:
        c.ok("config_write", f"config dir {cfgdir} is writable (temp-file probe OK).")
    # 2) direct append on config.yaml
    cfg = cfgdir / "config.yaml"
    if cfg.exists():
        ro = _readonly_attr(cfg)
        try:
            with open(cfg, "a", encoding="utf-8") as fh:
                fh.write("")  # no-op append; proves write permission
            if ro:
                c.warn("config_write", f"{cfg} has the Read-only attribute set (write probe still passed — attribute may flip later). {CONFIG_FIX}")
            else:
                c.ok("config_write", f"{cfg} is writable (append probe OK).")
        except (PermissionError, OSError) as exc:
            extra = " Read-only attribute IS set — " if ro else ""
            c.fail("config_write", f"cannot write {cfg}: {exc}.{extra} {CONFIG_FIX}")


# --------------------------------------------------------------------------- #
# (c) path sanity
# --------------------------------------------------------------------------- #

PATH_FIX = (
    "Fix: in Python always use os.path / pathlib (repo paths via Path(__file__).resolve()), "
    "never hardcode /tmp — use tempfile.gettempdir() (on Windows that is "
    "%LOCALAPPDATA%\\Temp; /tmp only exists inside git-bash/MSYS)."
)


def check_path_sanity(c: Checker) -> None:
    # 1) repo root resolves consistently via __file__ vs cwd-independent spellings
    root_fwd = REPO_ROOT.as_posix()
    root_back = REPO_ROOT.as_posix().replace("/", os.sep)
    same = os.path.normpath(root_fwd) == os.path.normpath(root_back)
    if not same:
        c.fail("path_sanity", f"repo root normalizes differently across spellings: {root_fwd!r} vs {root_back!r}")
    if not (REPO_ROOT / "pyproject.toml").exists():
        c.fail("path_sanity", f"repo marker pyproject.toml missing under {REPO_ROOT}")
    if same:
        c.ok("path_sanity", f"repo root {REPO_ROOT} resolves identically via forward-slash and {os.sep}-separated spellings.")
    # 2) mixed separators normalize to one string
    mixed = os.path.normpath("C:/Users/HP/xomni") if os.name == "nt" else os.path.normpath("/home/user/xomni")
    if os.name == "nt":
        if mixed == r"C:\Users\HP\xomni":
            c.ok("path_sanity", "mixed-separator path C:/Users/HP/xomni normalizes to C:\\Users\\HP\\xomni (os.path.normpath handles both).")
        else:
            c.fail("path_sanity", f"unexpected normpath result: {mixed!r}")
    # 3) /tmp policy
    if os.name == "nt":
        tmp = Path("/tmp")
        native = tempfile.gettempdir()
        if tmp.exists():
            c.warn("path_sanity", f"/tmp resolves to {tmp.resolve()} — this only happens inside git-bash/MSYS; native Python scripts must use tempfile.gettempdir() ({native}). {PATH_FIX}")
        else:
            c.ok("path_sanity", f"/tmp does not exist in native Windows Python (expected); native temp dir is {native}. {PATH_FIX}")
    else:
        c.ok("path_sanity", f"POSIX host: /tmp exists at {Path('/tmp').resolve()}; tempfile.gettempdir()={tempfile.gettempdir()}.")
    # 4) scan repo shell scripts for hardcoded /tmp (git-bash-only assumption)
    offenders: list[str] = []
    for pat in (".bench/*.sh", "scripts/*.sh", "run.sh", "run.cmd"):
        for f in sorted(REPO_ROOT.glob(pat)):
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(txt.splitlines(), 1):
                if "/tmp" in line and not line.lstrip().startswith("#"):
                    offenders.append(f"{f.relative_to(REPO_ROOT)}:{i}: {line.strip()[:100]}")
    if offenders:
        c.warn("path_sanity", "hardcoded /tmp found in shell scripts (works in git-bash, breaks elsewhere):\n    " + "\n    ".join(offenders))
    else:
        c.ok("path_sanity", "no hardcoded /tmp in .bench/*.sh, scripts/*.sh, run.sh, run.cmd.")


# --------------------------------------------------------------------------- #
# (d) python -m xomni_cli from a path containing spaces
# --------------------------------------------------------------------------- #


def check_spaces_path(c: Checker) -> None:
    """Prove `python -m xomni_cli` launches from a cwd whose path has spaces.

    Classic Windows breakage: unquoted argv[0]/sys.path entries fall apart when
    the working directory contains spaces. Uses the REAL repo CLI (--help is a
    fast, side-effect-free exit) with HERMES_HOME redirected to a throwaway dir.
    """
    tmp = Path(tempfile.mkdtemp(prefix="xomni space probe "))
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT)
    env["HERMES_HOME"] = str(tmp / "hermes_home")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "xomni_cli", "--help"],
            cwd=str(tmp),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0 and "xomni" in out.lower():
            c.ok(
                "spaces_path",
                f"`python -m xomni_cli --help` ran from spaces-path cwd {tmp} (rc=0). "
                f"interpreter={sys.executable}{' (contains spaces)' if ' ' in sys.executable else ''}.",
            )
        else:
            c.fail(
                "spaces_path",
                f"`python -m xomni_cli --help` from spaces-path cwd {tmp} failed: "
                f"rc={r.returncode} out={out[:300]!r}. Fix: quote every argv element / "
                f"sys.path entry that may contain spaces.",
            )
    except (subprocess.TimeoutExpired, OSError) as exc:
        c.fail("spaces_path", f"could not launch `python -m xomni_cli` from spaces-path cwd {tmp}: {exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# (e) mcp-catalog host-config writer: CRLF tolerance + backslash paths
# --------------------------------------------------------------------------- #


def _verify_edit(out: str, expected_servers: set, expected_top: dict) -> list:
    """Return a list of problems with an appended host-config edit."""
    problems: list[str] = []
    if "\r\n" not in out:
        problems.append("CRLF line endings not preserved")
    elif "\n" in out.replace("\r\n", ""):
        problems.append("mixed line endings (stray lone \\n)")
    backslash_quoted = all(
        s in out for s in ("'C:\\Program Files\\nodejs\\npx.CMD'", "'C:\\data'", "'C:\\Program Files\\nodejs'")
    )
    if not backslash_quoted:
        problems.append("backslash paths not single-quoted in rendered block")
    if HAVE_YAML:
        data = yaml.safe_load(out)
        if not isinstance(data, dict):
            problems.append(f"edited config does not parse as a YAML mapping ({type(data).__name__})")
            return problems
        servers = data.get("mcp_servers") or {}
        missing = [s for s in expected_servers if s not in servers]
        if missing:
            problems.append(f"server block(s) missing after parse: {missing}")
        for k, v in expected_top.items():
            if data.get(k) != v:
                problems.append(f"top-level key {k!r} altered: {data.get(k)!r} != {v!r}")
    return problems


def check_host_config_edit(c: Checker) -> None:
    """Exercise the mcp-catalog plugin's host config.yaml writer on Windows-style input.

    A CRLF config.yaml (typical of Windows-written files) with backslash command
    paths must survive the surgical append: line endings preserved, backslash
    scalars single-quoted, unrelated top-level keys untouched, and the result
    still a parseable YAML document that a follow-up idempotency scan detects.
    """
    try:
        spec = importlib.util.spec_from_file_location(
            "xomni_mcp_catalog_core", REPO_ROOT / "plugins" / "mcp-catalog" / "core.py"
        )
        if spec is None or spec.loader is None:
            c.fail("host_config_edit", "cannot locate plugins/mcp-catalog/core.py")
            return
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
    except Exception as exc:
        c.fail("host_config_edit", f"cannot import plugins/mcp-catalog/core.py: {exc}")
        return

    block = {
        "command": r"C:\Program Files\nodejs\npx.CMD",
        "args": ["-y", "server-filesystem", r"C:\data"],
        "env": {"NODE_NO_WARNINGS": "1", "NODE_PATH": r"C:\Program Files\nodejs"},
    }
    tmp = Path(tempfile.mkdtemp(prefix="xomni mcp probe "))
    try:
        problems: list[str] = []
        # scenario A: inline `mcp_servers: {}` in a CRLF config
        text_a = "model: default\r\nmcp_servers: {}\r\nlog_level: info\r\n"
        problems += _verify_edit(
            core._append_server_block(text_a, "win-test", block),
            {"win-test"},
            {"model": "default", "log_level": "info"},
        )
        # scenario B: mid-file insertion between existing entries
        text_b = "model: default\r\nmcp_servers:\r\n  already: {command: x}\r\nlog_level: info\r\n"
        problems += _verify_edit(
            core._append_server_block(text_b, "win-test-2", block),
            {"already", "win-test-2"},
            {"model": "default", "log_level": "info"},
        )
        # idempotency scan against a real file
        cfg = tmp / "config.yaml"
        cfg.write_text(core._append_server_block(text_a, "win-test", block), encoding="utf-8", newline="")
        if not core._server_registered(str(cfg), "win-test"):
            problems.append("_server_registered did not detect the appended server")
        if problems:
            c.fail("host_config_edit", "; ".join(problems))
        else:
            parse_note = "yaml.safe_load round-trip" if HAVE_YAML else "string-level (pyyaml not installed)"
            c.ok(
                "host_config_edit",
                f"mcp-catalog writer preserved CRLF, quoted backslash paths, kept top-level keys, "
                f"and round-tripped ({parse_note}); idempotency scan found the appended server (2 scenarios).",
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def main() -> int:
    c = Checker()
    check_npx_shim(c)
    check_config_write(c)
    check_path_sanity(c)
    check_spaces_path(c)
    check_host_config_edit(c)

    as_json = "--json" in sys.argv[1:]
    if as_json:
        print(json.dumps({"os": os.name, "repo": str(REPO_ROOT), "results": c.results}, indent=2))
    else:
        print(f"XOMNI Windows checks — os={os.name}, repo={REPO_ROOT}\n")
        for r in c.results:
            mark = {"PASS": "PASS", "FAIL": "FAIL", "WARN": "WARN"}.get(r["status"], "?")
            print(f"[{mark}] {r['check']}: {r['detail']}\n")
        fails = [r for r in c.results if r["status"] == "FAIL"]
        warns = [r for r in c.results if r["status"] == "WARN"]
        print(f"summary: {len(c.results) - len(fails) - len(warns)} passed, {len(warns)} warnings, {len(fails)} failed")
        if fails:
            print("exit=1 (FAILs present)")
    return 1 if c.has_fail() else 0


if __name__ == "__main__":
    sys.exit(main())
