"""mcp-catalog core — pure, stdlib-only catalog model for MCP servers.

The Model Context Protocol (MCP) lets an agent extend itself with external
tools by spawning stdio servers (or talking HTTP) and speaking JSON-RPC 2.0
over the transport. This module is the *catalog layer* — the piece that
discovers, validates, and documents MCP servers alongside the host's native
MCP plumbing (Hermes already spawns servers listed in ``config.yaml`` under
``mcp_servers`` and registers their tools as ``mcp__<server>__<tool>``; this
catalog is the user-facing inventory on top of that).

What lives here (all pure, all stdlib, no Hermes imports):

  * :func:`parse_catalog` / :func:`validate_catalog` — turn a JSON catalog
    document into a validated list of server entries
    ``{name, command, args, env, description}`` with clear error messages.
  * :func:`list_catalog_text` / :func:`list_tools_text` /
    :func:`format_tool_list` — human-readable views of catalogs and of
    discovered tool lists.
  * :func:`initialize_message` / :func:`list_tools_message` /
    :func:`call_tool_message` / :func:`initialized_notification` —
    JSON-RPC 2.0 message shapes per the MCP spec
    (https://modelcontextprotocol.io/specification/2025-06-18), returned as
    plain dicts; :func:`rpc_envelope` serializes them for the stdio
    transport (one JSON object per line).
  * :func:`load_catalog_file` / :func:`save_catalog_file` /
    :func:`round_trip` — catalog state round-trip (parse -> dump -> parse).

Catalog location convention: catalogs live in ``~/.hermes-mcp/catalogs/``
(override with the ``HERMES_MCP_CATALOG_DIR`` env var). Each ``*.json`` file
in that directory is one catalog; :func:`load_all_catalogs` merges them in
filename order. The choice of a home-directory store (rather than a
plugin-local directory) keeps the catalog across plugin re-installs and
makes it shareable between CLI and gateway sessions.
"""
from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List, Optional

# Latest stable MCP spec revision (modelcontextprotocol.io/specification).
MCP_PROTOCOL_VERSION = "2025-06-18"
JSONRPC_VERSION = "2.0"

# Catalog store location (see module docstring). "~" resolves via expanduser,
# so on Windows this is C:\\Users\\<user>\\.hermes-mcp\\catalogs\\.
CATALOG_DIR_NAME = ".hermes-mcp"
CATALOG_SUBDIR = "catalogs"
CATALOG_DIR_ENV = "HERMES_MCP_CATALOG_DIR"

# Canonical fields of a catalog entry. Extra keys in a source document are
# ignored (forward compatibility) and dropped from the canonical output.
ENTRY_FIELDS = ("name", "command", "args", "env", "description")


class CatalogError(Exception):
    """Catalog parse/validation failure with a clear, actionable message."""


# ─── Validation ──────────────────────────────────────────────────────────────


def _entry_label(index: int, name: str) -> str:
    """Human-readable label for error messages: ``entry 2 (filesystem)``."""
    label = f"catalog entry {index}"
    if name:
        label += f" ({name!r})"
    return label


def _validate_entry(index: int, raw: Any) -> List[str]:
    """Validate one raw catalog entry; return a list of error messages."""
    errors: List[str] = []
    label = f"catalog entry {index}"

    if not isinstance(raw, dict):
        return [f"{label}: must be an object, got {type(raw).__name__}"]

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{label}: missing or invalid 'name' (expected non-empty string)")
        name = ""

    label = _entry_label(index, name)

    command = raw.get("command")
    if not isinstance(command, str) or not command.strip():
        errors.append(f"{label}: missing or invalid 'command' (expected non-empty string)")
        command = ""

    args = raw.get("args", [])
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        errors.append(f"{label}: 'args' must be a list of strings")

    env = raw.get("env", {})
    if not isinstance(env, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in env.items()
    ):
        errors.append(f"{label}: 'env' must be an object mapping string to string")

    description = raw.get("description", "")
    if not isinstance(description, str):
        errors.append(f"{label}: 'description' must be a string")

    return errors


