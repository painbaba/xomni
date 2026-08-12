# mcp-catalog

MCP catalog layer (Goose P3a port): discover, validate, and manage MCP
servers as agent tools. Pure stdlib, no Hermes imports.

## What it does

- `parse_catalog` / `validate_catalog` — turn a JSON catalog document into a
  validated list of `{name, command, args, env, description}` entries with
  clear error messages (duplicate names, bad types, command not on PATH).
- **Marketplace install path (U2):** `install_server(name, host_config_path)`
  resolves a rich catalog entry (`install_command` + `connect_steps` from
  `data/mcp/catalog.json`, 311 servers) into a host `mcp_servers` block
  (`command`/`args`/`url`/`env`) and appends it to the host `config.yaml`
  surgically — idempotent (skips when already registered), and every failure
  (unknown server, no launcher, config missing/read-only) raises a loud
  `CatalogError` naming the file and the fix. `launch_config` strips shell
  install prefixes (`pip install X && uvx foo` → `uvx foo`) and maps
  `hermes mcp add <name> --url <url>` entries to `url:` blocks.
- **Marketplace badges:** `/mcp list` renders the rich catalog with
  stars (`★108.8k`), keyless (`keyless`/`needs-key` from secret hints in
  description/purpose/connect_steps), and security verdict
  (`VERIFIED`/`REVIEW`/`UNVERIFIED` from the catalog's `verified`+`source`).
- **Marketplace search:** `search_catalog(entries, query)` /
  `format_search_results(...)` — `/mcp search <query>` keyword search over
  name/description/purpose (all query words must match; name hits rank
  first) with the same badges as `/mcp list`.
- **Gap surfacing:** `gap_line(rich_count, host_servers)` — `/mcp status`
  prints the marketplace size vs the host's `mcp_servers` registered/enabled
  counts, with an explicit gap note when they differ (the '311 in catalog
  vs N on host' surface).
- JSON-RPC 2.0 message shapes per the MCP spec (2025-06-18):
  `initialize_message`, `list_tools_message`, `call_tool_message`,
  `initialized_notification`, `rpc_envelope` (newline-delimited stdio JSON).
- Catalog state round-trip: `load_catalog_file`, `save_catalog_file`,
  `round_trip`, `load_all_catalogs` (merges every `*.json` in the catalog
  dir in filename order). Sits on top of Hermes' native MCP plumbing
  (`config.yaml` → `mcp_servers` → tools as `mcp__<server>__<tool>`).

## Tools / commands

- Commands: `/mcp`, `/mcp list` (badged marketplace), `/mcp search <query>`
  (badged keyword search over name/description/purpose), `/mcp tools [server]`,
  `/mcp add <path>` (import a catalog file), `/mcp add <name> [--yes]`
  (install from the marketplace into host `config.yaml` `mcp_servers` —
  without `--yes` it prints the plan and asks for confirmation; with `--yes`
  it installs directly, idempotently, and issues a receipt), `/mcp status`
  (includes the marketplace-vs-host gap line: catalog size vs `mcp_servers`
  registered/enabled), `/mcp validate <path>`.
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
