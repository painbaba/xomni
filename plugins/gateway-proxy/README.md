# gateway-proxy

OpenAI-compatible localhost gateway for XOMNI. Speaks the OpenAI wire
format (`/v1/chat/completions`, `/v1/models`) and translates every request
into a XOMNI routing decision via `plugins/model-router/core.py`.

- **Zero hooks** — no `register_hook` anywhere.
- **Stdlib only** — `http.server`, `json`, `urllib`, `hashlib`, `threading`.
- **Localhost only** — binds `127.0.0.1` by default; other hosts refused.
- **Fail-loud** — every error path returns an OpenAI-style error envelope.
- **Lazy router import** — `plugins/model-router/core.py` is imported inside
  functions (via `sys.path` insertion), so cold import of this package stays
  fast; a static tier table (`FALLBACK_MODELS`) covers router unavailability.

## API

```python
from core import build_handler, start_server, route_openai, RouterBackend

server, thread = start_server(8787, RouterBackend())  # (server, thread)
# server.server_address[1] holds the bound port when port=0
```

- `build_handler(backend)` → `BaseHTTPRequestHandler` subclass.
- `start_server(port, backend, host='127.0.0.1')` → `(server, thread)`.
- `route_openai(payload, backend)` → pure function, OpenAI response dict.
- `RouterBackend` → default backend: lazy model-router import, static
  `FALLBACK_MODELS` tier table fallback, static model-list fallback
  `['xomni-quick', 'xomni-reasoning', 'xomni-vision']`.

## Endpoints

| Endpoint | Method | Behavior |
|---|---|---|
| `/v1/models` | GET | `{'object':'list','data':[{'id':...}]}` via `backend.model_list()` |
| `/v1/chat/completions` | POST | OpenAI payload → `backend.route(prompt)` → OpenAI response |
| anything else | – | 404 with OpenAI error envelope |

`stream: true` → 400 (unsupported). Malformed JSON → 400. Backend failure → 502.

## Tests

```bash
cd plugins/gateway-proxy
python -m unittest tests.test_core -q
```

See `docs/GATEWAY-PROXY.md` for the full design.
