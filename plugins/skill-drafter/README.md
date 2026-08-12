# skill-drafter — auto-skill from successful sessions

Zero-hooks XOMNI plugin that turns successful sessions into skills. After any
session with **5+ successful tool calls**, it drafts a complete `SKILL.md`
(goal-derived name, description, `version: "1.0.0"`, author from
`XOMNI_USER` / `git config user.name` / `xomni`) whose body is the numbered
procedure with the **exact commands discovered** — the user just approves.

## Commands

| Command | What it does |
|---|---|
| `/skill draft <session-file.jsonl>` | Draft + print the SKILL.md, then `approve with: /skill save <name>`. Rejects (< 5 successful tool calls) with the reason, loud. |
| `/skill save <name> [--target=...] [--category=...]` | Validate the drafted skill (frontmatter, name match, no destructive patterns, >= 3 steps) and write `skills/<category>/<name>/SKILL.md`. **Fail-loud on REJECT — nothing is ever written without a PASS verdict.** Prints `saved: <name> -> <path>`. |
| `/skill draft-session <session-id>` | Export a host session via `hermes sessions export <id>` (subprocess) and draft from it. If hermes is missing: loud error naming the export command to run by hand. |

Aliases: `/skill-draft`, `/skill-save`. Zero hooks — no `register_hook` anywhere.

## Core API (`core.py`, pure stdlib)

- `draft_skill(transcript, min_success_calls=5) -> dict | None` — parses
  `[{role, content/tool_calls}]` entries (assistant `tool_calls`, flattened
  standalone calls, `role: tool` outcomes), extracts the successful tool-call
  sequence (explicit `is_error`/`error`/`success` flags, plus content markers
  like `Traceback` / `exit_code: N`), infers the name from the goal line, and
  returns `{name, skill_md, steps, success_calls, tool_calls}`. Returns
  **None** when the gate isn't met — reason via `draft_reason()` (or use
  `draft_skill_checked()` for the full `{ok, reason}` result).
- `save_skill(name, skill_md, skills_root, category="auto-drafted")` —
  validates then writes `skills_root/<category>/<name>/SKILL.md`. Verdicts:
  `PASS` (saved), `REVIEW`/`REJECT` (fail-loud `{ok: False, reason}` naming
  every issue; destructive/obfuscated patterns are hard REJECTs).
- `export_session(session_id, runner=None)` — `hermes sessions export <id>`
  subprocess (injectable `runner` for tests); loud error with the export
  command when hermes is off PATH.
- `parse_transcript_file(path)` / `parse_transcript_text(text)` — JSONL or
  JSON-array transcript readers (non-JSON lines skipped, never raises).

## Transcript format

JSONL with `user` / `assistant`(+`tool_calls`) / `tool`(outcome) entries —
see `examples/session-6calls.jsonl`. Hermes session exports (`hermes sessions
export <id>`) match this shape.

## Demo

```bash
cd plugins/skill-drafter
python -m unittest tests.test_core -q      # 14 tests
python examples/demo_draft.py              # draft + save demo -> examples/demo-SKILL.md
```

## Verification

- [ ] Suite green: `cd plugins/skill-drafter && python -m unittest tests.test_core -q`
- [ ] Demo drafted + saved to a temp skills dir (see `examples/demo-SKILL.md`)
- [ ] Zero hooks (no `register_hook` in `__init__.py`)
