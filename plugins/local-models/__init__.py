"""local-models — Hermes plugin wiring for local LLM endpoints.

Commands:
    /localmodels status          list configured local servers (no network)
    /localmodels scan            live-probe defaults + servers.json extras
    /localmodels config [server] print wiring snippets for a server
    /localmodels add <base_url> [id]   remember an extra server (servers.json)
    /localmodels remove <id>           forget an extra server

Tool: ``local_models`` (action=status|scan|config[, server]) — model-callable
so the agent can query local models mid-task. All hooks return None / this
module never alters agent behavior.
"""
from __future__ import annotations

try:
    from . import core
except ImportError:  # standalone test import (no parent package)
    import core  # type: ignore

_CTX = None

HELP = (
    "/localmodels status          list configured local servers (no network)\n"
    "/localmodels scan            probe defaults + servers.json extras live\n"
    "/localmodels config [server] print wiring snippets (default: ollama)\n"
    "/localmodels add <base_url> [id]  remember an extra server\n"
    "/localmodels remove <id>          forget an extra server\n"
)


def _known_servers() -> list[dict]:
    """Defaults + plugin-local servers.json extras (deepcopy'd inside core)."""
    return core.default_servers() + core.load_servers()


def _status_text() -> str:
    servers = _known_servers()
    default_ids = {s["id"] for s in core.default_servers()}
    lines = ["local-models: local OpenAI-compatible servers (no network touched)"]
    for s in servers:
        tag = "default" if s.get("id") in default_ids else "extra"
        lines.append(f"  {str(s.get('id')):<10} {str(s.get('name', '')):<12} {s.get('base_url')}  ({tag})")
    if not servers:
        lines.append("  none configured")
    lines.append(f"  {len(servers)} server(s); /localmodels scan probes them live")
    return "\n".join(lines)


def _scan_text() -> str:
    results = core.detect_servers(_known_servers())
    return core.scan_text(results)


def _config_text(server_id: str) -> str:
    servers = _known_servers()
    if server_id:
        target = next((s for s in servers if str(s.get("id")) == server_id), None)
        if target is None:
            known = ", ".join(str(s.get("id")) for s in servers) or "none"
            return f"unknown server {server_id!r}. known ids: {known}\n" + HELP
        return core.config_text(target)
    # no argument: default to Ollama (deterministic, no network)
    return core.config_text(core.default_servers()[0])


def _add_server(raw: str) -> str:
    parts = (raw or "").split()
    if not parts:
        return "usage: /localmodels add <base_url> [id] — e.g. /localmodels add http://127.0.0.1:8000/v1 vllm"
    base = parts[0]
    if not (base.startswith("http://") or base.startswith("https://")):
        return f"invalid base_url {base!r} — must start with http:// or https://"
    sid = parts[1] if len(parts) > 1 else base.split("//")[1].split(":")[0]
    name = parts[2] if len(parts) > 2 else sid
    extras = core.load_servers()
    if any(str(s.get("id")) == sid for s in extras):
        return f"server {sid!r} already in servers.json"
    extras.append({"id": sid, "name": name, "base_url": base})
    core.save_servers(extras)
    return f"added {sid} ({base}) to servers.json — {len(extras)} extra server(s) total"


def _remove_server(raw: str) -> str:
    sid = (raw or "").strip()
    if not sid:
        return "usage: /localmodels remove <id>"
    extras = core.load_servers()
    kept = [s for s in extras if str(s.get("id")) != sid]
    if len(kept) == len(extras):
        return f"no extra server with id {sid!r} in servers.json"
    core.save_servers(kept)
    return f"removed {sid!r} from servers.json ({len(kept)} extra server(s) left)"


def _handle_localmodels(raw: str) -> str:
    args = (raw or "").strip()
    parts = args.split(None, 1)
    cmd = (parts[0] or "").lower()
    rest = parts[1].strip() if len(parts) > 1 else ""
    if not cmd or cmd in ("status", "?"):
        return _status_text()
    if cmd == "scan":
        return _scan_text()
    if cmd == "config":
        return _config_text(rest)
    if cmd == "add":
        return _add_server(rest)
    if cmd == "remove":
        return _remove_server(rest)
    if cmd in ("help", "-h", "--help"):
        return HELP
    return f"unknown subcommand {cmd!r}\n" + HELP


def _local_models_tool(params: dict) -> str:
    """Tool handler: params = {action: status|scan|config, server?: str}."""
    params = params or {}
    action = str(params.get("action") or "status").strip().lower()
    server = str(params.get("server") or "").strip()
    if action == "scan":
        return _scan_text()
    if action == "config":
        return _config_text(server)
    if action == "status":
        return _status_text()
    return f"unknown action {action!r}. actions: status | scan | config [server]"


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "localmodels",
        handler=_handle_localmodels,
        description=(
            "Local LLM endpoints (Ollama :11434/v1, LM Studio :1234/v1): "
            "detect, scan and wire local OpenAI-compatible servers "
            "(status | scan | config [server] | add <url> | remove <id>)"
        ),
        args_hint="[status|scan|config [server]]",
    )
    ctx.register_tool(
        "local_models",
        toolset="local",
        schema={
            "description": (
                "Detect and manage LOCAL OpenAI-compatible model servers "
                "(Ollama http://127.0.0.1:11434/v1, LM Studio "
                "http://127.0.0.1:1234/v1) so local free models are usable. "
                "action=status lists known servers (no network); action=scan "
                "probes them live and reports which are up with their model "
                "ids; action=config with optional server id returns wiring "
                "snippets for Hermes/opencode."
            ),
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "scan", "config"],
                    "description": "status: list known servers; scan: live-probe all; config: print wiring snippets",
                },
                "server": {
                    "type": "string",
                    "description": "server id (ollama, lmstudio, or an id from servers.json) — used with action=config",
                },
            },
            "required": ["action"],
        },
        handler=_local_models_tool,
        description="Probe and wire local OpenAI-compatible model servers (Ollama / LM Studio)",
        emoji="🖥️",
    )
