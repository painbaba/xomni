# Hunt tooling: MV3 header-injection extension + Edge launch + CDP verify

Pattern built 2026-08-07 for the Meesho program (X-Hackerone header
required on ALL test requests). Full working code: C:\Users\HP\meesho-hunter

## Why automate
Programs require a custom header on every test request. Hand-adding it in
Burp/extensions is error-prone and the USER DEMANDS zero manual steps —
the agent should build the tooling AND launch/verify it end-to-end, not
hand off "load this extension" instructions. Irreducible user inputs only:
account usernames/creds (ask ONCE, pre-seed a config file).

## Extension (Manifest V3, Chrome/Edge)
- `manifest.json`: permissions `declarativeNetRequest, storage, tabs,
  clipboardWrite`; host_permissions `*://*.<root>/*` per scoped domain;
  background service_worker; action popup; options_page.
- Header injection = declarativeNetRequest modifyHeaders rule:
  ```json
  { "id": 1, "priority": 1,
    "action": { "type": "modifyHeaders", "requestHeaders":
      [{ "header": "X-Hackerone", "operation": "set", "value": "<user>" }] },
    "condition": { "requestDomains": ["meesho.com", ...],
      "resourceTypes": ["main_frame","sub_frame","script","xmlhttprequest","image","font","media","websocket"] } }
  ```
  `requestDomains` suffix-matches subdomains. Install via
  `chrome.declarativeNetRequest.updateDynamicRules` (removeRuleIds first).
- Username seeding: background SW reads `config.json` (extension file via
  `fetch(chrome.runtime.getURL("config.json"))`) when sync storage is
  empty, seeds storage, builds rules. Lets the launcher pre-seed without
  the user ever touching the popup. Update config.json + restart Edge to
  change it.
- Keep rules/DNR-build logic in a pure `rules.js` (UMD: importScripts
  global + module.exports) so `node test.js` can deterministically test
  rule shape (no username → []; header name/operation/value; domains).
- Test the no-token/no-config path deterministically with an env flag
  (e.g. PUTER_FORCE_NO_TOKEN=1 skips ALL resolution).

## Launch (hunt.sh) — Edge with extension pre-loaded
```bash
"$EDGE" --user-data-dir="C:/Users/HP/<profile>" \
        --load-extension="C:/Users/HP/<ext>" \
        --remote-debugging-port=9223 --no-first-run \
        --new-window "<first-target>" </dev/null >/dev/null 2>&1 &
disown
```
- Custom --user-data-dir REQUIRED (recent Chrome/Edge ignore
  --load-extension on the default profile).
- --remote-debugging-port enables verification (below).
- CRITICAL bash detail: redirect </dev/null >/dev/null 2>&1 + disown or
  the backgrounded GUI exe holds the script's stdout pipe open → any
  caller doing `bash hunt.sh | grep ...` hangs until Edge exits.

## Verification via CDP (curl http://localhost:9223/json/list)
- Extension SW appears as a `service_worker` target with url
  `chrome-extension://<id>/background.js` — but ONLY while awake; MV3 SWs
  sleep ~30s after startup. VERIFY IMMEDIATELY after launch, or wake by
  navigating a tab to the extension's popup page.
- Edge ships built-in extensions whose SWs (background.rollup.js /
  background.html) pollute /json/list — filter with
  `url.endsWith('background.js')`.
- Don't guess the extension ID (sha256-of-path guesses are WRONG on
  Windows) — read it from the SW target URL, or hardcode the observed
  stable ID for this machine's path.
- Check the live rule from the SW target:
  `Runtime.evaluate` with
  `Promise.all([chrome.storage.sync.get('username'), chrome.declarativeNetRequest.getDynamicRules()])`
  (awaitPromise:true, returnByValue:true) → confirms username seeded AND
  rule installed.
- Kill ONLY the hunt instance: `Browser.close` on the browser-level WS
  (json/version → webSocketDebuggerUrl). NEVER `taskkill /IM msedge.exe`
  — kills the user's normal Edge windows too.
- Verify rules right after relaunch, not later — the SW sleeps.

## Node CDP helper (cdp.js pattern)
Modes: `close` (Browser.close), `rules` (evaluate DNR on our SW),
`goto <url>` (Page.navigate first page tab), `wake` (navigate tab to
popup). Node 22+ global WebSocket; fetch for /json/list.

## Load for real use
`chrome://extensions` → Developer mode → Load unpacked, or the
--load-extension launch above. After any config.json change: restart Edge.
