"""offline-kit — offline-first readiness kit for the local XOMNI stack.

Probes the local Ollama stack (chat + embeddings) and local search, then
produces an offline-ready report and a model plan. Pure stdlib, no Hermes
imports, ZERO HOOKS — this plugin never calls ``register_hook`` and never
alters agent behavior; ``probe()`` is diagnostic and never raises on network
failure.

Commands/tools (registered via the standard ``register(ctx)`` contract):
    /offline status   probe the local stack, print the offline-ready report
    /offline plan     probe, print the model plan (chat + embeddings)
    tool offline_kit  {action: status|plan} — same, model-callable
"""
from __future__ import annotations

try:
    from . import core
except ImportError:  # standalone import (tests run from the plugin dir)
    import core  # type: ignore

# Public API (re-exported for convenience).
probe = core.probe
build_offline_stack = core.build_offline_stack
offline_prompt_for = core.offline_prompt_for
smoke_prompt = core.smoke_prompt
render_markdown = core.render_markdown

BASE_URL = core.BASE_URL
EMBED_HINTS = core.EMBED_HINTS
CHAT_PREFERRED = core.CHAT_PREFERRED

HELP = (
    "/offline status      probe the local stack and print the offline-ready report\n"
    "/offline plan        probe and print the model plan (chat + embeddings)\n"
)


def _status_text() -> str:
    return core.render_markdown(core.probe())


def _plan_text() -> str:
    plan = core.build_offline_stack(core.probe())
    lines = [
        f"provider: {plan['provider']}",
        f"base_url: {plan['base_url']}",
        f"chat_model: {plan['chat_model'] or '(none — run /ollama pull qwen2.5:3b)'}",
        f"embeddings_model: {plan['embeddings_model'] or '(none — need an embed-capable model)'}",
        f"search: {plan['search']}",
        f"offline_ready: {plan['offline_ready']}",
    ]
    return "\n".join(lines)


def _handle_offline(raw: str) -> str:
    cmd = (raw or "").strip().lower()
    if cmd in ("plan", "stack"):
        return _plan_text()
    if cmd in ("status", "report", "", "?"):
        return _status_text()
    return HELP


def _offline_tool(params: dict) -> str:
    action = str((params or {}).get("action") or "status").strip().lower()
    return _plan_text() if action == "plan" else _status_text()


def register(ctx) -> None:
    """Standard command/tool registration. Zero hooks — no register_hook."""
    ctx.register_command(
        "offline",
        handler=_handle_offline,
        description=(
            "Offline-first readiness: probe the local Ollama stack (chat + "
            "embeddings) and fts5 local search, print the offline-ready "
            "report (status) or model plan (plan)"
        ),
        args_hint="[status|plan]",
    )
    ctx.register_tool(
        "offline_kit",
        toolset="local",
        schema={
            "description": (
                "Probe the local offline stack (Ollama chat + embeddings, "
                "fts5 local search) and report offline readiness. "
                "action=status prints the report; action=plan prints the "
                "model plan. Pure local, never raises."
            ),
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "plan"],
                    "description": "status: offline-ready report; plan: model plan (chat + embeddings)",
                }
            },
            "required": ["action"],
        },
        handler=_offline_tool,
        description="Probe the local offline stack (Ollama chat + embeddings, fts5 search)",
        emoji="📴",
    )
