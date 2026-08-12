"""skill-drafter core — auto-skill from successful sessions.

Pure stdlib. Zero hooks.

Parses a session transcript (list of {role, content/tool_calls} entries, or a
JSONL / JSON-array file), extracts the successful tool-call sequence (tool
name, inputs summary, successful-outcome markers), infers a skill name from
the goal line, and drafts a complete SKILL.md (frontmatter: name, description,
version 1.0.0, author from XOMNI_USER / git config; body: numbered procedure
steps carrying the exact commands discovered).

Gate: transcripts with fewer than ``min_success_calls`` (default 5) successful
tool calls are rejected — ``draft_skill`` returns None and the reason is
available via :func:`draft_reason` (or the full result via
:func:`draft_skill_checked`).

Saving: :func:`save_skill` validates the draft first (frontmatter present,
name/description/version present, name matches, no destructive/obfuscated
patterns, >= 3 procedure steps) and FAILS LOUD on REJECT — nothing is written
unless the verdict is PASS.

Host sessions: :func:`export_session` shells out to ``hermes sessions export
--session-id <id>`` when the hermes CLI is available; otherwise it returns a
loud error naming the exact export command to run by hand (the plugin never
hooks the host). :func:`draft_last_session` bridges the NEWEST host session
(``hermes sessions list`` -> export -> draft) in one call, and
:func:`save_skill` with ``flat=True`` writes straight into the host skills
root (``skills/<name>/SKILL.md``) for the host curator to govern.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

MIN_SUCCESS_CALLS = 5
DEFAULT_VERSION = "1.0.0"
DEFAULT_CATEGORY = "auto-drafted"
DEFAULT_SKILLS_ROOT = os.path.expanduser("~/AppData/Local/hermes/skills")

# ------------------------------------------------------------------ frontmatter
FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S | re.M)

DANGEROUS_PATTERNS = [
    (re.compile(r"\.\./|\.\.\\"), "path escape"),
    (re.compile(r"(?i)(rm\s+-rf|format\s+[a-z]:|del\s+/[fsq])"), "destructive command"),
    (re.compile(r"(?i)base64.*-d\s|powershell.*-enc|cmd\.exe\s+/c\s+.*\bdel\b"), "obfuscated exec"),
]

# Markers that make a tool outcome count as FAILED (in addition to explicit
# is_error/error/success flags in the transcript).
_FAIL_MARKERS = re.compile(
    r"(?i)(traceback|failed|failure|exception|error\s*:|exit_code\s*[:=]\s*[1-9]|"
    r"command exited with non-zero|nonzero exit|permission denied|no such file)"
)

_STOP_WORDS = {
    "please", "help", "can", "you", "could", "would", "i", "want", "need",
    "to", "the", "a", "an", "for", "me", "my", "with", "and", "of", "in",
    "on", "it", "this", "that", "is", "are", "do", "does", "how", "what",
}

_last_reason = ""


def draft_reason() -> str:
    """Human-readable reason for the most recent rejection (or '')."""
    return _last_reason


def _slugify(text: str, maxlen: int = 40, words: int = 4) -> str:
    """kebab-case skill name from a phrase — first *words* significant words."""
    parts = []
    for tok in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if tok in _STOP_WORDS:
            continue
        parts.append(tok)
        if len(parts) >= words:
            break
    if not parts:
        parts = ["auto-skill"]
    name = "-".join(parts)[:maxlen].rstrip("-")
    return name or "auto-skill"


def _author() -> str:
    """Author: XOMNI_USER env, else git config user.name, else 'xomni'."""
    env = (os.environ.get("XOMNI_USER") or "").strip()
    if env:
        return env
    git = shutil.which("git")
    if git:
        try:
            proc = subprocess.run([git, "config", "user.name"],
                                  capture_output=True, text=True, timeout=10)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception:
            pass
    return "xomni"


# ------------------------------------------------------------------ parsing
def parse_transcript_text(text: str) -> list[dict]:
    """Parse exported session text: a JSON array or JSONL lines -> [entries].

    Non-JSON lines are skipped; non-dict entries are dropped. Session
    envelopes (hermes ``sessions export`` JSONL: one object per session with a
    ``messages`` list) are unwrapped into their messages. Never raises.
    """
    text = (text or "").strip()
    if not text:
        return []

    def _flatten(item, out):
        if (isinstance(item, dict) and not item.get("role")
                and isinstance(item.get("messages"), list)):
            for sub in item["messages"]:
                _flatten(sub, out)
        elif isinstance(item, dict):
            out.append(item)

    entries = []
    if text.startswith("["):
        try:
            data = json.loads(text)
        except ValueError:
            data = []
        for item in data:
            _flatten(item, entries)
        return entries
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        _flatten(item, entries)
    return entries


def parse_transcript_file(path: str) -> list[dict]:
    """Read a session transcript from a .jsonl / .json file."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse_transcript_text(f.read())


