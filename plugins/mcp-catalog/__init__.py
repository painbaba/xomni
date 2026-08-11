"""mcp-catalog — Hermes plugin wiring: discover, validate, manage MCP servers.

This is the catalog layer on top of Hermes' native MCP plumbing: Hermes
already spawns the servers listed under ``mcp_servers`` in ``config.yaml``
and registers their tools as ``mcp__<server>__<tool>`` (see
``tools/mcp_tool.py``). This plugin adds the *inventory*: a user catalog of
MCP server definitions (name, command, args, env, description) plus
commands and a model tool to work with them.

Catalog store: ``~/.hermes-mcp/catalogs/`` (each ``*.json`` file is one
catalog; override the location with ``HERMES_MCP_CATALOG_DIR``). A
home-directory store was chosen over a plugin-local directory so the
catalog survives plugin re-installs and is shared by CLI and gateway
sessions.

Commands::

    /mcp                       list catalog servers
    /mcp list                  list catalog servers
    /mcp tools [server]        tool surface; with <server>, live-discover its tools
    /mcp add <path>            import a catalog JSON file into the catalog dir
    /mcp status                catalog dir, servers, host registration state
    /mcp validate <path>       validate a catalog JSON file (all errors)

Model tool: ``mcp_call(server, tool, args)`` — invokes a tool on a
registered MCP server through the host's public registry dispatch
(``tools.registry.dispatch`` on the ``mcp__<server>__<tool>`` name), with a
clear "not wired" message when the host runtime is unavailable.
"""
from __future__ import annotations

import json
import os
import shutil

from . import core

_CTX = None

HELP = (
    "/mcp                    list catalog servers\n"
    "/mcp list               list catalog servers\n"
    "/mcp tools [server]     tool surface; with <server>, live-discover its tools\n"
    "/mcp add <path>         import a catalog JSON file into ~/.hermes-mcp/catalogs/\n"
    "/mcp status             catalog dir, servers, host registration state\n"
    "/mcp validate <path>    validate a catalog JSON file (all errors)\n"
)


# ─── Host integration (all lazy + guarded: the plugin degrades to a pure
# ─── catalog manager if the Hermes runtime is not importable) ───────────────

def _host_config_servers() -> dict:
    """Return config.yaml ``mcp_servers`` mapping (empty on any failure)."""
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        servers = cfg.get("mcp_servers") or {}
        return servers if isinstance(servers, dict) else {}
    except Exception:
        return {}


def _host_probe_tools(server_name: str, entry: dict) -> list:
    """Live-discover a server's tools via the host's connection probe.

    Uses ``hermes_cli.mcp_config._probe_single_server`` — the same probe
    ``hermes mcp test`` runs. Returns ``[(tool_name, description), ...]``.
    Raises on any failure; callers report the message.
    """
    from hermes_cli.mcp_config import _probe_single_server

    config = {"command": entry["command"], "args": list(entry.get("args") or [])}
    if entry.get("env"):
        config["env"] = dict(entry["env"])
    return _probe_single_server(server_name, config)


# ─── /mcp command ────────────────────────────────────────────────────────────

def _cmd_list(servers) -> str:
    if not servers:
        return (
            f"no MCP servers in catalog ({core.default_catalog_dir()}). "
            "Add one with /mcp add <path-to-catalog-json>."
        )
    return core.list_catalog_text(servers)


def _cmd_tools(server: str, servers) -> str:
    if not server:
        return core.list_tools_text(servers)
    entry = core.find_server(servers, server)
    if entry is None:
        known = ", ".join(s["name"] for s in servers) or "(none)"
        return f"server {server!r} not in catalog. Known servers: {known}"
    try:
        found = _host_probe_tools(server, entry)
    except Exception as exc:
        return (
            f"server '{server}' is in the catalog, but live tool discovery failed: {exc}\n"
            "Register it with `hermes mcp add <name> --command ...` "
            "(config.yaml mcp_servers) to get native mcp__<server>__<tool> tools."
        )
    return core.format_tool_list(server, found)


def _cmd_add(path: str, servers) -> str:
    path = os.path.expanduser((path or "").strip())
    if not path:
        return "usage: /mcp add <path-to-catalog-json>"
    if not os.path.isfile(path):
        return f"/mcp add: no such file: {path}"
    try:
        parsed = core.load_catalog_file(path)
    except core.CatalogError as exc:
        return f"/mcp add: rejected — {exc}"
    dest_dir = core.default_catalog_dir()
    os.makedirs(dest_dir, exist_ok=True)
    basename = os.path.basename(path)
    if not basename.lower().endswith(".json"):
        basename += ".json"
    dest = os.path.join(dest_dir, basename)
    try:
        shutil.copyfile(path, dest)
    except OSError as exc:
        return f"/mcp add: failed to copy into catalog dir: {exc}"
    names = ", ".join(s["name"] for s in parsed)
    return (
        f"added {len(parsed)} server(s) to catalog ({dest}): {names}\n"
        f"Catalog dir: {dest_dir} — validated OK (commands checked on PATH)."
    )


