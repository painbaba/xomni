"""WaitPerk sponsorship module — Hermes plugin wiring.

Hooks: on_session_start/end (ledger windows), pre_llm_call + post_tool_call
(impression counting). Commands: /sponsor [status|pause|resume|sync|demo].
All hooks return None — this module never alters agent behavior.
"""
from __future__ import annotations

import os
import time

from . import core

_CTX = None

HELP = (
    "/sponsor               show sponsor status (impressions, share, earnings)\n"
    "/sponsor pause         blank the sponsor line (stops earning)\n"
    "/sponsor resume        un-pause\n"
    "/sponsor sync          push impressions to sync_url (dry-run if unset)\n"
    "/sponsor demo          cycle to the next demo sponsor"
)


def _on_session_start(**kwargs) -> None:
    led = core.Ledger.load()
    core.start_session(led)
    led.save()
    return None


def _on_session_end(**kwargs) -> None:
    led = core.Ledger.load()
    core.end_session(led)
    led.save()
    return None


def _on_work_event(**kwargs) -> None:
    """Impression counting hook — fires for LLM calls and tool calls."""
    led = core.Ledger.load()
    core.record_work_event(led, now=time.time())
    led.save()
    return None


def _handle_sponsor(raw: str) -> str:
    args = (raw or "").strip().lower()
    if not args or args.startswith(("status", "show", "?")):
        return core.status_text(core.Ledger.load())
    if args.startswith("pause"):
        led = core.Ledger.load()
        led.state["paused"] = True
        led.save()
        core._write_current_line(led)
        return "sponsor line paused — impressions no longer accrue. /sponsor resume to continue."
    if args.startswith("resume"):
        led = core.Ledger.load()
        led.state["paused"] = False
        led.save()
        core._write_current_line(led)
        return "sponsor line resumed."
    if args.startswith("sync"):
        led = core.Ledger.load()
        result = core.sync(led)
        led.save()
        if result["mode"] == "dry-run":
            return (
                "dry-run: no sync_url configured, nothing was sent.\n"
                "payload that WOULD be sent:\n"
                + _fmt_payload(result["payload"])
            )
        if result["mode"] == "live":
            return f"synced {result['payload']['impressions']} impressions (HTTP {result['status']})"
        return f"sync failed (agent unaffected): {result.get('error')}"
    if args.startswith("demo"):
        led = core.Ledger.load()
        sp = core.rotate_sponsor(led)
        led.save()
        core._write_current_line(led)
        return f"demo sponsor now on screen: {sp['message']}"
    if args.startswith(("help", "h")):
        return HELP
    return HELP


def _fmt_payload(payload: dict) -> str:
    return "\n".join(f"  {k}: {v}" for k, v in payload.items())


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("pre_llm_call", _on_work_event)
    ctx.register_hook("post_tool_call", _on_work_event)
    ctx.register_command(
        "sponsor", handler=_handle_sponsor, description="WaitPerk sponsor module: impressions, share, earnings",
        args_hint="[status|pause|resume|sync|demo]",
    )
