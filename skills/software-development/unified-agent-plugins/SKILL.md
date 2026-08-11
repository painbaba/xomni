---
name: unified-agent-plugins
description: "Use when extending the unified-agent/plugins collection."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [unified-agent, plugins, repomap, symbol-extraction, testing]
---

# Unified-Agent Plugins (in-place development)

The user keeps a project-local plugin collection at `C:\Users\HP\unified-agent\plugins\` — NOT `$HERMES_HOME/plugins` (see bundled `hermes-plugin-development` for the ctx API / hook side). Current members: `perkline`, `repomap`, `waitperk`, `mcp-catalog` (Goose-P3a-style MCP catalog: `/mcp list|tools|add|status|validate` + `mcp_call` model tool; catalog store `~/.hermes-mcp/catalogs/`, env override `HERMES_MCP_CATALOG_DIR`), `context-loader` (aider-style context: `fetch_page` web tool + `describe_image` vision tool via the opencode Zen gateway, `/fetch` + `/describe` commands), `title-statusline` (hook/command-only plugin, NO model tool: `post_tool_call` hook + `/title status|on|off|now` push the waitperk/perkline sponsor line into the Windows-native terminal title bar; plugin-local `state.json`), `provider-pool` (free-model gateway: live health + per-agent config gen for all agents), `context-compact` (pre_llm_call compaction), `sandbox-gate` (pre_tool_call risk gate), `local-models` (local OpenAI-compatible servers: `/localmodels status|scan|config|add|remove` + `local_models` model tool; Ollama :11434/v1 + LM Studio :1234/v1 defaults, plugin-local `servers.json` for extras), `gh-ops` (gh/glab CLI wrapper: `/gh status|prs [repo]|issues [repo]|me` + `gh_ops(action, repo?)` model tool; strict header-table/TSV parsing — never trust raw CLI output; error classification for missing CLI / not-authenticated / network fail). Tasks arrive as "extend the X plugin…" with precise specs: implement in place, preserve backward compatibility, run all tests until green.

## Layout convention (follow it)
Each plugin directory:
- `core.py` — pure-stdlib engine, NO hermes imports: functions + module-level tables (`_SYMBOL_PATTERNS`, `SKIP_DIRS`, `DEFAULT_MAX_FILES`, …)
- `__init__.py` — wiring only: `register(ctx)`, `_<name>_tool(params)` model-tool handler, `_handle_<name>(raw)` slash-command handler
- `plugin.yaml` — manifest (name/version/description)
- `tests/` — namespace package, NO `__init__.py`; `test_core.py` (existing suite, never edit) + `test_extended.py` (new-feature tests)

## Running tests (from the plugin dir)
```bash
cd /c/Users/HP/unified-agent/plugins/repomap
python -m unittest tests.test_core tests.test_extended -v
```
Use `python` (3.11) — on this box `python3` is 3.13 with a pip→3.14 mismatch. Both modules in one invocation; the namespace-package test dir works fine.

**Silent "Ran 0 tests" trap**: plain `python -m unittest discover` from the plugin root finds NOTHING when `tests/` lacks `__init__.py` — discovery skips non-package dirs without warning. The module-name invocation above is immune. If you want plain `discover` (or `-s tests`) to work too, add an empty `tests/__init__.py` AND keep the sys.path preamble in each test file so `import core` still resolves from any start dir. Never ship "Ran 0 tests" as green — confirm a real `Ran N tests` count.

## PITFALL: `import <pkgname>` fails when cwd IS the package dir (hit twice)
`python -m unittest` puts cwd at `sys.path[0]`. If cwd is `plugins/repomap/`, `import repomap` looks for `repomap/` *inside* cwd → ModuleNotFoundError. Same for `python -c` smoke scripts run from the plugin dir. Fix in the test-module header (and smoke scripts):

```python
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(_HERE)))  # plugins/   -> import repomap
sys.path.insert(0, os.path.dirname(_HERE))                   # repomap/   -> import core
import core
import repomap
```
Inserting the plugin dir too makes `import core` work when launched from anywhere, not just cwd.

**Hyphenated plugin dirs (`mcp-catalog`, `title-statusline`) can't be imported by module name** — `import mcp_catalog` fails even with the dir on sys.path. For standalone smoke tests of `__init__.py`, load by file with an importlib harness (register in `sys.modules` + set `__path__` so `from . import core` resolves); the canonical loader is in `hermes-plugin-development` (see its `references/mcp-catalog-plugin.md` for the worked recipe). A self-contained, copy-paste `_load_plugin()` harness is in `references/title-statusline-build.md`. Unit tests of `core.py` are unaffected — `import core` works from the plugin dir. **Trap (hit in context-loader): the harness's `from . import core` re-executes core.py as a SECOND module instance under the package name (`<pkgname>.core`), so `mock.patch.object(core, ...)` in tests silently patches the wrong object. Pre-seed `sys.modules['<pkgname>.core'] = core` BEFORE `exec_module` so `mod.core is core` and patches land.**

## Extending a tool with backward compatibility (mandatory pattern)
Specs for these tasks always demand "existing calls behave EXACTLY as before". Pattern that satisfies it:
- Add optional schema params only: `"query": {"type": "string", "description": …}` — never require them.
- Route in the handler: `query = (params.get("query") or "").strip(); if query: return core.rank_files(root, query); return core.build_map(root)` — absent/blank param → old path byte-identical. Also keep the `root` alias (`path` or `root` or cwd) and the not-a-directory guard.
- Command arg parsing: `raw.split(None, 1)` → first token = dir, remainder = query; preserve the old empty-raw fallback (→ cwd) and the old header line verbatim when no query. Bump `args_hint` (`"<directory> [query words...]"`).
- Share a walk helper (`_walk_entries`) between the old map and the new ranked function so the old rendering path is untouched.

## Symbol-extraction engine style (repomap core.py)
One regex per extension in `_SYMBOL_PATTERNS` (re.M, `^`-anchored, optional modifier-list prefix). `_symbols_for(path, ext)` reads the file (errors="replace", size-capped), takes the FIRST non-empty group per match, dedupes preserving order, returns []. Full regex craft for the 8 added languages + the `rank_files` relevance-scoring design: `references/repomap-symbol-patterns.md`.

## Test-writing conventions (keep suites green fast)
- New feature tests in `tests/test_extended.py` with the sys.path preamble; leave `tests/test_core.py` untouched.
- Assert exact map lines (`"[Server, main, Handler, Registry, Wrapper, Factory]"`) — substrings alone miss extraction regressions.
- The extractor also captures enclosing constructs: the class holding a `companion object` is itself a symbol — expected symbol lists must include it.
- Ranked output lines are score-first (`"3  auth.py  [login]"`): `ln.split()[1]` = path, token 0 = score. Assert order + scores this way.
- Importing the plugin package from a test: `repomap._repomap_tool({...})` / `repomap._handle_repomap(raw)` directly, and a `FakeCtx` capturing `register_tool`/`register_command` kwargs to assert schema/args_hint.
- urllib request-build asserts: `Request` stores headers via `key.capitalize()` (`"User-Agent"` → `"User-agent"` internally), so assert `req.get_header("User-agent")` / `dict(req.header_items())["User-agent"]`; timeout lands in `urlopen.call_args[1]["timeout"]`; a mocked `urlopen` needs explicit `resp.status = 200` (auto-created MagicMock attributes fail `!= 200`) and `resp.headers = {}` to trigger the charset fallback.
- **Probing local OpenAI-compatible servers** (local-models core): GET `{base}/models` with a browser `User-Agent` (Cloudflare-style 1010 blocks), 3s default timeout. Parse ALL THREE payload shapes: `{"data":[{"id":...}]}` (OpenAI / Ollama / LM Studio), `{"models":[...]}` (legacy), and a bare `["id", ...]` list. Port constants to document: Ollama `http://127.0.0.1:11434/v1`, LM Studio `http://127.0.0.1:1234/v1`. Real HTTPError fixture for the HTTP-error test — no mock needed: `urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))`.
- **`side_effect` variant of the urlopen context-manager trap** (hit live): a `side_effect` function patching `urlopen` must RETURN a context-manager mock (`cm = mock.MagicMock(); cm.__enter__.return_value = fake`), never the bare fake — `with fake as resp:` yields `fake.__enter__()` (a fresh child mock), so `resp.status`/`resp.read()` are MagicMocks and the probe silently reports DOWN (test sees 0 up). The `m.return_value.__enter__.return_value = fake` form is only for patching WITHOUT side_effect.
- **Config-gen assertion shapes**: hermes block = YAML comment lines with `provider:` / `base_url:` / `key_env: local` (placeholder — local endpoints need no real key); opencode block = valid JSON — `json.loads` it and assert `parsed["provider"][id]["options"]["baseURL"]`; a dummy `apiKey` string (`"local"`) satisfies opencode's `@ai-sdk/openai-compatible` provider.
- **Standalone `__init__.py` load — plain-name variant**: when the plugin's `__init__.py` carries `try: from . import core / except ImportError: import core`, tests can load it with a NON-package `spec_from_file_location("some_name", init_path)` — the fallback resolves `core` to the already-imported top-level module, so `mock.patch.object(mod.core, ...)` patches land with NO `__path__`/sys.modules pre-seed. Simpler than the `hermes_plugins.<slug>` mirror; the double-core pre-seed trap only applies to package-name loads.

