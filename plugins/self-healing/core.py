"""self-healing — watchdog, postconditions, config-drift auto-fix, audit trail.

Pure-stdlib core (no third-party imports). Everything here is testable with
injected paths via env vars:

  XOMNI_HEAL_DIR      audit log dir (default ~/.xomni-heal)
  XOMNI_HERMES_HOME   hermes home to scan/fix (default HERMES_HOME, else
                      ~/AppData/Local/hermes)
  XOMNI_ROOT          xomni repo root (default: repo containing this plugin,
                      else C:/Users/HP/xomni)
  XOMNI_CHECKS        path to data/heal/checks.json (default: plugin data dir)

Design rules:
  * Secrets are NEVER read or logged. .env fixes only add a bare ``KEY=``
    placeholder line when the KEY is absent; existing lines are untouched.
  * Every automatic action (watchdog kill, postcondition failure flag, drift
    fix) writes one JSON line to heal.jsonl:
        {ts, detector, subject, action, before, after}
"""
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time

# Canonical provider env-var names (mirrors xomni_cli PROVIDERS catalog).
DEFAULT_ENV_KEYS = [
    "OPENCODE_GO_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY", "GOOGLE_API_KEY", "DEEPSEEK_API_KEY", "XAI_API_KEY",
    "GROQ_API_KEY", "MISTRAL_API_KEY", "TOGETHER_API_KEY",
    "FIREWORKS_API_KEY", "CEREBRAS_API_KEY", "AZURE_OPENAI_API_KEY",
    "NOUS_PORTAL_API_KEY", "XOMNI_OLLAMA", "LMSTUDIO", "CUSTOM_API_KEY",
    "SARVAM_API_KEY", "BHASHINI_API_KEY", "KRUTRIM_API_KEY",
]

# Default provider block the drift scan expects in config.yaml (the XOMNI
# default per xomni_cli: "Zen gateway (opencode.ai) — the XOMNI default").
DEFAULT_PROVIDER = {
    "name": "opencode-go",
    "model_provider": "opencode-go",
    "block": {
        "request_timeout_seconds": "120",
        "stale_timeout_seconds": "60",
    },
}

_DEFAULT_XOMNI_ROOT = r"C:/Users/HP/xomni"
_ENV_LINE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------

def heal_dir() -> str:
    return os.environ.get("XOMNI_HEAL_DIR") or os.path.expanduser("~/.xomni-heal")


def audit_log_path() -> str:
    return os.path.join(heal_dir(), "heal.jsonl")


def hermes_home() -> str:
    return (os.environ.get("XOMNI_HERMES_HOME")
            or os.environ.get("HERMES_HOME")
            or os.path.expanduser("~/AppData/Local/hermes"))


def hermes_plugins_dir(home: str | None = None) -> str:
    return os.path.join(home or hermes_home(), "plugins")


def hermes_config_path(home: str | None = None) -> str:
    return os.path.join(home or hermes_home(), "config.yaml")


def hermes_env_path(home: str | None = None) -> str:
    return os.path.join(home or hermes_home(), ".env")


def _plugin_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def xomni_root() -> str:
    env = os.environ.get("XOMNI_ROOT")
    if env:
        return env
    # Running from the repo checkout: <root>/plugins/<this>/core.py
    candidate = os.path.dirname(os.path.dirname(_plugin_dir()))
    if (os.path.isdir(os.path.join(candidate, "plugins"))
            and os.path.isdir(os.path.join(candidate, "xomni_cli"))):
        return candidate
    return _DEFAULT_XOMNI_ROOT


def checks_path() -> str:
    return (os.environ.get("XOMNI_CHECKS")
            or os.path.join(_plugin_dir(), "data", "heal", "checks.json"))


# --------------------------------------------------------------------------
# audit trail
# --------------------------------------------------------------------------

def audit(detector: str, subject: str, action: str, before, after,
          profile: str | None = None) -> dict:
    """Append one {ts, detector, subject, action, before, after} line.

    ``profile`` stamps the audit entry with the profile name so multi-profile
    runs keep a per-profile trail; legacy single-profile calls leave the key
    out (exact legacy shape preserved).
    """
    entry = {
        "ts": round(time.time(), 3),
        "detector": detector,
        "subject": subject,
        "action": action,
        "before": before,
        "after": after,
    }
    if profile is not None:
        entry["profile"] = profile
    path = audit_log_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return entry


