---
name: gemini-browser-control
description: "Manus-style vision-driven browser control: Camoufox (anti-detect) + Gemini 3.6 flash as eyes, 6-key rotation. Use when sites block DOM automation or a task needs visual reasoning over a page."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [browser, vision, gemini, manus, computer-use, anti-detection, camofox]
---

# Gemini Browser Control (Manus-style)

Replicates Manus-class browser control without the proprietary extension:
**screenshot → Gemini vision decides → execute action → repeat**, on top of the
Camoufox anti-detection engine. Bypasses sites that block DOM/accessibility
automation (Cloudflare, JS-heavy SPAs, canvas UIs) because the model reads
pixels, not just the DOM tree.

## When to use

- A site 403s / Cloudflare-challenges plain Chromium or `curl` (Camoufox handles it)
- The accessibility snapshot has no usable refs (canvas, custom widgets, iframes)
- A task needs visual judgment: "click the red button", "read the chart", "which option is selected"
- OpenCLI site adapters don't cover the site

## Prerequisites (already set up on this machine)

1. **Camofox server running** on port 9377 (anti-detection Camoufox):
   ```
   cd C:\Users\HP\camofox && npx camofox-browser
   ```
   Health check: `curl http://localhost:9377/health` → `"engine":"camoufox","browserConnected":true`
2. **Gemini keys**: `GOOGLE_AI_STUDIO_API_KEY_1..6` in `AppData\Local\hermes\.env`
   (6 keys pooled; free tier ~10 RPM each; rotation = up to ~60 RPM)
3. Python 3.10+ (hermes venv works)

## Usage

```bash
# One-shot task with a start URL
python scripts/gemini_browser.py "Search for the latest ICSE 2026 physics syllabus PDF and give me the URL" --url https://www.google.com

# Without a start URL (opens about:blank, model navigates)
python scripts/gemini_browser.py "Go to example.com and tell me what's on the page"

# Tune
GEMINI_BROWSER_MAX_STEPS=25 python scripts/gemini_browser.py "task" --url https://...
GEMINI_BROWSER_MODEL=gemini-3.5-flash python scripts/gemini_browser.py "task"
```

Output: prints `ANSWER:` (extract) or `TASK COMPLETE:` (done) on stdout.
Progress/decisions go to stderr so you can `2>/dev/null` for clean answers.

## Gemini rotation proxy (for OpenAI-compatible clients like Nanobrowser)

Nanobrowser / other extensions store ONE API key. To give them 6-key rotation,
run the proxy and point the client's "custom OpenAI-compatible" provider at it:

```bash
# Start (reads GOOGLE_AI_STUDIO_API_KEY_1..6 from env / .env)
python scripts/gemini_rotation_proxy.py        # listens on http://127.0.0.1:8790

# Verify
curl -s http://127.0.0.1:8790/health           # {"keys":6,"model":"gemini-3.6-flash"}
```

Client config (Nanobrowser settings -> add provider -> custom OpenAI-compatible):
- base_url: `http://localhost:8790/v1`
- api_key: anything (rotation happens in the proxy, key is ignored)
- model: any name (proxy maps gpt-4o/claude-* -> gemini-3.6-flash; unknown names also fall back to it)

The proxy implements POST /v1/chat/completions (stream + non-stream) and
GET /v1/models, rotates keys on 429 with 60s cooldown per key, and rewrites
common OpenAI model names to the configured Gemini model.

## How the loop works

1. Open tab in Camoufox via Camofox REST API (`POST /tabs`)
2. Each step: fetch accessibility snapshot + base64 PNG screenshot (`GET /tabs/{id}/snapshot`)
3. Send both to `gemini-3.6-flash` (temperature 0.1) with the task + strict-JSON prompt
4. Model returns one of: `click <ref>` / `type <ref> <text>` / `press <key>` / `scroll` / `navigate` / `extract` / `done`
5. Execute via Camofox API (`POST /tabs/{id}/click|type|press|scroll|navigate`)
6. Repeat until `done`/`extract` or step limit (default 15)

## Key rotation

`_all_keys()` scans `GOOGLE_AI_STUDIO_API_KEY_1..N` then falls back to
`GOOGLE_API_KEY`/`GEMINI_API_KEY`. On HTTP 429 the script rotates to the next
key and pauses 55s for the exhausted key. All keys failing → raises with the
last error. The Hermes model pool (`hermes auth`) ALSO holds the same 6 keys
with auto-rotation for Hermes' own model calls — both paths benefit.

## Pitfalls

- **ALWAYS use responseSchema** (`responseMimeType: application/json` + a JSON
  schema with an `action` enum). Without it, gemini-3.6-flash free-associates
  reasoning text instead of returning strict JSON, the parser falls back, and
  the loop dies. This was the #1 failure mode during bring-up.
- **Token cap**: keep `maxOutputTokens` >= 2048. At 1200 the model hit the cap
  mid-JSON (unterminated string) and every parse failed. Parse failures now
  return action `retry` (fresh snapshot next step) instead of silently stopping.
- **Stale refs**: page re-renders between snapshot and click → the model is
  told to pick the closest current ref; if it still 400s, the script prints the
  error and retries next step (fresh snapshot).
- **Camofox idle shutdown**: the server closes the browser after ~5 min with no
  sessions (`browser idle shutdown`). It relaunches on the next `/tabs` call —
  first call after idle takes ~5-10s longer. Not an error.
- **Health-probe patch**: the installed camofox-browser server.js was patched
  (`viewport: null` in the health probe) to stop the `isMobile` CDP scheme
  crash. **Reinstall the npm package and the patch is lost** — re-apply it or
  browsing restarts every ~3 min. See memory.
- **Model naming**: `gemini-3.6-flash` exists on this account's model list
  (verified). If a 404 surfaces, `curl -s ".../v1beta/models?key=$KEY"` to list
  current names and set `GEMINI_BROWSER_MODEL`.
- **Long pages**: snapshot truncated to 12k chars in the prompt; screenshot is
  the visual ground truth.

## Verification

```bash
# 1. Server up
curl -s http://localhost:9377/health | grep -o '"engine":"camoufox"'
# 2. Key works
curl -s -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key=$KEY" \
  -H "Content-Type: application/json" -d '{"contents":[{"parts":[{"text":"say OK"}]}]}'
# 3. End-to-end: run a task against a bot-protected site
python scripts/gemini_browser.py "What is the main headline?" --url https://bot.sannysoft.com/
```

## Related

- OpenCLI (`opencli <site> <cmd>`) — deterministic adapters for 163 sites, no LLM needed. Use when a site adapter exists.
- Hermes native browser tools — accessibility-tree driven; use for normal sites.
- This skill is the fallback when the above fail or the task needs eyes.
