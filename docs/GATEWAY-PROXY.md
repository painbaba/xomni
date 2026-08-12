# GATEWAY PROXY — OpenAI-compatible localhost API for XOMNI

XOMNI speaks chat natively, but most apps speak **OpenAI**. The gateway proxy
is a thin localhost HTTP server that speaks the OpenAI wire format
(`/v1/chat/completions`, `/v1/models`) and translates every request into a
XOMNI routing decision — so **any** OpenAI-compatible client (VS Code
extensions, Excel/Power Automate, WhatsApp Business API bots, Cursor,
Continue, custom Python/curl scripts) can drive XOMNI without knowing XOMNI
exists.

One port, zero cloud: the proxy binds `127.0.0.1` only, so nothing leaves
your machine unless you point it somewhere else.

## Architecture

```
┌─────────────┐   OpenAI /v1/*   ┌──────────────────────┐   route()   ┌───────────────────────┐
│ Any client  │ ───────────────▶ │  gateway proxy        │ ──────────▶ │ plugins/model-router   │
│ VS Code /   │ ◀─────────────── │  127.0.0.1:<port>     │ ◀────────── │  core.py               │
│ Excel / bot │   SSE / JSON     │  (FastAPI-style)      │   model +   │  detect_task_type()    │
└─────────────┘                  └──────────────────────┘   provider  │  route()               │
                                                                    └───────────┬───────────┘
                                                                                │ registry + pool
                                                                    ┌───────────▼───────────┐
                                                                    │ plugins/provider-pool  │
                                                                    │  core.py                │
                                                                    │  (gateway_health,       │
                                                                    │   filter_by_tag,        │
                                                                    │   recommend)            │
                                                                    └────────────────────────┘
```

The proxy has **no routing logic of its own**. For every incoming chat
request it calls `route()` from `plugins/model-router/core.py` — the same
code path XOMNI's own chat uses:

1. `detect_task_type(prompt)` classifies the prompt
   (`vision > reasoning > heavy > quick > default` precedence).
2. `route(task_hint, registry)` picks the best model for that task type over
   the real omni-registry, enriched by provider-pool tags
   (`plugins/provider-pool/core.py`), and falls back to the
   `FALLBACK_MODELS` tier table when the registry is unavailable.
3. The chosen model id is remapped to the requested OpenAI model name (see
   Config), and the provider base URL + key come from the pool's
   `load_key()` / provider catalog.

## Config

All settings live in XOMNI's `config.yaml` under a `gateway_proxy:` block
(proxy code in `plugins/gateway-proxy/`, config keys in the same file):

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `false` | start the proxy with the host |
| `host` | `127.0.0.1` | bind address — keep this, see Security |
| `port` | `8787` | local port (any free port works) |
| `api_key` | *(empty)* | optional bearer token; empty = no auth (localhost only) |
| `model_map.fast` | `gpt-4o-mini` | OpenAI name clients may send for quick/default tasks |
| `model_map.reasoning` | `gpt-4o` | OpenAI name clients may send for reasoning/heavy tasks |
| `model_map.vision` | `gpt-4o` | OpenAI name clients may send for vision tasks |
| `cors` | `false` | CORS headers off — browser clients are not the target |

