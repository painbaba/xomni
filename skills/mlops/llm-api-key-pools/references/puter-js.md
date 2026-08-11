# Puter.js — serverless apps on the free GLM-5.2 channel (verified Aug 2026)

Puter is the verified free GLM-5.2 API channel (see GLM map in SKILL.md).
This file covers BUILDING apps with Puter.js (the SDK), not just key access.

## Docs & loading
- Docs index for LLMs: `https://docs.puter.com/llms.txt` (+ `llms-full.txt`)
  — fetch this FIRST for any Puter.js work; every API has a per-page .md
  (e.g. `https://docs.puter.com/AI/chat/index.md`, `.../KV/index.md`).
- Include via CDN: `<script src="https://js.puter.com/v2/"></script>`
- HARD REQUIREMENT: the app must be served over HTTP(S) — a `file://` URL
  will not work. Local dev: `python -m http.server <port>`.
- Footer must link `https://developer.puter.com` ("Powered by Puter").

## Core APIs used in a typical app
- `puter.auth.signIn()` / `isSignedIn()` / `getUser()` — popup-based login.
- `puter.kv.set(key, str)` / `get(key)` — cloud KV per user+app; values are
  STRINGS (JSON.stringify objects). Serialize writes via a promise chain to
  avoid races on rapid edits.
- `puter.ai.chat(messages, {model, temperature, max_tokens, stream})` —
  OpenAI-style; Z.AI is a first-class vendor, use `model: 'z-ai/glm-5.2'`
  for free GLM-5.2 (default model is gpt-5-nano). Response:
  `resp.message?.content`. Free tier is rate-limited per user — fine for
  app features, not for bulk batch work.

## Token for server/CLI use (Node)
- `npm install @heyputer/puter.js`; `import { init } from
  "@heyputer/puter.js/src/init.cjs"; const puter = init(token);`
- Token location (puter CLI on Windows):
  `%APPDATA%\puter-cli-nodejs\Config\config.json` → `profiles[0].token`
  (NOT ~/.puter). Also try `PUTER_AUTH_TOKEN` env.
- Testing no-token code paths deterministically:
  `PUTER_FORCE_NO_TOKEN=1` env var — the token resolution must SKIP ALL
  sources (env + files) when set, else the real token leaks into the test.

## Pitfalls
- Apps using puter.js must be served over HTTP (repeat: file:// fails).
- KV values are strings — JSON.stringify/parse on both ends.
- Browser-tools evaluate of chrome.*-style APIs won't exist here — plain
  DOM/web APIs only (this is a normal web SDK, not an extension).
- The docs' example snippets are React-oriented; vanilla JS works fine.
