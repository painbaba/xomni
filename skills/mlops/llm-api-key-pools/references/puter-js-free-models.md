# Puter.js — free-model gateway + serverless app platform (verified Aug 2026)

## Why it matters
The surviving free GLM-5.2 channel. z.ai's free era is over: new accounts
get a valid key (authenticates, /v1/models lists 8 GLM models) but ZERO
credits — every call fails with error 1113 "Insufficient balance or no
resource package". GLM Coding Plan is paid (Lite $12.6/mo = 10k
credits/wk ≈ 43-87M GLM-5.2 tokens/wk; Pro $56/mo ≈ 263-526M/wk).
Puter serves 500+ models (OpenAI, Anthropic, Google, Z.AI, OpenRouter
vendor) to app users free; rate-limited per user with anti-abuse.

## Docs (LLM-friendly — read FIRST)
- https://docs.puter.com/llms.txt — index of every doc as .md links
- https://docs.puter.com/llms-full.txt — full docs in one file
- https://docs.puter.com/getting-started/index.md
- https://docs.puter.com/AI/chat/index.md — puter.ai.chat reference

## Loading
- Browser: `<script src="https://js.puter.com/v2/"></script>` → global `puter`
- Node: `npm i @heyputer/puter.js`; `init(token)` for backend use,
  `getAuthToken()` for a browser-login flow

## Hard requirements (enforced by Puter)
- App MUST be served over HTTP(S); file:// is blocked (security error)
- Footer MUST link https://developer.puter.com — label it "Powered by Puter"

## API surface used in the proven todo-app pattern
- `puter.auth.signIn() / signOut() / isSignedIn() / getUser()` — popup auth
- `puter.kv.set(key, value) / get(key)` — cloud KV, per-user, values are
  strings (JSON.stringify); serialize writes through a promise chain to
  avoid race conditions on rapid edits
- `puter.ai.chat(messages, {model, temperature, max_tokens, stream})` —
  messages array supports `system` role; model "z-ai/glm-5.2" verified;
  resolves {message:{content}} or rejects with an Error
- `puter.ai.listModels() / listModelProviders()` — enumerate models/vendors
- `puter.fs.*` — real file storage; `puter.hosting.*` — subdomain hosting

## AI output parsing pitfall
GLM wraps JSON in ```json fences — strip with
`text.replace(/```(?:json)?/g,'')` before JSON.parse. For structured
output pin `temperature: 0.2` and a tight `max_tokens`.

## Deploy to live URL
`npm i -g puter-cli` → `puter login` (interactive browser auth — the
one step that must be the user's) → `puter deploy` in the app dir.

## Terminal wrapper pattern (C:\Users\HP\glm-tool)
- `glm` bash wrapper: Puter first (node glm_puter.js), NIM rotation
  fallback (glm_nim.py — reads NVIDIA_NIM_API_KEY_1..6 from hermes .env,
  503-retry, dead-key skip). Usage: `glm "question"`, stdin piped, or
  `glm --nim "question"` to force the NIM path.
- Token resolution in glm_puter.js: PUTER_AUTH_TOKEN env -> ~/.puter
  (auth.json / auth_token candidates — exact field name unverified until
  a post-login inspection).
- `npm run test` = deterministic suite (syntax, no-token path, path
  routing); `npm run test:live` = end-to-end, requires an authenticated
  channel (puter login or NIM off-peak).
- Server-side Node calls need a token — only in-browser is keyless;
  community "free unlimited" tutorials describe the browser path only.
- "User-Pays" model: end-users of your app pay via their OWN Puter
  accounts — relevant if you ship an app to others.

## Session evidence (2026-08-07)
- Built puter-todo (auth + KV persistence + GLM-5.2 "AI Prioritize" that
  reorders tasks + one-line coach note) — see
  templates/puter-js-app-starter.html in this skill.
- Verified: page renders, SDK loads, isSignedIn() runs clean (camofox).
  Full sign-in/KV/AI flow requires a real user browser session.
- Local test server: `python -m http.server 8811` (must be HTTP, not file://).
