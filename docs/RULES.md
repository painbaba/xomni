# RULES.md — XOMNI Rules Catalog & AGENTS.md/Rules Feature

> Status: **concept + seed data (P0)** · Data: `data/rules/rules.json` · Scope: AGENTS.md / `.cursor/rules`-style glob-scoped rules

## 1. What this is

The **Rules Catalog** (`data/rules/rules.json`) is a curated seed set of reusable, agent-facing
coding rules — the "don'ts and dos" that keep AI coding agents on rails. Each entry points at a
ready-to-use rule file (`.mdc` / markdown) maintained in the upstream
[`PatrickJS/awesome-cursorrules`](https://github.com/PatrickJS/awesome-cursorrules) repo (Apache-2.0,
~40.5k stars).

Rules are distinct from **skills** (see `data/curated-skills.json`): skills teach *how* to do
something; rules constrain *how* code is produced — style, architecture, testing discipline,
security guardrails, documentation expectations.

## 2. The feature concept: glob-scoped rules files

The end-state feature is a **rules system layered on the agent runtime's native conventions**:

- **`.cursor/rules/*.mdc`** — Cursor's native rule files, each with YAML frontmatter:
  ```yaml
  ---
  description: One-line summary of what this rule helps the agent do
  globs: **/*.ts, **/*.tsx
  alwaysApply: false
  ---
  ```
  `globs` scopes a rule to matching files; `alwaysApply: true` makes it universal guidance.
- **`AGENTS.md` / `CLAUDE.md`** — the cross-runtime entry point. A generated `AGENTS.md` can
  `@import` or reference the active ruleset so Claude Code, Codex, Gemini CLI, and Cursor all
  load the same constraints.

**XOMNI pipeline** (proposed): user picks rules from the catalog → XOMNI copies/adapts the rule
files into the project's `.cursor/rules/` (or bundles them into `AGENTS.md`) → the agent
runtime auto-attaches them via globs.

## 3. Catalog schema

`data/rules/rules.json` is a single object:

| Field | Type | Meaning |
|---|---|---|
| `catalog` | string | Schema id: `xomni/rules-catalog/v1` |
| `title` / `description` | string | Human summary |
| `source` / `source_url` | string | Upstream repo (PatrickJS/awesome-cursorrules) |
| `source_license` | string | `Apache-2.0` |
| `source_stars` | int | Upstream repo stars (per-rule star counts unavailable) |
| `fetched_at` | string | ISO date the seed was built |
| `count` | int | Number of entries |
| `rules[]` | array | The curated entries |

Each entry in `rules[]`:

| Field | Type | Meaning |
|---|---|---|
| `name` | string | Rule name as listed upstream |
| `description` | string | What the rule constrains |
| `category` | string | Normalized category slug (12 categories) |
| `source_url` | string | Link to the canonical rule file upstream |
| `stars` | int\|null | Per-rule stars (null — not tracked upstream) |

Categories: `frontend`, `backend`, `build-tools`, `css-styling`, `database-api`,
`documentation`, `hosting-deployments`, `language-specific`, `mobile`, `security`,
`state-management`, `testing`.

## 4. Curating & extending

Seed = 99 of 217 upstream rules, selected for general-purpose value:

- **Included:** coding standards & style (Code Guidelines, Code Style Consistency, TypeScript
  Code Convention, Python Best Practices), testing discipline (Jest/Vitest/Playwright/Cypress,
  PR Review, QA Bug Report), documentation (README, How-To, Gherkin), security
  (DevSecOps/SSDLC), language-specific guides (Rust, Go, C++, R, PySpark…), and major framework
  stacks (Next.js, React, Vue, Svelte, FastAPI, Django, Rails, Laravel, NestJS, Spring).
- **Excluded:** hyper-niche/app-specific rules (e.g. EEG processing, Z80 cellular automata,
  per-app SaaS stacks), and duplicate near-variants (only representative Next.js/TypeScript
  combos kept).

Refresh procedure: re-fetch the upstream README, re-run the curation filter (exact-name
allowlist in `.tmp/build_rules.py`), re-verify count ∈ [50, 100] and schema, then update
`fetched_at`.

## 5. Consuming the catalog

- **Programmatic:** load `data/rules/rules.json`, filter by `category`, take `source_url` +
  `name` + `description`. Example:
  ```python
  import json
  cat = json.load(open("data/rules/rules.json"))
  testing = [r for r in cat["rules"] if r["category"] == "testing"]
  ```
- **Install a rule:** fetch the `.mdc` from `source_url`, drop it into `.cursor/rules/`,
  adjust `globs`/`alwaysApply` frontmatter for the project.
- **Bundle into AGENTS.md:** concat selected rule bodies (stripped of frontmatter) under a
  "## Rules" section so every runtime honors them.

## 6. License & attribution

Content is derived from [PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules)
(Apache-2.0). Rule files are community-contributed; individual files may carry their own terms.
See `LICENSE-ATTRIBUTION.md` for XOMNI's global attribution policy.
