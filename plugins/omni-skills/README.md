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
| cmd | `/skills publish <dir> [--author=NAME] [--repo=<target-repo-dir>] [--to=github\|clawhub] [--dry-run]` | credit-stamp then delegate publish to the host CLI |
| tool | `skills_import(dir, target, dry_run)` | model-facing import |

## Publishing (host-first — the plugin is the credit layer)

`/skills publish` is **one** publish path: validate → credit-stamp → **delegate
to the host**. The plugin never runs a second, parallel publish — it stamps
CREDIT into `SKILL.md` (author/source/published_at/origin, **idempotent** —
never double-stamps, never rewrites `published_at`) and hands the stamped
skill dir to the host CLI, which owns the actual registry push:

```
/skills publish skills/<category>/<name> --to=github
```

Flow:

1. **Stamp** — validate (fail-closed; REJECT refused) + stamp CREDIT.
2. **Delegate** — if `hermes skills publish` is available (PATH check + a
   smoke `--help` call), run:
   `hermes skills publish --to <target> <skill_dir>` (`--to` ∈ github|clawhub,
   default github). The plugin prints the exact delegated command, the host
   output, and a receipt.
3. **Fallback** — only when the host CLI is missing: copy into a repo's
   `skills/` tree (`core.publish_skill`, the skills.sh content model), with a
   loud NOTE that host publish is preferred. Push steps + skills.sh
   submission note are printed.
4. **Index** — once published, https://skills.sh indexes the repo; anyone
   installs via `npx skills add <owner/repo>` or `/skills-marketplace <git-url>`.

`--dry-run` stamps the skill and prints the exact delegated command **without
publishing** — safe to preview. `--repo=<target-repo-dir>` is used by the
fallback copy path only. The host CLI's `--repo` flag (a GitHub repo slug) is
a separate, host-side option.

### Captured host help (`hermes skills publish --help`, 2026-08-12)

```
usage: hermes skills publish [-h] [--to {github,clawhub}] [--repo REPO]
                             skill_path

positional arguments:
  skill_path            Path to skill directory

options:
  -h, --help            show this help message and exit
  --to {github,clawhub}
                        Target registry
  --repo REPO           Target GitHub repo (e.g. openai/skills)
```

Python API: `publish_via_host(skill_dir, target="github", repo=None, author=None,
published_at=None, env=None, git_config=None, runner=None, dry_run=False,
fallback_repo=None)` — the single publish path (stamp → delegate → fallback).
`publish_skill` remains the repo-copy fallback; `build_publish_command` /
`host_publish_available` / `stamp_credit` are exposed for tests and tooling.

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
