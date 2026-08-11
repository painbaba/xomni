"""Context Compact — long-session context/RAM discipline (jcode P1 port).

A ``pre_llm_call`` hook watches ``conversation_history``. When the
message count crosses ``threshold`` (default 40) AND the cooldown
(default 60s) has elapsed AND auto mode is on, the OLDER portion is
compacted into a summary and injected into the CURRENT turn's
user-message api_content only — cache-safe, never mutates stored
history (mirrors the verified prompt-enhancer ``pre_llm_call`` pattern).

Real summaries run through ``ctx.llm.complete`` (temperature 0.2,
host-owned — no plugin key needed). If the LLM call fails or returns
empty, a deterministic fallback is used: the verbatim recent tail plus
counts of the omitted older messages.

Commands:
  /ctxcompact                  status
  /ctxcompact on|off           toggle auto mode
  /ctxcompact now              compact immediately; injected into your next message
  /ctxcompact threshold <n>    set the message-count threshold
  /ctxcompact reset            re-arm: clear cooldown + per-session fire marker

Toggle state lives in plugin-local state.json — never config.yaml.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from . import core

logger = logging.getLogger(__name__)

_CTX = None

STATE_FILE = Path(__file__).resolve().parent / "state.json"

# Last conversation_history snapshot seen by the hook (a shallow list
# copy — the message dicts inside are never touched). Lets /ctxcompact now
# run the summarization immediately without reaching into the agent.
_LAST_HISTORY: list = []

SUMMARY_SYSTEM_PROMPT = (
    "You are a context-compaction engine for a long-running agent conversation. "
    "The user gives you a batch of OLDER chat messages that will be omitted from "
    "the live context. Produce a tight, faithful recap a model can read in place "
    "of the originals to keep the session cheap.\n"
    "RULES\n"
    "1. Preserve every fact, decision, constraint, and piece of task state that "
    "could still matter later. Never invent facts.\n"
    "2. Keep concrete details: file paths, commands, numbers, names, IDs, URLs, "
    "key terms.\n"
    "3. Follow chronological order; 3-8 short bullets or a compact paragraph.\n"
    "4. Output ONLY the summary. No preamble, no markdown fences, no meta-commentary."
)

TRIVIAL_RE = re.compile(r"^\s*(?:\W|\d)*\s*$")  # punctuation / digits / emoji only
TRIVIAL_WORDS = {
    "ok", "okay", "k", "kk", "yes", "yeah", "yep", "y", "no", "nope", "n",
    "thanks", "thank you", "thx", "ty", "done", "got it", "gotcha", "cool",
    "nice", "great", "perfect", "good", "fine", "sure", "continue", "go on",
    "next", "again", "more", "👍", "✅", "🙏", "❤️", "😂",
}
MIN_TRIGGER_LEN = 4  # shorter -> never worth a compaction turn

HELP_TEXT = """context-compact — long-session context/RAM discipline

