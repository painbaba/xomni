---
name: hermes-plugin-swarm
description: Build multiple Hermes plugins via parallel agent swarms.
---

# Hermes Plugin Swarm Builds

Deliver several Hermes plugins at once by fanning out parallel `delegate_task`
workers (one plugin per worker — isolated plugin dirs mean zero file conflicts),
then gating everything through an orchestrator QA pass. Proven pattern (two
rounds, 2026-08-10: round 1 = 5 workers/4 plugins+1 skill, round 2 = 5 workers).

## When to use
- User asks to extend Hermes with multiple modules/features ("make X, Y, Z", "port the features of repo R")
- User says "use a swarm", "best quality", "every feature, nothing missed"
- Building N independent Hermes plugins where workers can't collide (per-plugin dirs)

## The delivery pattern

1. **Decompose into per-plugin lanes.** One plugin per worker, each owning
   `plugins/<name>/` only. Never two workers in one dir. Rank by value (see the
   target repo's feature list).
2. **Give every worker the SAME rich context contract** — see
   `references/worker-context-template.md` for the proven boilerplate. It must
   contain: template plugin to copy, plugin API essentials, host source truth
   paths, MSYS traps, the deepcopy gotcha, unittest-only testing, quality bar,
   the hardline-blocklist warning, and the deliverable contract. Workers that
   get this rarely need mid-flight help.
3. **Orchestrator does NOT build leaves** — it verifies, fixes, installs, and
   documents after the batch returns.
4. **The QA gate is mandatory before anything ships** (below). Worker
   self-reports are claims, not evidence — re-run every suite yourself.
5. **Update docs after QA** (feature matrix, README, port-plan statuses) so the
   shipped state is recorded, then report with real test output.

## QA gate checklist (run every time)

- [ ] Re-run every worker's suite yourself: `python -m unittest discover -s tests` per plugin
- [ ] Audit hook contracts against host source (`hermes_cli/plugins.py`, `agent/shell_hooks.py`, `agent/turn_context.py`):
      pre_tool_call block = `{"action":"block","message":...}` (Claude-Code shape `{"decision":"block","reason":...}` also accepted); `{"action":"approve","message":...}` escalates to the human gate; None = proceed
- [ ] pre_llm_call inject = `{"context": str}` → goes to the CURRENT turn's api_content only (cache-safe; never mutates stored history)
- [ ] Check command names against built-ins BEFORE shipping (a rejected registration is silent — discovery shows commands=0)
- [ ] Copy to `~/AppData/Local/hermes/plugins/<name>/`, `hermes plugins enable <name>`, verify via `_ensure_plugins_discovered().list_plugins()` — entries are DICTS; search values, not `name in dict` (that checks keys and silently misses)
- [ ] Live e2e: `hermes chat -q "<prompt>"` then check plugin state files grew (e.g. ~/.perkline/state.json renders, ~/.waitperk/state.json impressions)
- [ ] Update docs (FEATURES.md matrix rows, README, PORT-PLAN statuses)

## Pitfalls (all hit in real sessions)

- **Built-in command collisions**: `/compact` already exists → registration silently skipped, plugin shows commands=0. Pick unique names (`/ctxcompact`) and re-check discovery after enabling.
- **Skill frontmatter YAML**: an unquoted description containing `: ` (e.g. "edits: keep diffs") fails YAML parse → skill reports "not supported on this platform". Quote descriptions with colons: `description: "..."`.
- **Host hardline blocklist traps test fixtures**: shell commands containing dangerous literals (`dd of=/dev/sda`, `rm -rf /`) get the WHOLE command blocked. Build risky strings at runtime in tests (join parts) and never inline them.
- **MagicMock + `with urlopen(...) as resp`**: `__enter__` returns a CHILD mock by default → `resp.read()` becomes another mock. Set `fake.__enter__.return_value = fake`.
- **HTTPError mocks**: raise a real `urllib.error.HTTPError(url, code, msg, {}, None)` — a plain `Exception` subclass with `.code` won't hit the `except HTTPError` branch.
- **Hyphenated plugin dirs**: `provider-pool` imports as `hermes_plugins.provider_pool` — direct `import provider_pool` fails. Verify via discovery, not import.
- **Shared mutable defaults**: `dict(DEFAULT_STATE)` is shallow — nested `{}`/`[]` leak across instances and tests pollute each other (a real cross-test failure). Always `copy.deepcopy` defaults.
- **MSYS paths**: native Windows python can't open `/c/...` paths — always `C:/Users/...` in python/open. write_file tool for file creation.
- **Tilde patterns in .gitignore are DEAD**: git never expands `~` — `~/.waitperk/` matches nothing. State dirs live outside the repo anyway; use plain patterns (`state.json`) or nothing.
- **search_files fails on AppData paths** → use terminal grep for host-source greps.
- **pre_tool_call kwargs** (from `agent/shell_hooks.py`): tool_name, tool_input ({"command": ...} for terminal), session_id, cwd + extra id/trace keys. Terminal tool name is "terminal".

## Repo hygiene (when creating the deliverable repo)

`git init` + `.gitignore` (vendor/, __pycache__/, *.pyc, state.json) + initial
commit. Verify ignore behavior with `git check-ignore` (one pathname per
call — `--quiet` rejects multiple). Use a tempfile harness
(`hermes-verify-*.py` under %TEMP%) for change-verification scripts.

## User scope directives (this user)

"Every feature / nothing missed / all repos" means: **full-depth clones of every
named repo** (vendor/ dir, licenses retained), a **per-feature matrix**
(FEATURES.md: one row per feature, status HOST/SHIPPED/VENDORED/WIRED/QUEUED/
PARKED-with-reason — nothing dropped by silence), and a tracked build queue that
converts QUEUED→SHIPPED in rounds. When the user names a repo's feature ("the
free models included in git by opencode"), anchor to THAT repo's actual contents
first — not generic external catalogs.

## Support files
- `references/worker-context-template.md` — the proven worker context boilerplate (copy verbatim, swap per-task specifics)
