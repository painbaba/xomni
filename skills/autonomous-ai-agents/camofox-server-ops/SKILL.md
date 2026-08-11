---
name: camofox-server-ops
description: "Operate the Camofox anti-detection browser server."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [browser, camofox, camoufox, anti-detection, server-ops, cloudflare-bypass, troubleshooting]
---

# Camofox Server Ops

Camofox is a self-hosted Node.js server wrapping **Camoufox** (a Firefox fork
with C++ fingerprint spoofing) that gives Hermes / OpenCLI-style agents an
anti-detection browser backend. It defeats Cloudflare/bot checks that plain
Chromium and curl fail. This skill covers OPERATING the server itself — the
`gemini-browser-control` skill covers the Gemini-vision agent loop that drives
it.

## Layout

- Server: `C:\Users\HP\camofox` (npm pkg `@askjo/camofox-browser`, port 9377)
- Enabled via `CAMOFOX_URL=http://localhost:9377` in `AppData\Local\hermes\.env`
- Skills that drive it: `gemini-browser-control` (agent loop + rotation proxy)

## Install (fresh machine)

```bash
# npm 10.x vs project .npmrc engine-strict=true (wants >=11.17) — use --force
cd C:/Users/HP/camofox && npm init -y && npm install @askjo/camofox-browser --force
# Start: first run downloads Camoufox engine (~300MB)
cd C:/Users/HP/camofox && npx camofox-browser
```

Note: Hermes' `hermes tools post-setup camofox` runs `npm install` in the
hermes-agent project root, but the package is NOT in that package.json, so it
never installs. Install into a standalone dir as above, then set CAMOFOX_URL.

## Health check

```bash
curl -s http://localhost:9377/health
# expect: {"ok":true,"engine":"camoufox","browserConnected":true,"browserRunning":true}
```

## Two required server.js patches (both lost on `npm reinstall`)

The installed `node_modules/@askjo/camofox-browser/server.js` ships with two
bugs that surface within minutes on Windows + Camoufox. Apply both, then
restart:

1. **Health-probe viewport crash** (~line 6412): the health probe calls
   `browser.newContext()` with the DEFAULT viewport, which includes
   `isMobile: false` — Camoufox's CDP scheme rejects that field, so the probe
   fails and the server restarts the browser every ~3 min.
   Fix: `browser.newContext()` → `browser.newContext({ viewport: null })`
   (the OTHER probe at line 829 already passes `viewport: null` — mirror it).

2. **Tab-reaper unhandledRejection spam** (~line 5468): the per-tab inactivity
   reaper iterates sessions that can be mid-close (context already gone) and
   throws `Cannot read properties of undefined (reading 'url')` as an
   unhandledRejection every 60 s. Wrap the per-session body in try/catch so a
   bad session logs `tab reaper skipped session` and the pass continues.

After patching: `node --check server.js` + `npm run build` (the package's
canonical verification; `npm test` is NOT runnable for nested deps — jest is a
devDependency npm doesn't install).

## Session hygiene

Hermes browser tools create ephemeral `hermes_{uuid}` sessions. Deleting tabs
without the session (or a process dying mid-task) leaves an orphan session the
reaper trips on — same 'reading url' unhandledRejection signature as patch 2.

```bash
# List / clean orphan sessions
curl -s "http://localhost:9377/tabs?userId=<userId>"
curl -s -X DELETE "http://localhost:9377/sessions/<userId>"
```

Scripts that open tabs should close their session in a `finally` block
(`DELETE /sessions/<userId>`) so runs are self-cleaning.

**Persistence nuance (verified):** `DELETE /sessions/<userId>` SAVES the
session's storageState (cookies/IndexedDB) to the profile dir
(`C:\Users\HP\.camofox\profiles\<hash>\storage-state.json`) — it does NOT log
the user out. Reopening with the SAME userId restores the saved logins. Only
`DELETE /sessions/<userId>/storage_state` wipes them. So the standard cleanup
is safe for logged-in flows; use distinct userIds to keep separate login
contexts (the gemini-browser-control loop exposes `GEMINI_BROWSER_USER` for
this).

## Restart on Windows

Killing the background SHELL does NOT kill the node child holding :9377.

```bash
netstat -ano | grep ":9377" | grep LISTEN   # find real PID
taskkill /PID <pid> /F
cd C:/Users/HP/camofox && npx camofox-browser
```

## Behavior notes

- **Idle shutdown is normal**: after ~5 min with no sessions the browser closes
  (`browser idle shutdown`); it relaunches on the next `/tabs` call (first call
  +5-10s). Not an error.
- **API surface** (used by the agent loop): `POST /tabs` (body: url, userId,
  listItemId → tabId), `GET /tabs/{tabId}/snapshot?userId=` (accessibility tree
  + base64 screenshot), `POST /tabs/{tabId}/click|type|press|scroll|navigate`,
  `DELETE /tabs/{tabId}`, `DELETE /sessions/{userId}`.

## Companion stack installs

- **Nanobrowser** (open-source Manus-class Chrome extension, uses any
  OpenAI-compatible endpoint): download release zip from GitHub releases
  (`nanobrowser.zip`), unzip, load unpacked at chrome://extensions with
  Developer mode. Release builds ship a Vite **HMR dev client** that spams
  `WebSocket connection to 'ws://localhost:8081/' failed` in the console —
  stub it out in `background.iife.js`: replace every
  `new WebSocket(LOCAL_RELOAD_SOCKET_URL)` (3 occurrences) with a no-op object
  `{ onopen: null, addEventListener: () => {}, send: () => {} }`, then click
  the refresh icon on the extension card. Point its custom provider at the
  rotation proxy (`http://localhost:8790/v1`, any api_key).
- **Agent-Reach** (selector/installer for free browsing channels — web/Jina,
  YouTube, RSS, V2EX, Bilibili, GitHub, Exa): install into a dedicated venv
  (`python -m venv C:\Users\HP\.agent-reach-venv`, then pip install the
  github-main.zip URL). `agent-reach install --env=auto` is read-only;
  `--system` makes changes. Optional channels needing logins/cookies are NOT
  auto-read — run `agent-reach configure <platform>-cookies` per platform.
  pipx-requiring CLIs (bili-cli, twitter-cli) land in `~/.local/bin`; add that
  to PATH. It also installs an `agent-reach` skill for OpenClaw under
  `~/.openclaw/skills/`.

## Pitfall: act on the fix, don't narrate

When the server misbehaves and you hold the APIs (health endpoint, curl, the
server log), FIX IT directly — patch, restart, verify — rather than spending
turns explaining the investigation. The user's standard: you have the tools,
use them. Long diagnostic narratives read as stalling.

## Related

- `gemini-browser-control` — the Gemini-vision agent loop + key-rotation proxy
  that consume this server (user-owned; overlaps in the 'stack ops' territory —
  curator may consolidate).
- `hermes-agent` — native Hermes browser-tool routing (CAMOFOX_URL env var).
