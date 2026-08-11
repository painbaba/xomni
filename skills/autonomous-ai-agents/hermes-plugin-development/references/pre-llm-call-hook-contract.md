# pre_llm_call hook contract + plugin loading (verified against host source)

All line numbers from the hermes-agent checkout used during the context-compact
session (Aug 2026). Re-verify with grep if the source drifted.

## Hook invocation — agent/turn_context.py (`build_turn_context`, ~line 1050)

```python
_invoke_hook("pre_llm_call",
    session_id=agent.session_id,
    task_id=effective_task_id,
    turn_id=turn_id,
    user_message=original_user_message,
    conversation_history=list(messages),   # SHALLOW copy!
    is_first_turn=(not bool(conversation_history)),
    model=agent.model,
    platform=..., parent_session_id=..., sender_id=...)
```

- `conversation_history` is `list(messages)` — the dicts are the SAME objects as
  the agent's stored history, and the list already includes the current turn's
  user message. Never mutate those dicts; the hook must be read-only.
- Return handling (turn_context.py ~1080): a dict with a truthy `"context"` key,
  or a non-empty string, is collected; everything else is skipped. Multiple
  plugin results are joined with `"\n\n"`. Oversized output is spilled to disk
  via `tools.hook_output_spill` (codex PR #21069 port).
- Injection target (turn_context.py `compose_user_api_content`): appended to the
  CURRENT turn's user message as `api_content` ONLY — system prompt untouched
  (prompt-cache invariant), stored `content` stays clean, never persisted as
  history. Multimodal (list) content can't take the sidecar (returns None).
- The hook runs once per turn, BEFORE the loop's first API call. The whole hook
  block is wrapped in try/except — a raising callback is logged, never fatal.
- `ctx.llm.complete(...)` calls from inside the hook do NOT re-trigger the hook
  (plugin LLM calls bypass the turn pipeline) — no infinite loop.

## register_hook semantics — hermes_cli/plugins.py (~1177)

- Unknown hook names: `logger.warning` but the callback IS still stored
  ("so forward-compatible plugins don't break"). A typo therefore silently
  no-ops — grep `VALID_HOOKS` (~line 144) before registering.
- `register_command(name, handler, description="", args_hint="")`: handler is
  `fn(raw_args: str) -> str | None` (async allowed). `name` is lowercased,
  stripped, `/`-stripped, spaces→hyphens. Conflicts with built-in commands are
  rejected with a warning.
- `ctx.llm.complete(messages, *, provider, model, temperature, max_tokens,
  timeout, agent_id, profile, purpose)` → result with `.text/.provider/.model/
  .usage`; provider/model overrides are default-deny unless
  `plugins.entries.<id>.llm.allow_*_override` is set. Plain call = active model.

## Plugin loading — hermes_cli/plugins.py::_load_directory_module (~1851)

- Module name: `hermes_plugins.<slug>` where `slug = (key or name).replace("/",
  "__").replace("-", "_")` — hyphenated dirs import fine.
- The `hermes_plugins` namespace parent is created first:
  `types.ModuleType("hermes_plugins")` with `__path__=[]`, inserted into
  sys.modules. Then `spec_from_file_location(module_name, __init__.py,
  submodule_search_locations=[plugin_dir])`, `module.__package__ = module_name`,
  `module.__path__ = [plugin_dir]`, `sys.modules[module_name] = module`,
  `exec_module(module)`. Relative `from . import core` resolves via `__path__`.

## Unit-test harness that mirrors the loader

- Load the package exactly as above (with the namespace parent present), then:
  - patch `pkg.STATE_FILE` to a temp path in setUp (module reads the global at
    call time, so `mock.patch.object(pkg, "STATE_FILE", path)` works),
  - reset module-level mutable globals (`_LAST_HISTORY`-style) in setUp,
  - `pkg._CTX = fake` where `fake.llm.complete(**kw)` records calls and returns
    `SimpleNamespace(text=...)` or raises to exercise the fallback path,
  - call `pkg._on_pre_llm_call(**kwargs)` with the exact host kwargs above.
- Assert: payload shape `{"context": str}` startswith the marker;
  temperature/purpose of the recorded llm call; no-op returns None and makes
  zero llm calls; history dicts deep-equal before/after (never-mutate check).

## Worked example: context-compact plugin (unified-agent/plugins/context-compact/)

Stateful pre_llm_call plugin; the pattern to copy:

- `core.py` (pure stdlib): `DEFAULT_STATE` deepcopy'd per `State(path)` instance;
  `should_compact(state, history_len, now)` = paused → auto → threshold (>= 40)
  → cooldown (`now - last_compact_ts >= 60`); `mark_compacted` stamps ts +
  session marker + counter; `split_history(history, tail_n)`; `render_tail`
  (role/content flatten, never mutates); `format_summary(old_count, tail,
  summary_text)` — real summary text or deterministic "N older messages
  omitted + verbatim tail" fallback, always prefixed `[compacted history]`.
- `__init__.py`: skip gate (trivial msgs never trigger), LLM summary via
  `ctx.llm.complete(temperature=0.2, max_tokens=700, purpose="context
  compaction")`, fallback on any exception; fire at most once per session via
  `last_compact_session` until `/compact reset`; `/compact now` runs the
  summarization immediately and stores `pending_force` in state.json for the
  next hook turn to inject (the only cache-safe injection channel available to
  a command — plugin commands don't pass through pre_llm_call themselves).
- Tests: 30 cases green with `python -m unittest tests.test_core -v`
  (fires above threshold / no-op below / cooldown blocks / paused blocks /
  payload shape / fallback formatting / state round-trip / session-once).

## Windows quirk seen in-session

`patch` tool once failed with `Failed to read file: C:\Users\HP\...` (backslash
path) and succeeded when retried with forward slashes — on this host, pass
forward-slash paths to patch/write_file.
