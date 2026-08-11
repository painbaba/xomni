# mcp-catalog

MCP catalog layer (Goose P3a port): discover, validate, and manage MCP
servers as agent tools. Pure stdlib, no Hermes imports.

## What it does

- `parse_catalog` / `validate_catalog` — turn a JSON catalog document into a
  validated list of `{name, command, args, env, description}` entries with
  clear error messages (duplicate names, bad types, command not on PATH).
- JSON-RPC 2.0 message shapes per the MCP spec (2025-06-18):
  `initialize_message`, `list_tools_message`, `call_tool_message`,
  `initialized_notification`, `rpc_envelope` (newline-delimited stdio JSON).
- Catalog state round-trip: `load_catalog_file`, `save_catalog_file`,
  `round_trip`, `load_all_catalogs` (merges every `*.json` in the catalog
  dir in filename order). Sits on top of Hermes' native MCP plumbing
  (`config.yaml` → `mcp_servers` → tools as `mcp__<server>__<tool>`).

## Tools / commands

- Commands: `/mcp`, `/mcp list`, `/mcp tools [server]`, `/mcp add <path>`,
  `/mcp status`, `/mcp validate <path>`.
- Model tool: `mcp_call(server, tool, args)` — dispatches through the host
  registry (`mcp__<server>__<tool>`) when the server is registered.

## Speed posture

Zero hooks registered. Catalog parsing/validation is pure and local; live
tool discovery only runs on explicit `/mcp tools` invocations.

## Test

```bash
cd plugins/mcp-catalog && python -m unittest tests.test_core -v
```

## Config

- Catalog store: `~/.hermes-mcp/catalogs/` — each `*.json` file is one
  catalog (home-dir store survives plugin re-installs; shared by CLI and
  gateway). Override with env var `HERMES_MCP_CATALOG_DIR`.
- Example catalog: `mcp_catalog.example.json` (plugin dir).
- `MCP_PROTOCOL_VERSION = "2025-06-18"` (module constant).
