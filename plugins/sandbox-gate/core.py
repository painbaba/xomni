"""sandbox-gate core — pure, stdlib-only risk classification. No hermes imports.

The classifier is a pure string classifier: it NEVER executes commands. It
returns a verdict for a command string so callers (plugin hooks, the
``/sandbox test`` dry-run, tests) can decide what to do without running
anything.

Verdicts:
    allow — no risk pattern matched (or gate disabled / allowlisted)
    block — high-risk pattern matched; the call should be vetoed
    warn  — risky-but-conditional pattern matched; caller should ask a human
"""

from __future__ import annotations

import json
import os
import re
from copy import deepcopy

VERDICT_ALLOW = "allow"
VERDICT_BLOCK = "block"
VERDICT_WARN = "warn"

# plugin-local state.json lives next to this module. Operators can override
# via SANDBOX_GATE_STATE (tests do this instead of touching the plugin dir).
STATE_PATH = os.environ.get(
    "SANDBOX_GATE_STATE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json"),
)

DEFAULT_STATE = {"enabled": True, "allowlist": []}

# Shared branch names for the destructive-reset warning.
SHARED_BRANCHES = re.compile(
    r"(?:origin/)?(?:main|master|develop|dev|release|staging)\b", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Block rules (each is a pure function: str -> bool)
# ---------------------------------------------------------------------------


def _rule_rm_rf(cmd: str) -> bool:
    """rm -rf on root/home: `rm -rf /`, `rm -rf ~`, `rm -rf /c/`, `rm -rf C:\`."""
    m = re.search(r"\brm\b([^;|&\n]*)", cmd, re.IGNORECASE)
    if not m:
        return False
    rest = m.group(1)
    if not re.search(r"-[a-zA-Z]*r|--recursive", rest, re.IGNORECASE):
        return False
    if not re.search(r"-[a-zA-Z]*f|--force", rest, re.IGNORECASE):
        return False
    tokens = [t for t in rest.split() if not t.startswith("-")]
    if not tokens:
        return False
    raw = tokens[0].lower()
    target = raw.rstrip("/\\") or raw
    if target == "~":
        return True  # home
    if target in ("/", "/c", "c:"):
        return True  # fs root, msys C: root, windows C: root
    return False


def _rule_dd_dev(cmd: str) -> bool:
    """dd writing to a block device (`dd of=/dev/...`). Null/zero sinks are safe."""
    m = re.search(r"\bdd\b[^;|&\n]*\bof=(\S+)", cmd, re.IGNORECASE)
    if not m:
        return False
    target = m.group(1).strip().lower()
    if not target.startswith("/dev/"):
        return False
    return target not in ("/dev/null", "/dev/zero", "/dev/random", "/dev/urandom")


def _rule_mkfs_format(cmd: str) -> bool:
    """mkfs/format — filesystem creation or disk formatting."""
    if re.search(r"\bmkfs\b", cmd, re.IGNORECASE):
        return True
    # `format C:` / `format /q` (windows), but NOT `--format=oneline` etc.
    return bool(re.search(r"\bformat\s+(?:[a-zA-Z]:|/)", cmd, re.IGNORECASE))


def _rule_pipe_to_shell(cmd: str) -> bool:
    """curl|sh / wget|bash / any pipe-to-shell chain."""
    return bool(re.search(r"\|\s*(?:sudo\s+)?(?:ba|z|k)?sh\b", cmd, re.IGNORECASE))


def _rule_chmod_777(cmd: str) -> bool:
    """chmod ... 777 on an absolute/system path (/, ~, C:\, /c/...)."""
    m = re.search(r"\bchmod\b\s+(-[^\s]+\s+)*777\b\s+(\S+)", cmd, re.IGNORECASE)
    if not m:
        return False
    target = m.group(2)
    return bool(re.match(r"^([~/]|[a-zA-Z]:[\\/])", target))


def _rule_shutdown(cmd: str) -> bool:
    """shutdown / reboot / halt / poweroff."""
    return bool(re.search(r"\b(?:shutdown|reboot|halt|poweroff)\b", cmd, re.IGNORECASE))


def _rule_fork_bomb(cmd: str) -> bool:
    """fork bomb `:(){ :|:& };:` (also spaced variants)."""
    return bool(re.search(r":\s*\(\s*\)\s*\{", cmd))


def _rule_raw_device_write(cmd: str) -> bool:
    """Writes to raw block devices (`> /dev/sd...`). /dev/null is not matched."""
    return bool(re.search(r">\s*/dev/(?:sd|hd|vd|nvme|mmcblk|sr)[a-z0-9]*", cmd, re.IGNORECASE))


# ---------------------------------------------------------------------------
# Warn rules (str -> bool). These should escalate to human approval.
# ---------------------------------------------------------------------------


def _rule_git_push_force(cmd: str) -> bool:
    """git push --force / -f (warn). --force-with-lease is the safe variant."""
    m = re.search(r"\bgit\s+push\b[^;|&\n]*", cmd, re.IGNORECASE)
    if not m:
        return False
    tail = m.group(0)
    if re.search(r"--force-with-lease\b", tail, re.IGNORECASE):
        return False
    return bool(re.search(r"--force\b|(?<![-\w])-f\b", tail, re.IGNORECASE))


def _rule_git_reset_hard(cmd: str) -> bool:
    """git reset --hard on a shared branch (warn)."""
    m = re.search(r"\bgit\s+reset\b[^;|&\n]*--hard\b\s*(\S*)?", cmd, re.IGNORECASE)
    if not m:
        return False
    target = (m.group(1) or "").lower()
    return bool(SHARED_BRANCHES.search(target))


def _rule_curl_upload(cmd: str) -> bool:
    """curl -T / --upload-file — file upload (exfiltration risk, warn)."""
    return bool(re.search(r"\bcurl\b[^;|&\n]*\s(?:-T\b|--upload-file\b)", cmd, re.IGNORECASE))


def _rule_nc_exfil(cmd: str) -> bool:
    """nc <ip> <port> < file — netcat piping a file to a remote host (warn)."""
    return bool(re.search(r"\b(?:nc|ncat|netcat)\b[^;|&\n]*<", cmd, re.IGNORECASE))


def _rule_scp(cmd: str) -> bool:
    """scp to a remote host (warn). Local-only copies are fine."""
    return bool(re.search(r"\bscp\b[^;|&\n]*\S+@[^:\s]+:", cmd, re.IGNORECASE))


BLOCK_RULES = [
    ("rm -rf on filesystem root or home", _rule_rm_rf),
    ("dd writing to a block device", _rule_dd_dev),
    ("filesystem creation / disk format (mkfs/format)", _rule_mkfs_format),
    ("pipe-to-shell chain (curl|sh, wget|bash)", _rule_pipe_to_shell),
    ("chmod 777 on a system/absolute path", _rule_chmod_777),
    ("system shutdown / reboot / halt", _rule_shutdown),
    ("fork bomb", _rule_fork_bomb),
    ("write to a raw block device", _rule_raw_device_write),
]

WARN_RULES = [
    ("git push --force rewrites remote history", _rule_git_push_force),
    ("git reset --hard on a shared branch discards pushed history", _rule_git_reset_hard),
    ("curl upload — possible data exfiltration", _rule_curl_upload),
    ("netcat sending file contents to a remote host", _rule_nc_exfil),
    ("scp to a remote host — verify the destination", _rule_scp),
]


def classify(command_str: str) -> tuple[str, str]:
    """Classify a command string WITHOUT executing it.

    Returns ``(verdict, reason)`` with verdict in ``allow|block|warn``.
    Pure function of the string only — ignores state, allowlist, toggle.
    """
    cmd = (command_str or "").strip()
    if not cmd:
        return (VERDICT_ALLOW, "empty command")
    for reason, rule in BLOCK_RULES:
        try:
            if rule(cmd):
                return (VERDICT_BLOCK, reason)
        except Exception:
            continue  # a bad rule must never crash the classifier
    for reason, rule in WARN_RULES:
        try:
            if rule(cmd):
                return (VERDICT_WARN, reason)
        except Exception:
            continue
    return (VERDICT_ALLOW, "no risk patterns matched")


def _matches_allowlist(cmd: str, state: dict) -> bool:
    for prefix in state.get("allowlist", []) or []:
        if not isinstance(prefix, str) or not prefix.strip():
            continue
        if cmd.lower().startswith(prefix.strip().lower()):
            return True
    return False


def decide(command_str: str, state: dict | None = None) -> tuple[str, str]:
    """Full gate decision: pause toggle -> allowlist -> classify.

    This is what the pre_tool_call hook uses. ``state`` defaults to the
    on-disk state (loaded fresh) when omitted.
    """
    st = state if state is not None else load_state()
    if not st.get("enabled", True):
        return (VERDICT_ALLOW, "sandbox paused (off)")
    cmd = (command_str or "").strip()
    if not cmd:
        return (VERDICT_ALLOW, "empty command")
    if _matches_allowlist(cmd, st):
        return (VERDICT_ALLOW, "allowlisted command prefix")
    return classify(cmd)


# ---------------------------------------------------------------------------
# State persistence (deep-copied at every boundary)
# ---------------------------------------------------------------------------


def default_state() -> dict:
    """Fresh copy of the default state — callers may mutate freely."""
    return deepcopy(DEFAULT_STATE)


def load_state(path: str | None = None) -> dict:
    """Load state from JSON, deep-copied, merged over defaults.

    Missing/corrupt files fall back to defaults — the gate fails closed
    (enabled=True) so a state problem never silently disables the sandbox.
    """
    p = path or STATE_PATH
    state = default_state()
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return state
    if isinstance(data, dict):
        if isinstance(data.get("enabled"), bool):
            state["enabled"] = data["enabled"]
        al = data.get("allowlist")
        if isinstance(al, list):
            state["allowlist"] = [str(x) for x in al if isinstance(x, str)]
    return state


def save_state(state: dict, path: str | None = None) -> None:
    """Write a deep copy of state to JSON atomically (tmp + rename)."""
    p = path or STATE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(p)) or ".", exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(deepcopy(state), f, indent=2, sort_keys=True)
    os.replace(tmp, p)


def add_allow_prefix(state: dict, prefix: str) -> bool:
    """Add a command prefix to the allowlist. Returns True if newly added."""
    prefix = (prefix or "").strip()
    if not prefix:
        return False
    al = state.setdefault("allowlist", [])
    if prefix in al:
        return False
    al.append(prefix)
    return True


def remove_allow_prefix(state: dict, prefix: str) -> bool:
    """Remove a command prefix from the allowlist. Returns True if removed."""
    prefix = (prefix or "").strip()
    al = state.get("allowlist", [])
    if prefix in al:
        al.remove(prefix)
        return True
    return False
