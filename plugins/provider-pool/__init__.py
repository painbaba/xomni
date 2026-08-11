"""Provider pool — Hermes plugin wiring.

Commands: /models (live gateway status + model list), /provider (per-agent
config snippets so the same free models work across the whole stack).
No hooks — this module is read-only and never alters agent behavior.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/models                live status + free model list (opencode Zen gateway)\n"
    "/models <tag>          filter by tag: fast | reasoning | coding | vision | frontier\n"
    "/provider              show config snippets for Hermes/OpenCode/Codex/Aider/Goose\n"
    "/provider <agent>      show one agent's snippet"
)


def _handle_models(raw: str) -> str:
    tag = (raw or "").strip().lower()
    health = core.gateway_health()
    head = f"gateway: {'LIVE ✓' if health['ok'] else 'DOWN ✗'} (HTTP {health['http'] or '—'}"
    if health.get("error"):
        head += f", {health['error']}"
    head += f") — catalog says {health['model_count']} models, registry has {len(core.GATEWAY_MODELS)}"
    if not health["ok"] and not health["models"]:
        return head + "\n" + core.models_text(tag) if tag else head + "\n" + core.models_text()
    return head + "\n" + core.models_text(tag if tag in ("fast", "reasoning", "coding", "vision", "frontier") else None)


def _handle_provider(raw: str) -> str:
    agent = (raw or "").strip().lower()
    if not agent:
        out = [core.HERMES_PROVIDER_BLOCK, "", "AGENT-SPECIFIC (same gateway, one key):"]
        for name in core.AGENT_CONFIGS:
            out.append("")
            out.append(f"----- {name} -----")
            out.append(core.AGENT_CONFIGS[name])
        return "\n".join(out)
    cfg = core.agent_config(agent)
    if cfg is None:
        return f"unknown agent '{agent}'. Known: {', '.join(core.AGENT_CONFIGS)}"
    return cfg


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "models", handler=_handle_models,
        description="Free-model pool: live gateway status + model list (fast/reasoning/coding/vision)",
        args_hint="[tag]",
    )
    ctx.register_command(
        "provider", handler=_handle_provider,
        description="Provider config snippets: same free models across Hermes/OpenCode/Codex/Aider/Goose",
        args_hint="[agent]",
    )