## Hook/command-only plugins & plugin-local state (title-statusline pattern)
Some collection plugins are wiring-only (no model tool): a `post_tool_call` hook that does cheap side work + a `/cmd status|on|off|now` toggle. Reusable conventions from `title-statusline`:
- Plugin-local toggle state: `DEFAULT_STATE = {"enabled": True}` — `deepcopy`'d on EVERY load (never share/mutate the module default), `_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")`, `_load_state()`/`_save_state()` swallow `OSError`/`JSONDecodeError` (state persistence must never break the agent).
- Every hook handler is `def _on_x(**kwargs) -> None` returning None, with the whole body in try/except — observers never alter agent behavior.
- `/title` handler contract: bare/`status` → status block; `on` → persist + refresh now; `off` → persist + restore neutral title (e.g. `core.NEUTRAL_TITLE`); `now` → force refresh regardless of state.
- Tests patch the module-level `_STATE_PATH` to a tmpdir path; round-trip asserts read the JSON file back and call `_load_state()` fresh (also asserts deepcopy independence: mutate one loaded dict, the next load is unaffected).

## Windows-native console title (ctypes + OSC fallback)
`core.set_title(title)` pattern: if `sys.platform == "win32"` → `ctypes.windll.kernel32.SetConsoleTitleW(title)` (Unicode-safe, works in cmd.exe AND Windows Terminal); any failure falls through to the OSC 0 escape `"\x1b]0;{title}\x07"` written to stdout (every modern terminal honors it, incl. Windows Terminal in VT mode). Always strip `\x1b \x07 \r \n` from the title first — sponsor-file content must never inject escape sequences. Mock recipes for tests: `mock.patch.object(sys, "platform", "win32")` + `mock.patch.dict(sys.modules, {"ctypes": fake})`; ctypes missing = `mock.patch.dict(sys.modules, {"ctypes": None})` (import raises ImportError → fallback path); stdout capture = `mock.patch.object(sys, "stdout", io.StringIO())`. Isolate sponsor files by patching module-level path constants (`mock.patch.object(core, "WAITPERK_LINE", tmp_path)`).
**Live Windows verification** (real, not mocked): read current title via `ctypes.windll.kernel32.GetConsoleTitleW(ctypes.create_unicode_buffer(512), 512)` → `set_title(...)` → read back → assert changed → restore the original title.

