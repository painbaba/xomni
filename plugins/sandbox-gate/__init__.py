"""sandbox-gate — Hermes plugin wiring.

Pre-execution sandbox for the ``terminal`` tool (Codex P2 discipline port):
high-risk commands are intercepted in ``pre_tool_call`` and vetoed before
they can run, unless the command matches an allowlisted prefix or the gate
is paused (``/sandbox off``).

Hook contract (verified against hermes_cli/plugins.py
``_get_pre_tool_call_directive_details`` + agent/tool_executor.py): the hook
receives ``tool_name`` and ``args`` (dict) kwargs, and the FIRST valid dict
return wins:

    {"action": "block",   "message": "..."}   -> vetoes the tool call;
                                                 message becomes the tool result
    {"action": "approve", "message": "..."}   -> escalates to the human
                                                 approval gate (once/session/
                                                 always/deny)
    None / anything else                      -> tool proceeds untouched

Mapping used here:
    verdict block -> {"action": "block",   ...}   (hard veto)
    verdict warn  -> {"action": "approve", ...}   (human confirmation)
    verdict allow -> None                          (proceed)

Everything else (non-terminal tools, missing args) returns None — a no-op,
so observer-style behavior is preserved and no other tool is affected.

Commands: /sandbox [status|on|off|allow <prefix>|deny <prefix>|test <command>]
    test runs the classifier on a command string WITHOUT executing it.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/sandbox                    show gate status + allowlist\n"
    "/sandbox on|off             enable / pause the gate (state persisted)\n"
    "/sandbox allow <prefix>     allowlist a command prefix (bypasses gate)\n"
    "/sandbox deny <prefix>      remove a prefix from the allowlist\n"
    "/sandbox test <command>     dry-run classification (never executes)\n"
    "/sandbox status             alias for the bare /sandbox"
)

TERMINAL_TOOL_NAMES = ("terminal",)


def _on_pre_tool_call(**kwargs):
    """pre_tool_call hook: block high-risk terminal commands before execution."""
    tool_name = kwargs.get("tool_name") or ""
    if tool_name not in TERMINAL_TOOL_NAMES:
        return None  # non-terminal tools unaffected — pure no-op
    args = kwargs.get("args")
    if not isinstance(args, dict):
        return None
    command = args.get("command")
    if not isinstance(command, str) or not command.strip():
        return None

    verdict, reason = core.decide(command)

    if verdict == core.VERDICT_BLOCK:
        return {"action": "block", "message": f"[sandbox-gate] blocked: {reason}"}
    if verdict == core.VERDICT_WARN:
        return {"action": "approve", "message": f"[sandbox-gate] risky — {reason}"}
    return None


def _status_text(state: dict) -> str:
    lines = [
        f"sandbox-gate: {'ON (enforcing)' if state.get('enabled', True) else 'OFF (paused)'}",
        f"allowlist ({len(state.get('allowlist', []))} prefixes):",
    ]
    for prefix in state.get("allowlist", []):
        lines.append(f"  - {prefix}")
    if not state.get("allowlist"):
        lines.append("  (none)")
    return "\n".join(lines)


def _handle_sandbox(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    state = core.load_state()

    if not cmd or cmd in ("status", "show", "?"):
        return _status_text(state)

    if cmd == "on":
        state["enabled"] = True
        core.save_state(state)
        return "sandbox-gate ON — high-risk terminal commands are blocked unless allowlisted."

    if cmd == "off":
        state["enabled"] = False
        core.save_state(state)
        return "sandbox-gate OFF (paused) — no commands are intercepted. Use /sandbox on to resume."

    if cmd == "allow":
        if not rest:
            return "usage: /sandbox allow <command-prefix>"
        if core.add_allow_prefix(state, rest):
            core.save_state(state)
            return f"allowlisted prefix added: {rest}"
        return f"prefix already allowlisted: {rest}"

    if cmd == "deny":
        if not rest:
            return "usage: /sandbox deny <command-prefix>"
        if core.remove_allow_prefix(state, rest):
            core.save_state(state)
            return f"prefix removed from allowlist: {rest}"
        return f"prefix not in allowlist: {rest}"

    if cmd == "test":
        if not rest:
            return "usage: /sandbox test <command>  (dry-run classification, nothing executes)"
        verdict, reason = core.decide(rest, state)
        return f"verdict: {verdict} — {reason}\n(command was NOT executed)"

    return HELP


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_command(
        "sandbox",
        handler=_handle_sandbox,
        description="sandbox-gate: block high-risk terminal commands unless allowlisted; dry-run test classifier",
        args_hint="[status|on|off|allow <prefix>|deny <prefix>|test <command>]",
    )
