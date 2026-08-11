# Goose-P3a-style catalog plugin (mcp-catalog) — verified build notes

Reference for the pattern: a pure-core plugin that manages MCP servers as agent
tools. Built 2026-08-10 at `C:\Users\HP\unified-agent\plugins\mcp-catalog\`
(26/26 unit tests green; end-to-end smoke-tested). Use this as the concrete
worked example for the "testable plugin anatomy" section of SKILL.md.

## File layout (what made it testable)

```
plugins/mcp-catalog/
├── plugin.yaml                # name, version, description only
├── core.py                    # PURE stdlib: no Hermes imports, no I/O side effects
├── __init__.py                # register(ctx): thin wiring + lazy host imports
├── mcp_catalog.example.json   # 2 sample servers (filesystem: npx @modelcontextprotocol/server-filesystem; fetch: uvx mcp-server-fetch)
└── tests/
    └── test_core.py           # `import core` — NOT `from .. import core`
```

- Tests import `core` directly; run from the plugin dir:
  `python -m unittest tests.test_core -v`. `tests/` needs NO `__init__.py`
  (namespace package suffices on py3.11+). This mirrors the sibling plugins
  (perkline, repomap) in `unified-agent/plugins/`.
- Pure core pays off: parse/validate (`parse_catalog`, `validate_catalog` —
  errors as a collected list vs raise-first), formatting
  (`list_tools_text`, `list_catalog_text`, `format_tool_list`), JSON-RPC
  message builders (`initialize_message`, `list_tools_message`,
  `call_tool_message`, `initialized_notification`, `rpc_envelope` — stdio is
  newline-delimited JSON), and state round-trip (`save/load_catalog_file`,
  `round_trip`). "checkable" PATH validation = `shutil.which(command)` behind
  a `check_path: bool = True` param so tests/other machines can disable it.

## register(ctx) wiring used

```python
def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command("mcp", handler=_handle_mcp,
        description="MCP catalog: ...",
        args_hint="[list|tools [server]|add <path>|status|validate <path>]")
    ctx.register_tool(
        "mcp_call", toolset="mcp",
        schema={... "required": ["server", "tool"]},
        handler=_mcp_call_tool, description="Invoke a tool on a registered MCP server",
        emoji="🔌")
```

- `toolset` is a FREE-FORM label — `registry.register()` never validates it
  against a fixed set (MCP tools themselves use dynamic `mcp-<server>`
  toolsets). "mcp" worked fine.
- Slash-command handler: `fn(raw_args: str) -> str`, subcommand dispatch via
  `parts = (raw or "").strip().split(None, 1)`.

## Host-integration pattern (lazy + guarded) — key design

A plugin that touches host modules must degrade to pure-catalog behavior when
the host is absent. Every host import is function-local inside try/except:

```python
def _host_config_servers() -> dict:
    try:
        from hermes_cli.config import load_config
        ... # read-only: config.yaml mcp_servers
    except Exception:
        return {}

def _mcp_call_tool(params: dict) -> str:
    try:
        from tools.mcp_tool import mcp_prefixed_tool_name
        from tools.registry import registry
    except Exception as exc:
        return f"mcp_call: not wired — host MCP runtime unavailable ({exc}). ..."
    name = mcp_prefixed_tool_name(server, tool)   # public name builder
    if registry.get_entry(name) is None:          # public existence check
        return f"mcp_call: tool {name!r} is not registered. ..."
    result = registry.dispatch(name, args)        # PUBLIC invoke path
    return json.dumps(result) if not isinstance(result, str) else result
```

Wire a plugin model tool to a PUBLIC host API with explicit "not
wired"/"not registered" messages — never reach into underscore-private
internals when a public path exists. `tools/registry.dispatch(name, args)` is
the documented dispatch interface (`handler(args_dict) -> str`, async
bridged, exceptions normalized to `{"error": ...}`).

## Verification recipe used

1. `python -m unittest tests.test_core -v` from the plugin dir → green.
2. Standalone smoke test of `__init__.py` — hyphenated dir names
   (`mcp-catalog`) can't be `import`-ed, so load by file:
   ```python
   import importlib.util, sys, os
   spec = importlib.util.spec_from_file_location("plug", "__init__.py")
   mod = importlib.util.module_from_spec(spec)
   mod.__path__ = [os.getcwd()]          # REQUIRED for `from . import core`
   sys.modules["plug"] = mod             # REQUIRED for relative imports
   spec.loader.exec_module(mod)
   ```
3. Fake-ctx registration check (record register_command/register_tool calls).
4. `HERMES_MCP_CATALOG_DIR=$(mktemp -d)/cats` env override → exercise
   add/list/status/validate against a throwaway catalog dir (never the real
   `~/.hermes-mcp/`).
5. Live host read: `/mcp status` showed real `mcp_servers` (ffmpeg,
   youtube-transcript) from config.yaml — host imports worked from the
   plugin dir under the hermes venv python.

## Catalog store choice (documented, testable)

`~/.hermes-mcp/catalogs/` (env override `HERMES_MCP_CATALOG_DIR`), chosen
over plugin-local so the catalog survives plugin re-installs and is shared
across CLI/gateway sessions. Core helpers take explicit path params; the
env-var default lives in `core.default_catalog_dir()` — tests mock
`os.environ` to pin it.

## Pitfall found

`params.get("args") or {}` silently normalizes falsy non-dicts (`[]`) to `{}`
instead of rejecting them — check `isinstance` BEFORE the `or {}` fallback:
```python
args = params.get("args")
if args is not None and not isinstance(args, dict):
    return "mcp_call: 'args' must be a JSON object."
args = args or {}
```
