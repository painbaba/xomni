"""Title-statusline — Hermes plugin wiring.

Purpose: close the sponsorship loop. The waitperk/perkline modules write their
sponsor line to ~/.waitperk/current.txt + ~/.perkline/current.txt while the
agent works, but nothing visible shows it to the user. This plugin makes the
sponsor line VISIBLE in the terminal title bar — the Windows-native statusline
(the TUI core change is parked).

Hooks: post_tool_call — fires after every tool call, cheap and no-op-safe —
refreshes the title bar with the current sponsor line.
Commands: /statusline [status|on|off|now], toggling a plugin-local state.json.
All hooks return None; a title-bar failure must NEVER break the agent.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy

from . import core

_CTX = None

# Plugin-local toggle state. deepcopy'd on every load — never shared/mutated
# across loads (the mutable-default trap).
DEFAULT_STATE = {"enabled": True}
_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

HELP = (
    "/statusline                show statusline state + current title\n"
    "/statusline on             enable: sponsor line shows in the terminal title bar\n"
    "/statusline off            disable: restore a neutral title\n"
    "/statusline now            force-refresh the title right now"
)


def _load_state() -> dict:
    state = deepcopy(DEFAULT_STATE)
    try:
        with open(_STATE_PATH, encoding="utf-8") as f:
            state.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass  # first run / corrupt file → defaults
    return state


def _save_state(state: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        with open(_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
    except OSError:
        pass  # state persistence must never break the agent either


def _refresh_title() -> None:
    """Compute the sponsor line and push it to the title bar. Never raises."""
    title = core.pick_line(core.read_sponsor_lines())
    core.set_title(title)


def _on_post_tool_call(**kwargs) -> None:
    """post_tool_call hook: refresh the title bar after every tool call.

    Wrapped in try/except — a title-bar failure must NEVER break the agent.
    """
    try:
        if _load_state().get("enabled", True):
            _refresh_title()
    except Exception:
        pass
    return None


def _handle_title(raw: str) -> str:
    args = (raw or "").strip().lower()
    state = _load_state()

    if not args or args.startswith(("status", "show", "?")):
        return (
            "title-statusline\n"
            f"  enabled   : {state.get('enabled', True)}\n"
            f"  title     : {core.pick_line(core.read_sponsor_lines())}\n"
            f"  state file: {_STATE_PATH}\n"
            f"  /statusline on | off | now"
        )
    if args.startswith("on"):
        state["enabled"] = True
        _save_state(state)
        _refresh_title()
        return "title statusline ON — sponsor line will show in the terminal title bar."
    if args.startswith("off"):
        state["enabled"] = False
        _save_state(state)
        core.set_title(core.NEUTRAL_TITLE)  # off restores a neutral title
        return "title statusline OFF — neutral title restored."
    if args.startswith("now"):
        title = core.cycle_title()
        if title is None:
            return "no sponsor line on disk — nothing to show yet. (/statusline status)"
        return f"title set: {title}"
    return HELP


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_command(
        "statusline", handler=_handle_title,
        description="Terminal-title statusline: show the sponsor line in the title bar (Windows-native)",
        args_hint="[status|on|off|now]",
    )
