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

Usage:
    python .bench/windows_checks.py          # human report, exit 0 = all OK
    python .bench/windows_checks.py --json   # machine-readable report

Exit code is 1 when any check FAILs, 0 otherwise (WARNs do not fail the run).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECK_NAMES = ("npx_shim", "config_write", "path_sanity")

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
# main
# --------------------------------------------------------------------------- #


def main() -> int:
    c = Checker()
    check_npx_shim(c)
    check_config_write(c)
    check_path_sanity(c)

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