def validate_catalog(raw: Any, check_path: bool = True) -> List[str]:
    """Validate a catalog document; return ALL error messages (empty = valid).

    ``raw`` may be JSON text (str/bytes) or an already-decoded list.
    ``check_path`` (default True) additionally verifies each stdio
    ``command`` resolves on ``PATH`` via :func:`shutil.which` — the "when
    checkable" rule: launcher commands like ``npx``/``uvx`` are checked like
    anything else, and the check is skipped when the caller knows the
    command will only exist on the target machine (e.g. validating a
    catalog for someone else's box).
    """
    if isinstance(raw, (str, bytes)):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            return [f"invalid JSON: {exc}"]
    if not isinstance(raw, list):
        return [f"catalog must be a JSON array of server objects, got {type(raw).__name__}"]

    errors: List[str] = []
    seen: Dict[str, int] = {}
    for index, entry in enumerate(raw, start=1):
        errors.extend(_validate_entry(index, entry))
        name = entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str) and name.strip():
            key = name.strip()
            if key in seen:
                errors.append(
                    f"duplicate server name: {key!r} "
                    f"(entries {seen[key]} and {index})"
                )
            else:
                seen[key] = index
            if check_path:
                command = entry.get("command")
                if isinstance(command, str) and command.strip():
                    if shutil.which(command) is None:
                        errors.append(
                            f"catalog entry {index} ({key}): "
                            f"command not found on PATH: {command!r}"
                        )
    return errors


def parse_catalog(raw: Any, check_path: bool = True) -> List[dict]:
    """Parse + validate a catalog document into canonical server dicts.

    Returns a list of ``{name, command, args, env, description}`` entries
    (``args`` defaults to ``[]``, ``env`` to ``{}``, ``description`` to
    ``""``; unknown keys are dropped). Raises :class:`CatalogError` with a
    clear message on the first problem — use :func:`validate_catalog` to
    collect every problem at once.
    """
    errors = validate_catalog(raw, check_path=check_path)
    if errors:
        raise CatalogError(errors[0])

    if isinstance(raw, (str, bytes)):
        raw = json.loads(raw)

    servers: List[dict] = []
    for entry in raw:
        name = entry["name"].strip()
        command = entry["command"].strip()
        args = list(entry.get("args") or [])
        env = dict(entry.get("env") or {})
        description = entry.get("description") or ""
        servers.append(
            {
                "name": name,
                "command": command,
                "args": args,
                "env": env,
                "description": description,
            }
        )
    return servers


def find_server(servers: List[dict], name: str) -> Optional[dict]:
    """Return the first catalog entry whose ``name`` matches, or None."""
    for entry in servers:
        if entry.get("name") == name:
            return entry
    return None


# ─── Formatting ──────────────────────────────────────────────────────────────


def _command_line(entry: dict) -> str:
    """Render ``command args...`` as a shell-ish one-liner."""
    parts = [entry["command"]] + [str(a) for a in entry.get("args") or []]
    return " ".join(parts)


def list_catalog_text(servers: List[dict]) -> str:
    """Format a parsed catalog as a readable server listing (for ``/mcp list``)."""
    if not servers:
        return "no MCP servers in catalog."
    lines = [f"MCP catalog: {len(servers)} server(s)"]
    for entry in servers:
        lines.append(f"  {entry['name']}")
        if entry.get("description"):
            lines.append(f"    {entry['description']}")
        lines.append(f"    run: {_command_line(entry)}")
        env = entry.get("env") or {}
        if env:
            lines.append(f"    env: {', '.join(f'{k}={v}' for k, v in sorted(env.items()))}")
    return "\n".join(lines)


def list_tools_text(catalog: List[dict]) -> str:
    """Format a parsed catalog as the agent's discoverable *tool surface*.

    Each catalog server is an extensibility point: once registered with the
    host (``config.yaml`` ``mcp_servers``), its tools appear as
    ``mcp__<server>__<tool>``. This view shows what a catalog makes
    available and how it would be launched.
    """
    if not catalog:
        return "no MCP servers in catalog."
    lines = [f"MCP tool surface: {len(catalog)} server(s)"]
    for entry in catalog:
        name = entry["name"]
        lines.append(f"  mcp://{name}")
        lines.append(f"    description: {entry.get('description') or '(none)'}")
        lines.append(f"    launch: {_command_line(entry)}")
        lines.append(f"    tools: mcp__{name}__<tool> once connected")
    return "\n".join(lines)


