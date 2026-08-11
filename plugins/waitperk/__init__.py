"""WaitPerk sponsorship module — Hermes plugin wiring.

Hooks: on_session_start/end (ledger windows), pre_llm_call + post_tool_call
(impression counting). Commands: /sponsor [status|pause|resume|sync|demo].
Impressions are counted IN MEMORY against a cached ledger; disk writes
(state.json + current.txt) are batched to at most once per 30s and flushed
on session end. All hooks return None — this module never alters agent
behavior.
"""
from __future__ import annotations

import os
import time

from . import core

_CTX = None

# Hot-path throttling (incident fix): the original plugin rewrote
# ~/.waitperk/current.txt AND state.json on EVERY pre_llm_call and
# post_tool_call (4 file ops per turn, doubling every turn's disk I/O).
# Impressions now accumulate in memory and are persisted at most once per
# FLUSH_INTERVAL plus on session end.
FLUSH_INTERVAL = 30.0
_LEDGER: core.Ledger | None = None
_LAST_SAVE_TS = 0.0
_LAST_LINE_TS = 0.0

HELP = (
    "/sponsor               show sponsor status (impressions, share, earnings)\n"
    "/sponsor pause         blank the sponsor line (stops earning)\n"
    "/sponsor resume        un-pause\n"
    "/sponsor sync          push impressions to sync_url (dry-run if unset)\n"
    "/sponsor demo          cycle to the next demo sponsor"
)


def _flush(now: float | None = None) -> None:
    """Persist pending state + refresh current.txt (throttled by the caller)."""
    global _LAST_SAVE_TS, _LAST_LINE_TS
    led = _ledger()
    if led.dirty:
        led.save()
    core._write_current_line(led)
    now = now if now is not None else time.time()
    _LAST_SAVE_TS = now
    _LAST_LINE_TS = now


def _ledger() -> core.Ledger:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = core.Ledger.load()
    return _LEDGER


def _on_session_start(**kwargs) -> None:
    """Fresh ledger per session; rotate sponsor and persist (rare event)."""
    global _LEDGER, _LAST_SAVE_TS, _LAST_LINE_TS
    _LEDGER = core.Ledger.load()
    led = _LEDGER
    core.start_session(led)
    led.save()
    core._write_current_line(led)
    now = time.time()
    _LAST_SAVE_TS = now
    _LAST_LINE_TS = now
    return None


def _on_session_end(**kwargs) -> None:
    """Close the session window and flush everything."""
    global _LEDGER
    led = _ledger()
    core.end_session(led)
    _flush()
    return None


def _on_work_event(**kwargs) -> None:
    """Impression counting hook — fires for LLM calls and tool calls.

    Counts in memory; persists state.json + current.txt at most once per
    FLUSH_INTERVAL (and the final flush happens on session end).
    """
    global _LAST_SAVE_TS, _LAST_LINE_TS
    led = _ledger()
    if led.state.get("paused"):
        # keep the idle-clock fresh without any disk I/O
        core.record_work_event(led, now=time.time(), write_line=False)
        return None
    now = time.time()
    core.record_work_event(led, now=now, write_line=False)
    if now - _LAST_SAVE_TS >= FLUSH_INTERVAL:
        _flush(now)
    elif now - _LAST_LINE_TS >= FLUSH_INTERVAL:
        core._write_current_line(led)
        _LAST_LINE_TS = now
    return None


def _handle_sponsor(raw: str) -> str:
    args = (raw or "").strip().lower()
    if not args or args.startswith(("status", "show", "?")):
        return core.status_text(_ledger())
    if args.startswith("pause"):
        led = _ledger()
        led.state["paused"] = True
        _flush()
        return "sponsor line paused — impressions no longer accrue. /sponsor resume to continue."
    if args.startswith("resume"):
        led = _ledger()
        led.state["paused"] = False
        _flush()
        return "sponsor line resumed."
    if args.startswith("sync"):
        led = _ledger()
        result = core.sync(led)
        _flush()
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
        led = _ledger()
        sp = core.rotate_sponsor(led)
        _flush()
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
