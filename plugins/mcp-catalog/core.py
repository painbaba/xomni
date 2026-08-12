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
  * :func:`load_rich_catalog` — the marketplace catalog
    (``data/mcp/catalog.json``, 311 entries with ``install_command`` /
    ``connect_steps`` / ``stars`` / ``verified`` / ``source``).
  * :func:`install_server` / :func:`install_plan` / :func:`launch_config` —
    the install path: resolve a rich catalog entry into a host
    ``mcp_servers`` block (``command``/``args``/``url``/``env``) and append
    it to the host config.yaml — idempotent, with loud failures that name
    the file and the fix.
  * :func:`format_badges` / :func:`keyless` / :func:`security_verdict` /
    :func:`list_catalog_badged` — stars / keyless / security badges for
    ``/mcp list``.

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
import re
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


# ─── Marketplace install path (U2) ───────────────────────────────────────────

# Host config resolution order: MCP_HOST_CONFIG > HERMES_CONFIG >
# HERMES_HOME/config.yaml > ~/.hermes/config.yaml. The plugin's __init__
# passes the exact runtime path (hermes_cli.config.get_config_path()) when the
# Hermes runtime is importable; these are the pure-stdlib fallbacks.
HOST_CONFIG_ENV = "MCP_HOST_CONFIG"
_HOST_CONFIG_FALLBACK = os.path.join(os.path.expanduser("~"), ".hermes", "config.yaml")

# Shell install prefixes stripped from install_command before deriving the
# launch line: 'pip install browser-use && uvx browser-use' -> 'uvx browser-use'.
_SHELL_INSTALL_RE = re.compile(
    r"^\s*(?:pip|pip3|python\s+-m\s+pip|npm|pnpm|yarn|uv|brew|apt|apt-get|cargo|go)\s+"
    r"(?:install|i|add|get)\s+\S+\s*(?:&&|;)\s*",
    re.IGNORECASE,
)

_NO_LAUNCH_MARKERS = {
    "see repo", "see readme", "see repository", "n/a", "na", "-", "none", "manual",
}

# Sources treated as primary (verifiable upstream) for the security verdict.
_TRUSTED_SOURCE_HINTS = ("github", "pypi", "npm", "official", "smithery", "glama", "awesome-mcp")

# Secret/auth hints for the keyless badge (lowercased substring match).
_KEY_HINTS = (
    "api key", "api_key", "apikey", " token", "secret", "bearer", "oauth",
    "password", "credential", "env var", "env_var", "environment variable",
)


def default_rich_catalog_path() -> str:
    """The marketplace catalog path (repo ``data/mcp/catalog.json``), resolved
    from this file's location so it works regardless of the cwd."""
    here = os.path.dirname(os.path.abspath(__file__))      # plugins/mcp-catalog
    repo = os.path.dirname(os.path.dirname(here))          # repo root
    return os.path.join(repo, "data", "mcp", "catalog.json")


