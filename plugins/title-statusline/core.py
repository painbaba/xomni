"""Title-statusline core — OpenCode-style statusline, Windows-native.

P4 adaptation: the OpenCode statusline (sponsor line in the terminal title
bar) as a Hermes plugin. Pure stdlib, no Hermes imports — unit-testable in
isolation.

Why the title bar? The TUI core change that would render a persistent
statusline inside the app is parked; the terminal title bar is the one surface
every CLI user already has open while the agent works, and it costs zero
screen real estate. On Windows it is driven natively via
``kernel32.SetConsoleTitleW``; everywhere else we emit the standard OSC 0
title escape sequence, which every modern terminal (xterm, GNOME Terminal,
kitty, iTerm2, tmux, Windows Terminal in VT mode) honors.
"""
from __future__ import annotations

import os
import sys

# Sponsor line files written by the waitperk / perkline modules. Each holds
# one plain-text line: the sponsor line that was on screen at last write
# (e.g. "sponsor▸ PipeDeck: CI pipelines in minutes  [CPC]  (/perkline engage …)").
# Perkline's line carries the pricing/model tier; waitperk's is the plain line.
WAITPERK_LINE = os.path.join(os.path.expanduser("~/.waitperk"), "current.txt")
PERKLINE_LINE = os.path.join(os.path.expanduser("~/.perkline"), "current.txt")

# OSC 0: set window/icon title, BEL-terminated. Emitted to stdout on
# non-Windows terminals (and as a Windows fallback).
OSC_TITLE = "\x1b]0;{title}\x07"

TITLE_MAX = 60          # ~60 chars is the widest a title bar shows usefully
NEUTRAL_TITLE = "[agent]"  # shown when the statusline is off / nothing to show


def _sanitize(title: str) -> str:
    """Strip control characters that could break or smuggle an OSC escape."""
    return "".join(ch for ch in str(title) if ch not in "\x1b\x07\r\n")


def set_title(title: str) -> None:
    """Push ``title`` into the terminal title bar.

    Windows: ``ctypes.windll.kernel32.SetConsoleTitleW`` — native, Unicode-safe,
    works in cmd.exe and Windows Terminal alike. Guarded on ``sys.platform ==
    'win32'`` AND ctypes being importable; any failure falls through to the OSC
    escape rather than raising.

    Fallback (non-Windows, or ctypes unavailable): write the OSC 0 title escape
    ``ESC ] 0 ; <title> BEL`` to stdout, honored by every modern terminal.

    Control characters are stripped from ``title`` first (see ``_sanitize``) so
    sponsor-line content can never inject escape sequences.
    """
    safe = _sanitize(title)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(safe)
            return
        except Exception:
            pass  # ctypes missing/broken → fall through to the OSC escape
    sys.stdout.write(OSC_TITLE.format(title=safe))
    sys.stdout.flush()


def read_sponsor_lines() -> list[str]:
    """Read the current sponsor lines written by the waitperk / perkline modules.

    Order is contract: ``[waitperk_line, perkline_line]``. Missing files (or
    files that are empty/blank — e.g. perkline paused) contribute nothing, so
    missing everything returns ``[]`` and the caller degrades gracefully.
    """
    out: list[str] = []
    for path in (WAITPERK_LINE, PERKLINE_LINE):
        try:
            with open(path, encoding="utf-8") as f:
                line = f.read().strip()
        except OSError:
            continue
        if line:
            out.append(line)
    return out


def pick_line(lines: list[str], prefix: str = "[agent]") -> str:
    """Choose the line to show as the title.

    Prefers perkline's line (it carries the sponsor's pricing/model tier) —
    read_sponsor_lines() returns it LAST, so we scan from the back; a blank
    perkline line (paused) correctly falls through to waitperk's. With nothing
    at all, show just ``prefix`` (a neutral statusline).

    The returned title is ``prefix + line`` truncated to ~``TITLE_MAX`` chars
    — the widest a terminal title bar displays usefully.
    """
    chosen = ""
    for line in reversed(lines):
        if line and line.strip():
            chosen = line.strip()
            break
    title = f"{prefix} {chosen}".strip() if prefix else chosen
    return title[:TITLE_MAX]


def cycle_title(interval_hint: int = 30) -> str | None:
    """One statusline refresh cycle. Returns the title set, or None if there
    is nothing to show (no sponsor lines on disk).

    What it does: recompute the sponsor line from disk and push it to the
    title bar. The function is stateless and cheap — the CALLER owns timing:

      * Active agent: the plugin's ``post_tool_call`` hook fires after every
        tool call, so the title refreshes continuously while work happens;
        no timer is needed and ``interval_hint`` is ignored there.
      * Idle agent: a caller that wants the sponsor to keep showing while no
        tools run may schedule this on a wall-clock timer with
        ``interval_hint`` seconds between calls (default 30). 30s balances
        freshness against churn; SetConsoleTitleW is cheap enough for much
        tighter cadences if a caller wants them.
      * The ``/title now`` command calls this immediately.
    """
    lines = read_sponsor_lines()
    if not lines:
        return None
    title = pick_line(lines)
    set_title(title)
    return title
