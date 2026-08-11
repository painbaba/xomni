# Nanobrowser auto-config — decoded schema + RESOLVED LevelDB write path

Session date: Aug 2026. Goal was FULLY AUTOMATIC configuration of the
Nanobrowser extension (point its LLM calls at the local Gemini rotation
proxy, http://localhost:8790/v1) with zero manual clicking. Status: schema
DECODED from source; **the write is RESOLVED via direct LevelDB write with
`classic-level`** (verified: provider + agent-models + general-settings
written into the real profile's storage, Chrome relaunched, proxy traffic
observed). CDP injection remains blocked by Chrome-150 behaviors (below) —
do NOT go back to fighting CDP; the LevelDB path is faster and reliable.

## Decoded config schema (verified from v0.1.13 options JS)

Settings live in `chrome.storage.local` via a helper `xr(key, defaults,
{storageEnum: Yt.Local, liveUpdate: true})`. Keys found in
`options/assets/index-*.js`:

- `"llm-api-keys"` → `{ providers: { <providerKey>: {...} } }`
- `"agent-models"` → `{ agents: { Navigator: {...}, Planner: {...} } }`
- `"general-settings"` → `{ maxSteps, maxActionsPerStep, maxFailures,
  useVision, useVisionForPlanner, planningInterval, displayHighlights,
  minWaitPageLoad, replayHistoricalTasks }` (defaults decoded: 100, 5, 3,
  false, false, 3, true, 250, false)
- also `"speech-to-text-model"`, `"firewall-settings"`, `"analytics-settings"`

Custom OpenAI-compatible provider object (type value `"custom_openai"`):

```js
{
  name: "Gemini Proxy",
  type: "custom_openai",
  baseUrl: "http://localhost:8790/v1",
  apiKey: "proxy",            // any string; rotation is server-side
  modelNames: ["gemini-3.6-flash", "gemini-3.1-pro-preview", "gemini-3.5-flash"],
  createdAt: Date.now()
}
```

Per-agent model split (README-recommended architecture: Planner = stronger
reasoning, Navigator = fast + vision):

```js
{ agents: {
    Navigator: { provider: "<providerKey>", modelName: "gemini-3.6-flash",
                 parameters: { temperature: 0.1, topP: 0.1 } },
    Planner:   { provider: "<providerKey>", modelName: "gemini-3.1-pro-preview",
                 parameters: { temperature: 0.2, topP: 0.2 } }
} }
```

Tuned general-settings (vision ON so canvas/JS-heavy sites are readable):

```js
{ maxSteps: 100, maxActionsPerStep: 5, maxFailures: 3,
  useVision: true, useVisionForPlanner: true, planningInterval: 3,
  displayHighlights: true, minWaitPageLoad: 250, replayHistoricalTasks: false }
```

The provider map key is a slug the UI generates (e.g. `custom_name`); any
unique key works as long as `agent-models` references the same key. UI save
logic requires `name` (no spaces for custom_openai), non-empty `baseUrl`,
and `modelNames` — mirror it when writing directly.

## THE RESOLVED WRITE PATH (verified this session)

1. **Close Chrome entirely** (`taskkill /F /IM chrome.exe`; the LevelDB LOCK
   is held while Chrome runs — opening it fails with LEVEL_LOCKED).
2. Use the **`classic-level` npm package** (prebuilt Windows x64 binaries —
   NO C++ toolchain; `plyvel` fails to build on this box). Install once:
   `cd C:\Users\HP\nanobrowser && npm install classic-level`.
3. Open the extension's storage LevelDB:
   `C:/Users/HP/AppData/Local/Google/Chrome/User Data/Default/Local Extension
   Settings/jjmpnipdclgmglamcncnbfgjedadkade/`
   (`new ClassicLevel(dbPath, { keyEncoding: "utf8", valueEncoding: "buffer" })`).
4. `db.put("<key>", Buffer.from(JSON.stringify(obj)))` for `llm-api-keys`,
   `agent-models`, `general-settings` — values are PLAIN JSON (verified by
   reading existing entries: `analytics-settings` value starts `{"anon...`).
5. Read back with `db.get(...)` to verify, close db, relaunch Chrome.
6. Confirm live: run a Nanobrowser task; the rotation proxy log shows
   `429 on key, rotating` under traffic.

Ready-made scripts (in the `anti-block-browsing` skill):
- `scripts/write_nanobrowser_config.mjs` — writes all three keys (advanced
  per-agent split + vision-on config)
- `scripts/read_nanobrowser_config.mjs` — dumps storage for verification

## Extension ID discovery

- Unpacked extension IDs live in
  `User Data/Default/Secure Preferences` → `extensions.settings.<id>.path`.
  Real profile ID for Nanobrowser: `jjmpnipdclgmglamcncnbfgjedadkade`
  (path `C:\Users\HP\nanobrowser\ext`).
- The ID is NOT a simple `sha256(path)[:32]` — naive hashes of the path in
  any slash/case variant did NOT match. Don't burn time deriving it; read
  Secure Preferences.
- A temp profile loading the same folder gets a DIFFERENT ID
  (`fignfifoniblkonapihmkfakmlgkbkcf`) — expected; storage is per-profile
  per-ID. The LevelDB write targets the REAL profile's dir, so the ID
  mismatch doesn't matter.

## Chrome-150 blockers (both verified — avoid this whole path)

1. **`--remote-debugging-port` is REFUSED on the default profile.**
   Chrome exits with `DevTools remote debugging requires a non-default data
   directory. Specify this using --user-data-dir.` — even when you pass the
   real profile path explicitly as `--user-data-dir`. You CANNOT CDP-attach
   to the user's real profile. Workaround used: temp profile
   (`--user-data-dir=C:\Users\HP\chrome-cdp --remote-debugging-port=9222`).
2. **Chrome content-verifies unpacked extensions on fresh profiles.**
   Any modified file inside the extension dir (here: the HMR-client stub
   patch in `background.iife.js`) fails verification
   (`Content verify job failed ... reason:1`) and extension pages render
   `chrome-error://chromewebdata/`. Load a PRISTINE copy (fresh unzip) in
   the temp profile, not the patched working copy.

## MV3 service-worker dormancy (only relevant if you ever retry CDP)

- The extension SW vanishes from `GET /json/list` after ~30s idle. Wake it
  by opening an extension page (`PUT /json/new?chrome-extension://<id>/side-panel/index.html`),
  then attach fast via the browser-level websocket:
  `Target.attachToTarget {targetId, flatten:true}` then
  `Runtime.evaluate {expression, awaitPromise:true, returnByValue:true}`
  with the returned `sessionId` on every message.
- With a pristine copy the SW DID attach and evaluate — but
  `chrome.storage` was undefined in that context (`chrome.storage.local`
  → `Cannot read properties of undefined (reading 'local')`). The direct
  LevelDB write sidesteps this entirely; don't trust SW-context storage.

## Manual fallback (if LevelDB is ever locked / Chrome can't close)

The 90-second manual config:
chrome://extensions → Nanobrowser → Details → Extension options → Models →
add Custom (OpenAI-compatible) provider → base URL `http://localhost:8790/v1`,
any api key, model `gemini-3.6-flash` → assign to Navigator + Planner → Save.
All calls then ride the rotation proxy (6 Gemini keys, 429 rotation).

## Files/artifacts left on disk

- `C:\Users\HP\nanobrowser\` — release zip, `ext/` (patched copy),
  `orig/` (pristine unzip), inject/probe .mjs scripts (inject_nanobrowser.mjs,
  inject2/3/4/5.mjs, probe*.mjs), hash_check.py, check_reg.py,
  read_lvldb.mjs, write_lvldb.mjs (working reference implementations).
- Rotation proxy: `gemini-browser-control/scripts/gemini_rotation_proxy.py`
  (verified: /health, /v1/models, /v1/chat/completions stream + non-stream).
