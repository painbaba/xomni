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


def hermes_plugins_dir() -> str:
    return os.path.join(hermes_home(), "plugins")


def hermes_config_path() -> str:
    return os.path.join(hermes_home(), "config.yaml")


def hermes_env_path() -> str:
    return os.path.join(hermes_home(), ".env")


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

def audit(detector: str, subject: str, action: str, before, after) -> dict:
    """Append one {ts, detector, subject, action, before, after} line."""
    entry = {
        "ts": round(time.time(), 3),
        "detector": detector,
        "subject": subject,
        "action": action,
        "before": before,
        "after": after,
    }
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


def drift_scan(expected_state: dict | None = None) -> list[dict]:
    """Compare expected vs actual config; return a list of drifts.

    Each drift: {key, kind, expected, actual}. Never reads .env values — only
    KEY presence.
    """
    state = expected_state or default_expected_state()
    drifts: list[dict] = []

    # --- plugins roster -------------------------------------------------
    actual_plugins = set()
    if os.path.isdir(hermes_plugins_dir()):
        actual_plugins = {n for n in os.listdir(hermes_plugins_dir())
                          if os.path.isdir(os.path.join(hermes_plugins_dir(), n))}
    for name in state.get("plugins", []):
        if name not in actual_plugins:
            drifts.append({"key": f"plugins.{name}", "kind": "plugins",
                           "expected": "present", "actual": "missing"})

    # --- provider block -------------------------------------------------
    cfg_path = hermes_config_path()
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
    present = set(_read_env_keys(hermes_env_path()))
    for key in state.get("env_keys", []):
        if key not in present:
            drifts.append({"key": f"env.{key}", "kind": "env",
                           "expected": "present", "actual": "missing"})

    return drifts


def _fix_plugins(drift: dict) -> tuple[bool, dict, str | None]:
    name = drift["key"].split(".", 1)[1]
    src = os.path.join(xomni_root(), "plugins", name)
    dst = os.path.join(hermes_plugins_dir(), name)
    if not os.path.isdir(src):
        return False, {"present": False}, f"source missing: {src}"
    os.makedirs(hermes_plugins_dir(), exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return True, {"present": True}, None


def _fix_provider(drift: dict, state: dict) -> tuple[bool, dict, str | None]:
    cfg_path = hermes_config_path()
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


def _fix_env(drift: dict) -> tuple[bool, dict, str | None]:
    key = drift["key"].split(".", 1)[1]
    path = hermes_env_path()
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


def fix_drift(drift: dict, expected_state: dict | None = None) -> dict:
    """Apply the fix for one drift; every fix is audited (secrets never)."""
    state = expected_state or default_expected_state()
    kind = drift.get("kind") or drift["key"].split(".", 1)[0]
    error = None
    if kind == "plugins":
        fixed, after, error = _fix_plugins(drift)
    elif kind == "provider":
        fixed, after, error = _fix_provider(drift, state)
    elif kind == "env":
        fixed, after, error = _fix_env(drift)
    else:
        fixed, after, error = False, {}, f"unknown drift kind: {kind}"
    entry = audit(
        detector="drift",
        subject=drift["key"],
        action="fix" if fixed else "fix_failed",
        before={"expected": drift.get("expected"),
                "actual": drift.get("actual")},
        after={**(after or {}), "fixed": fixed, "error": error},
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
# /heal command logic
# --------------------------------------------------------------------------

def cmd_scan() -> str:
    checks = load_checks()
    out = ["-- /heal scan --"]
    for r in run_checks(checks):
        flag = "PASS" if r["ok"] else "FAIL"
        out.append(f"  [{r['kind']:>12}] {r['name']}: {flag} — {r['detail']}")
    drifts = drift_scan()
    if drifts:
        out.append(f"  [      drift] {len(drifts)} drift(s) found:")
        for d in drifts:
            out.append(f"      {d['key']}: expected={d['expected']} actual={d['actual']}")
    else:
        out.append("  [      drift] none — config in sync")
    return "\n".join(out)


def cmd_fix(arg: str) -> str:
    arg = (arg or "").strip()
    if not arg:
        return "/heal fix <id> — e.g. /heal fix plugins.omni-registry, /heal fix all"
    drifts = drift_scan()
    if arg == "all":
        if not drifts:
            return "/heal fix all: nothing to fix"
        lines = ["-- /heal fix all --"]
        for d in drifts:
            r = fix_drift(d)
            lines.append(f"  {d['key']}: {'FIXED' if r['fixed'] else 'FAILED'} "
                         f"({r['error'] or 'ok'}) → audit id line appended")
        return "\n".join(lines)
    match = [d for d in drifts if d["key"] == arg]
    if not match:
        return f"/heal fix {arg}: no such drift (run /heal scan to list current drifts)"
    r = fix_drift(match[0])
    return (f"/heal fix {arg}: {'FIXED' if r['fixed'] else 'FAILED'} "
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
