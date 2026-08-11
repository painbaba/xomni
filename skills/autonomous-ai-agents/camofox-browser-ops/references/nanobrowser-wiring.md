# Nanobrowser wiring (Manus-style Chrome extension)

Nanobrowser (github.com/nanobrowser/nanobrowser, MIT, ~13.5k stars) is the
open-source "Operator/Manus alternative" Chrome extension: multi-agent
(Planner + Navigator), runs fully in the local browser, supports OpenAI,
Anthropic, Gemini, Ollama, Groq, Cerebras, Llama, and **custom OpenAI-compatible
providers**. It stores ONE API key per provider — that's why the Gemini
rotation proxy (gemini-browser-control skill, port 8790) exists: point the
custom provider at the proxy and all 6 keys rotate on 429.

## Install state (this machine)

- Extracted to `C:\Users\HP\nanobrowser\ext` (v0.1.13 release zip)
- Loaded unpacked in Chrome (chrome://extensions → Developer mode → Load unpacked)
- **Extension ID**: `jjmpnipdclgmglamcncnbfgjedadkade`
  (read from `User Data/Default/Secure Preferences` → extensions.settings.<id>.path)

## Known bug in release builds — HMR WebSocket spam

The release zip ships the dev hot-reload client. Chrome console shows:
`WebSocket connection to 'ws://localhost:8081/' failed: ERR_CONNECTION_REFUSED`
(3 copies — the HMR init is duplicated in background.iife.js).

Fix (patched already; re-apply if the extension is re-downloaded):
replace every `new WebSocket(LOCAL_RELOAD_SOCKET_URL)` in background.iife.js
with a no-op stub:
```js
const ws = { onopen: null, addEventListener: () => {}, send: () => {} };
```
Then reload the extension (refresh icon on its chrome://extensions card).

## Storage schema (chrome.storage.local)

Settings stores are created via `xr("<key>", <defaults>, {storageEnum:
Yt.Local})` in `options/assets/index-*.js`. Keys found:

- `"llm-api-keys"` → `{ providers: { <providerId>: <providerConfig> } }`
- `"agent-models"` → `{ agents: { Navigator: {...}, Planner: {...} } }`
- `"speech-to-text-model"` → `{ speechToTextModel: {...} }`
- `"settings"` (general: maxSteps, maxActionsPerStep, maxFailures, useVision...)
- `"firewall-settings"`, `"analytics-settings"`

Provider config (custom OpenAI-compatible), type enum value `"custom_openai"`:
```js
{
  name: "anything",            // custom providers: no spaces in name
  type: "custom_openai",
  baseUrl: "http://localhost:8790/v1",
  apiKey: "anything",          // proxy ignores it; rotation is server-side
  modelNames: ["gemini-3.6-flash"],
  createdAt: <epoch ms>
}
```
Other type enum values seen: `"openai"`, `"azure_openai"`, plus Ollama /
OpenRouter / Groq / Cerebras / Llama / Gemini / Grok / Anthropic / DeepSeek.

Agent-model assignment (per agent; Ve.Navigator / Ve.Planner):
```js
{ provider: "<providerId>", modelName: "gemini-3.6-flash",
  parameters: { temperature: 0, topP: 0 } }
```

## Manual config path (working, ~90s) — the fallback when auto-injection fails

1. Click Nanobrowser icon → Settings (gear) → Models tab
2. Add provider → Custom / OpenAI-compatible
3. Base URL: `http://localhost:8790/v1`
4. API Key: anything (e.g. `proxy`)
5. Model: `gemini-3.6-flash`
6. Assign to Navigator (and Planner), Save

## Auto-injection attempts — what was tried and what blocked

Goal: inject the provider config directly so no clicking is needed.

1. **CDP injection** — decoded the full schema (above), got the extension ID,
   but Chrome on this machine **refuses to bind --remote-debugging-port**:
   browser process runs with the exact flags (`--remote-debugging-port=9222
   --user-data-dir=... --restore-last-session`), yet binds ZERO listening
   ports and writes no DevToolsActivePort. No enterprise policy blocks it.
   Chrome 136+ on Windows often requires an explicit `--user-data-dir` for the
   flag to bind — even that did not work here. Try on other machines; don't
   assume it fails everywhere.
2. **Direct LevelDB write** — chrome.storage.local lives at
   `User Data/Default/Local Extension Settings/<ext_id>/` (files: 000003.log,
   CURRENT, LOCK, LOG, MANIFEST-000001). Blocked two ways: LOCK file (Chrome
   holds it while running) and `plyvel` needs C++ build tools (won't pip
   install on this box). Would also need Chrome's value-serialization format.

So: manual config is the reliable path on this machine. The user's
auto-do-it preference means a future session should re-attempt programmatic
routes (CDP first) but fall back to the exact manual steps above rather than
leaving the user to reverse-engineer them.

## Verification after wiring

- Proxy health: `curl -s http://127.0.0.1:8790/health` → `{"keys":6,"model":"gemini-3.6-flash"}`
- Proxy end-to-end (non-stream + stream): POST /v1/chat/completions with
  `"model":"gpt-4o"` → proxy maps to gemini-3.6-flash; streaming returns SSE.
- Nanobrowser task in the sidebar → watch the proxy log for rotated keys.
