"""domain-guardrails — XOMNI plugin wiring.

Commands:
  /guardrails                    policy table
  /guardrails check <t>          verdict for a command/request (domain, action, policy)
  /guardrails check-tool <n> <d> verdict for an MCP tool (name + description)
  /guardrails check-skill <fm>   verdict for a skill install: inline frontmatter
                                 text, or a path to a SKILL.md file (reads it)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core


def _render_verdict(verdict: dict) -> str:
    lines = [f"VERDICT: {verdict['allowed'] and 'ALLOWED' or 'REQUIRES APPROVAL'}"]
    for k in ("domain", "action", "policy", "requires_approval", "reason"):
        lines.append(f"  {k}: {verdict[k]}")
    return "\n".join(lines)


def _skill_source(arg: str) -> str:
    """Resolve a check-skill argument: path-to-SKILL.md or inline frontmatter text."""
    arg = (arg or "").strip()
    if not arg:
        raise FileNotFoundError(
            "usage: /guardrails check-skill <frontmatter> or <path-to-SKILL.md>")
    looks_like_path = (
        "/" in arg or "\\" in arg
        or arg.lower().endswith(".md")
        or "skill.md" in arg.lower()
    )
    if os.path.isfile(arg):
        with open(arg, encoding="utf-8") as fh:
            return fh.read()
    if looks_like_path:
        raise FileNotFoundError(f"skill file not found: {arg}")
    return arg


def _handle_guardrails(raw: str) -> str:
    arg = (raw or "").strip()
    if not arg:
        return core.policy_table()
    if arg.startswith("check-tool"):
        rest = arg[len("check-tool"):].strip()
        name, _, desc = rest.partition(" ")
        if not name:
            return "ERROR: usage: /guardrails check-tool <name> <description>"
        return _render_verdict(core.decide_tool(name, desc))
    if arg.startswith("check-skill"):
        rest = arg[len("check-skill"):].strip()
        try:
            frontmatter = _skill_source(rest)
        except FileNotFoundError as e:
            return f"ERROR: {e}"
        return _render_verdict(core.decide_skill(frontmatter))
    if arg.startswith("check"):
        return _render_verdict(core.decide(arg[len("check"):].strip()))
    return core.policy_table()


def register(ctx) -> None:
    ctx.register_command(
        "guardrails", handler=_handle_guardrails,
        description="Per-domain approval policies: trading analysis OK, execution requires explicit approval. Usage: /guardrails check <text> | check-tool <name> <desc> | check-skill <frontmatter|path-to-SKILL.md>",
        args_hint="[check <text> | check-tool <name> <desc> | check-skill <frontmatter|path>]",
    )
    # zero hooks — nothing runs between turns