def last_audit_entries(n: int = 10) -> list[dict]:
    path = audit_log_path()
    if not os.path.isfile(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-n:]


# --------------------------------------------------------------------------
# watchdog: kill silent hangs / over-time processes
# --------------------------------------------------------------------------

def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the process and (on Windows) its whole tree. Best effort."""
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=10,
            )
            return
        except Exception:
            pass
    try:
        proc.kill()
    except Exception:
        pass


def run_with_watchdog(cmd, timeout: float = 60.0, quiet_after_s: float = 0.0,
                      tail_lines: int = 20, cap_output: int = 200_000) -> dict:
    """Run ``cmd`` under a watchdog.

    Kills the process if it exceeds ``timeout`` seconds total, or — the
    vectorbt-hang case — if it stays alive but produces NO output for
    ``quiet_after_s`` seconds (alive + silent = hang). ``quiet_after_s <= 0``
    disables the quiet detector.

    Returns: {ok, timed_out, killed, exit_code, tail, output, elapsed, error}
    """
    start = time.time()
    state = {"last_output": time.time()}
    chunks: list[str] = []

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
    except OSError as exc:
        return {"ok": False, "timed_out": False, "killed": False,
                "exit_code": None, "tail": "", "output": "", "error": str(exc)}

    def _reader() -> None:
        # NOTE: raw os.read, NOT proc.stdout.buffer.read(n) — on this Windows
        # build the buffered pipe read blocks until the full n bytes or EOF,
        # which would make output tracking useless. os.read on a pipe returns
        # as soon as ANY bytes arrive (tracks \r progress bars too, not just
        # newline-terminated lines).
        while True:
            try:
                chunk = os.read(proc.stdout.fileno(), 4096)
            except Exception:
                break
            if not chunk:
                break
            state["last_output"] = time.time()
            chunks.append(chunk.decode("utf-8", errors="replace"))

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()

    timed_out = killed = False
    while True:
        rc = proc.poll()
        if rc is not None:
            break
        now = time.time()
        elapsed = now - start
        if timeout and elapsed >= timeout:
            timed_out = killed = True
            _kill_tree(proc)
            break
        if quiet_after_s > 0 and (now - state["last_output"]) >= quiet_after_s:
            killed = True
            _kill_tree(proc)
            break
        time.sleep(0.05)

    try:
        proc.wait(timeout=10)
    except Exception:
        pass
    reader.join(timeout=5)

    full = "".join(chunks)[-cap_output:]
    lines = full.splitlines()
    elapsed = round(time.time() - start, 3)
    return {
        "ok": (rc == 0 and not killed),
        "timed_out": timed_out,
        "killed": killed,
        "exit_code": rc,
        "tail": "\n".join(lines[-tail_lines:]),
        "output": full,
        "elapsed": elapsed,
        "error": None,
    }


def _audit_watchdog_kill(check: dict, res: dict) -> None:
    action = "kill_timeout" if res["timed_out"] else "kill_silent_hang"
    audit(
        detector="watchdog",
        subject=check.get("name") or str(check.get("cmd")),
        action=action,
        before={"exit_code": res["exit_code"], "elapsed": res["elapsed"]},
        after={"killed": True, "elapsed": res["elapsed"],
               "reason": "timeout" if res["timed_out"] else "no output for "
                         f"{check.get('quiet_after_s')}s"},
    )


# --------------------------------------------------------------------------
# postconditions: catch exit-0-but-nothing-happened
# --------------------------------------------------------------------------

def verify_postconditions(cmd_result: dict, expected: list[dict]) -> dict:
    """Verify ``expected`` checks against a command result.

    ``expected`` entries: {type: file_exists|output_contains|service_ping,
    target, value}. A process that exits 0 but fails a postcondition is the
    classic "install claimed success, binary missing" failure — returned as
    ok=False with the failing check flagged.
    """
    checks = []
    for chk in expected:
        ctype = chk.get("type")
        target = chk.get("target", "")
        value = chk.get("value")
        passed = False
        actual = None
        try:
            if ctype == "file_exists":
                # value: truthy => must exist, falsy => must NOT exist
                exists = os.path.exists(target)
                passed = bool(exists) == bool(value)
                actual = "present" if exists else "missing"
            elif ctype == "output_contains":
                hay = (cmd_result or {}).get("output", "") or ""
                actual = value in hay
                passed = actual == bool(value)
            elif ctype == "service_ping":
                host, _, port = target.rpartition(":")
                sock = socket.create_connection((host, int(port)), timeout=1.0)
                sock.close()
                actual = "reachable"
                passed = bool(value)
            else:
                actual = f"unknown check type {ctype!r}"
        except OSError:
            actual = "unreachable" if ctype == "service_ping" else actual
            passed = not bool(value)
        checks.append({
            "type": ctype, "target": target, "value": value,
            "passed": bool(passed), "actual": actual,
        })
    failed = [c for c in checks if not c["passed"]]
    return {"ok": not failed, "checks": checks, "failures": failed}


# --------------------------------------------------------------------------
# config drift scan + auto-fix
# --------------------------------------------------------------------------

def _yaml_flat(text: str) -> dict:
    """Minimal YAML-subset flatten: {dotted.path: (value, line_no)}.

    Good enough for the config keys self-healing cares about (model.provider,
    providers.<name>); skips list items and comments.
    """
    out: dict[str, tuple[str, int]] = {}
    stack: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines()):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        if content.startswith("-") or ":" not in content:
            continue
        key, _, val = content.partition(":")
        key = key.strip().strip('"').strip("'")
        val = val.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        path = ".".join([s[1] for s in stack] + [key])
        stack.append((indent, key))
        out[path] = (val, i)
    return out


def _read_env_keys(path: str) -> list[str]:
    if not os.path.isfile(path):
        return []
    keys = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if _ENV_LINE.match(line):
                keys.append(line.split("=", 1)[0])
    return keys


def default_expected_state() -> dict:
    """Expected state: plugin roster, provider block, canonical env KEY names."""
    plugins = []
    try:
        import sys
        root = xomni_root()
        if root not in sys.path:
            sys.path.insert(0, root)
        import xomni_cli  # noqa: F401
        plugins = sorted(xomni_cli.PLUGIN_TESTS.keys())
    except Exception:
        # fallback: anything in the repo plugins dir with __init__.py
        repo_plugins = os.path.join(xomni_root(), "plugins")
        if os.path.isdir(repo_plugins):
            plugins = sorted(
                n for n in os.listdir(repo_plugins)
                if os.path.isfile(os.path.join(repo_plugins, n, "__init__.py"))
            )
    env_keys = list(DEFAULT_ENV_KEYS)
    return {
        "plugins": plugins,
        "provider": dict(DEFAULT_PROVIDER),
        "env_keys": env_keys,
    }


def drift_scan(expected_state: dict | None = None,
               home: str | None = None) -> list[dict]:
    """Compare expected vs actual config; return a list of drifts.

    ``home``: the profile home to scan (default: the base hermes home).
    Each drift: {key, kind, expected, actual}. Never reads .env values — only
    KEY presence.
    """
    state = expected_state or default_expected_state()
    drifts: list[dict] = []

    # --- plugins roster -------------------------------------------------
    actual_plugins = set()
    if os.path.isdir(hermes_plugins_dir(home)):
        actual_plugins = {n for n in os.listdir(hermes_plugins_dir(home))
                          if os.path.isdir(os.path.join(hermes_plugins_dir(home), n))}
    for name in state.get("plugins", []):
        if name not in actual_plugins:
            drifts.append({"key": f"plugins.{name}", "kind": "plugins",
                           "expected": "present", "actual": "missing"})

    # --- provider block -------------------------------------------------
    cfg_path = hermes_config_path(home)
    flat = _yaml_flat(open(cfg_path, "r", encoding="utf-8").read()) \
        if os.path.isfile(cfg_path) else {}
    prov = state.get("provider", {})
    pname = prov.get("name", "opencode-go")
    model_provider = flat.get("model.provider", (None, -1))[0]
    if model_provider != prov.get("model_provider"):
        drifts.append({"key": "provider.model_provider", "kind": "provider",
                       "expected": prov.get("model_provider"),
                       "actual": model_provider or "missing"})
    if f"providers.{pname}" not in flat:
        drifts.append({"key": f"provider.block.{pname}", "kind": "provider",
                       "expected": f"providers.{pname}: block present",
                       "actual": "missing"})

    # --- .env KEY presence (values NEVER read) -------------------------
    present = set(_read_env_keys(hermes_env_path(home)))
    for key in state.get("env_keys", []):
        if key not in present:
            drifts.append({"key": f"env.{key}", "kind": "env",
                           "expected": "present", "actual": "missing"})

    return drifts


def _fix_plugins(drift: dict, home: str | None = None) -> tuple[bool, dict, str | None]:
    name = drift["key"].split(".", 1)[1]
    src = os.path.join(xomni_root(), "plugins", name)
    dst = os.path.join(hermes_plugins_dir(home), name)
    if not os.path.isdir(src):
        return False, {"present": False}, f"source missing: {src}"
    os.makedirs(hermes_plugins_dir(home), exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return True, {"present": True}, None


def _fix_provider(drift: dict, state: dict,
                  home: str | None = None) -> tuple[bool, dict, str | None]:
    cfg_path = hermes_config_path(home)
    if not os.path.isfile(cfg_path):
        return False, {"present": False}, f"config missing: {cfg_path}"
    prov = state.get("provider", DEFAULT_PROVIDER)
    pname = prov.get("name", "opencode-go")
    with open(cfg_path, "r", encoding="utf-8") as f:
        text = f.read()
    lines = text.splitlines()
    flat = _yaml_flat(text)
    before = {}
    # backup first — config edits are the riskiest fix
    bak = cfg_path + ".bak.heal." + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(cfg_path, bak)
    before["backup"] = os.path.basename(bak)

    if drift["key"] == "provider.model_provider":
        key = "model.provider"
        if key in flat:
            ln = flat[key][1]
            lines[ln] = re.sub(r"^(\s*provider\s*:).*",
                               rf"\1 {prov.get('model_provider')}", lines[ln])
    elif drift["key"] == f"provider.block.{pname}":
        # insert the provider block under providers: (or append the whole
        # providers: section if it doesn't exist yet)
        block = [f"  {pname}:",
                 f"    request_timeout_seconds: {prov['block']['request_timeout_seconds']}",
                 f"    stale_timeout_seconds: {prov['block']['stale_timeout_seconds']}"]
        if "providers" in flat:
            anchor = flat["providers"][1]
            end = len(lines)
            for p, (_, ln) in flat.items():
                if p != "providers" and ln > anchor:
                    end = min(end, ln)
                    break
            # re-indent any existing content under providers: by 2 if needed
            lines[end:end] = block
        else:
            lines.extend([""] + ["providers:"] + block)
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    after = {"provider_block": drift["key"] == f"provider.block.{pname}",
             "model_provider": prov.get("model_provider")}
    return True, after, None


def _fix_env(drift: dict, home: str | None = None) -> tuple[bool, dict, str | None]:
    key = drift["key"].split(".", 1)[1]
    path = hermes_env_path(home)
    before = {"key": key, "state": "absent"}
    with open(path, "a", encoding="utf-8") as f:
        if os.path.getsize(path) > 0:
            with open(path, "rb") as r:
                r.seek(-1, os.SEEK_END)
                if r.read(1) != b"\n":
                    f.write("\n")
        # placeholder only — NEVER a secret value
        f.write(f"{key}=\n")
    return True, {"key": key, "state": "placeholder_added"}, None


def fix_drift(drift: dict, expected_state: dict | None = None,
              home: str | None = None, profile: str | None = None) -> dict:
    """Apply the fix for one drift; every fix is audited (secrets never).

    ``home`` targets a specific profile home (default: base hermes home);
    ``profile`` stamps the audit entry so multi-profile runs keep a
    per-profile trail.
    """
    state = expected_state or default_expected_state()
    kind = drift.get("kind") or drift["key"].split(".", 1)[0]
    error = None
    if kind == "plugins":
        fixed, after, error = _fix_plugins(drift, home)
    elif kind == "provider":
        fixed, after, error = _fix_provider(drift, state, home)
    elif kind == "env":
        fixed, after, error = _fix_env(drift, home)
    else:
        fixed, after, error = False, {}, f"unknown drift kind: {kind}"
    entry = audit(
        detector="drift",
        subject=drift["key"],
        action="fix" if fixed else "fix_failed",
        before={"expected": drift.get("expected"),
                "actual": drift.get("actual")},
        after={**(after or {}), "fixed": fixed, "error": error},
        profile=profile,
    )
    return {"fixed": fixed, "audit": entry, "error": error}


# --------------------------------------------------------------------------
# checks.json runner
# --------------------------------------------------------------------------

def _expand(s: str) -> str:
    def repl(m):
        name = m.group(1)
        if name == "XOMNI_ROOT":
            return xomni_root()
        if name == "HERMES_HOME":
            return hermes_home()
        return os.environ.get(name, m.group(0))
    return re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", repl, s)


def load_checks(path: str | None = None) -> dict:
    path = path or checks_path()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_checks(checks: dict | None = None) -> list[dict]:
    """Run watchdog checks + postcondition checks; audit kills/failures.

    Returns per-check results [{name, kind, ok, detail, data}].
    """
    checks = checks or load_checks()
    results = []
    for chk in checks.get("watchdog", []):
        if not chk.get("enabled", True):
            results.append({"name": chk.get("name"), "kind": "watchdog",
                            "ok": True, "detail": "skipped (disabled)",
                            "data": {}})
            continue
        cmd = [_expand(c) for c in chk.get("cmd", [])]
        res = run_with_watchdog(cmd, timeout=chk.get("timeout", 60),
                                quiet_after_s=chk.get("quiet_after_s", 0))
        if res["killed"]:
            _audit_watchdog_kill(chk, res)
            detail = (f"KILLED ({'timeout ' + str(res['elapsed']) + 's' if res['timed_out'] else 'silent hang'}) "
                      f"elapsed={res['elapsed']}s")
        else:
            detail = f"exited rc={res['exit_code']} in {res['elapsed']}s"
        results.append({"name": chk.get("name"), "kind": "watchdog",
                        "ok": res["ok"], "detail": detail, "data": res})
    for chk in checks.get("postconditions", []):
        res = {"ok": True, "exit_code": None, "output": "", "elapsed": 0.0}
        if chk.get("cmd"):
            res = run_with_watchdog([_expand(c) for c in chk["cmd"]],
                                    timeout=chk.get("timeout", 60),
                                    quiet_after_s=chk.get("quiet_after_s", 0))
        expected = [{"type": chk["type"], "target": _expand(chk.get("target", "")),
                     "value": chk.get("value")}]
        verdict = verify_postconditions(res, expected)
        if not verdict["ok"]:
            audit(detector="postcondition", subject=chk.get("name"),
                  action="check_failed",
                  before={"exit_code": res["exit_code"], "elapsed": res["elapsed"]},
                  after={"failures": verdict["failures"]})
        results.append({"name": chk.get("name"), "kind": "postcondition",
                        "ok": verdict["ok"],
                        "detail": "PASS" if verdict["ok"] else
                                  f"FAILED exit-0-nothing-happened: {verdict['failures']}",
                        "data": verdict})
    return results


# --------------------------------------------------------------------------
# multi-profile: discover / scan / fix ALL hermes profiles (U-ASSURE-2)
# --------------------------------------------------------------------------

def profiles_dir() -> str:
    """Directory holding named hermes profiles (siblings of the base home)."""
    return os.path.join(hermes_home(), "profiles")


def discover_profiles() -> list[dict]:
    """Discover every hermes profile: the base home + profiles/* children.

    Returns [{name, home}] — base first, then profiles/* alphabetically. A
    profile counts only if its home holds a config.yaml; the BASE home is
    included when it exists (it always does in a real install).
    """
    found: list[dict] = []
    base = hermes_home()
    if os.path.isfile(os.path.join(base, "config.yaml")):
        found.append({"name": "base", "home": base})
    pdir = profiles_dir()
    if os.path.isdir(pdir):
        for name in sorted(os.listdir(pdir)):
            home = os.path.join(pdir, name)
            if (os.path.isdir(home)
                    and os.path.isfile(os.path.join(home, "config.yaml"))):
                found.append({"name": name, "home": home})
    return found


def scan_profile(profile: dict, expected_state: dict | None = None) -> dict:
    """Drift-scan one profile (plugins roster + config + .env KEY presence).

    Never reads .env VALUES — KEY presence only. Returns
    {profile, home, ok, drifts, error}; unreadable / missing homes come back
    as a loud error entry, never a crash.
    """
    name = profile.get("name", "?")
    home = profile.get("home", "")
    if not home or not os.path.isdir(home):
        return {"profile": name, "home": home, "ok": False, "drifts": [],
                "error": f"unreadable profile home: {home or '(none)'}"}
    if not os.path.isfile(os.path.join(home, "config.yaml")):
        return {"profile": name, "home": home, "ok": False, "drifts": [],
                "error": f"unreadable profile: config.yaml missing in {home}"}
    try:
        drifts = drift_scan(expected_state, home=home)
    except OSError as exc:
        return {"profile": name, "home": home, "ok": False, "drifts": [],
                "error": f"unreadable profile: {exc}"}
    return {"profile": name, "home": home, "ok": True, "drifts": drifts,
            "error": None}


def scan_profiles(names: list[str] | None = None) -> dict[str, dict]:
    """Scan all discovered profiles (or only ``names``).

    Returns {profile_name: scan_profile_result}; unknown names come back as
    loud error entries.
    """
    profs = discover_profiles()
    by_name = {p["name"]: p for p in profs}
    out: dict[str, dict] = {}
    if names is not None:
        for n in names:
            if n not in by_name:
                out[n] = {"profile": n, "home": None, "ok": False,
                          "drifts": [], "error": f"unknown profile: {n}"}
        profs = [by_name[n] for n in names if n in by_name]
    for p in profs:
        out[p["name"]] = scan_profile(p)
    return out


def fix_profile(profile: dict, expected_state: dict | None = None,
                apply: bool = True) -> dict:
    """Fix every drift of one profile; placeholders only, per-profile audit.

    ``apply=False`` returns the plan ({would_fix}) without touching files.
    Every applied fix is audited with the profile name stamped on the entry.
    """
    name = profile.get("name", "?")
    home = profile.get("home", "")
    res = scan_profile(profile, expected_state)
    if res["error"]:
        return {"profile": name, "home": home, "fixed": 0, "failed": 0,
                "results": [], "error": res["error"]}
    if not apply:
        return {"profile": name, "home": home, "fixed": 0, "failed": 0,
                "would_fix": len(res["drifts"]),
                "results": [{"key": d["key"], "status": "would_fix"}
                            for d in res["drifts"]],
                "error": None}
    results = []
    for d in res["drifts"]:
        r = fix_drift(d, expected_state, home=home, profile=name)
        results.append({"key": d["key"], "fixed": r["fixed"],
                        "error": r["error"]})
    return {"profile": name, "home": home,
            "fixed": sum(1 for r in results if r["fixed"]),
            "failed": sum(1 for r in results if not r["fixed"]),
            "results": results, "error": None}


def fix_profiles(names: list[str] | None = None,
                 apply: bool = True) -> dict[str, dict]:
    """Fix drifts across all discovered profiles (or only ``names``)."""
    profs = discover_profiles()
    by_name = {p["name"]: p for p in profs}
    out: dict[str, dict] = {}
    if names is not None:
        for n in names:
            if n not in by_name:
                out[n] = {"profile": n, "home": None, "fixed": 0, "failed": 0,
                          "results": [], "error": f"unknown profile: {n}"}
        profs = [by_name[n] for n in names if n in by_name]
    for p in profs:
        out[p["name"]] = fix_profile(p, apply=apply)
    return out


# --------------------------------------------------------------------------
# /heal command logic
# --------------------------------------------------------------------------

def cmd_profiles() -> str:
    results = scan_profiles()
    out = ["-- /heal profiles --"]
    for name in sorted(results):
        res = results[name]
        if res["error"]:
            status = f"ERROR: {res['error']}"
        elif res["drifts"]:
            status = f"{len(res['drifts'])} drift(s)"
        else:
            status = "OK"
        out.append(f"  {name:<12} {res['home'] or '?'}  [{status}]")
    return "\n".join(out)


def cmd_scan(arg: str = "") -> str:
    arg = (arg or "").strip().lower()
    out = ["-- /heal scan --"]
    for r in run_checks(load_checks()):
        flag = "PASS" if r["ok"] else "FAIL"
        out.append(f"  [{r['kind']:>12}] {r['name']}: {flag} — {r['detail']}")
    # drift scan: one profile or all (default all)
    names = None if arg in ("", "all") else [arg]
    results = scan_profiles(names)
    for name in sorted(results):
        res = results[name]
        if res["error"]:
            out.append(f"  [   profile] {name}: ERROR — {res['error']}")
        elif res["drifts"]:
            out.append(f"  [   profile] {name}: {len(res['drifts'])} drift(s) found:")
            for d in res["drifts"]:
                out.append(f"      {d['key']}: expected={d['expected']} actual={d['actual']}")
        else:
            out.append(f"  [   profile] {name}: none — config in sync")
    return "\n".join(out)


def cmd_fix(arg: str) -> str:
    arg = (arg or "").strip()
    if not arg:
        return ("/heal fix <profile|all> [--yes]  fix every drift of a profile\n"
                "                                 ('all' = every profile; --yes applies,\n"
                "                                 without it: dry-run plan only)\n"
                "/heal fix <id>                    legacy: fix one drift of the base\n"
                "                                 profile, e.g. plugins.omni-registry,\n"
                "                                 env.ANTHROPIC_API_KEY")
    tokens = arg.split()
    want_yes = "--yes" in [t.lower() for t in tokens]
    target = " ".join(t for t in tokens if t.lower() != "--yes").strip()
    if not target:
        return cmd_fix("")
    names = {p["name"] for p in discover_profiles()}
    if target in names or target == "all":
        sel = None if target == "all" else [target]
        results = fix_profiles(sel, apply=want_yes)
        lines = [f"-- /heal fix {target} {'--yes' if want_yes else '(dry run)'} --"]
        for name in sorted(results):
            r = results[name]
            if r["error"]:
                lines.append(f"  {name}: ERROR — {r['error']}")
            elif not want_yes:
                lines.append(f"  {name}: would fix {r['would_fix']} drift(s) — "
                             "re-run with --yes to apply")
            else:
                lines.append(f"  {name}: {r['fixed']} fixed, {r['failed']} failed")
        if not want_yes:
            total = sum(r.get("would_fix", 0) for r in results.values())
            lines.append(f"  (no changes made; {total} drift(s) pending --yes)")
        return "\n".join(lines)
    # legacy single-drift fix against the base profile (no --yes needed)
    match = [d for d in drift_scan() if d["key"] == target]
    if not match:
        return (f"/heal fix {target}: no such drift or profile "
                "(run /heal scan to list current drifts)")
    r = fix_drift(match[0])
    return (f"/heal fix {target}: {'FIXED' if r['fixed'] else 'FAILED'} "
            f"({r['error'] or 'ok'}) — audited to heal.jsonl")


def cmd_status() -> str:
    entries = last_audit_entries(10)
    if not entries:
        return "-- /heal status: no audit entries yet --"
    out = ["-- /heal status (last %d audit entries) --" % len(entries)]
    for e in entries:
        out.append("  %s  %-13s %-10s %-28s %s" % (
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e["ts"])),
            e["detector"], e["action"], str(e["subject"])[:28],
            json.dumps(e["after"], default=str)[:60]))
    return "\n".join(out)
