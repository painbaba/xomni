"""local-models — detect and manage LOCAL OpenAI-compatible model servers.

Ollama and LM Studio both expose OpenAI-compatible REST endpoints on
localhost (no API key required). This module probes those endpoints
(``GET {base}/models``), remembers extra user-configured servers in a
plugin-local ``servers.json``, and generates per-agent config snippets so the
unified agent (Hermes, OpenCode, ...) can route to local free models too.

PORT CONSTANTS (documented):
    OLLAMA_BASE_URL     http://127.0.0.1:11434/v1 — Ollama's OpenAI-compatible
                        API. Port 11434 is Ollama's default serve port
                        (OLLAMA_HOST can move it; the /v1 path is the
                        OpenAI-compat shim).
    LM_STUDIO_BASE_URL  http://127.0.0.1:1234/v1  — LM Studio's local server.
                        Port 1234 is the default when "Start Server" is
                        enabled (Settings -> Local Server).

Pure stdlib, no Hermes imports. Unit-testable in isolation.
"""
from __future__ import annotations

import json
import os
import urllib.error
from copy import deepcopy
from urllib.request import Request, urlopen

# --- Port constants (documented above) -------------------------------------
OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
LM_STUDIO_BASE_URL = "http://127.0.0.1:1234/v1"

DEFAULT_SERVERS = [
    {"id": "ollama", "name": "Ollama", "base_url": OLLAMA_BASE_URL},
    {"id": "lmstudio", "name": "LM Studio", "base_url": LM_STUDIO_BASE_URL},
]

# Local endpoints ignore auth, but a stack can sit behind a Cloudflare-style
# reverse proxy that 1010-blocks non-browser User-Agents — send a browser UA.
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Plugin-local extra-servers file (created by /localmodels add; hand-editable).
SERVERS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "servers.json")


def default_servers() -> list[dict]:
    """Deepcopy of the built-in defaults — callers may mutate the result freely."""
    return deepcopy(DEFAULT_SERVERS)


def _extract_model_ids(data) -> list[str]:
    """Model ids from an OpenAI-compatible /models payload.

    Handles {"data": [{"id": ...}, ...]} (OpenAI / Ollama / LM Studio),
    {"models": [...]} (legacy), and a bare list of ids.
    """
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("data") or data.get("models") or []
    else:
        return []
    ids = []
    for row in rows:
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
        elif isinstance(row, str):
            ids.append(row)
    return ids


def probe_server(base_url: str, timeout: float = 3) -> dict:
    """Probe one local OpenAI-compatible server: GET {base}/models.

    Returns {"ok": bool, "http": int|None, "models": [ids], "error": str|None}.
    HTTP errors (real urllib.error.HTTPError) report the status code;
    connection failures (OSError / refused) report the message.
    """
    base = (base_url or "").strip().rstrip("/")
    result = {"ok": False, "http": None, "models": [], "error": None}
    if not base:
        result["error"] = "empty base_url"
        return result
    req = Request(base + "/models", headers={"User-Agent": BROWSER_UA})
    try:
        with urlopen(req, timeout=timeout) as resp:
            result["http"] = resp.status
            payload = json.loads(resp.read().decode("utf-8", "replace"))
            result["models"] = _extract_model_ids(payload)
            result["ok"] = True
    except urllib.error.HTTPError as exc:
        result["http"] = exc.code
        result["error"] = f"HTTP {exc.code}"
    except Exception as exc:  # OSError (refused), URLError, timeout, bad JSON...
        result["error"] = str(exc)[:160]
    return result


def detect_servers(defaults: list | None = None, timeout: float = 3) -> list[dict]:
    """Probe every server in ``defaults`` (deepcopy of DEFAULT_SERVERS if None).

    Returns one identity-tagged probe result per server:
        {server_id, name, base_url, ok, http, models, error}
    Down servers are still reported (ok=False, error explains why) so callers
    can show the reason; ``scan_text`` surfaces only the up ones as usable.
    Accepts server dicts or bare base-url strings.
    """
    src = defaults if defaults is not None else DEFAULT_SERVERS
    servers = []
    for s in deepcopy(src):
        if isinstance(s, str):
            sid = s.split("//")[-1].split(":")[0]
            s = {"id": sid, "name": s, "base_url": s}
        servers.append(s)
    out = []
    for s in servers:
        r = probe_server(s.get("base_url", ""), timeout=timeout)
        r["server_id"] = str(s.get("id") or s.get("name") or "?").lower()
        r["name"] = s.get("name") or r["server_id"]
        r["base_url"] = s.get("base_url", "")
        out.append(r)
    return out


