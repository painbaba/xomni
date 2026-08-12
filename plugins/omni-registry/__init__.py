"""omni-registry — capability-declared model registry (Hermes plugin wiring).

Commands: /models2 (registry view: ctx/tools/think/vision/video per model with
per-field source tags), tool: registry_status (summary or single-model lookup
with provenance).

No hooks — advisory metadata only, zero Hermes imports in core, zero network.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/models2                 capability registry: ctx/tools/think/vision/video per model + source tags\n"
    "/models2 <capability>    filter rows: image_in | video_in | thinking | always_thinking | tools | structured_output\n"
)


def _handle_models2(raw: str) -> str:
    cap = (raw or "").strip().lower()
    try:
        return core.capabilities_text(cap_filter=cap or None)
    except ValueError as exc:
        return f"/models2: {exc}"


def _registry_status_tool(params: dict) -> str:
    model = (params.get("model") or "").strip()
    if model:
        return core.model_detail_text(model)
    return core.registry_summary_text()


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "models2",
        handler=_handle_models2,
        description="Capability registry: ctx/tools/think/vision/video per model with per-field source tags",
        args_hint="[capability]",
    )
    ctx.register_tool(
        "registry_status",
        toolset="local",
        schema={
            "description": (
                "Model capability registry status: counts by status, verified "
                "models, capability enum, and internal conflict report. Pass "
                "'model' to get one model's full record with per-field source "
                "attribution (verified|spec|estimated) and origin provenance. "
                "Pure local data — no network."
            ),
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "gateway model slug (e.g. deepseek-v4-flash); omit for summary",
                },
            },
        },
        handler=_registry_status_tool,
        description="Model capability registry status / single-model provenance lookup",
        emoji="📇",
    )