def _goal_line(transcript: list[dict]) -> str:
    """First user message (cleaned) — the session goal used for name/desc."""
    for entry in transcript:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role") or ""
        if role != "user":
            continue
        content = entry.get("content") or entry.get("text") or ""
        if not isinstance(content, str):
            content = str(content)
        content = re.sub(r"(?i)^\s*(please|hey|hi|hello)[\s,!:]*", "", content)
        content = re.sub(r"\s+", " ", content).strip()
        content = re.sub(r"^\[[^\]]*\]\s*", "", content)  # "[IMPORTANT: ...]" wrappers
        if content:
            return content[:200]
    return ""


# ------------------------------------------------------------------ tool calls
def _iter_tool_calls(transcript: list[dict]):
    """Yield (name, arguments) for every tool call in the transcript.

    Handles three shapes:
      * assistant entries with a ``tool_calls`` list
        — incl. the hermes export shape (``function: {name, arguments}`` with
        arguments as a JSON string, tool outcomes carrying ``tool_call_id``)
      * flattened standalone entries {role, name, content, is_error}
      * tool-role outcome entries, matched to their call by tool_call_id
        first, then by name, then positionally
    """
    calls = []          # (name, arguments, call_id)
    outcomes = []       # outcome entries
    for entry in transcript:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role") or ""
        if "tool_calls" in entry and isinstance(entry["tool_calls"], list):
            for tc in entry["tool_calls"]:
                if not isinstance(tc, dict):
                    continue
                fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
                name = (tc.get("name") or tc.get("tool")
                        or fn.get("name") or "tool")
                args = (tc.get("arguments") or tc.get("input")
                        or tc.get("inputs") or fn.get("arguments") or {})
                if isinstance(args, str):
                    try:
                        parsed = json.loads(args)
                    except ValueError:
                        parsed = None
                    args = parsed if isinstance(parsed, dict) else {"raw": args}
                if not isinstance(args, dict):
                    args = {"raw": str(args)}
                calls.append((name, args, tc.get("id") or tc.get("call_id")))
        elif role == "tool":
            outcomes.append(entry)
        elif entry.get("name") and role in ("assistant", ""):
            # flattened standalone call: it is its own outcome
            name = entry.get("name")
            args = {"content": (entry.get("content") or "")[:120]}
            calls.append((name, args, None))
            outcomes.append(entry)
    # pair each call with its outcome: tool_call_id, then name, then position
    used = set()
    paired = []
    for name, args, call_id in calls:
        outcome, idx = None, None
        if call_id:
            for i, o in enumerate(outcomes):
                if i in used:
                    continue
                if (o.get("tool_call_id") or o.get("call_id")) == call_id:
                    outcome, idx = o, i
                    break
        if outcome is None:
            for i, o in enumerate(outcomes):
                if i in used:
                    continue
                if (o.get("name") or o.get("tool_name") or o.get("tool")) == name:
                    outcome, idx = o, i
                    break
        if outcome is None:
            for i, o in enumerate(outcomes):
                if i in used:
                    continue
                outcome, idx = o, i
                break
        if idx is not None:
            used.add(idx)
        paired.append((name, args, outcome))
    return paired


def _is_failure(outcome: dict | None) -> bool:
    """Successful-outcome markers: explicit flags win, then JSON fields
    (exit_code/error/success), then content markers."""
    if outcome is None:
        return False
    if outcome.get("is_error") in (True, "true", "True", 1):
        return True
    if outcome.get("error") in (True, "true", "True", 1):
        return True
    if outcome.get("success") in (False, "false", "False", 0):
        return True
    content = outcome.get("content") or outcome.get("text") or ""
    if not isinstance(content, str):
        content = str(content)
    if content.lstrip().startswith(("{", "[")):
        try:
            parsed = json.loads(content)
        except ValueError:
            parsed = None
        if isinstance(parsed, dict):
            code = parsed.get("exit_code")
            if isinstance(code, int) and code != 0:
                return True
            err = parsed.get("error")
            if err not in (None, "", False, "null"):
                return True
            if parsed.get("success") is False:
                return True
    return bool(_FAIL_MARKERS.search(content))


