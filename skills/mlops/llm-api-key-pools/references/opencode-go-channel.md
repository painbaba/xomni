# OpenCode Go API channel (verified 2026-08-08)

OpenAI-compatible chat_completions endpoint for deepseek-v4-flash. This is the
provider Hermes itself runs on (the "opencode-go" provider), so it is a durable,
near-free channel — the user explicitly wants it used for swarm workloads
("use ur own api the opencode go").

## Endpoint & config
- base_url: `https://opencode.ai/zen/go/v1` (api_mode: chat_completions)
- model: `deepseek-v4-flash`
- Hermes config: `C:\Users\HP\AppData\Local\hermes\config.yaml` provider block
  (alias: `opengo` = `custom/deepseek-v4-flash`)

## Keys
- In `C:\Users\HP\AppData\Local\hermes\.env`: `OPENGO_API_KEY`,
  `OPENCODE_GO_API_KEY`, `CUSTOM_API_KEY` — all present, same value, len 67.
  Any of the three works interchangeably.

## Cloudflare requirement (the critical quirk)
- Raw urllib/curl request WITHOUT a browser User-Agent -> HTTP 403,
  body `{"error":"error code: 1010"}` (Cloudflare browser-signature block).
  Looks like a key/auth failure — it is NOT.
- Fix: send ANY browser-like User-Agent header. Verified: Chrome UA returned 200;
  even `curl/8.5.0` as UA returned 200 — the PRESENCE of a UA header is what
  matters, not the exact string.
- Standard `Authorization: Bearer <key>` + `Content-Type: application/json`.

## Verified probe snippet (Python, reads key from .env itself)
```python
import json, urllib.request, urllib.error
ENV = r"C:\Users\HP\AppData\Local\hermes\.env"
env = {}
for line in open(ENV, encoding="utf-8", errors="ignore"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip()
key = env.get("OPENCODE_GO_API_KEY") or env.get("OPENGO_API_KEY")
req = urllib.request.Request(
    "https://opencode.ai/zen/go/v1/chat/completions",
    data=json.dumps({"model": "deepseek-v4-flash",
                     "messages": [{"role": "user", "content": "Reply: OK"}],
                     "max_tokens": 10}).encode(),
    headers={"Content-Type": "application/json",
             "Authorization": f"Bearer {key}",
             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
with urllib.request.urlopen(req, timeout=30) as r:
    print(r.status, r.read(300).decode("utf-8", "ignore"))
```

## Sibling channel status snapshot (2026-08-08, swarm_probe.py run)
- Gemini: 6/6 keys HTTP 200 on `gemini-3.1-flash-lite` — the swarm workhorse
  (free ~15 RPM/key).
- NIM: `openai/gpt-oss-120b` POSTs timed out (HTTP 0) at 20s on all 3 probed
  keys — congested at peak hours, night-shift only.
- ZAI: `glm-4.7-flash` -> HTTP 429 on zai1 (rate-limited; the "free GLM Flash"
  claim needs re-verification each time).
- webui-pool bridge :8791: not running this session.
- OpenRouter: no `OPENROUTER_API_KEY` value in .env.

## Swarm budget math (300-agent plan)
6 Gemini keys x ~15 RPM = ~90 calls/min + 2 OpenCode Go keys -> 300 parallel
research agents in ~5-10 min wall clock. NIM reserved for night shift.