def load_servers(path: str | None = None) -> list[dict]:
    """Extra user-configured servers from the plugin-local servers.json.

    Missing or corrupt file -> [] (extras live on top of DEFAULT_SERVERS).
    """
    p = path or SERVERS_JSON
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return deepcopy(data)
        return deepcopy(data.get("servers", []))
    except (OSError, ValueError):
        return []


def save_servers(servers: list[dict], path: str | None = None) -> None:
    """Persist extra servers to servers.json (list of {id, name, base_url})."""
    p = path or SERVERS_JSON
    parent = os.path.dirname(os.path.abspath(p))
    os.makedirs(parent, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(servers, f, indent=2, sort_keys=True)


# --- Config snippet generators ---------------------------------------------

def hermes_provider_block(server: dict, model_ids: list[str] | None = None) -> str:
    """YAML snippet for config.yaml: OpenAI-compatible provider on a local server.

    key_env is the placeholder 'local' — local endpoints need no real API key.
    """
    sid = str(server.get("id") or "local")
    name = server.get("name") or sid
    base = (server.get("base_url") or "").strip().rstrip("/")
    model_line = f"# model: {model_ids[0]}" if model_ids else "# model: <id from /localmodels scan>"
    return (
        f"# --- local-models: {name} ({base}) ---\n"
        f"# Place under `model:` (or fallback_model) in config.yaml.\n"
        f"# provider: {sid}\n"
        f"{model_line}\n"
        f"# base_url: {base}\n"
        f"# key_env: local   # placeholder — local servers need no real key\n"
    )


def _opencode_block(server: dict, model_ids: list[str] | None = None) -> str:
    """opencode.json provider block (@ai-sdk/openai-compatible), valid JSON."""
    sid = str(server.get("id") or "local")
    name = server.get("name") or sid
    base = (server.get("base_url") or "").strip().rstrip("/")
    models: dict = {}
    for mid in model_ids or []:
        models[mid] = {"name": mid}
    if not models:
        models = {"<model-id>": {"name": "<Model Name>"}}
    block = {
        "provider": {
            sid: {
                "npm": "@ai-sdk/openai-compatible",
                "name": name,
                "options": {"baseURL": base, "apiKey": "local"},
                "models": models,
            }
        }
    }
    return json.dumps(block, indent=2)


def opencode_config(server: dict, model_ids: list[str] | None = None) -> str:
    """opencode.json provider block wiring the local server into OpenCode."""
    return _opencode_block(server, model_ids)


def ollama_config(server: dict, model_ids: list[str] | None = None) -> str:
    """The canonical Ollama-shaped opencode block, for ANY local server.

    Same wiring as ``opencode_config`` — opencode's docs model every local
    provider on the Ollama example (npm @ai-sdk/openai-compatible, baseURL,
    dummy apiKey). Provided as a named generator so the canonical form is
    easy to reference for any server id (ollama, lmstudio, custom).
    """
    return _opencode_block(server, model_ids)


def config_text(server: dict, model_ids: list[str] | None = None) -> str:
    """Full wiring bundle for one server: Hermes YAML + opencode JSON."""
    return "\n".join(
        [
            hermes_provider_block(server, model_ids),
            "",
            "# opencode.json provider block:",
            opencode_config(server, model_ids),
            "",
            "# canonical Ollama-shaped opencode block (same wiring):",
            ollama_config(server, model_ids),
        ]
    )


# --- Text formatting --------------------------------------------------------

def scan_text(results: list[dict]) -> str:
    """Human-readable scan output; only ok servers are listed as usable."""
    up = [r for r in results if r.get("ok")]
    lines = [f"local-models scan: {len(up)} of {len(results)} server(s) up"]
    for r in results:
        sid = r.get("server_id") or "?"
        if r.get("ok"):
            models = ", ".join(r.get("models") or []) or "(no models reported)"
            lines.append(f"  UP    {sid:<10} {r.get('base_url')}  [HTTP {r.get('http')}]")
            lines.append(f"          models: {models}")
        else:
            lines.append(f"  DOWN  {sid:<10} {r.get('base_url')}  ({r.get('error')})")
    if up:
        usable = ", ".join((r.get("server_id") or "?") for r in up)
        lines.append(f"  usable: {usable} — /localmodels config <id> for wiring")
    return "\n".join(lines)
