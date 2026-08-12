"""capability-probe — live-probe ANY provider's /models into the registry.

Commands:
  /probe <provider-id>   probe the provider's /models endpoint (OpenAI or
                         Anthropic shape), merge into the omni-registry
                         capabilities.json with source='live-probe', and show
                         the count + diff vs registry (added/removed/changed).
  /probe all             probe every provider with a key present in the
                         environment and merge each result.

Zero hooks — commands only; core is pure stdlib and never prints an API key.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/probe <provider-id>   live-probe the provider's /models into the registry: count + diff (added/removed/changed)\n"
    "/probe all             probe every provider with a key present in the environment\n"
)


def _handle_probe(raw: str) -> str:
    arg = (raw or "").strip()
    if arg.lower() in ("all", "*", "-a"):
        return core.probe_all_command_text()
    return core.probe_command_text(arg)


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "probe",
        handler=_handle_probe,
        description=(
            "Live-probe a provider's /models endpoint into the model registry: "
            "model count + diff vs registry (added/removed/changed), merged with "
            "source=live-probe. 'all' probes every provider with a key present. "
            "API keys are never printed."
        ),
        args_hint="<provider-id> | all",
    )
