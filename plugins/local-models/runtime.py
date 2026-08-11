"""Ollama runtime manager - XOMNI ships Ollama so users get LOCAL models
with zero extra installs.

Strategy (honest, no giant binary in git):
  1. A first-run installer downloads the official portable Ollama build
     (ollama-windows-amd64.zip, ~130 MB) and expands it once into the
     XOMNI runtime dir (official, MIT-licensed source only).
  2. The starter launches ``ollama serve`` detached on 127.0.0.1:11434
     and waits for the OpenAI-compatible /v1/models endpoint.
  3. If the default small model is absent, it is pulled once
     (qwen2.5:3b, ~1.9 GB) so local inference works offline afterwards.

Pure helpers are dependency-injected (probe/binary params) so the module
is unit-testable without a real Ollama install.

Pure stdlib, no Hermes imports.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

OLLAMA_PORT = 11434
OLLAMA_BASE_URL = "http://127.0.0.1:%d/v1" % OLLAMA_PORT
OLLAMA_WIN_ZIP = "https://ollama.com/download/ollama-windows-amd64.zip"
DEFAULT_MODEL = "qwen2.5:3b"  # small (~1.9 GB), good quality-to-size
READY_TIMEOUT = 90.0
PULL_TIMEOUT = 900.0
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"

RUNTIME_REL = "ollama/runtime"  # <XOMNI_HOME>/ollama/runtime
BIN_NAME = "ollama.exe" if sys.platform == "win32" else "ollama"


def runtime_dir(xomni_home: str | None = None) -> Path:
    """$XOMNI_HOME/ollama/runtime, or ~/.xomni/ollama/runtime by default."""
    home = xomni_home or os.environ.get("XOMNI_HOME") or str(Path.home() / ".xomni")
    return Path(home) / RUNTIME_REL


def binary_path(xomni_home: str | None = None) -> Path | None:
    """Path to the bundled ollama binary, or None when not installed yet."""
    p = runtime_dir(xomni_home) / BIN_NAME
    return p if p.is_file() else None


def find_binary(xomni_home: str | None = None) -> str | None:
    """Bundled binary first, then system PATH (user-installed Ollama)."""
    bundled = binary_path(xomni_home)
    if bundled is not None:
        return str(bundled)
    on_path = shutil.which(BIN_NAME)
    return on_path


def is_serving(probe=None, timeout: float = 2.0) -> bool:
    """True when something answers GET {base}/models on the Ollama port."""
    if probe is None:
        from .core import probe_server

        probe = probe_server
    return bool(probe(OLLAMA_BASE_URL, timeout=timeout).get("ok"))


def _extract_zip(zip_path: str, dest: Path) -> None:
    """Expand the official zip into dest (flat or single-dir root)."""
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(str(dest))
    if not (dest / BIN_NAME).is_file():
        for child in dest.iterdir():
            if child.is_dir() and (child / BIN_NAME).is_file():
                shutil.move(str(child / BIN_NAME), str(dest / BIN_NAME))
                break


def install_runtime(xomni_home: str | None = None, url: str = OLLAMA_WIN_ZIP) -> dict:
    """Download + expand the official Ollama build once.

    Returns {'installed': bool, 'binary': str|None, 'error': str|None}.
    Uses a temp file so a failed download never leaves a half-written zip.
    """
    dest = runtime_dir(xomni_home)
    if binary_path(xomni_home) is not None:
        return {"installed": True, "binary": str(binary_path(xomni_home)), "error": None}
    tmp_zip = None
    try:
        dest.mkdir(parents=True, exist_ok=True)
        fd, tmp_zip = tempfile.mkstemp(suffix=".zip", dir=str(dest))
        os.close(fd)
        req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=600) as resp, open(tmp_zip, "wb") as out:
            shutil.copyfileobj(resp, out)
        _extract_zip(tmp_zip, dest)
        os.unlink(tmp_zip)
        tmp_zip = None
    except Exception as exc:  # noqa: BLE001 - report, never crash a turn
        if tmp_zip:
            try:
                os.unlink(tmp_zip)
            except OSError:
                pass
        return {"installed": False, "binary": None, "error": str(exc)}
    binary = binary_path(xomni_home)
    if binary is None:
        return {"installed": False, "binary": None, "error": "zip extracted but binary not found"}
    return {"installed": True, "binary": str(binary), "error": None}


def start_serve(binary: str, xomni_home: str | None = None, wait_ready: bool = True) -> dict:
    """Launch ``ollama serve`` detached and (optionally) wait for readiness.

    Returns {'started': bool, 'ready': bool, 'error': str|None}.
    """
    if is_serving():
        return {"started": True, "ready": True, "error": None}
    env = dict(os.environ)
    env.setdefault("OLLAMA_HOST", "127.0.0.1:%d" % OLLAMA_PORT)
    env.setdefault("OLLAMA_MODELS", str(Path.home() / ".ollama" / "models"))
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [binary, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            creationflags=flags,
        )
    except OSError as exc:
        return {"started": False, "ready": False, "error": str(exc)}
    if not wait_ready:
        return {"started": True, "ready": False, "error": None}
    return {"started": True, "ready": wait_for_ready(), "error": None}


def wait_for_ready(timeout: float = READY_TIMEOUT, step: float = 1.0) -> bool:
    """Poll /v1/models until it answers or the budget runs out."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_serving():
            return True
        time.sleep(step)
    return is_serving()


