#!/usr/bin/env python3
"""
Gemini key-rotation proxy for OpenAI-compatible clients (Nanobrowser, etc.)

Nanobrowser (and other OpenAI-compatible clients) store ONE API key in their
settings. This proxy accepts their requests, rotates through N Gemini keys on
429 (free tier ~10 RPM each), and forwards to Gemini's OpenAI-compatible
endpoint. Clients point their "custom OpenAI-compatible" provider at:

    base_url: http://localhost:8790/v1
    api_key:  anything (ignored — rotation happens here)

Endpoints implemented:
    POST /v1/chat/completions   (models + streaming + non-streaming)
    GET  /v1/models             (returns gemini models, rewritten ids)

Env:
    GOOGLE_AI_STUDIO_API_KEY_1..N   (or GOOGLE_API_KEY / GEMINI_API_KEY)
    GEMINI_PROXY_PORT               default 8790
    GEMINI_BROWSER_MODEL            default gemini-3.6-flash (fallback when
                                    client sends a model we don't map)
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("GEMINI_PROXY_PORT", "8790"))
# Gemini's OpenAI-compatible endpoint
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = os.environ.get("GEMINI_BROWSER_MODEL", "gemini-3.6-flash")

# Map common OpenAI model names to our Gemini default (clients hardcode
# gpt-4o / gpt-4o-mini etc. — we just run Gemini underneath).
MODEL_MAP = {
    "gpt-4o": DEFAULT_MODEL,
    "gpt-4o-mini": DEFAULT_MODEL,
    "gpt-4": DEFAULT_MODEL,
    "gpt-4-turbo": DEFAULT_MODEL,
    "gpt-3.5-turbo": DEFAULT_MODEL,
    "o1": DEFAULT_MODEL,
    "o3": DEFAULT_MODEL,
    "o4-mini": DEFAULT_MODEL,
    "claude-3-5-sonnet-20241022": DEFAULT_MODEL,
    "claude-sonnet-4-20250514": DEFAULT_MODEL,
}


def _all_keys() -> list[str]:
    keys: list[str] = []
    i = 1
    while True:
        k = os.environ.get(f"GOOGLE_AI_STUDIO_API_KEY_{i}") or os.environ.get(f"GEMINI_API_KEY_{i}")
        if not k:
            break
        keys.append(k)
        i += 1
    if not keys:
        for env in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY"):
            if os.environ.get(env):
                keys.append(os.environ[env])
    if not keys:
        sys.exit("No Gemini keys found. Set GOOGLE_AI_STUDIO_API_KEY_1..N (or GOOGLE_API_KEY).")
    return keys


_KEYS = _all_keys()
_lock = threading.Lock()
_key_idx = 0
_key_cooldown_until: dict[int, float] = {}  # key index -> epoch until which it's paused
_calls: dict[int, int] = {}  # rolling count for logging


def _next_key() -> str:
    """Round-robin, skipping keys in cooldown."""
    global _key_idx
    with _lock:
        now = time.time()
        for _ in range(len(_KEYS)):
            idx = _key_idx
            _key_idx = (_key_idx + 1) % len(_KEYS)
            if _key_cooldown_until.get(idx, 0) <= now:
                _calls[idx] = _calls.get(idx, 0) + 1
                return _KEYS[idx]
        # all in cooldown: take the one with the earliest expiry
        idx = min(_key_cooldown_until, key=lambda i: _key_cooldown_until[i])
        return _KEYS[idx]


def _mark_429(idx: int) -> None:
    with _lock:
        _key_cooldown_until[idx] = time.time() + 60
        print(f"  [proxy] key #{idx + 1} hit 429, cooling down 60s", file=sys.stderr)


def forward_chat(body: dict) -> tuple[int, dict, dict]:
    """Forward a chat/completions request. Returns (status, json_body, headers)."""
    # Normalize: some clients send "model" as a list or nested; pick our model
    body = dict(body)
    req_model = body.get("model")
    if isinstance(req_model, list):
        req_model = req_model[0] if req_model else DEFAULT_MODEL
    model = MODEL_MAP.get(str(req_model), str(req_model or DEFAULT_MODEL))
    # If client sent an unknown non-gemini name, force our default
    if not str(model).startswith("gemini"):
        model = DEFAULT_MODEL
    body["model"] = model

    stream = bool(body.get("stream", False))
    payload = json.dumps(body).encode()
    last_err = None
    for attempt in range(len(_KEYS) * 2):
        key = _next_key()
        url = f"{GEMINI_BASE}/chat/completions"
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json",
                                              "Authorization": f"Bearer {key}"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "application/json")
                if stream:
                    # stream back raw SSE
                    return 200, None, {"stream": data, "content_type": ctype}
                return resp.status, json.loads(data), {"content_type": ctype}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode(errors="replace")[:500]
            if e.code == 429:
                last_err = f"429: {err_body[:150]}"
                print(f"  [proxy] 429 on key, rotating", file=sys.stderr)
                _mark_429(_key_idx)
                continue
            # 400 with a model-not-found message -> retry with default model
            if e.code == 400 and "model" in err_body.lower():
                body["model"] = DEFAULT_MODEL
                payload = json.dumps(body).encode()
                last_err = f"400 model: {err_body[:150]}"
                continue
            return e.code, {"error": {"message": err_body}}, {"content_type": "application/json"}
        except Exception as e:
            last_err = str(e)
            continue
    return 502, {"error": {"message": f"All keys failed: {last_err}"}}, {"content_type": "application/json"}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter
        pass

    def _send(self, status: int, body: dict, ctype: str = "application/json") -> None:
        data = json.dumps(body).encode()
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
            # Client disconnected mid-response (cancel/refresh/timeout). Normal —
            # don't spam the log with tracebacks.
            pass

    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models" or self.path.rstrip("/").endswith("/models"):
            models = [{
                "id": DEFAULT_MODEL,
                "object": "model",
                "owned_by": "gemini-proxy",
            }]
            self._send(200, {"object": "list", "data": models})
        elif self.path == "/health" or self.path == "/":
            self._send(200, {"ok": True, "engine": "gemini-rotation-proxy",
                             "keys": len(_KEYS), "model": DEFAULT_MODEL})
        else:
            self._send(404, {"error": {"message": f"not found: {self.path}"}})

    def do_POST(self):
        if "/chat/completions" not in self.path:
            self._send(404, {"error": {"message": f"not found: {self.path}"}})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception as e:
            self._send(400, {"error": {"message": f"bad json: {e}"}})
            return
        status, result, extra = forward_chat(body)
        if extra.get("stream"):
            # raw SSE passthrough
            try:
                self.send_response(200)
                self.send_header("Content-Type", extra["content_type"])
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(extra["stream"])
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError, OSError):
                pass  # client disconnected mid-stream — normal
            return
        self._send(status, result, extra.get("content_type", "application/json"))


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[proxy] Gemini rotation proxy on http://127.0.0.1:{PORT} "
          f"({len(_KEYS)} keys, model {DEFAULT_MODEL})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