def _call_summary(name: str, arguments: dict) -> str:
    """One-line inputs summary — prefers the exact command/path/url used."""
    if not isinstance(arguments, dict):
        arguments = {}
    for key in ("command", "cmd", "url", "path", "file_path", "pattern",
                "query", "package", "dir", "session_id", "prompt"):
        val = arguments.get(key)
        if isinstance(val, str) and val.strip():
            return " ".join(val.split())[:160]
    if arguments:
        return json.dumps(arguments, ensure_ascii=False)[:160]
    return name


# ------------------------------------------------------------------ drafting
def _procedure_steps(calls) -> list[str]:
    """Numbered procedure steps for the successful calls, in order.

    Repeated identical (tool, summary) calls are collapsed to one step —
    retries/reruns of the same command don't bloat the skill.
    """
    steps = []
    last = None
    for name, args, outcome in calls:
        if _is_failure(outcome):
            continue
        summary = _call_summary(name, args)
        if (name, summary) == last:
            continue
        last = (name, summary)
        steps.append(f"Run `{summary}` (via {name}).")
    return steps


def render_skill_md(name: str, description: str, steps: list[str],
                    success_calls: int, author: str | None = None,
                    version: str = DEFAULT_VERSION) -> str:
    """Assemble the complete SKILL.md (frontmatter + numbered procedure)."""
    title = " ".join(w.capitalize() for w in name.replace("-", " ").split())
    author = author or _author()
    lines = ["---",
             f"name: {name}",
             f"description: \"{description}\"",
             f"version: \"{version}\"",
             f"author: \"{author}\"",
             "tags: [drafted, auto-skill]",
             "---",
             "",
             f"# {title}",
             "",
             description,
             "",
             f"Auto-drafted from a successful session ({success_calls} "
             "successful tool calls).",
             "",
             "## Procedure",
             ""]
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. {step}")
    lines += ["",
              "## Verification",
              "",
              f"The originating session completed {success_calls} tool calls "
              f"successfully, ending with: {steps[-1] if steps else 'done'}.",
              ""]
    return "\n".join(lines)


def draft_skill_checked(transcript: list[dict],
                        min_success_calls: int = MIN_SUCCESS_CALLS,
                        author: str | None = None) -> dict:
    """Full-result draft: {ok, name, description, skill_md, steps,
    success_calls, tool_calls, reason?}. Never raises."""
    global _last_reason
    if not transcript:
        _last_reason = f"empty transcript (need >= {min_success_calls} successful tool calls)"
        return {"ok": False, "reason": _last_reason}
    calls = _iter_tool_calls(transcript)
    successes = [(n, a, o) for n, a, o in calls if not _is_failure(o)]
    if len(successes) < min_success_calls:
        _last_reason = (
            f"only {len(successes)} successful tool call(s) — "
            f"need >= {min_success_calls} (gate not met, nothing drafted)")
        return {"ok": False, "reason": _last_reason}
    goal = _goal_line(transcript)
    name = _slugify(goal or "auto-skill")
    description = goal or f"Procedure distilled from a {len(successes)}-step successful session."
    steps = _procedure_steps(calls)
    skill_md = render_skill_md(name, description, steps, len(successes),
                               author=author)
    _last_reason = ""
    return {"ok": True, "name": name, "description": description,
            "skill_md": skill_md, "steps": steps,
            "success_calls": len(successes),
            "tool_calls": len(calls)}


def draft_skill(transcript: list[dict],
                min_success_calls: int = MIN_SUCCESS_CALLS,
                author: str | None = None) -> dict | None:
    """Draft a skill from a session transcript — None + reason on rejection
    (fewer than ``min_success_calls`` successful tool calls)."""
    result = draft_skill_checked(transcript, min_success_calls, author)
    return result if result["ok"] else None


