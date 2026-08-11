"""Provider pool — the free-model layer of XOMNI.

One OpenAI-compatible gateway (opencode Zen, the channel OpenCode itself ships)
serves 25 models VERIFIED LIVE on this machine (HTTP 200, 2026-08-10, browser-UA
required). The same base_url + key works in EVERY agent in the XOMNI stack
(Hermes, OpenCode, Codex, Aider, Goose) because they all speak OpenAI-compatible
chat/completions — so the free models are available across all of them.

Additional free channels are cataloged with exact wiring (NVIDIA NIM, Google AI
Studio, OpenRouter 17 :free models) but are NOT wired until keys exist — this
module never assumes a key that isn't in .env.

Pure stdlib, no Hermes imports. Unit-testable in isolation.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

GATEWAY_URL = "https://opencode.ai/zen/go/v1"
KEY_ENV = "OPENCODE_GO_API_KEY"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}

# Verified live against the gateway (2026-08-10): 25 models.
# vision = verified working with image input (minimax-m3 tested via chat
# completions with base64 frames). Others may support vision but are unverified.
GATEWAY_MODELS: list[dict] = [
    {"id": "deepseek-v4-flash", "tags": ["fast", "reasoning", "default"], "vision": False},
    {"id": "deepseek-v4-pro", "tags": ["reasoning", "heavy"], "vision": False},
    {"id": "kimi-k3", "tags": ["reasoning", "frontier"], "vision": False},
    {"id": "kimi-k2.7-code", "tags": ["coding", "heavy"], "vision": False},
    {"id": "kimi-k2.6", "tags": ["coding", "fast"], "vision": False},
    {"id": "kimi-k2.5", "tags": ["fast"], "vision": False},
    {"id": "glm-5.2", "tags": ["reasoning", "frontier"], "vision": False},
    {"id": "glm-5.1", "tags": ["reasoning"], "vision": False},
    {"id": "glm-5", "tags": ["reasoning"], "vision": False},
    {"id": "qwen3.8-max", "tags": ["frontier"], "vision": False},
    {"id": "qwen3.7-max", "tags": ["frontier"], "vision": False},
    {"id": "qwen3.7-plus", "tags": ["fast", "coding"], "vision": False},
    {"id": "qwen3.6-plus", "tags": ["fast", "coding"], "vision": False},
    {"id": "qwen3.5-plus", "tags": ["fast", "coding"], "vision": False},
    {"id": "minimax-m3", "tags": ["vision", "reasoning"], "vision": True},
    {"id": "minimax-m2.7", "tags": ["reasoning"], "vision": False},
    {"id": "minimax-m2.5", "tags": ["fast"], "vision": False},
    {"id": "mimo-v2-pro", "tags": ["fast", "coding"], "vision": False},
    {"id": "mimo-v2-omni", "tags": ["fast", "omni"], "vision": False},
    {"id": "mimo-v2.5-pro", "tags": ["fast", "coding"], "vision": False},
    {"id": "mimo-v2.5", "tags": ["fast"], "vision": False},
    {"id": "hy3", "tags": ["reasoning", "frontier"], "vision": False},
    {"id": "hy3-preview", "tags": ["reasoning", "preview"], "vision": False},
    {"id": "gpt-5.6-luna", "tags": ["frontier"], "vision": False},
    {"id": "grok-4.5", "tags": ["frontier", "reasoning"], "vision": False},
]

RECOMMENDED = {
    "default": "deepseek-v4-flash",
    "reasoning": "deepseek-v4-pro",
    "coding": "kimi-k2.7-code",
    "vision": "minimax-m3",
    "fast": "qwen3.7-plus",
}

# Other free channels: status wired|needs-keys. key_env = .env var name.
FREE_CHANNELS = [
    {
        "name": "opencode-zen",
        "status": "wired",
        "base_url": GATEWAY_URL,
        "key_env": KEY_ENV,
        "models": len(GATEWAY_MODELS),
        "note": "OpenCode's own gateway. Verified live 2026-08-10. Requires browser User-Agent header.",
    },
    {
        "name": "nvidia-nim",
        "status": "needs-keys",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "key_env": "NVIDIA_NIM_API_KEY_1..6",
        "models": "~99 catalog / per-account subset",
        "note": "Free keys from build.nvidia.com. Per-account provisioning trap: catalog lists models the key can't call (404). ~40 RPM/key.",
    },
    {
        "name": "google-ai-studio",
        "status": "needs-keys",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "key_env": "GOOGLE_AI_STUDIO_API_KEY_1..6",
        "models": "gemini-3.6-flash, 3.5-flash, 3.5-flash-lite, 3.1-flash-lite",
        "note": "Card-free. Standard API keys retire Sept 2026 (service-account auth). 15 RPM/key.",
    },
    {
        "name": "openrouter",
        "status": "needs-keys",
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "models": "17 :free (verified live 2026-08-10)",
        "note": ":free models need no credit balance. 20 RPM, 50 req/day without credits, 1000 with any balance. No GLM/DeepSeek/Qwen free variants.",
    },
]


def load_key(key_env: str = KEY_ENV) -> str:
    """Read a key from .env by env name. Empty string = not configured."""
    env_path = os.path.expanduser("~/AppData/Local/hermes/.env")
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                m = re.match(rf"\s*{re.escape(key_env)}\s*=\s*\"?([^\"\s]+)", line)
                if m:
                    return m.group(1)
    except OSError:
        return ""
    return ""


def gateway_health(key: str | None = None, timeout: int = 40) -> dict:
    """Live health check of the opencode Zen gateway: real GET /models.

    Requires the browser User-Agent (Cloudflare 1010 block otherwise).
    Returns {ok, http, model_count, models: [ids], error}.
    """
    key = key if key is not None else load_key()
    headers = dict(UA)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(GATEWAY_URL + "/models", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
            ids = [m["id"] for m in data.get("data", [])]
            return {"ok": True, "http": resp.status, "model_count": len(ids), "models": ids, "error": None}
    except urllib.error.HTTPError as e:
        return {"ok": False, "http": e.code, "model_count": 0, "models": [], "error": f"HTTP {e.code}"}
    except Exception as exc:
        return {"ok": False, "http": None, "model_count": 0, "models": [], "error": str(exc)[:120]}


def filter_by_tag(tag: str) -> list[str]:
    return [m["id"] for m in GATEWAY_MODELS if tag in m["tags"]]


def recommend(role: str | None = None) -> str:
    return RECOMMENDED.get(role or "default", RECOMMENDED["default"])


# ---------------------------------------------------------------------------
# Config generation — the SAME free models across every agent in the stack.
# Each agent speaks OpenAI-compatible chat/completions, so one base_url + key
# works everywhere.
# ---------------------------------------------------------------------------

HERMES_PROVIDER_BLOCK = """\
# --- xomni provider-pool: free models (opencode Zen gateway) ---
# Place under `model:` in config.yaml. Primary is the gateway; the fallback
# chain activates automatically when the primary is unavailable.
#   provider: opencode-go
#   model: deepseek-v4-flash
#   base_url: https://opencode.ai/zen/go/v1
#   key_env: OPENCODE_GO_API_KEY
#
# fallback_model:
#   provider: openrouter        # needs OPENROUTER_API_KEY in .env
#   model: nvidia/nemotron-3-ultra-550b-a55b:free
#   base_url: https://openrouter.ai/api/v1
#   key_env: OPENROUTER_API_KEY
"""

AGENT_CONFIGS = {
    "opencode": """\