def load_rich_catalog(path: Optional[str] = None) -> List[dict]:
    """Load the marketplace catalog (``data/mcp/catalog.json``): 311 rich
    entries carrying ``install_command``/``connect_steps``/``stars``/
    ``verified``/``source``. Raises :class:`CatalogError` naming the file on
    any read/parse problem."""
    path = path or default_rich_catalog_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        raise CatalogError(f"cannot read MCP catalog {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"invalid JSON in MCP catalog {path}: {exc}") from exc
    if not isinstance(data, list):
        raise CatalogError(
            f"MCP catalog {path} must be a JSON array of server objects, "
            f"got {type(data).__name__}"
        )
    return data


def default_host_config_path() -> str:
    """The host Hermes config.yaml path (``MCP_HOST_CONFIG`` >
    ``HERMES_CONFIG`` > ``HERMES_HOME``/config.yaml > ``~/.hermes/config.yaml``)."""
    for var in (HOST_CONFIG_ENV, "HERMES_CONFIG"):
        val = os.environ.get(var, "")
        if val.strip():
            return os.path.expanduser(val.strip())
    home = os.environ.get("HERMES_HOME", "")
    if home.strip():
        return os.path.join(os.path.expanduser(home.strip()), "config.yaml")
    return _HOST_CONFIG_FALLBACK


def launch_config(entry: dict) -> Optional[dict]:
    """Derive the host ``mcp_servers`` block shape from a rich catalog entry.

    Returns ``{"command": str, "args": [str]}`` for stdio servers (shell
    install prefixes like ``pip install X && `` are stripped), ``{"url": str}``
    for hosted HTTP servers (``hermes mcp add <name> --url <url>``), or None
    when the entry has no auto-installable launcher (e.g. ``see repo``)."""
    raw = (entry.get("install_command") or "").strip()
    if not raw or raw.lower() in _NO_LAUNCH_MARKERS:
        return None
    if raw.lower().startswith("hermes mcp add"):
        match = re.search(r"--url\s+(\S+)", raw)
        if match:
            return {"url": match.group(1).strip("\"'")}
        return None
    # Smithery-hosted remotes register via `npx -y @smithery/cli mcp add
    # <https-url>` — those are HTTP servers, not stdio launchers; write the
    # hosted `url:` block (mirrors xomni_cli._parse_install_command).
    if "@smithery/cli" in raw.lower():
        match = re.search(r"https?://\S+", raw)
        if match:
            return {"url": match.group(0).strip("\"'")}
        return None
    cmd = _SHELL_INSTALL_RE.sub("", raw)
    cmd = cmd.split("&&")[0].split(";")[0].strip()
    tokens = [t for t in cmd.split() if t not in ("&&", ";", "|", "||")]
    if not tokens:
        return None
    return {"command": tokens[0], "args": tokens[1:]}


# ─── Host config editing (surgical, preserves the rest of the file) ──────────

_SAFE_SCALAR_RE = re.compile(r"^[A-Za-z0-9_@./+~%-]+$")


def _yaml_scalar(value: Any) -> str:
    """Render a YAML scalar; single-quote anything outside the safe charset."""
    value = str(value)
    if _SAFE_SCALAR_RE.match(value):
        return value
    return "'" + value.replace("'", "''") + "'"


def _render_server_block(name: str, block: dict) -> str:
    """Render one ``mcp_servers`` entry (2-space server indent, 4-space keys)
    matching the shape ``hermes mcp add`` writes."""
    lines = [f"  {_yaml_scalar(name)}:"]
    if "url" in block:
        lines.append(f"    url: {_yaml_scalar(block['url'])}")
    else:
        lines.append(f"    command: {_yaml_scalar(block.get('command', ''))}")
        args = block.get("args") or []
        if args:
            lines.append("    args:")
            lines.extend(f"      - {_yaml_scalar(a)}" for a in args)
        env = block.get("env") or {}
        if env:
            lines.append("    env:")
            lines.extend(
                f"      {_yaml_scalar(k)}: {_yaml_scalar(v)}" for k, v in sorted(env.items())
            )
    return "\n".join(lines)


def _append_server_block(text: str, name: str, block: dict) -> str:
    """Surgically append ``name`` under the top-level ``mcp_servers`` key,
    preserving every other byte of the config (comments, key order, other
    sections). Returns the new file text."""
    eol = "\r\n" if "\r\n" in text else "\n"
    if text and not text.endswith("\n"):
        text += eol
    block_text = _render_server_block(name, block)
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not line[:1].isspace():
            if stripped.split(":", 1)[0].strip() == "mcp_servers":
                start = i
                break
    if start is None:
        if text and not text.endswith(eol):
            text += eol
        return text + f"mcp_servers:{eol}" + block_text.replace("\n", eol) + eol
    if re.search(r":\s*\{\}\s*(#.*)?$", lines[start]):
        lines[start] = "mcp_servers:"
        lines[start + 1 : start + 1] = block_text.splitlines()
        return eol.join(lines) + eol
    end = len(lines)
    for i in range(start + 1, len(lines)):
        line = lines[i]
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not line[:1].isspace():
            end = i
            break
    lines[end:end] = block_text.splitlines()
    return eol.join(lines) + eol


def _server_registered(host_config_path: str, server_name: str) -> bool:
    """True when ``server_name`` is already a key under ``mcp_servers`` in the
    host config (line-level scan; a missing file yields False)."""
    if not os.path.isfile(host_config_path):
        return False
    try:
        with open(host_config_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return False
    pattern = re.compile(r"^ {2}\"?%s\"?:" % re.escape(server_name))
    return any(pattern.match(line) for line in text.splitlines())


# ─── Install plan + write ────────────────────────────────────────────────────


def install_plan(
    server_name: str,
    host_config_path: Optional[str] = None,
    catalog: Optional[List[dict]] = None,
) -> dict:
    """Resolve a rich catalog entry into an install plan (no writes).

    Returns ``{name, block, exists, path, launch, steps, entry}``. Raises
    :class:`CatalogError` — loudly, naming the file and the fix — when the
    server is unknown or has no auto-installable launcher. ``exists`` is True
    when the name is already registered under ``mcp_servers`` (an install
    would be a no-op)."""
    catalog_path = None
    if catalog is None:
        catalog = load_rich_catalog()
        catalog_path = default_rich_catalog_path()
    entry = find_server(catalog, server_name)
    if entry is None:
        src = catalog_path or "<provided catalog>"
        raise CatalogError(
            f"server {server_name!r} not found in MCP catalog ({src}) — "
            f"run /mcp list for known server names"
        )
    block = launch_config(entry)
    if block is None:
        steps = entry.get("connect_steps") or []
        detail = "\n".join(f"  {s}" for s in steps) if steps else "  (see the catalog entry)"
        raise CatalogError(
            f"server {server_name!r} has no auto-installable launcher "
            f"(install_command={entry.get('install_command')!r}). Manual steps:\n{detail}"
        )
    path = host_config_path or default_host_config_path()
    if "command" in block:
        launch = _command_line({"command": block["command"], "args": block.get("args") or []})
    else:
        launch = block.get("url", "")
    return {
        "name": server_name,
        "block": block,
        "exists": _server_registered(path, server_name),
        "path": path,
        "launch": launch,
        "steps": entry.get("connect_steps") or [],
        "entry": entry,
    }


def install_server(
    server_name: str,
    host_config_path: Optional[str] = None,
    catalog: Optional[List[dict]] = None,
) -> dict:
    """Append a catalog server block to the host config ``mcp_servers``.

    Idempotent: when ``server_name`` is already registered, nothing is
    written and ``written`` is False. Returns ``{name, block, written, path}``.

    Failures are loud — :class:`CatalogError` naming the file and the fix:
    unknown server, no auto-installable launcher, config file missing, or
    config file read-only/unwritable. Never silently cancels."""
    plan = install_plan(server_name, host_config_path, catalog)
    if plan["exists"]:
        return {
            "name": plan["name"],
            "block": plan["block"],
            "written": False,
            "path": plan["path"],
        }
    path = plan["path"]
    if not os.path.isfile(path):
        raise CatalogError(
            f"host config not found: {path} — create it (or point "
            f"MCP_HOST_CONFIG / HERMES_CONFIG at an existing config.yaml) and re-run"
        )
    if not os.access(path, os.W_OK):
        raise CatalogError(
            f"host config is read-only: {path} — clear the read-only attribute "
            f"(attrib -R \"{path}\" / chmod +w) and re-run"
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        raise CatalogError(f"cannot read host config {path}: {exc}") from exc
    try:
        new_text = _append_server_block(text, plan["name"], plan["block"])
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
    except OSError as exc:
        raise CatalogError(
            f"failed to write host config {path}: {exc} — check permissions "
            f"(clear the read-only attribute, close editors holding the file) and re-run"
        ) from exc
    return {"name": plan["name"], "block": plan["block"], "written": True, "path": path}


# ─── Marketplace badges (stars / keyless / security) ─────────────────────────


def keyless(entry: dict) -> bool:
    """True when the server needs no secret env var / auth to run (heuristic
    over description + purpose + connect_steps)."""
    hay = " ".join(
        [
            entry.get("description") or "",
            entry.get("purpose") or "",
            " ".join(entry.get("connect_steps") or []),
        ]
    ).lower()
    return not any(hint in hay for hint in _KEY_HINTS)


def security_verdict(entry: dict) -> str:
    """Security posture from the catalog's ``verified``/``source`` fields:
    VERIFIED (verified + primary source), REVIEW (verified, secondary source),
    UNVERIFIED (not verified)."""
    verified = bool(entry.get("verified"))
    source = (entry.get("source") or "").lower()
    if not verified:
        return "UNVERIFIED"
    if any(hint in source for hint in _TRUSTED_SOURCE_HINTS):
        return "VERIFIED"
    return "REVIEW"


def format_badges(entry: dict) -> str:
    """Render stars/keyless/security badges for one rich catalog entry."""
    stars = entry.get("stars")
    if isinstance(stars, (int, float)) and stars:
        stars_badge = f"★{stars / 1000:.1f}k" if stars >= 1000 else f"★{int(stars)}"
    else:
        stars_badge = "★-"
    return " ".join(
        [stars_badge, "keyless" if keyless(entry) else "needs-key", security_verdict(entry)]
    )


def list_catalog_badged(entries: List[dict]) -> str:
    """Marketplace listing with badges (for ``/mcp list``)."""
    if not entries:
        return "no MCP servers in catalog."
    lines = [f"MCP catalog: {len(entries)} server(s)"]
    for entry in entries:
        name = entry.get("name", "?")
        lines.append(f"  {name}  [{format_badges(entry)}]")
        desc = entry.get("description") or entry.get("purpose") or ""
        if desc:
            lines.append(f"    {desc}")
        install = entry.get("install_command") or "(manual steps)"
        lines.append(f"    install: {install}")
    return "\n".join(lines)