# ------------------------------------------------------------------ validation
def parse_frontmatter(text: str) -> dict:
    """Parse the YAML-subset frontmatter used by SKILL.md (never raises)."""
    m = FM_RE.search(text or "")
    if not m:
        return {}
    out = {}
    for raw in m.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        if not key:
            continue
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            out[key] = [x.strip().strip('"').strip("'")
                        for x in val[1:-1].split(",") if x.strip()]
        else:
            out[key] = val
    return out


def validate_draft(skill_md: str, expected_name: str | None = None) -> dict:
    """Validation gate before save: {ok, verdict, issues: [(where, reason)]}.

    REJECT — hard failures: no frontmatter, missing name, dangerous patterns.
    REVIEW — soft issues: missing description/version, < 3 procedure steps,
    name mismatch. Only PASS may be saved (fail-loud otherwise).
    """
    issues = []
    fm = parse_frontmatter(skill_md or "")
    if not fm:
        issues.append(("frontmatter", "no frontmatter"))
    else:
        if not fm.get("name"):
            issues.append(("name", "missing name in frontmatter"))
        elif expected_name and _slugify(fm["name"]) != _slugify(expected_name):
            issues.append(("name", f"frontmatter name {fm['name']!r} != requested {expected_name!r}"))
        if not fm.get("description"):
            issues.append(("description", "missing description in frontmatter"))
        if not fm.get("version"):
            issues.append(("version", "missing version in frontmatter"))
    for pat, reason in DANGEROUS_PATTERNS:
        if pat.search(skill_md or ""):
            issues.append(("body", reason))
    steps = re.findall(r"^\s*\d+\.\s+", (skill_md or ""), re.M)
    if len(steps) < 3:
        issues.append(("body", f"too few procedure steps ({len(steps)} < 3)"))
    hard = [i for i in issues if i[1] in ("no frontmatter",) or
            (i[0] == "name" and "missing" in i[1]) or
            (i[0] == "body" and i[1] in ("path escape", "destructive command", "obfuscated exec"))]
    if hard:
        return {"ok": False, "verdict": "REJECT", "issues": issues}
    if issues:
        return {"ok": False, "verdict": "REVIEW", "issues": issues}
    return {"ok": True, "verdict": "PASS", "issues": []}


# ------------------------------------------------------------------ save
def save_skill(name: str, skill_md: str, skills_root: str | None = None,
               category: str = DEFAULT_CATEGORY, flat: bool = False) -> dict:
    """Validate then write SKILL.md. Fail-loud.

    Defaults to skills/<category>/<name>/SKILL.md; with ``flat=True`` writes
    directly to skills/<name>/SKILL.md (host skills-dir layout, no category).
    Never writes on REJECT/REVIEW — returns {ok: False, reason} naming the
    issues. Returns {ok: True, dest, name, verdict} on PASS.
    """
    name = re.sub(r"[^a-z0-9._-]", "-", (name or "").lower()) or "auto-skill"
    check = validate_draft(skill_md, expected_name=name)
    if check["verdict"] != "PASS":
        detail = "; ".join(f"{w}: {r}" for w, r in check["issues"]) or "validation failed"
        return {"ok": False, "reason": f"{check['verdict']} — {detail}",
                "verdict": check["verdict"], "issues": check["issues"], "name": name}
    root = skills_root or DEFAULT_SKILLS_ROOT
    if flat:
        dest = os.path.join(root, name)
    else:
        dest = os.path.join(root,
                            re.sub(r"[^a-z0-9._-]", "-", (category or "").lower()) or DEFAULT_CATEGORY,
                            name)
    try:
        os.makedirs(dest, exist_ok=True)
        with open(os.path.join(dest, "SKILL.md"), "w", encoding="utf-8") as f:
            f.write(skill_md)
    except OSError as exc:
        return {"ok": False, "reason": f"write failed: {exc}",
                "verdict": check["verdict"], "name": name}
    return {"ok": True, "dest": dest, "name": name, "verdict": "PASS"}