## gh/glab CLI wrapper plugins (gh-ops pattern)
CLI-wrapper plugins run `gh`/`glab` via subprocess, parse strictly, format. The non-obvious, live-verified lesson: **`gh pr list` / `gh issue list` change output SHAPE when piped** — `subprocess.run(capture_output=True)` never sees the pretty aligned table. Piped output is TAB-separated with NO header line, and the column ORDER differs from the TTY table:
- piped `gh pr list`    → `number \t title \t branch \t state \t createdAt`
- piped `gh issue list` → `number \t state \t title \t labels \t createdAt` (state BEFORE title!)
- TTY table (terminal only) → `NUMBER TITLE BRANCH STATE DRAFT` / `NUMBER TITLE LABELS STATE`

So parse BOTH shapes: (1) header-table → find the header line by token match, derive column start positions via `line.find(tok, pos)` in token order, slice rows by those positions — NEVER whitespace-split, titles contain spaces; (2) headerless TSV → split on tabs using a per-kind column map. Skip any row whose NUMBER cell isn't a digit (footer hints like `Use 'gh pr list --author @me' ...`). Empty-result wordings vary by gh version — match all of: "No pull requests found" / "There are no open issues in OWNER/REPO" / "No issues are currently open". Error surfaces must be classified, not dumped: missing CLI (FileNotFoundError), not-authenticated (stderr mentions "auth login"/"not logged in"), network ("no such host"/"connection refused"/"timed out"), else first stderr line. Full format tables, argv recipes, and subprocess encoding: `references/gh-cli-output-formats.md`.

