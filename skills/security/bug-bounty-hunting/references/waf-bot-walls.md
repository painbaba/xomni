# WAF / Bot-Detection Walls — measured findings (Aug 2026)

## The wall: Akamai blocks auth APIs on automated sessions
Target: meesho.com (in-scope HackerOne asset). The consumer OTP flow:

- Pages load fine under automation (Edge+CDP, and Camoufox anti-detect):
  product grid, product page, Add-to-Cart, phone-entry sheet all work.
- The APP's OWN XHR to `/api/v1/user/login/request-otp` returns
  **403 Access Denied** (HTML, `errors.edgesuite.net` reference) — both from
  the real app code and from direct same-origin XHR/fetch in the page.
- Everything else on the same host works (product APIs, page assets) — the
  WAF specifically protects the auth endpoint with Bot Manager.

## Proof technique: XHR hook (fetch hooks miss axios traffic)
```js
window.__cap = [];
const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; return oo.apply(this, arguments); };
XMLHttpRequest.prototype.send = function (b) {
  if (this.__u && String(this.__u).includes('request-otp'))
    this.addEventListener('load', () => window.__cap.push({ status: this.status, body: (this.responseText || '').slice(0, 300) }));
  return os.apply(this, arguments);
};
```
Run via CDP Runtime.evaluate, click the button, read `window.__cap`.
A fetch() monkeypatch alone captures nothing when the app uses axios/XHR.

## What does NOT pass the API-level check (all tested)
- `navigator.webdriver` spoof via Page.addScriptToEvaluateOnNewDocument
- Edge launch with `--disable-blink-features=AutomationControlled`
- Camoufox anti-detect browser (passes page-level bot checks: full page
  load, product, cart, phone entry — but the OTP API still 403s)
- Direct same-origin XHR from the page context

Conclusion: phone/OTP auth flows on Akamai-protected targets are NOT
automatable. A single human OTP entry is the minimal irreducible step.

## Adjacent findings
- Supplier panel (`supplier.meesho.com/panel/v3/new/root/login`,
  username+password, no OTP) — both provided test accounts returned
  "Invalid credentials" on the web panel. Verify creds once, then pivot.
- Valmo unauth tracking API (`GET /api/valmo-web/track-order?request_id=<ts>&tracking_id=<id>`)
  — 200 + JSON with NO auth; Spring backend (error shape
  `{timestamp,path,status,error,message,requestId}`, `/api/valmo-web` prefix
  stripped to `/api/...`). Strict server-side AWB-format validation rejects
  all guessed formats (`{"success":false,"remarks":"Invalid AWB/Tracking ID"}`)
  — demonstrating PII impact needs ONE real AWB (from a program-authorized
  test order), otherwise it stays a lead, not a finding.
- WAF XSS filtering observed on Valmo join-us POST (403 on `<script>` payload).
- Java class-name disclosure in Spring 400 bodies (e.g.
  `com.valmo.controllers.impls.ValmoJoinUsControllerImpl`) — recon intel;
  usually N/A per program fingerprinting rules.

## Pivot playbook (user preference: autonomous)
1. One probe per wall — if the auth API 403s under automation, it will keep
   403ing. Do NOT iterate bypass attempts beyond a single documented check.
2. Pivot to what works without auth: OSS-source-code programs (Vercel OSS),
   unauth API surface of other assets, or the human-OTP path offered once.
3. OSS audit loop (proven): `git clone --depth 1` in-scope repos →
   map structure → paste high-risk files into the GLM CLI (prompt from ARGS,
   not stdin, when args present) → verify claims against code → append
   verified candidates to findings.md. Never submit externally; human review.
