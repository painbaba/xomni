# omni-skills — SKILL.md Interop (XOMNI)

Import, security-validate, and install SKILL.md skills — the cross-vendor agent-skill
format (agentskills.io) — from any directory or marketplace repo into the Hermes
skills surface. Grounded in the P0 roadmap from `docs/COMPETITIVE.md`.

## What it does

- **`/skills-scan <dir>`** — inventory every skill dir under `<dir>` (SKILL.md present),
  parse the YAML-subset frontmatter (name/description/version/license/tags), list
  support files, and security-validate each one.
- **`/skills-install <dir> [--target=…] [--dry-run]`** — install a single skill dir
  **or** a whole marketplace root (every skill under it). Fail-closed: a skill with
  no frontmatter, path escapes, destructive commands, or obfuscated exec is REJECTED
  and never installed; borderline issues (<=2) downgrade to REVIEW and still install.
- **`/skills-marketplace <dir>`** — alias of install for marketplace roots.
- **Tool `skills_import(dir, target, dry_run)`** — same capabilities for the model.

## Why interop matters

Hermes skills are the richest in the space (170 shipped, 519-skill DB), but they live
in Hermes' own format. Claude's moat is content *standards*: SKILL.md + progressive
disclosure is now adopted by Cursor, Codex CLI, Gemini CLI, and OpenCode. This plugin
makes XOMNI a consumer AND producer of that standard — install `anthropics/skills`,
`wshobson/agents`, or any marketplace in one command; every installed skill goes
through the same fail-closed security posture as `data/build_db.py`.

## Speed posture

**Zero hooks** — nothing runs between turns. All work is inside the explicit
commands/tool. Per-turn cost: 0ms.

## Commands / tools

| Surface | Name | Purpose |
|---|---|---|
| cmd | `/skills-scan <dir>` | inventory + validate |
| cmd | `/skills-install <dir> [--target=…] [--dry-run]` | install skill/marketplace |
| cmd | `/skills-marketplace <dir>` | install marketplace alias |
| tool | `skills_import(dir, target, dry_run)` | model-facing import |

## Security model

`validate_skill()` is fail-closed: missing SKILL.md → REJECT; no frontmatter or
missing name/description → issue; support files scanned for `../` escapes,
destructive shell commands, and obfuscated exec patterns. 0 issues → PASS; 1–2 →
REVIEW (installs, flagged); 3+ → REJECT (never installs). `--dry-run` shows the full
plan with verdicts before anything is written.

## Test

```bash
cd plugins/omni-skills && python -m unittest tests.test_core -v
```

## Config

No config. Default target: `~/AppData/Local/hermes/skills` (override with
`--target=<root>` / the tool's `target` arg).