## Ad-hoc verification script (when fresh evidence is demanded)
## Ad-hoc verification script (when fresh evidence is demanded)
When a session must prove changed behavior beyond the unit suite: write a focused script to the OS temp dir with a `hermes-verify-` filename prefix, run it, then DELETE it and confirm deletion. Shape: `sys.path.insert(0, PLUGIN_DIR)`; a `check(name, cond)` helper accumulating failures; `print("PASS  " / "FAIL  " + name)` per check; final `"{n} failure(s)"` or `"ALL CHECKS PASSED"`; `sys.exit(1 if failures else 0)`. Include one live round-trip check (real ctypes console title) when the change is Windows-native. Use `python` (3.11), never `python3`.

## Files
- `references/repomap-symbol-patterns.md` — validated regexes for kotlin/swift/dart/scala/lua/r/terraform/vue, the multi-group first-non-empty mechanic, vue `<script>` handling, and rank_files scoring tiers (+3/+2/+1).
- `references/title-statusline-build.md` — worked `_load_plugin()` importlib harness for hyphenated `__init__.py` tests, mock recipes, plugin-local state.json pattern, and the full `hermes-verify-` ad-hoc verification flow.
- `references/context-loader-plugin.md` — network-tool + vision-gateway plugin build: html_to_text pipeline order (incl. the `world ,` punctuation fix), urllib fetch_page patterns, the VERIFIED opencode Zen vision recipe (endpoint, model `minimax-m3`, browser UA mandatory — 403 error code 1010 without it, key from `~/AppData/Local/hermes/.env`), and the harness pre-seed trap.
- `references/gh-cli-output-formats.md` — live-verified `gh pr list` / `gh issue list` output shapes (TTY header table vs piped TSV, exact column orders), the strict header-position slicing algorithm, empty-result wordings, argv recipes, error classification, Windows subprocess encoding, and fixture alignment rules for parser tests.
- `references/local-models-plugin.md` — local OpenAI-compatible server probing: port constants, /models payload shapes, urlopen mock recipes (return_value AND side_effect context-manager traps), real HTTPError fixture, hermes/opencode config-gen shapes (`key_env: local` placeholder), plain-name `__init__.py` test-loading variant, live-scan DOWN shape.