# ------------------------------------------------------------------ host export
def export_session(session_id: str, runner=None, timeout: int = 60) -> dict:
    """Export a host session via `hermes sessions export --session-id <id>`.

    Uses the hermes CLI when available (subprocess). If hermes is missing,
    returns {ok: False, reason} naming the exact export command to run by
    hand — the plugin never hooks the host.
    """
    sid = (session_id or "").strip()
    command = f"hermes sessions export {sid}"
    exe = shutil.which("hermes")
    if not exe:
        return {"ok": False,
                "reason": (f"hermes CLI not found on PATH — export the session "
                           f"manually and draft from the file: {command} > "
                           f"{sid or 'session'}.jsonl, then /skill draft <file>"),
                "command": command}
    argv = [exe, "sessions", "export", "--session-id", sid,
            "--format", "jsonl", "-"]
    try:
        proc = (runner or subprocess.run)(argv, capture_output=True, text=True,
                                          timeout=timeout)
    except Exception as exc:
        return {"ok": False, "reason": f"hermes sessions export failed: {exc}",
                "command": command}
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()[:200]
        return {"ok": False,
                "reason": f"hermes sessions export exited {proc.returncode}: {err}",
                "command": command}
    transcript = parse_transcript_text(proc.stdout or "")
    if not transcript:
        return {"ok": False,
                "reason": f"hermes sessions export returned no transcript entries for {sid}",
                "command": command}
    return {"ok": True, "transcript": transcript, "command": command,
            "session_id": sid}


# ------------------------------------------------------------------ newest session
def list_session_ids(runner=None, limit: int = 20) -> list[str]:
    """Session ids from `hermes sessions list --limit N`, newest first.

    Parses the human table (the id is the last token of each row; rows that
    do not look like session ids — header, separator — are skipped). Returns
    [] when hermes is missing or the call fails.
    """
    exe = shutil.which("hermes")
    if not exe:
        return []
    argv = [exe, "sessions", "list", "--limit", str(limit)]
    try:
        proc = (runner or subprocess.run)(argv, capture_output=True, text=True,
                                          timeout=30)
    except Exception:
        return []
    if proc.returncode != 0:
        return []
    ids = []
    for line in proc.stdout.splitlines():
        tok = line.strip().split()[-1] if line.strip() else ""
        if (re.fullmatch(r"[A-Za-z0-9_]+", tok)
                and re.search(r"\d{8}_\d{6}", tok)):
            ids.append(tok)
    return list(dict.fromkeys(ids))


def draft_last_session(limit_messages: int = 200, runner=None,
                       timeout: int = 60) -> dict:
    """Draft a skill from the NEWEST host session — one-shot bridge.

    Finds session ids via ``hermes sessions list`` (newest first), exports
    each via ``hermes sessions export --session-id <id>`` (subprocess, never
    hooks the host), truncates to the last ``limit_messages`` entries (keeping
    the goal line), and drafts. In-flight/empty sessions (a cron still running
    exports zero messages) are skipped in favor of the next newest. Returns
    the draft result plus ``session_id``, or {ok: False, reason} — never
    raises.
    """
    ids = list_session_ids(runner=runner)
    if not ids:
        return {"ok": False,
                "reason": ("no host sessions found — `hermes sessions list` "
                           "returned no session ids (is hermes on PATH?)")}
    skipped, last_export_fail = [], None
    for sid in ids:
        exported = export_session(sid, runner=runner, timeout=timeout)
        if not exported["ok"]:
            if "no transcript entries" in exported["reason"]:
                skipped.append(sid)  # in-flight / empty — nothing to draft yet
                continue
            last_export_fail = exported["reason"]
            continue
        transcript = exported["transcript"]
        if not transcript:
            skipped.append(sid)
            continue
        if limit_messages and len(transcript) > limit_messages:
            tail = transcript[-limit_messages:]
            if not _goal_line(tail):  # keep the session goal if truncation dropped it
                for entry in transcript:
                    if isinstance(entry, dict) and entry.get("role") == "user":
                        tail.insert(0, entry)
                        break
            transcript = tail
        draft = draft_skill_checked(transcript)
        if not draft["ok"]:
            return {"ok": False, "reason": draft["reason"], "session_id": sid}
        draft["ok"] = True
        draft["session_id"] = sid
        if skipped:
            draft["skipped"] = skipped
        return draft
    if skipped:
        shown = ", ".join(skipped[:3]) + ("..." if len(skipped) > 3 else "")
        return {"ok": False,
                "reason": (f"no draftable host sessions — {len(skipped)} newest "
                           f"session(s) in-flight/empty: {shown}; try again in a "
                           f"moment or /skill draft-session <id>"),
                "session_id": ids[0]}
    return {"ok": False,
            "reason": last_export_fail or "host session export failed",
            "session_id": ids[0]}
