---
name: anti-block-browsing
description: "Browse blocked sites: Camoufox, Nanobrowser, OpenCLI."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [browsing, anti-detection, camofox, nanobrowser, gemini, cloudflare, scraping, personal-browser]
---

# Anti-Block Browsing Stack

Three independent routes to reach sites that block normal browsing. All are
installed and verified on this machine (Aug 2026). Pick by need:

| Route | What it is | Best for | Blocked-by proof |
|-------|-----------|----------|------------------|
| A. Camoufox sandbox | Anti-detect Firefox server (fingerprint spoofing), driven by scripts or Hermes browser tools | Sites with Cloudflare/bot checks, JS-heavy, canvas UIs. Fully automated, no human browser | bot.sannysoft.com read OK; DuckDuckGo search flow completed |
| B. Personal Chrome + Nanobrowser ext | Your real Chrome with the Nanobrowser extension (Manus-class multi-agent UI), backed by Gemini rotation proxy | Human-in-the-loop tasks, logged-in sites (Reddit/FB/IG/XHS), visual agent workflows | Reddit live via OpenCLI bridge; extension configured to gemini-3.6-flash |
| C. Channel adapters | OpenCLI (163 site adapters) + Agent-Reach (15 channels) | Sites with ready-made adapters (Reddit, YouTube, Bilibili, RSS, GitHub, XHS) | Reddit search returned ICSE results; Bilibili hot/search live |

## Quick start (all three)

```bash
# 0. One command starts both servers (Camofox :9377 + rotation proxy :8790)
cd C:\Users\HP\AppData\Local\hermes\skills\autonomous-ai-agents\anti-block-browsing
python scripts/start_stack.py

# 1. Camofox (sandbox browser) — port 9377 (if not started above)
cd C:\Users\HP\camofox && npx camofox-browser
curl -s http://localhost:9377/health   # {"engine":"camoufox","browserConnected":true}

# 2. Gemini rotation proxy — port 8790 (if not started above)
cd C:\Users\HP\AppData\Local\hermes\skills\autonomous-ai-agents\gemini-browser-control
set -a && source "$HOME/AppData/Local/hermes/.env" && set +a
python scripts/gemini_rotation_proxy.py
curl -s http://127.0.0.1:8790/health   # {"keys":6,"model":"gemini-3.6-flash"}

# 3. Personal Chrome — just open it. Nanobrowser extension is installed and
#    pre-configured to route through the rotation proxy.
```

## Route A: Camoufox sandbox (fully automated)

**Start server** (first call after idle takes ~5-10s — browser relaunches on demand):
```
cd C:\Users\HP\camofox && npx camofox-browser
```

**Health / verify:** `curl -s http://localhost:9377/health` → engine=camoufox.

**Direct REST API** (all JSON, port 9377):
- `POST /tabs {"url": "...", "userId": "X", "listItemId": "Y"}` → tabId
- `GET /tabs/{tabId}/snapshot?userId=X` → accessibility tree + base64 screenshot
- `POST /tabs/{tabId}/click|type|press|scroll|navigate|evaluate` with `{"userId":"X", ...}`
- `DELETE /sessions/{userId}` → close session (ALWAYS do this after a task to avoid orphan noise)

**Vision-driven agent loop (Manus-style)** — screenshot → gemini-3.6-flash decides → act:
```bash
cd C:\Users\HP\AppData\Local\hermes\skills\autonomous-ai-agents\gemini-browser-control
set -a && source "$HOME/AppData/Local/hermes/.env" && set +a
python scripts/gemini_browser.py "YOUR TASK" --url https://target-site.com
# Output: ANSWER: ... or TASK COMPLETE: ...  (progress on stderr)
```
The loop auto-closes its Camofox session in a `finally` block. See
`skill_view(name='gemini-browser-control')` for the full loop + pitfalls.

**Hermes native browser tools**: set `CAMOFOX_URL=http://localhost:9377` in
`AppData\Local\hermes\.env` (already done). After restarting Hermes, the
`browser_*` tools route through Camoufox automatically (is_camofox_mode).

## Route B: Personal Chrome + Nanobrowser extension

Nanobrowser is the Manus-class extension: Planner + Navigator agents, sidebar
chat, your own API keys, runs in your real Chrome with your logins.

**Status: INSTALLED and PRE-CONFIGURED** (Aug 2026):
- Extension ID (real profile): `jjmpnipdclgmglamcncnbfgjedadkade`
- Provider `gemini-proxy` → baseUrl `http://localhost:8790/v1`, model
  `gemini-3.6-flash`, assigned to Navigator AND Planner
