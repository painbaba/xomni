#!/usr/bin/env node
/* cdp.js — CDP control for the hunt browser (Edge/Chrome launched with
 * --remote-debugging-port=9223 --user-data-dir=<profile> --load-extension=<ext>).
 * Modes:
 *   node cdp.js tabs              — list open page tabs
 *   node cdp.js goto <url>        — navigate the first page tab
 *   node cdp.js fetch <path> [METHOD] [body] — same-origin fetch in current
 *                                  page (passes WAF, carries extension-injected
 *                                  headers); prints status/ctype/body[:1500]
 *   node cdp.js rules             — dump installed DNR rules + stored username
 *                                  from the extension context (verify header
 *                                  rule is LIVE, not just written)
 *   node cdp.js wake              — wake the sleeping extension SW (open popup)
 *   node cdp.js close             — Browser.close THIS debug instance only
 */
const mode = process.argv[2] || "tabs";
const BASE = "http://localhost:9223";

// hard watchdog: never hang the caller
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
    for (const t of list) {
      if (t.type === "page") console.log("TAB:", t.url);
    }
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

  if (mode === "fetch") {
    const url = process.argv[3];
    const method = (process.argv[4] || "GET").toUpperCase();
    const body = process.argv[5] || null;
    const page = list.find(t => t.type === "page");
    if (!page) { console.log("no page tab"); process.exit(1); }
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    const expr = `fetch(${JSON.stringify(url)}, {method:${JSON.stringify(method)}, headers:{"Accept":"application/json"}, body:${body ? JSON.stringify(body) : "undefined"}}).then(r => r.text().then(t => JSON.stringify({status:r.status, ctype:r.headers.get('content-type'), body:t.slice(0, 1500)})))`;
    const result = await new Promise((resolve, reject) => {
      ws.onmessage = e => {
        const m = JSON.parse(e.data);
        if (m.id === 1) resolve(m.result);
      };
      ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate",
        params: { expression: expr, awaitPromise: true, returnByValue: true } }));
      setTimeout(() => reject(new Error("timeout")), 20000);
    });
    console.log(result.result.value || JSON.stringify(result));
    process.exit(0);
  }

  if (mode === "goto") {
    const url = process.argv[3] || "https://admin.meeshosupply.com";
    const page = list.find(t => t.type === "page");
    if (!page) { console.log("no page tab"); process.exit(1); }
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    ws.send(JSON.stringify({ id: 1, method: "Page.navigate", params: { url } }));
    await new Promise(r => setTimeout(r, 1200));
    console.log("navigated to", url);
    return;
  }

  if (mode === "wake") {
    const sw = list.find(t => t.type === "service_worker" && t.url.endsWith("background.js"));
    const id = sw ? sw.url.split("/")[2]
                  : "jdfdejcfahoojocflghkgglplgdpkfbf"; // observed stable ID for this path
    const page = list.find(t => t.type === "page");
    if (!page) { console.log("no page tab"); process.exit(1); }
    const ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    ws.send(JSON.stringify({ id: 1, method: "Page.navigate",
      params: { url: `chrome-extension://${id}/popup.html` } }));
    await new Promise(r => setTimeout(r, 1500));
    console.log("woke extension, id=" + id);
    return;
  }

  if (mode === "rules") {
    // our extension's SW ends with background.js (Edge builtins use rollup/background.html)
    let sw = list.find(t => t.type === "service_worker" && t.url.endsWith("background.js"));
    if (!sw) sw = list.find(t => t.type === "page" && t.url.startsWith("chrome-extension://"));
    if (!sw) { console.log("extension target not found"); process.exit(1); }
    const ws = new WebSocket(sw.webSocketDebuggerUrl);
    await new Promise(r => ws.onopen = r);
    const result = await new Promise((resolve, reject) => {
      ws.onmessage = e => {
        const m = JSON.parse(e.data);
        if (m.id === 1) resolve(m.result);
      };
      ws.send(JSON.stringify({
        id: 1, method: "Runtime.evaluate",
        params: {
          expression: "Promise.all([chrome.storage.sync.get('username'), chrome.declarativeNetRequest.getDynamicRules()]).then(([s,r]) => JSON.stringify({stored:s.username||'', rules:r.map(x => ({id:x.id, header:x.action.requestHeaders, domains:x.condition.requestDomains}))}))",
          awaitPromise: true, returnByValue: true
        }
      }));
      setTimeout(() => reject(new Error("timeout")), 8000);
    });
    console.log("VERIFY:", result.result.value || JSON.stringify(result));
    process.exit(0);
  }
}

main().catch(e => { console.error(e.message); process.exit(1); });
