"""domain-guardrails — XOMNI plugin wiring.

Commands:
  /guardrails            policy table
  /guardrails check <t>  verdict for a command/request (domain, action, policy)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core


def _handle_guardrails(raw: str) -> str:
    arg = (raw or "").strip()
    if not arg:
        return core.policy_table()
    if arg.startswith("check"):
        verdict = core.decide(arg[len("check"):].strip())
        lines = [f"VERDICT: {verdict['allowed'] and 'ALLOWED' or 'REQUIRES APPROVAL'}"]
        for k in ("domain", "action", "policy", "reason"):
            lines.append(f"  {k}: {verdict[k]}")
        return "\n".join(lines)
    return core.policy_table()


def register(ctx) -> None:
    ctx.register_command(
        "guardrails", handler=_handle_guardrails,
        description="Per-domain approval policies: trading analysis OK, execution requires explicit approval. Usage: /guardrails check <text>",
        args_hint="[check <text>]",
    )
    # zero hooks — nothing runs between turns