- Storage lives at:
  `C:\Users\HP\AppData\Local\Google\Chrome\User Data\Default\Local Extension Settings\jjmpnipdclgmglamcncnbfgjedadkade\`

**Use it**: click the Nanobrowser icon in Chrome → side panel → type a task.
Every request flows: extension → localhost:8790 (proxy rotates 6 Gemini keys) → Gemini.

**Reconfigure via direct LevelDB write (no clicking, works while Chrome closed)**:
```bash
# Scripts live IN THIS SKILL:
cd C:\Users\HP\AppData\Local\hermes\skills\autonomous-ai-agents\anti-block-browsing
node scripts/write_nanobrowser_config.mjs   # writes provider + agent models
node scripts/read_nanobrowser_config.mjs    # verify
# (requires classic-level npm lib: cd C:\Users\HP\nanobrowser && npm install classic-level)
```
Format learned from source: keys `llm-api-keys` (providers map, type
`custom_openai` with name/baseUrl/apiKey/modelNames/createdAt) and
`agent-models` (agents.Navigator/Planner → {provider, modelName, parameters}).
Values are plain JSON in Chrome's LevelDB. **Chrome must be closed** when
writing (LOCK file). `read_lvldb.mjs` reads/verifies.

**Pitfall — CDP injection into the real profile does NOT work**: Chrome 150
refuses `--remote-debugging-port` on the default profile ("requires a
non-default data directory") and content-verifies unpacked extensions (a
patched background.iife.js fails verify → extension pages show chrome-error).
Workaround: write the LevelDB directly (above), or load the UNPATCHED copy
(`C:\Users\HP\nanobrowser\orig`) in a temp profile for CDP experiments.

## Route C: Channel adapters

**OpenCLI** (163 site adapters, uses your Chrome session via extension):
```bash
opencli reddit search "query" --limit 5    # reddit, youtube, bilibili, twitter, xiaohongshu, facebook, instagram, linkedin, wikipedia, google, github, ...
opencli <site> --help                      # per-site commands
opencli doctor                             # bridge connectivity (daemon :19825 + ext v1.0.22)
```
Needs Chrome open with the OpenCLI extension. Logged-in sites (FB/IG/XHS) need
you logged in there first.

**Agent-Reach** (selector/installer/router, 15 channels):
```bash
# venv-installed; health check:
C:/Users/HP/.agent-reach-venv/Scripts/agent-reach.exe install --env=auto
# channels: Web (Jina Reader), YouTube, GitHub, RSS, V2EX, Bilibili, Exa search
# optional: Twitter/X, Reddit, FB, IG, XHS, LinkedIn, Xueqiu, Xiaoyuzhou (need cookies/keys)
# Jina Reader (any webpage → clean text, no browser):
curl -s https://r.jina.ai/https://target-site.com
```

## Decision guide for blocked sites

1. **Site has a channel adapter** → OpenCLI or Agent-Reach first (fastest, no browser).
2. **Cloudflare/bot-check/canvas/JS-heavy** → Route A: `gemini_browser.py` (vision loop on Camoufox).
3. **Logged-in site, human OK to watch** → Route B: Nanobrowser side panel task.
4. **Hermes browser tools needed mid-session** → they route via Camoufox (CAMOFOX_URL set).
5. **Page text extraction only** → `curl https://r.jina.ai/URL` (zero setup).

## Operational notes

- **Both servers die on reboot**; restart commands at top. Optionally wire a
  cron job to start them.
- **Camofox orphan sessions**: Hermes browser tools create ephemeral
  `hermes_{uuid}` sessions. If the tab reaper logs `Cannot read properties of
  undefined (reading 'url')`, clean with `DELETE /sessions/{userId}` (server
  tab-reaper is patched to guard, so it's now log-only, not crashing).
- **Camofox server.js has TWO patches** (lost on npm reinstall): health probe
  `{viewport:null}` (isMobile CDP crash) + tab-reaper try/catch. See memory.
- **Gemini keys**: `GOOGLE_AI_STUDIO_API_KEY_1..6` in
  `AppData\Local\hermes\.env` + Hermes auth pool (auto-rotate on 429).
  `gemini-3.6-flash` is the newest flash model (verified on account).
- **Nanobrowser storage writes need Chrome closed.** If Chrome is open, close
  it, write, reopen (session restores).