**Model mapping rules** — clients send *any* OpenAI-style model name
(`gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, ...). The proxy never passes that name
to a provider; it maps it to a **task type**, then lets the router pick the
real XOMNI model:

- name contains `mini` / `flash` / `small` → `quick`
- name contains `reason` / `o1` / `o3` / `thinking` → `reasoning`
- anything else → `default` (router auto-detects vision from the prompt
  when image input is present)

`/v1/models` returns the three mapped names plus the router's current
recommended model per task type.

## Request / response mapping

| OpenAI field (request) | XOMNI mapping |
|---|---|
| `model` | mapped to task type (`fast`/`reasoning`/`vision`), then `route()` picks the real model |
| `messages` | concatenated into one prompt (system + user + assistant turns joined), passed to `detect_task_type()` |
| `messages[].content` (string) | prompt text |
| `messages[].content` (array with `image_url`) | vision task — image bytes forwarded to the routed vision model |
| `stream: true` | SSE chunked responses (`data: {...}` + `[DONE]`) |
| `temperature` / `max_tokens` | mapped to provider call params when the routed provider supports them, else ignored |
| `stop` / `top_p` | ignored (router controls generation) |
| `user` / `seed` / `tools` / `tool_choices` | ignored — XOMNI routing is prompt-driven; tool calls not exposed |

| OpenAI field (response) | Value |
|---|---|
| `id` | `chatcmpl-<uuid>` |
| `object` | `chat.completion` (or `chat.completion.chunk` when streaming) |
| `created` | unix timestamp |
| `model` | the OpenAI name the client sent |
| `choices[0].message.content` | router's `route_text(res)` output |
| `choices[0].finish_reason` | `stop` |
| `usage` | token counts from the provider response (0s if unknown) |

## Usage — curl

**1. Chat completion**

```bash
curl -s http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Summarize this: XOMNI routes fast."}]
  }'
```

**2. List models**

```bash
curl -s http://127.0.0.1:8787/v1/models
```

**3. Streaming (SSE)**

```bash
curl -N -s http://127.0.0.1:8787/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "stream": true,
    "messages": [{"role": "user", "content": "Explain routing in one line."}]
  }'
```

With a token configured, add `-H "Authorization: Bearer <token>"` to every
request.

## Getting started

1. **Enable + configure** — in `config.yaml` set `gateway_proxy.enabled: true`
   (and `port` / `api_key` if you want them), then start the host:
   `xomni launch` (entry in `xomni_cli/__init__.py`).
2. **Verify** — `curl http://127.0.0.1:8787/v1/models` returns the mapped
   model list; then run the chat completion example above.
3. **Point your app at it** — set the app's OpenAI base URL to
   `http://127.0.0.1:8787/v1` (and key to the configured token, if any):
   - VS Code (Continue / Cline): base URL `http://127.0.0.1:8787/v1`
   - Excel / Power Automate: HTTP action against the same URL
   - WhatsApp bot / custom client: any OpenAI SDK with `base_url` override

## Security

- **Localhost-only bind** — the default `127.0.0.1` is mandatory: the proxy
  is never reachable from the LAN or the internet. Do not set `host: 0.0.0.0`.
- **No cloud exposure** — no tunnel, no public URL, no telemetry; traffic
  stays inside the process pair on your machine.
- **Optional bearer token** — set `api_key` to require
  `Authorization: Bearer <token>`; without it the endpoint is open to any
  local process (fine for a single-user dev box, not for shared machines).
- **CORS off by default** — browser-based clients are not a supported target;
  keep `cors: false` unless you deliberately proxy through a same-origin
  layer.
- **Prompt-only surface** — the proxy exposes chat and model listing only;
  no file access, no tool calls, no admin endpoints.

## Implementation

The M1 implementation lives in `plugins/gateway-proxy/` (stdlib only,
zero hooks): `core.py` exposes `build_handler(backend)` (returns a
`BaseHTTPRequestHandler` subclass), `start_server(port, backend,
host='127.0.0.1')` (returns `(server, thread)`; port `0` = ephemeral for
tests), and the pure function `route_openai(payload, backend)`. The default
`RouterBackend` lazily imports `plugins/model-router/core.py` `route()` via
`sys.path` insertion (fallback: static `FALLBACK_MODELS` tier table and
model list `['xomni-quick', 'xomni-reasoning', 'xomni-vision']`). Error
paths are fail-loud OpenAI-style envelopes: `stream: true` → 400, malformed
JSON → 400, unknown path → 404, backend failure → 502. Run the tests with
`python -m unittest tests.test_core -q` from the plugin dir.

```bash
cd plugins/gateway-proxy && python -c "from core import start_server, RouterBackend; s,t=start_server(8787, RouterBackend()); print('gateway on', s.server_address)" &
curl -s http://127.0.0.1:8787/v1/models
curl -s http://127.0.0.1:8787/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hello"}]}'
```
