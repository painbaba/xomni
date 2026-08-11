#!/usr/bin/env node
/*
 * cdp.js — CDP control toolkit for a Chromium instance launched with
 * --remote-debugging-port=9223 (see SKILL.md launch recipe).
 * Usage: node cdp.js <mode> [args]
 *   tabs            — list open page tabs
 *   close           — Browser.close (this instance only)
 *   goto <url>      — navigate the first page tab
 *   eval <expr>     — evaluate JS in the page (awaitPromise + returnByValue)
 *   clickat <expr>  — trusted CDP mouse click at element center (scrollIntoView first)
 *   type <expr> <text>    — focus element + Input.insertText (simple fields)
 *   typekey <expr> <text> — per-character key events (React-safe)
 *   fetch <path> [METHOD] [body] — same-origin fetch from page context
 *   rules           — dump DNR rules from our extension SW (URL ends background.js)
 *   wake            — wake the extension SW by opening its popup page
 *   evalspoof       — install navigator.webdriver spoof for new documents
 * All modes have a 45s hard watchdog so nothing hangs the caller.
 */
const mode = process.argv[2] || "tabs";
const BASE = "http://localhost:9223";

setTimeout(() => { console.error("watchdog: cdp.js timed out"); process.exit(1); }, 45000).unref();

