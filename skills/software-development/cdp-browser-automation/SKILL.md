---
name: cdp-browser-automation
description: Automate Chromium via CDP — trusted input, extensions.
---

# CDP Browser Automation

Drive a real Chromium browser (Edge/Chrome) over the DevTools Protocol when
you need: browser extensions loaded, React/SPA flows automated with TRUSTED
input, or verification of what the browser actually did (not just what the
code intends). Built and proven on Windows/git-bash (Aug 2026).

## When to use
- Automating login/checkout/order flows on SPAs (React ignores synthetic
  events — trusted CDP input required).
- Loading an unpacked extension and verifying it works end-to-end.
- Anything where curl/fetch can't reach (WAF-passing real-browser requests).

## Launch recipe (Edge/Chrome, extensions + debugging)
```
msedge.exe --user-data-dir="C:/.../hunting-profile" \
  --load-extension="C:/.../ext-dir" \
  --remote-debugging-port=9223 \
  --disable-blink-features=AutomationControlled \
  --no-first-run --new-window "<url>"
```
- `--load-extension` is IGNORED on the default profile — a custom
  `--user-data-dir` is mandatory.
- `--disable-blink-features=AutomationControlled` hides the automation flag
  (best-effort only — see the bot-detection boundary below).
- Launch from bash: append `</dev/null >/dev/null 2>&1 &` + `disown` or the
  backgrounded process holds the stdout pipe and `grep`-ing the script's
  output hangs forever.
- State lives in the profile dir; if the extension misbehaves after a
  restart, `rm -rf` the profile and relaunch fresh.

## Control surface
- `http://localhost:9223/json/list` — every target: `page` tabs,
  `service_worker` (extensions), `background_page` (Edge builtins).
  Each has a `webSocketDebuggerUrl`.
- Node 22+ has a global `WebSocket` — no deps needed for CDP scripts.
- See `scripts/cdp.js` — the proven toolkit: goto/eval/clickat/type/typekey/
  fetch/rules/wake/evalspoof/tabs/close with a hard watchdog timer.

## Verified techniques
- **Trusted clicks**: `Input.dispatchMouseEvent` mouseMoved(300ms)+pressed+
  released at element center. `el.scrollIntoView({block:'center'})` FIRST —
  clicking off-viewport coords silently misses. JS `.click()` works for
  buttons with onClick but NOT for hover menus.
- **React-safe typing**: per-character `Input.dispatchKeyEvent`
  (keyDown{text} + char + keyUp) — this is what updates React controlled
  state. `Input.insertText` sets the DOM value but can leave React state
  stale (button submits empty). Native setter + input/change events is the
  fallback for read-back, not for submit.
- **Capture API responses**: monkeypatch `XMLHttpRequest.prototype.open/
  send` in the page (apps use axios/XHR — a fetch-only hook sees NOTHING),
  push {status, body} to a window array, read it via a later evaluate.
  This is how WAF blocks are proven.
- **MV3 extension service workers SLEEP**: the SW disappears from
  /json/list ~30s after startup. Verify rules IMMEDIATELY after launch, or
  wake it by navigating a tab to `chrome-extension://<id>/popup.html`.
- **Extension ID**: do NOT compute it as sha256(path) — Chromium's real ID
  differs. Derive from the SW target URL (`url.split("/")[2]`), or find the
  SW whose URL ends with `background.js` (Edge builtins use
  background.rollup.js / background.html).
- **Runtime.evaluate**: pass `awaitPromise:true, returnByValue:true` for
  async expressions (e.g. `chrome.declarativeNetRequest.getDynamicRules()`)
  — the definitive way to verify a DNR header rule is installed.
- **Watchdog**: `setTimeout(()=>process.exit(1), 45000).unref()` at script
  top — WS connects can hang forever on dead targets.

## Windows/git-bash gotchas
- MSYS paths (`/c/Users/...`) break Windows binaries (node, python, curl's
  -o). Convert with `cygpath -w "$DIR"` before interpolating into node/
  python args. This bites repeatedly — check it first when you see
  "can't open file 'C:\\c\\Users\\..." or MODULE_NOT_FOUND.
- The write_file lint hook runs `node --check` with a mangled
  `C:\c\Users\...` path — its "lint error" on .js files is noise; verify
  with `node --check` from the file's directory instead.

## Bot-detection boundary (measured 2026-08)
- Page-level bot checks: pass with Camoufox and usually with CDP+spoof.
- Auth-API checks (Akamai Bot Manager on /login/* endpoints): 403 for ALL
  CDP-driven sessions even with `--disable-blink-features` + webdriver
  spoof. Route around it (username+password panels, one manual OTP), don't
  burn hours fighting it.
- For anti-detection browser stacks see the `anti-block-browsing` skill
  (user-owned) — it covers Camoufox/Nanobrowser/OpenCLI routes.

## Pitfalls
- Don't trust /json/list snapshot taken seconds before use — targets churn
  (navigations replace page targets, SWs sleep). Re-fetch per action.
- gzip responses look like binary garbage in curl output — add
  `--compressed` before concluding anything about a body.
- Automating flows that hit real production side-effects (orders, payments)
  needs explicit authorization (e.g. a bug-bounty program's provided test
  accounts). See `bug-bounty-hunting` skill for the discipline.
