"""skill-drafter — XOMNI plugin wiring (zero hooks).

Commands:
  /skill draft <session-file.jsonl>   draft a SKILL.md from an exported
                                      session transcript (5+ successful tool
                                      calls required), print it, and show
                                      "approve with: /skill save <name>"
  /skill draft-session <session-id>   export a host session via
                                      `hermes sessions export <id>` (subprocess)
                                      and draft from it; loud error naming the
                                      export command when hermes is missing
  /skill draft-last [--limit=N]       draft from the NEWEST host session in
                                      one shot (`hermes sessions list` ->
                                      export -> draft)
  /skill save <name> [--yes] [--target=...] [--category=...]
                                      validate the drafted skill and write
                                      SKILL.md — FAILS LOUD on REJECT (never
                                      writes). --yes skips further prompts and
                                      writes flat into the HOST skills dir
                                      (~/AppData/Local/hermes/skills/<name>/)
                                      so the host curator governs it

Core: core.draft_skill / core.save_skill / core.export_session /
core.draft_last_session.
No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

import os

try:  # normal package import
    from . import core
except ImportError:  # loaded as a bare file (tests / demo scripts)
    import core  # noqa: F401

_DRAFTS: dict[str, str] = {}  # name -> drafted skill_md awaiting approval


def _parse_save_args(raw: str) -> tuple:
    """Split (name, target, category, yes). --yes/-y flagged, not kept."""
    target, category, yes = None, None, False
    keep = []
    for p in (raw or "").split():
        if p.startswith("--target="):
            target = p.split("=", 1)[1].strip() or None
        elif p.startswith("--category="):
            category = p.split("=", 1)[1].strip() or None
        elif p in ("--yes", "-y"):
            yes = True
        else:
            keep.append(p)
    return " ".join(keep).strip(), target, category, yes


def _handle_draft(raw: str) -> str:
    path = (raw or "").strip().strip('"')
    if not path:
        return ("/skill draft <session-file.jsonl> — draft a SKILL.md from an "
                "exported session transcript (5+ successful tool calls required).")
    if not os.path.isfile(path):
        return f"/skill draft: FAILED — no such file: {path}"
    try:
        transcript = core.parse_transcript_file(path)
    except Exception as exc:
        return f"/skill draft: FAILED — could not read transcript: {exc}"
    draft = core.draft_skill(transcript)
    if draft is None:
        return f"/skill draft: REJECTED — {core.draft_reason()} (from {path})"
    _DRAFTS[draft["name"]] = draft["skill_md"]
    return (f"DRAFT {draft['name']} — {draft['success_calls']} successful "
            f"tool calls (from {path})\n\n{draft['skill_md']}\n\n"
            f"approve with: /skill save {draft['name']}")


def _handle_save(raw: str) -> str:
    name, target, category, yes = _parse_save_args(raw)
    if not name:
        return ("/skill save <name> [--yes] [--target=...] [--category=...] — "
                "approve a drafted skill: validate, then write SKILL.md "
                "(fail-loud on REJECT). --yes writes flat into the HOST skills "
                "dir (~/AppData/Local/hermes/skills/<name>/) — no further prompts.")
    if name not in _DRAFTS:
        return (f"/skill save: FAILED — unknown draft '{name}' (draft it first: "
                f"/skill draft <session-file.jsonl>, /skill draft-session <id> "
                f"or /skill draft-last)")
    if yes:
        root = target or core.DEFAULT_SKILLS_ROOT
        result = core.save_skill(name, _DRAFTS[name], skills_root=root, flat=True)
    else:
        result = core.save_skill(name, _DRAFTS[name],
                                 skills_root=target,
                                 category=category or core.DEFAULT_CATEGORY)
    if not result["ok"]:
        return f"/skill save: FAILED — {result['reason']}"
    _DRAFTS.pop(name, None)
    where = "host skills dir" if yes else "plugin drafts"
    return f"/skill save: OK — saved: {name} -> {result['dest']} ({where})"


def _handle_draft_session(raw: str) -> str:
    sid = (raw or "").strip()
    if not sid:
        return ("/skill draft-session <session-id> — export a host session via "
                "`hermes sessions export <id>` and draft a SKILL.md from it.")
    exported = core.export_session(sid)
    if not exported["ok"]:
        return f"/skill draft-session: FAILED — {exported['reason']}"
    draft = core.draft_skill(exported["transcript"])
    if draft is None:
        return f"/skill draft-session: REJECTED — {core.draft_reason()} (session {sid})"
    _DRAFTS[draft["name"]] = draft["skill_md"]
    return (f"DRAFT {draft['name']} — {draft['success_calls']} successful "
            f"tool calls (session {sid})\n\n{draft['skill_md']}\n\n"
            f"approve with: /skill save {draft['name']}")


def _handle_draft_last(raw: str) -> str:
    limit = 200
    for p in (raw or "").split():
        if p.startswith("--limit="):
            try:
                limit = max(1, min(int(p.split("=", 1)[1]), 5000))
            except ValueError:
                pass
    result = core.draft_last_session(limit_messages=limit)
    if not result["ok"]:
        sid = result.get("session_id")
        return (f"/skill draft-last: FAILED — {result['reason']}"
                + (f" (session {sid})" if sid else ""))
    _DRAFTS[result["name"]] = result["skill_md"]
    return (f"DRAFT {result['name']} — {result['success_calls']} successful "
            f"tool calls (session {result['session_id']})\n\n"
            f"{result['skill_md']}\n\n"
            f"approve with: /skill save {result['name']} --yes")


def _handle_skill(raw: str) -> str:
    """/skill dispatcher: draft-last | draft | save | draft-session | <file>."""
    raw = (raw or "").strip()
    low = raw.lower()
    for sub, handler in (("draft-last", _handle_draft_last),
                         ("draft-session", _handle_draft_session),
                         ("draft", _handle_draft),
                         ("save", _handle_save)):
        if low == sub or low.startswith(sub + " "):
            return handler(raw[len(sub):].strip())
    return _handle_draft(raw)  # legacy: bare file path


def register(ctx) -> None:
    """Register commands. Zero hooks — no register_hook call anywhere."""
    ctx.register_command(
        "skill", handler=_handle_skill,
        description="Draft a SKILL.md from a session (file, host session id, or newest) and approve it.",
        args_hint="draft <session-file.jsonl> | draft-session <session-id> | draft-last [--limit=N] | save <name> [--yes] [--target=...] [--category=...]")
    ctx.register_command(
        "skill-draft", handler=_handle_draft,
        description="Alias of /skill draft — draft a SKILL.md from an exported session transcript.",
        args_hint="<session-file.jsonl>")
    ctx.register_command(
        "skill-draft-last", handler=_handle_draft_last,
        description="Draft a SKILL.md from the newest host session (list -> export -> draft).",
        args_hint="[--limit=N]")
    ctx.register_command(
        "skill-save", handler=_handle_save,
        description="Alias of /skill save — validate and write a drafted skill (fail-loud on REJECT).",
        args_hint="<name> [--yes] [--target=...] [--category=...]")
