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
<id>`` when the hermes CLI is available; otherwise it returns a loud error
naming the exact export command to run by hand (the plugin never hooks the
host).
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

    Non-JSON lines are skipped; non-dict entries are dropped. Never raises.
    """
    text = (text or "").strip()
    if not text:
        return []
    entries = []
    if text.startswith("["):
        try:
            data = json.loads(text)
        except ValueError:
            data = []
        for item in data:
            if isinstance(item, dict):
                entries.append(item)
        return entries
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            entries.append(item)
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
        if content:
            return content[:200]
    return ""


# ------------------------------------------------------------------ tool calls
def _iter_tool_calls(transcript: list[dict]):
    """Yield (name, arguments) for every tool call in the transcript.

    Handles three shapes:
      * assistant entries with a ``tool_calls`` list
      * flattened standalone entries {role, name, content, is_error}
      * tool-role outcome entries are matched by name to their call
    """
    calls = []          # (name, arguments)
    outcomes = []       # outcome entries, matched positionally by name
    for entry in transcript:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role") or ""
        if "tool_calls" in entry and isinstance(entry["tool_calls"], list):
            for tc in entry["tool_calls"]:
                if not isinstance(tc, dict):
                    continue
                name = tc.get("name") or tc.get("tool") or "tool"
                args = tc.get("arguments") or tc.get("input") or tc.get("inputs") or {}
                if not isinstance(args, dict):
                    args = {"raw": str(args)}
                calls.append((name, args))
        elif role == "tool" and entry.get("name"):
            outcomes.append(entry)
        elif entry.get("name") and role in ("assistant", "tool", ""):
            # flattened standalone call: it is its own outcome
            name = entry.get("name")
            args = {"content": (entry.get("content") or "")[:120]}
            calls.append((name, args))
            outcomes.append(entry)
    # pair each call with the first unused outcome of the same tool name
    used = set()
    paired = []
    for name, args in calls:
        outcome = None
        for i, o in enumerate(outcomes):
            if i in used:
                continue
            if (o.get("name") or o.get("tool")) == name:
                outcome = o
                used.add(i)
                break
        paired.append((name, args, outcome))
    return paired


def _is_failure(outcome: dict | None) -> bool:
    """Successful-outcome markers: explicit flags win, else content markers."""
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
               category: str = DEFAULT_CATEGORY) -> dict:
    """Validate then write skills/<category>/<name>/SKILL.md. Fail-loud.

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
    dest = os.path.join(root, re.sub(r"[^a-z0-9._-]", "-", (category or "").lower()) or DEFAULT_CATEGORY,
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
    """Export a host session via `hermes sessions export <id>`.

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
    argv = [exe, "sessions", "export", sid]
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
