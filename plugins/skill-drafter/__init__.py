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
  /skill from-session <session-id>   [U-SURF-2] the FULL lifecycle in ONE
      [--no-save] [--no-publish]     command: export the host session ->
      [--no-receipt]                 draft -> validate (REJECT blocks) ->
                                      save (flat host skills dir) -> receipt
                                      (plugins/receipts ledger when available,
                                      skipped gracefully when not) -> publish
                                      offer (the omni-skills /skills publish
                                      path — never executed). --no-save =
                                      preview (nothing written, no receipt)
  /skill sync [--dry-run]            [U-SURF-2] cross-profile skills sync:
      [--direction=...]              host skills dir <-> xomni profile skills
                                      dir, diff-based, NO-CLOBBER — only
                                      source-only skills are copied; skills
                                      whose content differs on either side are
                                      reported (updated) but never overwritten

Core: core.draft_skill / core.save_skill / core.export_session /
core.draft_last_session / core.lifecycle / core.sync_cross_profile.
No hooks registered — zero per-turn cost.
"""
from __future__ import annotations

import os

try:  # normal package import
    from . import core
except ImportError:  # loaded as a bare file (tests / demo scripts)
    import core  # noqa: F401

_DRAFTS: dict[str, str] = {}  # name -> drafted skill_md awaiting approval


# ─── receipts-by-default (U7) ────────────────────────────────────────────────
# A successful /skill save issues a verifiable receipt (sha256 of the written
# SKILL.md) into the JSONL ledger (plugins/receipts). The receipts plugin is
# optional — if it cannot be loaded or the ledger cannot be written, saves
# behave exactly as before (never raises, never breaks the caller).
_RECEIPTS = None


def _receipts_core():
    """Lazily resolve receipts.core (installed package, else XOMNI checkout)."""
    global _RECEIPTS
    if _RECEIPTS is None:
        mod = None
        try:
            from receipts import core as mod
        except Exception:
            mod = None
        if mod is None:
            try:
                import importlib.util
                import sys as _sys
                home = os.environ.get("XOMNI_HOME", "")
                if not home:
                    home = os.path.abspath(os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "..", ".."))
                cand = os.path.join(home, "plugins", "receipts", "core.py")
                if os.path.isfile(cand):
                    fspec = importlib.util.spec_from_file_location("receipts_core", cand)
                    mod = importlib.util.module_from_spec(fspec)
                    _sys.modules["receipts_core"] = mod
                    fspec.loader.exec_module(mod)
            except Exception:
                mod = None
        _RECEIPTS = mod if mod is not None else False
    return _RECEIPTS or None


def _receipt_file(action: str, target: str, result: str, meta: dict | None = None):
    """Issue a sha256-handled receipt; never raises, never breaks the caller."""
    mod = _receipts_core()
    if mod is None:
        return None
    try:
        return mod.try_file_receipt(action, target, result, meta)
    except Exception:
        return None


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
    _receipt_file("skill.draft.save", os.path.join(result["dest"], "SKILL.md"),
                  f"saved {name} -> {result['dest']}",
                  {"skill": name, "flat": bool(yes)})
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


def _handle_from_session(raw: str) -> str:
    """/skill from-session <session-id> [--no-save] [--no-publish]
    [--no-receipt] — the FULL lifecycle in ONE command: export the host
    session, draft, show the SKILL.md, save with --yes (flat into the HOST
    skills dir), issue the receipt, print the publish offer."""
    save, publish, receipt = True, True, True
    keep = []
    for p in (raw or "").split():
        if p == "--no-save":
            save = False
        elif p == "--no-publish":
            publish = False
        elif p == "--no-receipt":
            receipt = False
        else:
            keep.append(p)
    sid = " ".join(keep).strip().strip('"')
    if not sid:
        return ("/skill from-session <session-id> [--no-save] [--no-publish] "
                "[--no-receipt] — full pipeline in one command: draft -> "
                "validate -> save (host skills dir) -> receipt -> publish offer.")
    result = core.lifecycle(sid, save=save, publish=publish, receipt=receipt)
    lines = [f"/skill from-session {sid}"]
    for st in result["steps"]:
        lines.append(f"  [{st['step']:>9}] {st['status']:<7} {st['detail']}")
    if not result["ok"]:
        lines.append(f"FAILED — {result['reason']}")
        return "\n".join(lines)
    lines.append("")
    lines.append(f"DRAFT {result['name']} — {result['skill_md'].count(chr(10))} "
                 f"lines (session {result.get('session_id') or sid})")
    lines.append("--- SKILL.md ---")
    lines.append(result["skill_md"])
    lines.append("---")
    if result["saved"]:
        lines.append(f"SAVED -> {result['saved']['dest']} "
                     f"(verdict {result['saved']['verdict']}, flat host skills dir)")
    else:
        lines.append("SAVE skipped (--no-save preview — nothing written)")
    if result["receipt"]:
        r = result["receipt"]
        lines.append(f"RECEIPT {r.get('id')} — action={r.get('action')} "
                     f"handle={r.get('handle')}")
    else:
        lines.append("RECEIPT skipped (ledger unavailable or --no-save)")
    offer = result.get("publish_offer") or {}
    if offer.get("command"):
        lines.append(f"PUBLISH OFFER: {' '.join(offer['command'])}")
    if offer.get("hint"):
        lines.append(f"  {offer['hint']}")
    return "\n".join(lines)


def _handle_sync(raw: str) -> str:
    """/skill sync [--dry-run] [--direction=both|host2xomni|xomni2host] —
    cross-profile sync: copies the host skills dir into the xomni profile
    skills dir and vice versa. Diff-based, no-clobber — only source-only
    skills are copied; differing skills are reported (updated) but never
    overwritten."""
    dry, direction = False, "both"
    for p in (raw or "").split():
        if p == "--dry-run":
            dry = True
        elif p.startswith("--direction="):
            direction = p.split("=", 1)[1].strip().lower() or "both"
        elif p in ("--yes", "-y"):
            continue  # never prompts — accepted for U3 non-interactive parity
    if direction not in ("both", "host2xomni", "xomni2host"):
        return (f"/skill sync: unknown --direction '{direction}' — use one of "
                f"both | host2xomni | xomni2host")
    result = core.sync_cross_profile(direction=direction, dry_run=dry)
    if not result["ok"]:
        return f"/skill sync: FAILED — {result['reason']}"
    # receipts-by-default: every skill actually copied (no-clobber adds) gets
    # a sha256-handled receipt; dry runs and no-op passes issue nothing.
    if not dry:
        n = 0
        for label, sync_res in result.get("passes", []):
            for rel, dest in sync_res.get("added", []):
                if _receipt_file("skill.sync", os.path.join(dest, "SKILL.md"),
                                 f"synced {rel} (no-clobber)",
                                 {"skill": rel, "direction": label}):
                    n += 1
    lines = [f"/skill sync {'DRY-RUN' if dry else 'OK'} (direction={direction})"]
    for label, r in result["passes"]:
        lines.append(f"{label}: added {r['added_count']}, "
                     f"updated {r['updated_count']} (no-clobber), "
                     f"skipped {r['skipped_count']} (identical)")
        for rel, dest in r["added"]:
            lines.append(f"  + {rel} -> {dest}")
        for rel, reason in r["updated"]:
            lines.append(f"  ~ {rel} ({reason})")
        for rel in r["skipped"]:
            lines.append(f"  = {rel} (identical)")
        lines.append(f"    src: {r['src']}")
        lines.append(f"    dst: {r['dst']}")
    return "\n".join(lines)


def _handle_skill(raw: str) -> str:
    """/skill dispatcher: from-session | sync | draft-last | draft | save |
    draft-session | <file>."""
    raw = (raw or "").strip()
    low = raw.lower()
    for sub, handler in (("from-session", _handle_from_session),
                         ("sync", _handle_sync),
                         ("draft-last", _handle_draft_last),
                         ("draft-session", _handle_draft_session),
                         ("draft", _handle_draft),
                         ("save", _handle_save)):
        if low == sub or low.startswith(sub + " "):
            return handler(raw[len(sub):].strip())
    return _handle_draft(raw)  # legacy: bare file path


def register(ctx) -> None:
    """Register commands only. Zero hooks — no hook registration anywhere."""
    ctx.register_command(
        "skill", handler=_handle_skill,
        description="Draft a SKILL.md from a session (file, host session id, or newest) and approve it.",
        args_hint="from-session <session-id> [--no-save] [--no-publish] | sync [--dry-run] [--direction=both|host2xomni|xomni2host] | draft <session-file.jsonl> | draft-session <session-id> | draft-last [--limit=N] | save <name> [--yes] [--target=...] [--category=...]")
    ctx.register_command(
        "skill-from-session", handler=_handle_from_session,
        description="Full lifecycle in ONE command from a host session: draft -> validate -> save (host skills dir) -> receipt -> publish offer.",
        args_hint="<session-id> [--no-save] [--no-publish] [--no-receipt]")
    ctx.register_command(
        "skill-sync", handler=_handle_sync,
        description="Cross-profile skills sync (host <-> xomni profile skills dir): diff-based, no-clobber.",
        args_hint="[--dry-run] [--direction=both|host2xomni|xomni2host]")
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
