---
name: hermes-plugin-development
description: "Use when building Hermes plugins: slash commands, hooks."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, plugins, extension, slash-commands, ctx-api]
---

# Hermes Plugin Development

Extend a Hermes install with custom in-session options WITHOUT editing core code: slash commands (`/name`), model-callable tools, and lifecycle hooks. This is the sanctioned path for "make a new option in Hermes" / "add a command that does X" requests. (The bundled `hermes-agent` skill covers usage/config; this skill covers authoring plugins.)

## When to use
- User asks for a new slash command / "new option" / custom feature inside Hermes
- A local-only tool or command that shouldn't live in core (`tools/`)
- Anything that needs the user's active model from plugin code (`ctx.llm`)

## Anatomy

A plugin is a directory under `$HERMES_HOME/plugins/<name>/` (on Windows: `C:\Users\<user>\AppData\Local\hermes\plugins\<name>\`):

```
plugins/prompt-enhancer/
├── plugin.yaml      # manifest: name, version, description
└── __init__.py      # register(ctx) — wires commands/tools/hooks
```

Minimal manifest:

```yaml
name: my-plugin
version: "1.0.0"
description: "What it does"
```

The entry point is `register(ctx)`; all wiring happens there via ctx.* calls.

## ctx API (the parts that matter)

| Call | Purpose |
|---|---|
| `ctx.register_command(name, handler, description, args_hint="")` | In-session slash command. Handler is `fn(raw_args: str) -> str | None`; the return value is printed to the user. Async handlers are supported (awaited, 30s timeout). `args_hint` (e.g. `"<raw prompt>"`) surfaces an arg field on gateway platforms (Discord). Names conflicting with built-ins are rejected. |
| `ctx.register_tool(name, toolset, schema, handler, check_fn=None, requires_env=None, is_async=False, description="", emoji="", override=False)` | Model-callable tool. `schema["description"]` is what the model sees (prefer defining text once in schema). **`toolset` is a free-form label** — `tools/registry.py register()` never validates it (MCP tools use dynamic `mcp-<server>` toolsets); any string works. Handler is `fn(args_dict) -> str` (async via `is_async`); exceptions are normalized by the registry. `override=True` replaces a built-in but needs `plugins.entries.<id>.allow_tool_override: true` unless the plugin is bundled. |
| `ctx.register_hook("post_tool_call", fn)` | Hook at lifecycle points. Full list in `hermes_cli/plugins.py` -> `VALID_HOOKS` (pre_llm_call, pre_api_request, transform_llm_output, on_session_start/end, subagent_start/stop, pre_verify, ...). Registering an UNKNOWN name logs a warning but the callback IS still stored (forward compatibility, `hermes_cli/plugins.py` ~1180) — a typo silently no-ops, so grep `VALID_HOOKS` first. **`pre_tool_call`** (fires for EVERY model tool with `tool_name` + `args` kwargs) has its own return contract: `{"action": "block", "message": "..."}` vetoes the call, `{"action": "approve", "message": "..."}` escalates to the human approval gate, anything else incl. `None` proceeds — see `references/pre-tool-call-hook-contract.md`. |
| `ctx.inject_message(content, role="user")` | Queue a message as the next user turn (agent idle -> pending_input; agent running -> interrupt). THE way a command feeds work back into the agent loop. Returns bool; not available in gateway mode. |
| `ctx.llm.complete(messages, temperature=, max_tokens=, purpose=)` | Host-owned completion on the USER'S ACTIVE model (no API key needed). OpenAI message shape (`[{"role":"system",...},{"role":"user",...}]`). Returns result object with `.text`, `.provider`, `.model`, `.usage`. Sync. |

**Trust gate**: `ctx.llm` provider/model/agent_id/profile OVERRIDES are default-deny unless `plugins.entries.<id>.llm.allow_*_override` is set in config. A plain call with no overrides uses the active model with zero config — the common case.

## Enablement — plugins are OPT-IN

A plugin directory alone does NOT load. It must appear in `plugins.enabled`:

```bash
hermes plugins enable <name>
```

- Takes effect on the NEXT session start — no hot reload; restart `hermes` (or tell the user the command is live from next launch).
- `--allow-tool-override` grants replacing built-in tools — only needed for privileged cases.
- Verify: `hermes plugins list`, or in Python `_ensure_plugins_discovered()._plugin_commands` shows registered command names.

## Handler pattern (module-global ctx)

The CLI dispatch calls the stored handler with no ctx argument, so stash ctx at register time:

```python
_CTX = None

def _handle(raw_args: str) -> str:
    if not raw_args.strip():            # always guard empty/help
        return HELP_TEXT
    try:
        enhanced = _enhance(_CTX, raw_args.strip())
    except Exception as exc:
        return f"\033[1;31m/name failed: {exc}\033[0m"   # ANSI red, don't crash
    _CTX.inject_message(enhanced, role="user")
    return "[enhanced prompt queued — the agent will now execute it]\n\n" + enhanced

def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command("name", handler=_handle, description="...", args_hint="<prompt>")
```

Catch exceptions and return an error string — a raised exception prints "Plugin command error" to the terminal instead of a useful message.

## Global auto mode — silent per-turn rewriting via `pre_llm_call`

The `pre_llm_call` hook is the sanctioned way to transparently upgrade EVERY user message before the agent's first model call of a turn (verified working pattern: prompt-enhancer plugin's `auto` mode). It fires once per turn in `agent/turn_context.py` (`build_turn_context`, ~line 1050) with kwargs: `session_id`, `task_id`, `turn_id`, `user_message`, `conversation_history`, `is_first_turn`, `model`, `platform`, `parent_session_id`, `sender_id`. Verified detail: `conversation_history=list(messages)` is a SHALLOW copy — the message dicts are shared with the agent's stored history and already include the current turn's user message. Never mutate those dicts; take a fresh `list(...)` snapshot only if you need it later (e.g. a `/cmd now` force). `session_id` enables per-session one-shot gating (see "Stateful plugins" below). Return `{"context": "..."}` (or a bare string) and it is appended into the CURRENT turn's user message as `api_content` — ephemeral, cache-safe (injected into the user message, never the system prompt), never persisted to the session DB. This is exactly "silent": the transcript stores the original, the model sees the enhanced.

```python
def _on_pre_llm_call(**kwargs):
    if not _auto_enabled():          # toggle from state file, not config.yaml
        return None
    raw = kwargs.get("user_message")
    if not isinstance(raw, str) or _should_skip(raw):
        return None                  # trivial msgs never cost an LLM call
    try:
        result = _CTX.llm.complete(
            messages=[{"role": "system", "content": AUTO_PROMPT},
                      {"role": "user", "content": raw}],
            temperature=0.3, max_tokens=1200, purpose="auto prompt enhancement",
        )
        enhanced = (result.text or "").strip()
        if not enhanced or enhanced == raw.strip():
            return None
        return {"context": "[auto-enhanced — follow the refined prompt below]\n\n" + enhanced}
    except Exception:
        return None                  # SILENT fallback: message passes through untouched

def register(ctx) -> None:
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
```

Critical details:
- **The enhancement's own `ctx.llm.complete` does NOT re-trigger the hook** — plugin LLM calls bypass the turn pipeline. No infinite loop.
- **Skip gate before the call**: empty, `<8 chars`, slash-prefixed, punctuation/emoji-only, and a small stopword set (ok/yes/thanks/done/continue...) return None without burning a completion. One-turn latency cost is the tradeoff: every non-trivial message adds one extra LLM call (~10-20s). Offer `/cmd auto off` as the escape hatch.
- **Toggle state in a `state.json` next to `__init__.py`** (read on every hook call, written by the `/cmd auto on|off` subcommand). Never hand-edit config.yaml; a plugin-local file survives restarts and can't corrupt Hermes config.
- **Auto-mode system prompt differs from manual**: must handle conversational follow-ups ("make it faster") using the provided history tail, never bloat short asks, preserve code/paths/commands verbatim. The hook's `conversation_history` kwarg gives you the recent tail for disambiguation — pass a trimmed slice into the enhancement call.
- Use `startswith("auto")` parsing in the SAME handler as the manual mode so `/cmd auto on` and `/cmd <raw>` coexist (`/cmd --show <raw>` for preview-only, `/cmd auto` to query state).

## Stateful plugins: pure core.py + plugin-local state.json

For plugins with toggles/thresholds/counters (auto on/off, cooldowns, last-fire timestamps), split the logic:

- `core.py` — pure stdlib ONLY (zero hermes imports), unit-testable with `python -m unittest tests.test_core -v`:
  - `DEFAULT_STATE` dict + a `State` class with `load(path)`/`save()`. **deepcopy the default per instance** — nested dicts shared across instances is the classic mutation-leak footgun (tests/sessions corrupt each other).
  - `load()` merges stored JSON over defaults and silently falls back on missing/corrupt files — a plugin must never break the agent loop over its own state.
  - Pure predicates (e.g. `should_compact(state, history_len, now)` with paused → enabled → threshold → cooldown ordering) so policy is unit-testable without a live agent. Coerce stored numerics defensively (try/except around `int(state.get("threshold", 40))`) — hand-edited state files arrive as strings.
- `__init__.py` — wiring only: read state on every hook call, write it back on state changes. State file = `Path(__file__).resolve().parent / "state.json"` (plugin-local, NEVER config.yaml).
- **Per-session one-shot gating**: to make a hook "fire at most once per session until reset", stamp `state["last_compact_session"] = session_id` (the hook kwarg) on fire, skip while it matches, and add a `/cmd reset` subcommand that clears it. Combined with a timestamp cooldown (`last_compact_ts`, default 60s) you get both time- and session-scoped discipline.
- **Skip gate**: reuse the prompt-enhancer trivial-message gate (empty / `<4` chars / slash-prefixed / punctuation-emoji-only / small stopword set) so short acknowledgements never trigger expensive work.
- **Deterministic fallback for LLM-dependent hooks**: wrap `ctx.llm.complete` in try/except; on failure fall back to a pure function (e.g. verbatim last-N tail + counts of omitted messages) so the hook ALWAYS returns something useful and never raises into the turn pipeline.

## Stateless plugins: one public function powers both command and tool

For a check/action plugin (run something on a directory, return a verdict), put the WHOLE behavior in one public function and make both surfaces one-line wrappers — the model tool and the `/cmd` output stay byte-identical and there is exactly one code path to test:

```python
def verify_project(dir: str) -> str:
    if not dir:
        dir = os.getcwd()
    if not os.path.isdir(dir):
        return f"verify_project: not a directory: {dir}"   # error LINE, never raise
    # ... run steps, append one verdict line per step + failing tails ...

def _verify_tool(params: dict) -> str:
    return verify_project((params or {}).get("dir") or "")

def _handle_verify(raw: str) -> str:
    return verify_project((raw or "").strip())
```

- Validate input up front and return an error string — a raising tool handler breaks the agent loop; a raising command handler prints "Plugin command error".
- Return a multi-line string the model can grep: header, one verdict line per step (`TEST PASS (exit 0)`), failing output tails, and a final `VERDICT: PASS|FAIL` line.
- Keep the heavy logic (discovery, subprocess, formatting) in pure `core.py`; `__init__.py` holds only the shared function + wrappers + `register(ctx)`. Worked example: `references/verify-runner-plugin.md` (test+lint automation).

## Loading & unit-testing a plugin package

Directory plugins load as `hermes_plugins.<slug>` where `slug = key.replace("/", "__").replace("-", "_")` (`hermes_cli/plugins.py::_load_directory_module`). The host creates the `hermes_plugins` namespace parent (`__path__=[]`) BEFORE exec'ing `__init__.py` — that is why `from . import core` works despite a hyphenated directory name.

To unit-test hook/command wiring (not just core), mirror the loader exactly:

```python
def _load_plugin_pkg(plugin_dir):
    spec = importlib.util.spec_from_file_location(
        "hermes_plugins.my_plugin", os.path.join(plugin_dir, "__init__.py"),
        submodule_search_locations=[plugin_dir])
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "hermes_plugins.my_plugin"
    mod.__path__ = [plugin_dir]
    sys.modules["hermes_plugins.my_plugin"] = mod
    spec.loader.exec_module(mod)   # 'from . import core' resolves via __path__
    return mod
```

- **Module-identity trap (verified in verify-runner's tests)**: without pre-seeding, `from . import core` inside the plugin loads a SECOND module instance under `<name>.core`, distinct from the test file's top-level `import core` — `mock.patch.object(core, "run_command")` then silently patches the WRONG instance and the handler keeps running real code. Fix, before `exec_module`:
  `sys.modules["hermes_plugins.my_plugin.core"] = core`  # reuse the already-imported module
- Skipping the namespace parent raises `ModuleNotFoundError: No module named 'hermes_plugins'` — create it first (`types.ModuleType` + `__path__=[]`) or name the test module without a dotted parent.
- **Register the module in `sys.modules` BEFORE `exec_module`**: `sys.modules["name"] = spec.loader.exec_module(mod) or mod` runs exec first and the relative `from . import core` fails with `ModuleNotFoundError: No module named '<name>'`. Order matters: `sys.modules[name] = mod` → then `spec.loader.exec_module(mod)`.
- **Host scanner flags literal dangerous command strings** (e.g. `dd of=/dev/sda`) written inside shell heredocs/one-liners — the host's own hardline blocklist rejects the terminal call with ITS block message before your code runs. When probing security/classifier plugins, build the dangerous strings programmatically (`"dd if=/dev/zero " + "of=/dev/sda" + " bs=1M"`) or keep them as string literals inside `.py` test files that only ever pass them to the classifier — never to a shell.
- Drive the hook with the EXACT host kwargs (full list in the section above) and a fake ctx: `FakeLlm.complete(**kwargs)` records calls (assert temperature/purpose) and returns `SimpleNamespace(text=...)`, or raises for the fallback path; patch the module's `STATE_FILE` to a per-test temp path in setUp; reset module-level globals (`_LAST_HISTORY` etc.) between tests.
- Test file at `tests/test_core.py`: `import core` resolves because the plugin dir is sys.path[0] under `python -m unittest tests.test_core -v`; also insert the plugin dir into sys.path defensively at the top so the file runs from a repo root too.

## Host integration from plugins — lazy + guarded imports

A plugin that touches host modules (`hermes_cli.*`, `tools.*`) must degrade
gracefully when the host is unavailable (standalone test runs, other hosts).
Pattern (verified in the mcp-catalog plugin): every host import is
function-local inside try/except, returning a clear message on failure:

```python
def _mcp_call_tool(params: dict) -> str:
    try:
        from tools.mcp_tool import mcp_prefixed_tool_name   # public name builder
        from tools.registry import registry
    except Exception as exc:
        return f"mcp_call: not wired — host MCP runtime unavailable ({exc}). ..."
    name = mcp_prefixed_tool_name(server, tool)
    if registry.get_entry(name) is None:      # public existence check
        return f"mcp_call: tool {name!r} is not registered. ..."
    result = registry.dispatch(name, args)    # PUBLIC invoke path
    return json.dumps(result) if not isinstance(result, str) else result
```

- Wire model tools to PUBLIC host APIs (`tools/registry.dispatch(name, args)`
  is the documented dispatch interface: `handler(args_dict) -> str`, async
  bridged, exceptions normalized) — never reach into underscore-private
  internals when a public path exists. Emit explicit "not wired" / "not
  registered" messages instead of raising into the agent loop.
- Host-dependent slash-command subcommands (`status` reading config.yaml)
  follow the same guarded-import shape; the pure core stays import-free so
  `tests/test_core.py` never needs the host.
- Read-only host reads (e.g. `hermes_cli.config.load_config` → `mcp_servers`)
  worked from the plugin dir under the hermes venv python; still guard them
  for gateway/other contexts.

## Verification workflow (do this before declaring done)

1. **Unit test the handler** with a fake ctx: `FakeLlm.complete` returns `SimpleNamespace(text=...)`; `FakeCtx` records `inject_message` calls. Assert show-only mode does NOT inject, default mode does, help/empty returns help.
2. **Test the real LLM path standalone**: `from agent.plugin_llm import PluginLlm; PluginLlm(plugin_id="<name>").complete(messages=[...])` works outside the CLI and prints provider/model/token usage — proves the model call end-to-end.
3. **Confirm discovery via `list_plugins()`** — the `_plugin_commands` attribute NO LONGER exists on the manager (AttributeError); use `d = _ensure_plugins_discovered()` then `for p in d.list_plugins(): ...`. Entries are DICTS with `name/source/enabled/commands/hooks/tools/error`; filter `p.get('source') == 'user'` and verify the counts MATCH what you registered (`enabled=True, error=None`). Do NOT test `if 'name' in p` on the dict — that checks dict KEYS, not values (silently matches nothing).
4. **Live end-to-end — prefer `hermes chat -q`**: one-shot mode runs the EXACT same agent loop, hooks, and message store as interactive (`hermes chat -q "raw prompt"`), and persists to state.db. This is the reliable way to prove a hook fired — no PTY fighting. For interactive-only verification (a real `/cmd` dispatch), spawn `hermes` via `terminal(pty=true, background=true)`, wait ~30s for MCP init + banner, submit `/name args` — but expect flaky input delivery (see pitfalls) and ALWAYS verify in state.db, never the PTY output.
5. **Verify hooks via `api_content`, not `content`**: for a `pre_llm_call` rewrite, the messages row stores BOTH — `content` is what the user typed, `api_content` is what the model actually received. If `api_content` contains your injected text while `content` stays clean, the silent rewrite worked:

```sql
-- sessions.id (NOT session_id); messages.timestamp (NOT ts)
SELECT substr(content,1,150), substr(api_content,1,700) FROM messages
WHERE session_id='<id>' AND role='user' ORDER BY timestamp ASC;
```

This is THE authoritative proof for silent-injection hooks (the enhanced prompt appears in api_content; the transcript stays clean).

## Pitfalls (all hit in real sessions)

- **MSYS path breakage**: setting `HERMES_HOME` to a git-bash path (`/c/Users/...`) makes standalone discovery miss user plugins entirely. Unset HERMES_HOME (real home auto-resolves) or pass a native `C:\...` path.
- **`process submit` sends `\n`, prompt_toolkit wants `\r`**: the typed text sits in the input buffer and the command never dispatches. Send data ending in `\r` (or `submit` twice / `write` with explicit `\r`). Even so, PTY input delivery is flaky — when it fights back, switch to `hermes chat -q` for the end-to-end proof instead of debugging the pty.
- **PTY capture lies**: rich/prompt_toolkit redraw in place with ANSI escapes; `process poll/log` shows garbage frames or looks frozen while the agent IS working (killing the PTY reveals the actual progress). Kill the PTY and read state.db — the session id is in the banner (`Session: YYYYMMDD_HHMMSS_xxxx`).
- **Killing test PTY processes on Windows**: `taskkill //F` breaks in git-bash (arg mangling) and `process kill` can hit access-denied. Write a tiny `.ps1` and run `powershell -ExecutionPolicy Bypass -File kill.ps1` with `Stop-Process -Id <pids> -Force` — inline `powershell -Command` mangles `$_` through MSYS, so use the file form. Check survivors with `Get-Process | Where-Object {$_.Path -like '*hermes-agent*'}`; leave PIDs that predate your test session alone (user's live gateway/sessions).
- **state.db is WAL-locked**: the sqlite3 CLI errors (`no such table` on WAL databases); use python3's sqlite3 module instead.
- **Docs site is incomplete**: `*.md` endpoints 404 and some pages are JS shells (empty curl). The installed source is the truth: `hermes_cli/plugins.py` (ctx API, discovery, trust gate, enablement), `agent/plugin_llm.py` (`complete()` signature), `cli.py` ~line 10350 (plugin command dispatch). Grep those.
- **register_command vs register_cli_command**: the former = in-session `/cmd` (CLI + gateway); the latter = `hermes <subcommand>` terminal command. In-session "new option" requests -> register_command.
- **Silent command-name conflicts**: a registered command that collides with a built-in (e.g. `/compact` exists in core) is dropped SILENTLY — no error at register time, the plugin just shows `commands=0` in discovery. Always compare discovery counts against what you registered; rename to a unique name (`/ctxcompact`). Pre-check a candidate name before committing to it: `from hermes_cli.commands import resolve_command; resolve_command('verify') is None` means `/verify` is free (verify-runner used this).
- **Mocking `urlopen` used as a context manager**: `with urlopen(...) as resp:` — a plain `Mock` raises "does not support the context manager protocol"; `MagicMock` accepts `with` but its `__enter__` returns a CHILD mock, so `resp.read()`/`resp.status` land on the wrong object and the path fails silently. Set `fake.__enter__.return_value = fake` explicitly.
- **`TimeoutExpired` has NO `.stdout` attribute** — partial output from a timed-out subprocess lives in `exc.output` and `exc.stderr` (bytes or str depending on `text=True`); read them via `getattr(exc, "output", None)`. Pass `text=True, encoding="utf-8", errors="replace"` to `subprocess.run` so non-UTF8 bytes can't blow up the capture. This is how a run-and-report plugin returns `timed_out=True` without ever hanging the agent (verify-runner's `run_command`, 180s default).
- **Shell-style command strings on Windows**: run them as `shlex.split(cmd)` + `shell=False` argv, never `shell=True` (cmd.exe quoting + injection). POSIX-mode `shlex.split` mangles UNQUOTED backslash paths (`src\app.py` → `srcapp.py`), so when a command embeds file paths wrap every one in `shlex.quote()` — quote and split both use POSIX rules, so backslash paths round-trip safely. Same trap with `side_effect`: a side_effect function must RETURN a context-manager mock (`cm = MagicMock(); cm.__enter__.return_value = fake`) — returning the fake itself makes `with fake as resp` yield a child mock and the probe silently reports down/zero-up in tests.
- **Don't add requirements when enhancing**: for a prompt-rewriter, preserve the user's intent 100% — no invented constraints, no dropped details.