def format_tool_list(server: str, tools: List[Any]) -> str:
    """Format a discovered tool list for one server.

    ``tools`` is a list of ``(name, description)`` tuples (as returned by
    the host's connection probe) or of dicts with ``name``/``description``.
    """
    if not tools:
        return f"server '{server}': connected, but exposed no tools."
    lines = [f"server '{server}': {len(tools)} tool(s)"]
    for tool in tools:
        if isinstance(tool, dict):
            tname = tool.get("name", "?")
            tdesc = tool.get("description", "")
        else:
            tname, tdesc = tool[0], (tool[1] if len(tool) > 1 else "")
        if len(tdesc) > 80:
            tdesc = tdesc[:77] + "..."
        lines.append(f"  mcp__{server}__{tname} — {tdesc or '(no description)'}")
    return "\n".join(lines)


# ─── JSON-RPC message shapes (MCP spec) ──────────────────────────────────────


def rpc_message(method: str, params: dict, request_id: int) -> dict:
    """A JSON-RPC 2.0 request/response envelope for the stdio transport."""
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "method": method,
        "params": params,
    }


def initialize_message(
    client_name: str = "hermes-mcp-catalog",
    client_version: str = "1.0.0",
    protocol_version: str = MCP_PROTOCOL_VERSION,
    capabilities: Optional[dict] = None,
    request_id: int = 0,
) -> dict:
    """The ``initialize`` handshake message the client sends first.

    Per the spec the params carry ``protocolVersion``, client ``capabilities``
    and ``clientInfo`` ``{name, version}``.
    """
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": protocol_version,
            "capabilities": dict(capabilities or {}),
            "clientInfo": {"name": client_name, "version": client_version},
        },
    }


def initialized_notification() -> dict:
    """``notifications/initialized`` — sent after the server's initialize
    response, before any other request. Notifications carry no ``id``."""
    return {"jsonrpc": JSONRPC_VERSION, "method": "notifications/initialized"}


def list_tools_message(request_id: int = 1) -> dict:
    """``tools/list`` — enumerate the server's tools (empty params)."""
    return rpc_message("tools/list", {}, request_id)


def call_tool_message(name: str, arguments: Optional[dict] = None, request_id: int = 2) -> dict:
    """``tools/call`` — invoke a tool. ``arguments`` is optional per spec."""
    params: dict = {"name": name}
    if arguments:
        params["arguments"] = arguments
    return rpc_message("tools/call", params, request_id)


def rpc_envelope(message: dict) -> str:
    """Serialize one JSON-RPC message for the MCP stdio transport, which is
    newline-delimited JSON: exactly one compact object per line."""
    return json.dumps(message) + "\n"


# ─── State round-trip ────────────────────────────────────────────────────────


def default_catalog_dir() -> str:
    """The catalog store directory (``~/.hermes-mcp/catalogs`` unless the
    ``HERMES_MCP_CATALOG_DIR`` env var overrides it)."""
    override = os.environ.get(CATALOG_DIR_ENV, "")
    if override.strip():
        return os.path.expanduser(override.strip())
    return os.path.join(os.path.expanduser("~"), CATALOG_DIR_NAME, CATALOG_SUBDIR)


def catalog_to_json(servers: List[dict]) -> str:
    """Serialize a parsed catalog (canonical form) to JSON text."""
    return json.dumps(servers, indent=2, ensure_ascii=False)


def load_catalog_file(path: str, check_path: bool = True) -> List[dict]:
    """Read + parse a catalog JSON file. Raises CatalogError on any problem."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        raise CatalogError(f"cannot read {path}: {exc}") from exc
    return parse_catalog(text, check_path=check_path)


def save_catalog_file(path: str, servers: List[dict]) -> None:
    """Write a parsed catalog to ``path`` (creating parent dirs)."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(catalog_to_json(servers))


def round_trip(servers: List[dict]) -> List[dict]:
    """Structural round-trip: canonical form -> JSON text -> canonical form.

    ``check_path`` is intentionally off here: round-tripping is about the
    data shape, not the host's PATH.
    """
    return parse_catalog(catalog_to_json(servers), check_path=False)


def load_all_catalogs(dir_path: Optional[str] = None) -> List[dict]:
    """Merge every ``*.json`` catalog file under the catalog dir, in filename
    order. Files that fail to parse are skipped (``/mcp validate <path>`` is
    the tool for surfacing details); a missing directory yields ``[]``."""
    dir_path = dir_path or default_catalog_dir()
    merged: List[dict] = []
    if not os.path.isdir(dir_path):
        return merged
    for filename in sorted(os.listdir(dir_path)):
        if not filename.lower().endswith(".json"):
            continue
        path = os.path.join(dir_path, filename)
        try:
            merged.extend(load_catalog_file(path))
        except (CatalogError, OSError):
            continue
    return merged