// opencode.json (OpenCode Go) — same gateway, same free models
{
  "provider": {
    "opencode-zen": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "OpenCode Zen",
      "options": {
        "baseURL": "https://opencode.ai/zen/go/v1",
        "apiKey": "{env:OPENCODE_GO_API_KEY}"
      },
      "models": {
        "deepseek-v4-flash": { "name": "DeepSeek V4 Flash" },
        "kimi-k2.7-code":    { "name": "Kimi K2.7 Code" },
        "minimax-m3":        { "name": "MiniMax M3 (vision)" }
      }
    }
  }
}""",
    "codex": """\
// ~/.codex/config.toml — same gateway
model_provider = "opencode-zen"
model = "deepseek-v4-flash"

[model_providers.opencode-zen]
name = "OpenCode Zen"
base_url = "https://opencode.ai/zen/go/v1"
env_key = "OPENCODE_GO_API_KEY"
wire_api = "chat"   # OpenAI-compatible""",
    "aider": """\
# aider — same gateway
aider --model openai/deepseek-v4-flash \\
      --openai-api-base https://opencode.ai/zen/go/v1 \\
      --openai-api-key $OPENCODE_GO_API_KEY""",
    "goose": """\
# goose (Goosey/CLI) — same gateway via OpenAI-compatible provider
goose configure --provider openai \\
  --model deepseek-v4-flash \\
  --base-url https://opencode.ai/zen/go/v1 \\
  --api-key $OPENCODE_GO_API_KEY""",
}


def agent_config(agent: str) -> str | None:
    return AGENT_CONFIGS.get(agent)


def models_text(tag: str | None = None) -> str:
    """Formatted model list for /models output."""
    ids = filter_by_tag(tag) if tag else [m["id"] for m in GATEWAY_MODELS]
    lines = [f"opencode Zen gateway — {len(GATEWAY_MODELS)} free models ({GATEWAY_URL})"]
    lines.append(f"  recommended: default={recommend('default')} reasoning={recommend('reasoning')} "
                 f"coding={recommend('coding')} vision={recommend('vision')} fast={recommend('fast')}")
    for m in GATEWAY_MODELS:
        if m["id"] in ids:
            vis = " [VISION-verified]" if m["vision"] else ""
            lines.append(f"  {m['id']:<22} {', '.join(m['tags'])}{vis}")
    return "\n".join(lines)


def channels_text() -> str:
    lines = ["free-model channels:"]
    for ch in FREE_CHANNELS:
        lines.append(
            f"  {ch['name']:<18} {ch['status']:<12} {ch['models']:<28} key: {ch['key_env']}"
        )
        lines.append(f"      {ch['note']}")
    return "\n".join(lines)