def _cmd_status(servers) -> str:
    catalog_dir = core.default_catalog_dir()
    n_files = 0
    if os.path.isdir(catalog_dir):
        n_files = len(
            [f for f in os.listdir(catalog_dir) if f.lower().endswith(".json")]
        )
    host = _host_config_servers()
    lines = [
        f"catalog dir: {catalog_dir} ({n_files} catalog file(s), {len(servers)} server(s))",
    ]
    for entry in servers:
        name = entry["name"]
        state = "registered+enabled" if host.get(name, {}).get("enabled", True) else "registered"
        if name not in host:
            state = "NOT registered in host config.yaml mcp_servers"
        lines.append(f"  {name}: {state} ({core._command_line(entry)})")
    host_only = [n for n in host if n not in {s["name"] for s in servers}]
    if host_only:
        lines.append(f"  host-configured, not in catalog: {', '.join(sorted(host_only))}")
    if not servers and not host:
        lines.append("  (empty — add a catalog with /mcp add <path>)")
    return "\n".join(lines)


def _cmd_validate(path: str) -> str:
    path = os.path.expanduser((path or "").strip())
    if not path:
        return "usage: /mcp validate <path-to-catalog-json>"
    if not os.path.isfile(path):
        return f"/mcp validate: no such file: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        return f"/mcp validate: cannot read {path}: {exc}"
    errors = core.validate_catalog(text)
    if not errors:
        parsed = core.parse_catalog(text)
        names = ", ".join(s["name"] for s in parsed)
        return f"OK: {len(parsed)} server(s) valid ({names})."
    lines = [f"INVALID: {len(errors)} problem(s) in {path}"]
    lines.extend(f"  - {e}" for e in errors)
    return "\n".join(lines)


def _handle_mcp(raw: str) -> str:
    parts = (raw or "").strip().split(None, 1)
    cmd = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    servers = core.load_all_catalogs()
    if not cmd or cmd in ("list", "ls"):
        return _cmd_list(servers)
    if cmd == "tools":
        return _cmd_tools(rest.strip(), servers)
    if cmd == "add":
        return _cmd_add(rest, servers)
    if cmd == "status":
        return _cmd_status(servers)
    if cmd == "validate":
        return _cmd_validate(rest)
    return HELP


# ─── Model tool: mcp_call ────────────────────────────────────────────────────

def _mcp_call_tool(params: dict) -> str:
    server = (params.get("server") or "").strip()
    tool = (params.get("tool") or "").strip()
    args = params.get("args")
    if not server or not tool:
        return "mcp_call: 'server' and 'tool' are required."
    if args is not None and not isinstance(args, dict):
        return "mcp_call: 'args' must be a JSON object."
    args = args or {}
    try:
        from tools.mcp_tool import mcp_prefixed_tool_name
        from tools.registry import registry
    except Exception as exc:
        return (
            f"mcp_call: not wired — host MCP runtime unavailable "
            f"(could not import tools.mcp_tool: {exc}). "
            "Use the native mcp__<server>__<tool> tools instead."
        )
    name = mcp_prefixed_tool_name(server, tool)
    if registry.get_entry(name) is None:
        return (
            f"mcp_call: tool {name!r} is not registered. The server must be configured "
            "under mcp_servers in config.yaml (`hermes mcp add <name> --command ...`) "
            "and connected — check /mcp status or /mcp tools <server>. "
            "Until then, no call was made."
        )
    result = registry.dispatch(name, args)
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False)
    except TypeError:
        return str(result)


# ─── Registration ────────────────────────────────────────────────────────────

def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "mcp",
        handler=_handle_mcp,
        description=(
            "MCP catalog: discover, validate and manage MCP servers as agent tools "
            "(list | tools [server] | add <path> | status | validate <path>)"
        ),
        args_hint="[list|tools [server]|add <path>|status|validate <path>]",
    )
    ctx.register_tool(
        "mcp_call",
        toolset="mcp",
        schema={
            "description": (
                "Call a tool on a configured MCP (Model Context Protocol) server. "
                "The server must be registered under mcp_servers in config.yaml "
                "(see /mcp status); its tools are then available natively as "
                "mcp__<server>__<tool> — this tool is a convenience wrapper for "
                "invoking one by logical server + tool name. Args: server (string), "
                "tool (string), args (object of tool arguments)."
            ),
            "type": "object",
            "properties": {
                "server": {
                    "type": "string",
                    "description": "MCP server name, e.g. 'ffmpeg' or 'youtube-transcript'",
                },
                "tool": {
                    "type": "string",
                    "description": "Tool name exposed by that server, e.g. 'convert'",
                },
                "args": {
                    "type": "object",
                    "description": "Tool arguments as a JSON object (omit if none)",
                },
            },
            "required": ["server", "tool"],
        },
        handler=_mcp_call_tool,
        description="Invoke a tool on a registered MCP server",
        emoji="🔌",
    )