async function main() {
  let list;
  try {
    list = await (await fetch(BASE + "/json/list")).json();
  } catch (e) {
    console.log("browser not running (port 9223)");
    process.exit(1);
  }

  if (mode === "tabs") {
    for (const t of list) if (t.type === "page") console.log("TAB:", t.url);
    return;
  }
  if (mode === "close") {
    const ver = await (await fetch(BASE + "/json/version")).json();
    const ws = new WebSocket(ver.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    ws.send(JSON.stringify({ id: 1, method: "Browser.close" }));
    console.log("close sent");
    return;
  }

  const page = list.find(t => t.type === "page");
  if (!page) { console.log("no page tab"); process.exit(1); }
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);

  const evalOne = (expression) => new Promise((resolve) => {
    const id = Math.floor(Math.random() * 1e9);
    const handler = e => {
      const m = JSON.parse(e.data);
      if (m.id === id) { ws.removeEventListener("message", handler); resolve(m.result); }
    };
    ws.addEventListener("message", handler);
    ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { expression, returnByValue: true } }));
  });
  const send = (method, params) => ws.send(JSON.stringify({ id: Math.floor(Math.random() * 1e9), method, params }));

  if (mode === "goto") {
    const url = process.argv[3] || "https://example.com";
    send("Page.navigate", { url });
    await new Promise(r => setTimeout(r, 1200));
    console.log("navigated to", url);
    return;
  }
  if (mode === "eval") {
    const expr = process.argv[3];
    const result = await evalOne(expr);
    if (result.exceptionDetails) {
      console.log("EXC:", result.exceptionDetails.text, result.exceptionDetails.exception?.description || "");
    } else {
      console.log(typeof result.result.value === "string" ? result.result.value : JSON.stringify(result.result.value));
    }
    return;
  }
  if (mode === "clickat") {
    const expr = process.argv[3];
    const pt = await evalOne(`(()=>{const el=${expr}; if(!el) return null; el.scrollIntoView({block:'center'}); const r=el.getBoundingClientRect(); return {x:r.x+r.width/2, y:r.y+r.height/2};})()`);
    const { x, y } = pt.result.value || {};
    if (!x) { console.log("element not found"); process.exit(1); }
    send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
    await new Promise(r => setTimeout(r, 300));
    send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
    await new Promise(r => setTimeout(r, 120));
    send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
    await new Promise(r => setTimeout(r, 800));
    console.log(`clicked at ${x.toFixed(0)},${y.toFixed(0)}`);
    return;
  }
  if (mode === "type") {
    await evalOne(`(()=>{const el=${process.argv[3]}; if(!el) return 'no el'; el.focus(); return 'focused';})()`);
    await new Promise(r => setTimeout(r, 300));
    send("Input.insertText", { text: process.argv[4] || "" });
    await new Promise(r => setTimeout(r, 400));
    console.log("typed:", process.argv[4]);
    return;
  }
  if (mode === "typekey") {
    const text = process.argv[4] || "";
    await evalOne(`(()=>{const el=${process.argv[3]}; if(!el) return 'no el'; el.focus(); el.click(); return 'focused';})()`);
    await new Promise(r => setTimeout(r, 400));
    for (const ch of text) {
      send("Input.dispatchKeyEvent", { type: "keyDown", text: ch, key: ch });
      send("Input.dispatchKeyEvent", { type: "char", text: ch, key: ch });
      send("Input.dispatchKeyEvent", { type: "keyUp", key: ch });
      await new Promise(r => setTimeout(r, 40));
    }
    await new Promise(r => setTimeout(r, 400));
    console.log("typed via keys:", text);
    return;
  }
  if (mode === "fetch") {
    const url = process.argv[3];
    const method = (process.argv[4] || "GET").toUpperCase();
    const body = process.argv[5] || null;
    const expr = `fetch(${JSON.stringify(url)}, {method:${JSON.stringify(method)}, headers:{"Accept":"application/json"}, body:${body ? JSON.stringify(body) : "undefined"}}).then(r => r.text().then(t => JSON.stringify({status:r.status, ctype:r.headers.get('content-type'), body:t.slice(0, 1500)})))`;
    const result = await new Promise((resolve, reject) => {
      ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id === 1) resolve(m.result); };
      ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: { expression: expr, awaitPromise: true, returnByValue: true } }));
      setTimeout(() => reject(new Error("eval timeout")), 20000);
    });
    console.log(result.result.value || JSON.stringify(result));
    return;
  }
  if (mode === "rules") {
    // our extension's SW ends with background.js (Edge builtins use rollup/background.html)
    let sw = list.find(t => t.type === "service_worker" && t.url.endsWith("background.js"));
    if (!sw) sw = list.find(t => t.type === "page" && t.url.startsWith("chrome-extension://"));
    if (!sw) { console.log("extension target not found"); process.exit(1); }
    const sws = new WebSocket(sw.webSocketDebuggerUrl);
    await new Promise(r => sws.onopen = r);
    const result = await new Promise((resolve, reject) => {
      sws.onmessage = e => { const m = JSON.parse(e.data); if (m.id === 1) resolve(m.result); };
      sws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate", params: {
        expression: "Promise.all([chrome.storage.sync.get('username'), chrome.declarativeNetRequest.getDynamicRules()]).then(([s,r]) => JSON.stringify({stored:s.username||'', rules:r.map(x => ({id:x.id, header:x.action.requestHeaders, domains:x.condition.requestDomains}))}))",
        awaitPromise: true, returnByValue: true } }));
      setTimeout(() => reject(new Error("timeout")), 8000);
    });
    console.log("VERIFY:", result.result.value || JSON.stringify(result));
    return;
  }
  if (mode === "wake") {
    const sw = list.find(t => t.type === "service_worker" && t.url.endsWith("background.js"));
    const id = sw ? sw.url.split("/")[2] : "<extension-id-from-rules-mode>";
    send("Page.navigate", { url: `chrome-extension://${id}/popup.html` });
    await new Promise(r => setTimeout(r, 1500));
    console.log("woke extension, id=" + id);
    return;
  }
  if (mode === "evalspoof") {
    send("Page.addScriptToEvaluateOnNewDocument", {
      source: `Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
       window.chrome = window.chrome || {runtime: {}};
       Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
       Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});`
    });
    await new Promise(r => setTimeout(r, 500));
    console.log("spoof script installed");
    return;
  }
  console.log("unknown mode:", mode);
  process.exit(1);
}

main().catch(e => { console.error(e.message); process.exit(1); });