def pull_model(binary: str, model: str = DEFAULT_MODEL, timeout: float = PULL_TIMEOUT) -> dict:
    """``ollama pull <model>`` -> {'ok': bool, 'error': str|None}."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            [binary, "pull", model],
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
        return {"ok": False, "error": "; ".join(tail) or "ollama pull exited %d" % proc.returncode}
    return {"ok": True, "error": None}


def parse_ollama_list(output: str) -> list[dict]:
    """Parse ``ollama list`` output into [{name, size, modified}].

    Real layout: ``NAME ID SIZE MODIFIED`` e.g. ``qwen2.5:3b 0faf2.. 1.9 GB 2 days ago``.
    Tolerates a legacy 4-col form without the ID column
    (``name 1.2 GB today``) by sniffing whether parts[1] is a size. Skips headers.
    """
    units = {"GB", "MB", "KB", "B"}
    rows = []
    for line in (output or "").splitlines():
        line = line.strip()
        if not line or line.startswith("NAME") or "SIZE" in line.upper():
            continue
        parts = [p for p in line.split() if p]
        if not parts:
            continue
        name = parts[0]
        rest = parts[1:]
        if not rest:
            rows.append({"name": name, "size": "?", "modified": "?"})
            continue
        is_numeric = rest[0].replace(".", "", 1).isdigit()
        if is_numeric:
            # legacy: name SIZE [UNIT] MODIFIED...
            size = rest[0]
            rest = rest[1:]
            if rest and rest[0] in units:
                size = "%s %s" % (size, rest[0])
                rest = rest[1:]
            modified = " ".join(rest) if rest else "?"
        else:
            # real: name ID SIZE [UNIT] MODIFIED...
            rest = rest[1:]
            size = rest[0] if rest else "?"
            rest = rest[1:]
            if rest and rest[0] in units:
                size = "%s %s" % (size, rest[0])
                rest = rest[1:]
            modified = " ".join(rest) if rest else "?"
        rows.append({"name": name, "size": size, "modified": modified})
    return rows


def list_models(binary: str) -> list[dict]:
    """``ollama list`` -> [{name, size, modified}]; [] on any failure."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            [binary, "list"],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return parse_ollama_list(proc.stdout)


def status(xomni_home: str | None = None) -> dict:
    """One-shot status dict for the /ollama command."""
    serving = is_serving()
    binary = find_binary(xomni_home)
    models = list_models(binary) if serving and binary else []
    base = DEFAULT_MODEL.split(":")[0]
    return {
        "serving": serving,
        "binary": binary,
        "bundled_installed": binary_path(xomni_home) is not None,
        "default_model_present": any(m["name"].split(":")[0] == base for m in models),
        "models": [m["name"] for m in models],
        "runtime_dir": str(runtime_dir(xomni_home)),
    }
