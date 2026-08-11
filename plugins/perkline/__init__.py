"""PerkLine v2 — Hermes plugin wiring.

Hooks: pre_llm_call + post_tool_call count renders (the line was on screen),
plus on_session_end flushes state. All counting happens in memory against a
cached ledger; disk writes (state.json + current.txt) are batched to at most
once per 30s and on session end. All hooks return None — this module never
alters agent behavior.
Commands: /perkline [status|engage|complete|pause|resume|auction|demo|sync].
"""
from __future__ import annotations

import json
import os
import time

from . import core

_CTX = None

# Hot-path throttling (incident fix): the hooks fire on EVERY pre_llm_call
# and post_tool_call. Loading + saving the 20KB ledger and walking the cwd
# on every event is exactly what caused the ~100x slowdown. The ledger is
# now held in memory for the life of the process and persisted at most once
# per FLUSH_INTERVAL plus on session end.
FLUSH_INTERVAL = 30.0
_LEDGER: core.Ledger | None = None
_LAST_SAVE_TS = 0.0
_LAST_LINE_TS = 0.0

HELP = (
    "/perkline                show status (renders, engagements, earnings, auction)\n"
    "/perkline engage [id]    record an engagement with the on-screen sponsor (CPC)\n"
    "/perkline complete <id>  confirm a completed action (CPA) — only when you actually did it\n"
    "/perkline pause|resume    blank the line / resume earning\n"
    "/perkline auction         run a demo second-price auction of the slot\n"
    "/perkline sync            push receipts + counts to sync_url (dry-run if unset)"
)


def _ledger() -> core.Ledger:
    global _LEDGER
    if _LEDGER is None:
        _LEDGER = core.Ledger.load()
    return _LEDGER


def _flush(now: float | None = None) -> None:
    """Persist pending state + refresh current.txt (throttled by the caller)."""
    global _LAST_SAVE_TS, _LAST_LINE_TS
    led = _ledger()
    if led.dirty:
        led.save()
    core._write_line(led)
    now = now if now is not None else time.time()
    _LAST_SAVE_TS = now
    _LAST_LINE_TS = now


def _repo_tags() -> list[str]:
    try:
        return core.stack_tags(os.getcwd())
    except OSError:
        return []


def _on_render(**kwargs) -> None:
    """Count a render in memory; persist at most once per FLUSH_INTERVAL."""
    global _LAST_SAVE_TS, _LAST_LINE_TS
    led = _ledger()
    if led.state.get("paused"):
        return None  # cheap guard: no load, no walk, no write while paused
    now = time.time()
    core.record_render(led, repo_tags=_repo_tags(), now=now, write_line=False)
    if now - _LAST_SAVE_TS >= FLUSH_INTERVAL:
        _flush(now)
    elif now - _LAST_LINE_TS >= FLUSH_INTERVAL:
        core._write_line(led)
        _LAST_LINE_TS = now
    return None


def _on_session_end(**kwargs) -> None:
    """Flush everything on session end so counts survive a crash."""
    _flush()
    return None


def _handle_perkline(raw: str) -> str:
    args = (raw or "").strip()
    parts = args.split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    led = _ledger()
    tags = _repo_tags()

    if not cmd or cmd.startswith(("status", "show", "?")):
        return core.status_text(led, tags)
    if cmd == "engage":
        r = core.engage(led, rest or None, now=time.time())
        if not r.get("counted"):
            return "no sponsor on screen (paused or none eligible)."
        _flush()
        extra = f" — open: {r['url']}" if r.get("url") else ""
        return f"engagement recorded for {r['sponsor']['id']} (CPC ${r['sponsor'].get('price', 0)}).{extra}"
    if cmd == "complete":
        if not rest:
            return "usage: /perkline complete <sponsor-id> — only confirm when you actually completed the action."
        r = core.complete_action(led, rest, now=time.time())
        if r.get("error"):
            return r["error"]
        _flush()
        return f"action recorded for {r['sponsor']['id']} (CPA ${r['sponsor'].get('price', 0)})."
    if cmd == "pause":
        led.state["paused"] = True
        _flush()
        return "perkline paused — renders no longer accrue."
    if cmd == "resume":
        led.state["paused"] = False
        _flush()
        return "perkline resumed."
    if cmd == "auction":
        bids = [{"sponsor_id": s["id"], "bid": float(s.get("budget", 100) * 0.1)} for s in led.config.get("sponsors", [])]
        if len(bids) < 2:
            return "need at least 2 sponsors to run an auction."
        r = core.run_auction(led, bids)
        _flush()
        return f"second-price auction: winner {r['winner']} pays ${r['price']:.2f} (second-highest bid)."
    if cmd == "sync":
        r = core.sync(led)
        _flush()
        if r["mode"] == "dry-run":
            return (
                "dry-run: no sync_url configured, nothing was sent.\n"
                "payload that WOULD be sent (receipts included, no prompts/code):\n"
                + json.dumps(r["payload"], indent=2)
            )
        if r["mode"] == "live":
            return f"synced (HTTP {r['status']})"
        return f"sync failed (agent unaffected): {r.get('error')}"
    return HELP


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_hook("pre_llm_call", _on_render)
    ctx.register_hook("post_tool_call", _on_render)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_command(
        "perkline", handler=_handle_perkline,
        description="PerkLine v2 sponsor engine: tiers, relevance match, receipts, auction",
        args_hint="[status|engage|complete|pause|resume|auction|sync]",
    )
