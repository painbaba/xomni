# Worker context boilerplate (proven twice, 2026-08-10)

Copy this into every leaf worker's `context` field, then append the
task-specific goal. It carries the whole contract so workers never need
mid-flight help.

```
REPO ROOT: C:\Users\HP\unified-agent\ (bash: /c/Users/HP/unified-agent/).
TEMPLATE TO COPY: C:\Users\HP\unified-agent\plugins\perkline\ (plugin.yaml +
__init__.py + core.py + tests/test_core.py) — read it first: core.py = pure
stdlib NO hermes imports (unit-testable), __init__.py = register(ctx) with
module-global _CTX, tests = stdlib unittest.
PLUGIN API: ctx.register_command(name, handler, description, args_hint) —
handler fn(raw_args: str) -> str; ctx.register_hook(name, fn) — hooks receive
**kwargs and return None unless a documented contract says otherwise
(pre_llm_call may return {"context": str} for current-turn api_content only);
ctx.register_tool(name, toolset, schema, handler).
Host source truth: C:\Users\HP\AppData\Local\hermes\hermes-agent\ (hermes_cli/
plugins.py for API; agent/shell_hooks.py for pre_tool_call contract; agent/
turn_context.py for pre_llm_call kwargs; plugin dirs use hyphens, loaded as
hermes_plugins.<slug>).
MSYS TRAPS: native python can't read /c/... paths — use C:/Users/... in
python/open; write files with write_file tool. python = 3.11.
TESTS: `python -m unittest tests.test_core -v` from plugin dir (stdlib
unittest only).
GOTCHA: copy.deepcopy for nested mutable defaults (shared-mutable-default
bug: dict(DEFAULT_STATE) is shallow — nested dicts/lists leak across
instances and tests).
QUALITY BAR: stdlib only, no pip installs, no hermes core edits, no
telemetry, hooks that don't act return None.
HOST HARDLINE: the shell guard BLOCKS terminal commands containing dangerous
literals (e.g. 'dd of=/dev/sda', 'rm -rf /') — in tests build dangerous
strings at runtime (join parts) and never put them in shell commands.
DELIVERABLE: full plugin dir with all tests green; report absolute paths +
final unittest output. Do not edit README/docs (orchestrator updates them).
```

## Per-task additions that pay off

- Point at the SPECIFIC host file to read for the contract the task depends on
  ("verify hook kwargs against agent/turn_context.py BEFORE coding").
- Give exact verified recipes when available (e.g. the vision path: POST
  https://opencode.ai/zen/go/v1/chat/completions, model minimax-m3, browser UA
  mandatory — 403 error 1010 without it; read keys from .env in python, never
  shell, never print).
- Warn about silent failure modes ("403 'error code: 1010' = missing UA",
  "empty assistant content = model returned nothing").
- Tell workers whether they may do ONE live probe (e.g. `gh --version`,
  localhost scan) and what to report — never tokens.

## Round-1 evidence (what the gate caught)

- 4 plugin suites + skill built by 5 workers; orchestrator re-ran everything:
  30 + 29 + 26 + 15 tests green, plus provider-pool 16 built by orchestrator.
- Catches: /compact built-in collision (commands=0, silent); skill frontmatter
  colon-in-plain-scalar; MagicMock __enter__; hardline-blocked test fixtures;
  config-write race when enabling plugins in parallel (run `hermes plugins
  enable` sequentially).
- E2E proof: hermes chat -q session → ~/.perkline/state.json renders grew,
  ~/.waitperk/state.json impressions grew; context-compact correctly silent
  below threshold (that IS the pass criterion).
