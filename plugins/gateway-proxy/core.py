"""OpenAI-compatible gateway proxy core (stdlib only).

Speaks the OpenAI wire format on a localhost HTTP server and translates
every request into a XOMNI routing decision via plugins/model-router.

Zero hooks. Pure stdlib: http.server, json, urllib, hashlib, threading.

Public API:
  build_handler(backend)         -> BaseHTTPRequestHandler subclass
  start_server(port, backend, host='127.0.0.1') -> (server, thread)
  route_openai(payload, backend) -> OpenAI response dict (pure function)
  RouterBackend                  -> default backend (lazy model-router import)
  GatewayError                   -> raised by route_openai on client errors
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import uuid

# ---------------------------------------------------------------------------
# Static tier table used when the model router cannot be loaded.
# ---------------------------------------------------------------------------
FALLBACK_MODELS = [
    {"id": "quick", "tier": "quick"},
    {"id": "reasoning", "tier": "reasoning"},
    {"id": "vision", "tier": "vision"},
]

MODEL_LIST_FALLBACK = ["xomni-quick", "xomni-reasoning", "xomni-vision"]

_PLUGINS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class GatewayError(Exception):
    """Client-facing error carrying the HTTP status and OpenAI error type."""

    def __init__(self, status: int, message: str, error_type: str = "invalid_request_error"):
        super().__init__(message)
        self.status = status
        self.message = message
        self.error_type = error_type

    def envelope(self) -> dict:
        return {"error": {"message": self.message, "type": self.error_type}}


# ---------------------------------------------------------------------------
# Pure mapping / routing helpers (no I/O, no server state).
# ---------------------------------------------------------------------------

def map_model_name(model: str) -> str:
    """Map an OpenAI-style model name to a XOMNI task tier.

    mini/flash/small -> quick; reason/o1/o3/thinking -> reasoning;
    vision -> vision; anything else -> default (router auto-detects).
    """
    name = (model or "").lower()
    if any(k in name for k in ("reason", "o1", "o3", "thinking")):
        return "reasoning"
    if "vision" in name:
        return "vision"
    if any(k in name for k in ("mini", "flash", "small")):
        return "quick"
    return "default"


def messages_to_prompt(messages) -> str:
    """Concatenate chat messages (string or list content) into one prompt."""
    if not isinstance(messages, list) or not messages:
        raise GatewayError(400, "payload must include a non-empty 'messages' list")
    parts = []
    for msg in messages:
        if not isinstance(msg, dict):
            raise GatewayError(400, "each message must be an object with role/content")
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for chunk in content:
                if isinstance(chunk, dict) and isinstance(chunk.get("text"), str):
                    parts.append(chunk["text"])
                elif isinstance(chunk, dict) and chunk.get("type") == "image_url":
                    parts.append("[image]")
        else:
            raise GatewayError(400, "message content must be a string or a list")
    if not any(parts):
        raise GatewayError(400, "messages must contain some text content")
    return "\n".join(parts)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _completion_id(payload: dict) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return "chatcmpl-%s%s" % (digest[:12], uuid.uuid4().hex[:12])


def route_openai(payload: dict, backend) -> dict:
    """Translate an OpenAI chat completion payload into an OpenAI response.

    Pure function: no sockets, no I/O. Raises GatewayError on client errors
    (streaming unsupported, malformed payload) and on backend failure (502).
    """
    if not isinstance(payload, dict):
        raise GatewayError(400, "request body must be a JSON object")
    if payload.get("stream"):
        raise GatewayError(
            400,
            "streaming is not supported by the XOMNI gateway proxy "
            "(stream: true); send a non-streaming request",
        )
    model = payload.get("model") or "gpt-4o-mini"
    prompt = messages_to_prompt(payload.get("messages"))

    try:
        routed = backend.route(prompt)
    except GatewayError:
        raise
    except Exception as exc:  # fail-loud: surface backend failures as 502
        raise GatewayError(
            502,
            "backend routing failed: %s: %s" % (type(exc).__name__, exc),
            error_type="server_error",
        ) from exc

    if not isinstance(routed, dict):
        raise GatewayError(
            502,
            "backend route() must return a dict, got %r" % type(routed).__name__,
            error_type="server_error",
        )
    reply = routed.get("reply", "")
    if not isinstance(reply, str):
        reply = str(reply)

    return {
        "id": _completion_id(payload),
        "object": "chat.completion",
        "created": _now(),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": _estimate_tokens(prompt),
            "completion_tokens": _estimate_tokens(reply),
            "total_tokens": _estimate_tokens(prompt) + _estimate_tokens(reply),
        },
    }


def _now() -> int:
    import time

    return int(time.time())


def _models_response(model_ids) -> dict:
    return {
        "object": "list",
        "data": [{"id": mid, "object": "model", "owned_by": "xomni"} for mid in model_ids],
    }


# ---------------------------------------------------------------------------
# Default backend: lazily imports plugins/model-router/core.py route().
# ---------------------------------------------------------------------------

def _load_router():
    """Import plugins/model-router/core.py lazily. Returns module or None."""
    try:
        if _PLUGINS_DIR not in sys.path:
            sys.path.insert(0, _PLUGINS_DIR)
        import model_router_core  # type: ignore
    except Exception:
        try:
            import importlib

            spec = importlib.util.spec_from_file_location(
                "model_router_core", os.path.join(_PLUGINS_DIR, "model-router", "core.py")
            )
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception:
            return None
    else:
        return model_router_core


class RouterBackend:
    """Default gateway backend backed by plugins/model-router/core.py route().

    The router import happens lazily inside route()/model_list(); if it
    cannot be loaded, a deterministic static tier table is used instead.
    """

    def __init__(self):
        self._router = None
        self._router_attempted = False

    def _router_or_none(self):
        if not self._router_attempted:
            self._router = _load_router()
            self._router_attempted = True
        return self._router

    def route(self, prompt: str) -> dict:
        """Route a prompt -> {'model', 'provider', 'reply'}."""
        router = self._router_or_none()
        if router is not None:
            try:
                res = router.route(prompt, None)
                return {
                    "model": res.get("model", "xomni-default"),
                    "provider": res.get("provider", "xomni"),
                    "reply": router.route_text(res),
                }
            except Exception as exc:
                # Fail-loud: fall through to the static table, but say so.
                return self._fallback_route(prompt, reason="router error: %r" % (exc,))
        return self._fallback_route(prompt, reason="model-router unavailable")

    def _fallback_route(self, prompt: str, reason: str) -> dict:
        tier = _tier_for_prompt(prompt)
        entry = next((m for m in FALLBACK_MODELS if m["tier"] == tier), FALLBACK_MODELS[0])
        return {
            "model": entry["id"],
            "provider": "xomni-fallback",
            "reply": (
                "[xomni gateway] routed to %r (%s tier) via static fallback table "
                "(%s)" % (entry["id"], entry["tier"], reason)
            ),
        }

    def model_list(self) -> list:
        """Return the /v1/models id list (router-enriched, else static)."""
        router = self._router_or_none()
        if router is not None:
            try:
                ids = []
                for tier in ("quick", "reasoning", "vision"):
                    res = router.route("recommend %s model" % tier, None)
                    ids.append(res.get("model", "xomni-%s" % tier))
                return ids
            except Exception:
                pass
        return list(MODEL_LIST_FALLBACK)


def _tier_for_prompt(prompt: str) -> str:
    low = prompt.lower()
    if any(k in low for k in ("image", "photo", "picture", "vision", "screenshot")):
        return "vision"
    if any(k in low for k in ("why", "think", "reason", "explain", "derive")):
        return "reasoning"
    if len(low) < 120:
        return "quick"
    return "default"


# ---------------------------------------------------------------------------
# HTTP server.
# ---------------------------------------------------------------------------

def build_handler(backend):
    """Return a BaseHTTPRequestHandler subclass bound to the given backend."""
    from http.server import BaseHTTPRequestHandler  # lazy: heavy stdlib module

    class GatewayHandler(BaseHTTPRequestHandler):
        # backend is attached below (class bodies don't close over locals)
        backend = None

        # Silence per-request stderr logging.
        def log_message(self, fmt, *args):
            pass

        def _send(self, status: int, body: dict):
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_error_envelope(self, err: GatewayError):
            self._send(err.status, err.envelope())

        def do_GET(self):
            if self.path == "/v1/models":
                try:
                    ids = self.backend.model_list()
                    self._send(200, _models_response(ids))
                except Exception as exc:
                    self._send_error_envelope(
                        GatewayError(502, "model list failed: %r" % (exc,), "server_error")
                    )
                return
            self._send_error_envelope(
                GatewayError(404, "unknown path %r; try GET /v1/models or POST /v1/chat/completions" % self.path)
            )

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                self._send_error_envelope(
                    GatewayError(404, "unknown path %r; try POST /v1/chat/completions" % self.path)
                )
                return
            try:
                length = int(self.headers.get("Content-Length", "0") or 0)
                raw = self.rfile.read(length) if length else b""
                if not raw.strip():
                    raise ValueError("empty request body")
                payload = json.loads(raw.decode("utf-8"))
            except Exception as exc:
                self._send_error_envelope(
                    GatewayError(
                        400,
                        "malformed JSON body: %s: %s" % (type(exc).__name__, exc),
                    )
                )
                return
            try:
                response = route_openai(payload, self.backend)
            except GatewayError as err:
                self._send_error_envelope(err)
                return
            except Exception as exc:  # fail-loud: never swallow
                self._send_error_envelope(
                    GatewayError(502, "internal gateway error: %r" % (exc,), "server_error")
                )
                return
            self._send(200, response)

        def do_OPTIONS(self):  # pragma: no cover - CORS off by default
            self._send_error_envelope(GatewayError(404, "CORS is disabled"))

    GatewayHandler.backend = backend
    return GatewayHandler


def start_server(port: int, backend, host: str = "127.0.0.1"):
    """Start the gateway on 127.0.0.1 (localhost only). Returns (server, thread).

    Pass port=0 for an ephemeral port (tests). The thread is a daemon; call
    server.shutdown() + server.server_close() to stop.
    """
    if host != "127.0.0.1":
        raise GatewayError(500, "gateway binds 127.0.0.1 ONLY; refusing host %r" % host, "server_error")
    from http.server import ThreadingHTTPServer  # lazy: heavy stdlib module

    handler = build_handler(backend)
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    thread = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.05),
        name="gateway-proxy",
        daemon=True,
    )
    thread.start()
    return server, thread