/ctxcompact                  show status
/ctxcompact on|off           toggle auto-compaction
/ctxcompact now              compact immediately (injected into your next message's context)
/ctxcompact threshold <n>    set the message-count threshold (default 40)
/ctxcompact reset            re-arm: clear cooldown and per-session fire marker

Auto mode: when the conversation passes the threshold, the OLDER
messages are summarized (host model, temp 0.2; deterministic
tail+counts fallback) and the summary rides the current turn's
api_content only — stored history is never mutated (cache-safe)."""


def _should_skip(raw: object) -> bool:
    """Cheap local gate: trivial messages never trigger a compaction."""
    text = (raw or "").strip() if isinstance(raw, str) else ""
    if not text:
        return True
    if text.startswith("/"):
        return True  # slash commands are handled outside the agent loop
    if len(text) < MIN_TRIGGER_LEN:
        return True
    if TRIVIAL_RE.match(text):
        return True
    if text.lower().rstrip(".!?").strip() in TRIVIAL_WORDS:
        return True
    return False


def _get_state() -> core.State:
    return core.State.load(str(STATE_FILE))


def _summarize_older(older: list) -> str | None:
    """Real summary via ctx.llm.complete (host-owned, temperature 0.2).

    Returns ``None`` on any failure so the caller falls back to the
    deterministic tail+counts summary. Never raises into the hook.
    """
    if not older:
        return None
    payload = core.render_tail(older, max_chars=600) or "(no readable text content)"
    try:
        result = _CTX.llm.complete(
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": "OLDER MESSAGES TO COMPACT:\n" + payload},
            ],
            temperature=0.2,
            max_tokens=700,
            purpose="context compaction",
        )
        text = (result.text or "").strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 — silent fallback, never break the loop
        logger.warning("context-compact: LLM summary failed, using fallback: %s", exc)
        return None


def _build_compaction(history: list, state: dict) -> str | None:
    """Compaction context for ``history`` given ``state``.

    Returns ``None`` when there is nothing to compact (history fits
    inside the tail window).
    """
    tail_n = core._coerce_int(state, "tail_n", core.DEFAULT_STATE["tail_n"])
    older, tail = core.split_history(history, tail_n)
    if not older:
        return None
    summary_text = _summarize_older(older)
    return core.format_summary(len(older), core.render_tail(tail), summary_text)


def _on_pre_llm_call(**kwargs):
    """pre_llm_call hook: inject a compacted summary of the OLDER portion
    into the CURRENT turn's api_content. Returns None unless it fires."""
    global _LAST_HISTORY
    history = kwargs.get("conversation_history") or []
    _LAST_HISTORY = list(history)  # shallow snapshot for /ctxcompact now

    state = _get_state()

    # /ctxcompact now force: inject the pre-built compaction on this turn,
    # bypassing every gate (explicit user intent).
    pending = state.data.pop("pending_force", None)
    if pending:
        core.mark_compacted(state.data, time.time(), "")
        state.save()
        return {"context": pending}

    if not core.should_compact(state.data, len(history), time.time()):
        return None
    # Skip gate: trivial current messages never trigger.
    if _should_skip(kwargs.get("user_message")):
        return None
    # Fire at most once per session until /ctxcompact reset re-arms it.
    session_id = kwargs.get("session_id") or ""
    if state.data.get("last_compact_session") == session_id:
        return None

    context = _build_compaction(history, state.data)
    if not context:
        return None
    core.mark_compacted(state.data, time.time(), session_id)
    state.save()
    return {"context": context}


def _status_text(state: core.State) -> str:
    d = state.data
    last = core._coerce_float(d, "last_compact_ts", 0.0)
    ago = max(0.0, time.time() - last)
    fired_line = f"{ago:.0f}s ago" if last else "never"
    arm = (
        "armed"
        if not d.get("last_compact_session")
        else "fired this session (run /ctxcompact reset to re-arm)"
    )
    return "\n".join([
        "context-compact — long-session context/RAM discipline",
        f"  mode        : {'ON (auto)' if d.get('auto', True) else 'OFF (manual only)'}",
        f"  paused      : {bool(d.get('paused'))}",
        f"  threshold   : {core._coerce_int(d, 'threshold', core.DEFAULT_STATE['threshold'])} messages",
        f"  cooldown    : {core._coerce_float(d, 'cooldown_seconds', core.DEFAULT_STATE['cooldown_seconds'])}s between fires",
        f"  tail kept   : {core._coerce_int(d, 'tail_n', core.DEFAULT_STATE['tail_n'])} messages verbatim",
        f"  last fire   : {fired_line}",
        f"  compactions : {d.get('compactions', 0)}",
        f"  session arm : {arm}",
        "  state file  : plugin-local state.json (config.yaml untouched)",
    ])


def _handle_compact(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1].strip() if len(parts) > 1 else ""
    state = _get_state()

    if not cmd or cmd in ("status", "show", "?"):
        return _status_text(state)
    if cmd in ("on", "enable", "true", "1"):
        state.data["auto"] = True
        state.save()
        return "context-compact auto mode ON — long sessions get compacted summaries automatically."
    if cmd in ("off", "disable", "false", "0"):
        state.data["auto"] = False
        state.save()
        return "context-compact auto mode OFF — use /ctxcompact now to compact manually."
    if cmd == "now":
        if not _LAST_HISTORY:
            return "no conversation history seen yet — send a message first, then /ctxcompact now."
        context = _build_compaction(_LAST_HISTORY, state.data)
        if not context:
            return "nothing to compact yet (history fits inside the verbatim tail window)."
        state.data["pending_force"] = context
        core.mark_compacted(state.data, time.time(), "")
        state.save()
        return (
            "[compaction ready — it will be injected into the context of your "
            "next message]\n\n" + context
        )
    if cmd == "threshold":
        if not rest or not rest.isdigit():
            return "usage: /ctxcompact threshold <n>  (message count, e.g. 40)"
        n = max(2, int(rest))
        state.data["threshold"] = n
        state.save()
        return f"context-compact threshold set to {n} messages."
    if cmd == "pause":
        state.data["paused"] = True
        state.save()
        return "context-compact paused — no auto fires until /ctxcompact resume."
    if cmd == "resume":
        state.data["paused"] = False
        state.save()
        return "context-compact resumed."
    if cmd == "reset":
        state.data["last_compact_ts"] = 0.0
        state.data["last_compact_session"] = ""
        state.data.pop("pending_force", None)
        state.save()
        return "context-compact reset — cooldown cleared and the auto hook is re-armed for this session."
    return HELP_TEXT


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_command(
        "ctxcompact",
        handler=_handle_compact,
        description=(
            "Long-session context/RAM discipline: compacts older history into a "
            "summary injected cache-safe into the current turn. "
            "Subs: status|on|off|now|threshold <n>|reset"
        ),
        args_hint="[status|on|off|now|threshold <n>|reset]",
    )
