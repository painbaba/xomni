# Bot-Protection Bypass Playbook (Cloudflare / Akamai / AWS) — for authorized in-scope testing only

Source: 300-agent fast swarm + 50-agent web-browsing swarm (2026-08-08), full report at
`C:\Users\HP\ai-workforce\swarm\report_botbypass.md` (2,800+ lines) + `matrix_botbypass.csv`.
This file is the condensed, hunt-actionable version. Hard boundary: test ONLY in-scope
assets with program permission. Origin/IP-reputation findings often need impact framing
(defense-in-depth) to get accepted.

## Layer model (the mental map)
No single "full bypass" exists — every vendor is layered. Attack in this order:
1. ORIGIN-FIRST: get past the CDN edge entirely (bypasses WAF + bot manager + rate limits at once).
2. WAF EVASION: if stuck at edge, evade the rule engine (payload encoding, parser mismatch).
3. FINGERPRINT EVASION: defeat TLS/browser fingerprinting for bot-managed endpoints.
4. API-SHIFT: find endpoints the bot protection doesn't cover (mobile APIs, v1/v2 variants, GraphQL).

## 1. Cloudflare — origin IP discovery (highest ROI, lowest dup risk)
- DNS history: SecurityTrails / ViewDNS / PassiveTotal — the A record from BEFORE they proxied.
- Grey-cloud subdomains: dev/mail/direct/staging subdomains often DNS-only (not proxied) → same origin IP.
- Certificate transparency: crt.sh → Censys/Shodan for certs issued to origin hostnames/SANs; misconfigured origins present backend IP in SAN.
- Favicon hashing: `http.favicon.hash:` on Shodan/Fofa finds clones of the same origin server.
- Email/webhook leaks: trigger an email or webhook; raw headers show origin IP.
- MX/SPF records: mail servers often sit on the origin network.
- Tooling: CloudFlair (CT-log based), shodan queries, netlas/fofa/criminalip.

## 2. Direct origin access (once IP known)
- Host-header manipulation + direct IP (SNI = origin, Host = domain) — reach origin, WAF gone.
- Verify via TLS cert difference (origin cert issuer/CN ≠ Cloudflare's) and missing CF headers (cf-ray, server: cloudflare).
- X-Forwarded-For / CF-Connecting-IP / X-Real-IP spoofing defeats IP-allowlist rules at origin.
- Cloudflare "orange vs grey cloud" DNS setting determines reachability — grey = no protection at all.

## 3. Cloudflare WAF evasion
- HPP (duplicate params), Unicode/double-URL-encoding, chunked Transfer-Encoding, JSON content-type confusion, multipart boundary tricks, case+comment injection (`/**/`), payload fragmentation (slow fragments defeat signature inspection).
- Cloudflare managed rules are regex-based — normalization mismatch between WAF and backend is the core class.
- 403 diagnosis: cf-ray header + "Cloudflare" in body = edge block; missing = app-level.

## 4. Akamai
- G2G (ghost-to-ghost) header abuse and True-Client-IP spoofing — origin-access classes; defenses = strict header stripping.
- CVE-2020-9295 (Akamai WAF bypass) — the canonical encoding/normalization bypass, still referenced.
- Bot Manager: JS challenges + device fingerprinting. Page-level passes with Camoufox, but auth-API 403s persist (measured on Meesho — API-level wall not beatable via headers). "Bot or Not" interactive captcha = human-solve only.

## 5. AWS
- CloudFront → S3/ALB direct origin access (missing OAC / security-group misconfig); X-Forwarded-Host abuse.
- AWS WAF: JSON body inspection limits (oversize body bypass), X-Forwarded-For rate-limit spoofing, geo-match spoofing, Re2 regex limitations.
- API Gateway: invoke-URL exposure (the default .execute-api URL often bypasses WAF attached to custom domain), stage variables.
- SSRF → IMDS metadata chain; IMDSv1 vs v2.

## 6. Bot detection general
- TLS fingerprinting: JA3/JA3S/JA4 — bypass with curl-impersonate / pyhttpx / tls-client (browser-accurate TLS).
- HTTP/2 fingerprinting (Akamai): needs a real browser stack.
- Headless detection: navigator.webdriver, canvas/WebGL — Camoufox handles these.
- CAPTCHA: Turnstile/reCAPTCHA v3 scoring research exists; service-based solving violates ToS; the cleaner finding class is "CAPTCHA not enforced on API endpoint" (direct API access).

## Honest wall taxonomy (measured 2026-08, do not burn turns re-proving)
- Cloudflare JS challenge: PASSABLE — Camoufox solves; then call target API from INSIDE page context (same-origin fetch carries cf_clearance).
- Akamai API-level 403: NOT header-beatable — pivot.
- Shape Security ("767 Help Me") / Akamai captcha ("Bot or Not"): human-solve only — pivot.
- Real-browser fingerprint binding: cf_clearance pasted cross-browser gets re-challenged — wait 15-25s, verify via document.title.

## Reporting reality
- Origin-IP / WAF-bypass findings often closed as N/A without demonstrated impact — chain to a concrete vuln (data leak, auth bypass, rate-limit abuse) before filing.
- Rate-limit bypass: accepted only with impact; test sparingly (program rules), 10 rapid valid calls to baseline = enough evidence.
- Duplicate risk is HIGH for CDN-bypass classes (popular technique) — check program hacktivity + known dups first.
- Key resource: github.com/0xInfection/Awesome-WAF (the definitive WAF-evasion library — bookmark).