## Files
- `templates/prompt-enhancer-plugin.py` — the complete, verified `/enhance` plugin (register_command + ctx.llm.complete + inject_message + `--show` mode + `/pe` alias). Copy, modify, ship.
- `references/auto-mode-pre-llm-call.md` — full verified implementation of the global auto mode: state-file toggle, skip gate, the `pre_llm_call` hook, the auto-mode system prompt, and the `api_content` verification SQL. Copy the parts you need.
- `references/pre-llm-call-hook-contract.md` — verified hook contract (exact kwargs, return handling + spill, register_hook semantics), plugin loading mechanics (`hermes_plugins.<slug>`), the importlib test harness, and the stateful core.py / session-once gating patterns, with the context-compact plugin as the worked example.
- `references/pre-tool-call-hook-contract.md` — verified `pre_tool_call` contract (exact kwargs, block/approve/no-op return table, first-valid-dict-wins, where defined), verdict→directive mapping, per-tool filtering, and the sandbox-gate worked example (risk classifier + allowlist + plugin-local state, fail-closed).
- `references/mcp-catalog-plugin.md` — Goose-P3a-style MCP catalog plugin, worked example of the testable pure-core anatomy (core.py validation/formatting/JSON-RPC builders + tests), the lazy host-import pattern, wiring a model tool to `registry.dispatch`, and the hyphenated-dir smoke-test loader.
- `references/verify-runner-plugin.md` — stateless test+lint verification plugin (`/verify [dir]` + `verify_project` tool): command AND tool delegating to one public function, subprocess capture with 3000-char tails + timeout handling, discovery fallbacks (pytest/unittest, ruff/py_compile-of-changed-files), the module-identity test harness, and host-truth checks (`resolve_command` pre-check + `PluginManager._load_plugin`).
