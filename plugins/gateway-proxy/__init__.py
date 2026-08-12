# gateway-proxy — OpenAI-compatible localhost gateway for XOMNI.
#
# Zero-hook plugin: no register_hook anywhere. `register(ctx)` only exposes
# the start_server helper as a command (optional). All heavy work (model
# router import) happens lazily inside functions so cold import stays fast.

from .core import (
    FALLBACK_MODELS,
    GatewayError,
    RouterBackend,
    build_handler,
    route_openai,
    start_server,
)

__all__ = [
    "FALLBACK_MODELS",
    "GatewayError",
    "RouterBackend",
    "build_handler",
    "route_openai",
    "start_server",
]
__version__ = "0.1.0"
