"""Context Compact — pure logic for long-session context/RAM discipline (jcode P1 port).

No Hermes imports: this module is stdlib-only and unit-testable in
isolation with ``python -m unittest tests.test_core -v``.

The plugin's ``pre_llm_call`` hook watches ``conversation_history``.
Once the message count crosses ``threshold`` AND the cooldown has
elapsed AND auto mode is on, the OLDER portion (everything before the
verbatim tail) is compacted into a summary and injected into the
CURRENT turn's user-message api_content only — cache-safe, never
mutates stored history.
"""

from __future__ import annotations

import json
import os
from copy import deepcopy

# Default state. deepcopy'd per State instance so nested values are never
# shared across instances (mutation leakage between tests/sessions).
DEFAULT_STATE = {
    "auto": True,               # auto-compaction on
    "paused": False,            # manual freeze — blocks should_compact
    "threshold": 40,            # fire once history reaches this many messages
    "cooldown_seconds": 60.0,   # min wall-clock gap between fires
    "tail_n": 10,               # messages kept verbatim in the fallback tail
    "last_compact_ts": 0.0,     # wall-clock of last fire (0 = never fired)
    "last_compact_session": "", # session_id of the last auto fire; /compact reset clears it
    "compactions": 0,           # total fires (auto + manual)
}

# Default path for standalone use. The plugin __init__ always passes the
# plugin-local state.json explicitly, so this is never config.yaml.
STATE_PATH = os.path.join(os.path.expanduser("~"), ".context-compact", "state.json")


class State:
    """Plugin-local JSON state with deepcopy'd defaults.

    Mirrors the perkline Ledger pattern: nested mutable defaults are
    deep-copied per instance so no two states ever share a dict/list
    (the classic Python footgun — mutation leaking between tests,
    sessions, or /compact command invocations).
    """

    def __init__(self, path: str | None = None) -> None:
        self.path = path or STATE_PATH
        self.data = deepcopy(DEFAULT_STATE)
        self.dirty = False

    @classmethod
    def load(cls, path: str | None = None) -> "State":
        """Load state, merging any stored JSON over the defaults.

        Missing or corrupt files fall back to defaults silently — the
        plugin must never break the agent loop over its own state.
        """
        st = cls(path)
        try:
            with open(st.path, encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                st.data.update(loaded)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass  # corrupt/missing state -> defaults
        return st

    def save(self) -> None:
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, sort_keys=True)
        self.dirty = False


def _coerce_int(state: dict, key: str, default: int) -> int:
    try:
        return int(state.get(key, default))
    except (TypeError, ValueError):
        return default


def _coerce_float(state: dict, key: str, default: float) -> float:
    try:
        return float(state.get(key, default))
    except (TypeError, ValueError):
        return default


def should_compact(state: dict, history_len: int, now: float) -> bool:
    """Pure gate: paused -> auto -> threshold -> cooldown.

    Returns ``True`` when a compaction should fire for a turn whose
    history has ``history_len`` messages at wall-clock time ``now``.
    """
    if state.get("paused"):
        return False
    if not state.get("auto", True):
        return False
    threshold = _coerce_int(state, "threshold", DEFAULT_STATE["threshold"])
    if history_len < threshold:
        return False
    cooldown = _coerce_float(state, "cooldown_seconds", DEFAULT_STATE["cooldown_seconds"])
    last = _coerce_float(state, "last_compact_ts", 0.0)
    if now - last < cooldown:
        return False
    return True


def mark_compacted(state: dict, now: float, session_id: str = "") -> dict:
    """Record a fire: stamp the cooldown clock, optionally the session
    marker for the at-most-once-per-session rule, and bump the counter."""
    state["last_compact_ts"] = float(now)
    if session_id:
        state["last_compact_session"] = session_id
    state["compactions"] = int(state.get("compactions", 0)) + 1
    return state


def split_history(history: list, tail_n: int) -> tuple[list, list]:
    """Split into ``(older, tail)`` — older is everything before the
    last ``tail_n`` messages. Returns ``([], history)`` when the whole
    history fits inside the tail window. Never mutates the input."""
    n = max(0, int(tail_n))
    if len(history) <= n:
        return [], list(history)
    return list(history[:-n]), list(history[-n:])


def render_tail(messages: list, max_chars: int = 300) -> str:
    """Flatten user/assistant messages to compact ``[role] text`` lines.

    Deterministic and side-effect free: only reads message dicts, never
    mutates them (cache-safe by construction).
    """
    lines = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            snippet = content.strip().replace("\n", " ")[:max_chars]
            if snippet:
                lines.append(f"[{role}] {snippet}")
    return "\n".join(lines)


def format_summary(old_count: int, tail: str, summary_text: str = "") -> str:
    """Build the injected context block.

    - Real-summary path: ``summary_text`` is embedded as-is.
    - Deterministic fallback: counts of the omitted older messages plus
      the verbatim recent tail.
    Always starts with ``[compacted history]`` so the injection is
    self-describing inside the current turn's user-message context.
    """
    parts = ["[compacted history]"]
    text = (summary_text or "").strip()
    if text:
        parts.append(text)
    else:
        parts.append(
            f"{old_count} earlier message(s) omitted to keep this session cheap; "
            "no summary was available, so the recent tail is preserved verbatim below."
        )
    if tail:
        parts.append("Recent messages (verbatim tail):\n" + tail)
    return "\n\n".join(parts)
