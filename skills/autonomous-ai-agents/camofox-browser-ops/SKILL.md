---
name: camofox-browser-ops
description: "Use when running or fixing the Camofox browser server."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [browser, camofox, camoufox, anti-detection, nanobrowser, chrome, cdp]
---

# Camofox Browser Ops

Operational skill for the Camofox anti-detection browser server
(`@askjo/camofox-browser` npm package wrapping Camoufox, a Firefox fork with
C++ fingerprint spoofing). Covers server lifecycle, the two known server.js
patches, session hygiene, and wiring third-party clients (Nanobrowser) through
the Gemini rotation proxy.

Companion skill: `gemini-browser-control` (user-owned) covers the agent loop
(screenshot → Gemini vision → act) built on top of this server.

Verified site flows on this stack: Amazon.in + Flipkart price research (search
URLs, snapshot-truncation handling, cross-platform price check, fake-ANC
filter) — `references/ecommerce-price-research.md`. YouTube search/channel
harvesting (ytInitialData `videoRenderer` vs channel-grid `lockupViewModel`
extractors, oEmbed batch verification + "Unauthorized" quirk, decoy-handle
check) — `references/youtube-search-harvesting.md`. Batch mega-hunts (15+
queries) add: Python walker MUST iterate lists, exact-title quoted-search
re-verification for oEmbed-401 IDs, dead-ID replacement, handle discovery via
`channelRenderer` — same reference file.

## Stack layout (this machine)

- Server: `C:\Users\HP\camofox` (npm pkg `@askjo/camofox-browser` v1.13.1), port 9377
- Enabled via `CAMOFOX_URL=http://localhost:9377` in `AppData\Local\hermes\.env`
  (loaded at Hermes startup — restart Hermes for routing changes to take effect)
- Restart after reboot: `cd C:\Users\HP\camofox && npx camofox-browser`
- Health: `curl http://localhost:9377/health` → `{"engine":"camoufox","browserConnected":true}`
- Gemini rotation proxy: `scripts` of gemini-browser-control skill, port 8790

## Hard-won rules

0. **git-bash paths**: `cd C:\Users\HP\camofox` (backslash form) FAILS in this
   host's git-bash terminal — backslashes are eaten, `cd: C:UsersHPcamofox: No
   such file or directory`. Use MSYS paths: `cd /c/Users/HP/camofox`.
1. **The npm wrapper kill trap**: killing the shell/tee process does NOT kill the
   node server. The real pid holds port 9377 — find it with
   `netstat -ano | grep ":9377" | grep LISTEN` then `taskkill /PID <pid> /F`.
   (In git-bash, `taskkill //PID` fails — use single-slash `/PID`.)
2. **Two server.js patches exist** (both lost on `npm install`/reinstall):
   health-probe `viewport:null` fix, and the tab-reaper try/catch guard. Exact
   recipes: `references/camofox-server-patches.md`. Verify with
   `node --check server.js` after re-applying. Canonical build check:
   `npm run build` (jest devDeps are NOT installed for nested deps — `npm test`
   is not a runnable verification here).
3. **Session hygiene**: Hermes browser tools create ephemeral `hermes_{uuid}`
   sessions per task. Deleting tabs individually while the session object
   lingers → reaper crashes with `Cannot read properties of undefined
   (reading 'url')` unhandledRejections every 60s. Clean with
   `curl -X DELETE http://localhost:9377/sessions/<userId>`. Always close
   sessions (not just tabs) in finally blocks.
4. **Idle shutdown is normal**: after ~5 min with zero sessions the server logs
   `browser idle shutdown` and closes the engine. It relaunches on the next
   `/tabs` call (first call ~5-10s slower). Not an error.
5. **Auto-do-it preference**: when the user says "auto do it", exhaust the
   programmatic routes (CDP injection, storage APIs, LevelDB) before handing
   manual steps — and present manual config as the last resort with exact
   click paths, not as the primary answer. See the CDP/LevelDB experience in
   `references/nanobrowser-wiring.md` for what was tried and what blocked.

## Client wiring (Nanobrowser)

Nanobrowser (MIT, multi-agent Planner/Navigator Chrome extension) supports
custom OpenAI-compatible providers → point at the Gemini rotation proxy so 6
keys rotate on 429. Full schema, extension ID, storage keys, HMR patch, and
manual config steps: `references/nanobrowser-wiring.md`.

## Verification

```bash
curl -s http://localhost:9377/health          # engine camoufox, browserConnected true
grep -c "unhandledRejection" camofox.log      # should stay frozen after cleanup
node --check server.js                        # after re-applying patches
```
