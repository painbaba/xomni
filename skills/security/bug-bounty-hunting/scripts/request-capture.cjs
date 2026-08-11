// Request-capture harness: learn the EXACT working request an app sends
// when hand-built curl/urllib requests 500 but the logged-in browser works.
// Uses camoufox-js (Playwright API). Drop in cookies + target URL, run,
// read the JSON, replay verbatim.
//
// Usage: node request-capture.cjs <target-url> <cookies-json-file> <out-json>
//   cookies file: [{"name":"token","value":"...","domain":".example.com","path":"/"}, ...]
//   (cookie exports from DevTools/browser dumps work directly)
//
// Dep: camoufox-js (or playwright) — the Hermes camofox install lives at
// C:\Users\HP\camofox\node_modules\camoufox-js (require by absolute path).
// API note: module exports {Camoufox, launchOptions, NewBrowser,
// launchServer}; `Camoufox()` is CALLABLE (returns a Playwright-like
// browser), NOT `new Camoufox()`.
//
// Filter the captured list for your API (graphql/api/etc.) before replay.

const fs = require("fs");
const path = require("path");

const CAMOFOX_PATH = process.env.CAMOFOX_PATH || "C:/Users/HP/camofox/node_modules/camoufox-js";

(async () => {
  const [url, cookiesFile, outFile] = process.argv.slice(2);
  if (!url || !cookiesFile || !outFile) {
    console.error("usage: node request-capture.cjs <url> <cookies.json> <out.json>");
    process.exit(1);
  }
  const { Camoufox } = require(CAMOFOX_PATH);
  const cookies = JSON.parse(fs.readFileSync(cookiesFile, "utf8"));

  const browser = await Camoufox();
  const ctx = await browser.newContext();
  await ctx.addCookies(cookies);

  const page = await ctx.newPage();
  const captured = [];
  page.on("request", (req) => {
    captured.push({
      url: req.url().slice(0, 200),
      method: req.method(),
      headers: req.headers(),
      body: req.postData() || "",
    });
  });
  page.on("response", (res) => {
    if (captured.length && !captured[captured.length - 1].status) {
      captured.push({ respUrl: res.url().slice(0, 200), status: res.status() });
    }
  });

  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(9000); // let lazy API calls fire

  fs.writeFileSync(outFile, JSON.stringify(captured, null, 2));
  console.log(`captured ${captured.length} requests -> ${outFile}`);
  const withBody = captured.filter((c) => c.body);
  if (withBody.length) {
    console.log("first body-carrying request:", withBody[0].url);
    console.log("BODY:", withBody[0].body.slice(0, 400));
  }
  await browser.close();
})().catch((e) => { console.error("FAIL:", e.message); process.exit(1); });
