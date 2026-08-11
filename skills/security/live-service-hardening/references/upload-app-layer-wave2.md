# DEFENDER-6 wave-2 session — upload/app-layer hardening (ACME BANK, 2026-08-08)

Role: DEFENDER-6, upload/app-layer focus. Live target: `bank_server_v2_app.py` on
127.0.0.1:9988 (wave-2 build, merged with siblings DEFENDER-4 network/transport +
DEFENDER-10 in-memory state). Contract: `ADMIN_PASS=admin123 BANK_PORT=9988 python verify_v2.py`
→ FUNCTIONAL 3/3, VULNERABILITIES 0/16.

## Probe matrix — live results BEFORE patching (session+CSRF used for PUT)
| Probe | Before | After patch |
|---|---|---|
| PUT /upload/shell.py | 400 (ext allowlist) | 400 |
| PUT .txt = `<html><script>alert(1)</script></html>` | **200** | 400 (HTML magic reject) |
| PUT .txt = `%PDF-1.4 ... /JavaScript ...` (PDF smuggled as .txt) | **200** | 400 (foreign magic reject) |
| PUT .pdf = `%PDF-... /S /JavaScript` | **200** (accepted by design) | 200 |
| PUT .jpg = `\xff\xd8\xff\xe0<html><script>...` (payload after 3-byte magic) | **200** | 200 (prefix-only sniff; no server-side exec path — accepted risk, nosniff+CSP mitigate) |
| PUT .png = PNG sig + MZ/PE payload | **200** | 200 (same reasoning) |
| PUT .txt = `a`*600 + NULs (controls past byte 512) | **200** (sniff scanned only first 512) | 400 (whole-body scan) |
| PUT /upload/..%2f..%2fwin.ini, %252e%252e%252f… | 400 | 400 |
| PUT no X-CSRF | 403 | 403 |
| PUT .txt body = `{"csrf":"WRONG"}` + VALID X-CSRF header | **403** (body overrode header!) | 200 (header authoritative) |
| PUT .txt body = `{"csrf":"<correct>"}` | 200 | 200 (legacy fallback kept) |
| PUT empty body | 400 | 400 |
| PUT 65537 bytes | 413 | 413 |
| PUT flood 25× in 0.5s | **25×200, no limit** | 12×200 then 429 (15/60s per session; 4 pre-flood probes had consumed budget — cap runs before sniff) |
| GET /upload/<registered> | 200 | 200 |
| GET /upload/<planted/unknown> | n/a | 404 (registry) |
| GET /api/keys | 403 | 403 |
| GET /admin no session | 401 | 401 |
| Hidden sweep (25 paths: /debug /status /health /flag /secret /env /.env /console /metrics /actuator /swagger /openapi.json /trace …) | all 404 | all 404 |
| GET /upload/CON.txt, NUL.txt | 404 (Windows device-name quirk not live-exploitable via full-path open) | 400 (blacklisted anyway) |

## Patches applied (bank_server_v2_app.py, all confirmed live)
1. `_sniff` (.txt): whole-body control-byte scan + foreign-magic prefix blacklist
   (`%PDF-`, PNG/JPEG/GIF sigs, `PK\x03\x04`, `MZ`, `\x7fELF`, `<html`, `<!doctype`,
   `<script`, `<svg`, `<?php`, `<?xml`).
2. CSRF precedence: X-CSRF header authoritative; JSON-body `csrf` legacy fallback only.
3. `MAX_UPLOADS_PER_WINDOW=15/60s` per session + `MAX_STORED_UPLOADS=400` global cap → 429.
   Cap check placed BEFORE name parse/sniff so rejected uploads still consume budget.
4. GET serving: in-process `_uploaded` registry (set, guarded by `_upload_lock`), only
   API-uploaded names served; `os.path.islink` refused; `os.fstat` + `stat.S_ISREG` required.
5. Boot-wipe of `UPLOAD_DIR` in `init_db()` (removes files AND symlinks).
6. Windows reserved device names (`CON/PRN/AUX/NUL/COM1-9/LPT1-9`, stem check) blacklisted
   in `_parse_upload_name`.
7. Killed stale wave-1 `bank_server.py` dual-listener (SO_REUSEADDR co-bind, PID 960/19508)
   — that build was a fake-upload stub (echoed "uploaded" without storing) and its /admin
   leaked card number `4111-1111-1111-1111`.

## Coordination learnings (this session)
- Sibling `sa-3-cb465520` (D4+D10) modified the file at 23:47 mid-task → "modified by
  sibling subagent" warnings on every patch. Merges were clean; verified with
  `grep -c 'DEFENDER-6'` = 9 markers + `python -m py_compile`.
- Sibling restarted the listener AFTER my patches → live server had D6 behavior despite
  me never restarting. Proved it behaviorally (smuggle→400, flood→429, header-CSRF→200),
  NOT by PID/mtime. `wmic process where "name='python.exe'" get processid,commandline`
  maps PID → script for the port owner.
- Intel channel: append with `cat >> … <<'EOF'` worked fine here (contrary to earlier
  "heredocs trip the guard" note — YMMV); include PID, restart ownership, balance delta,
  live verification numbers.

## Final state
verify_v2.py: FUNCTIONAL 3/3, VULNERABILITIES 0/16. Balance 1274530.12 (baseline − $10 F3
− $5k V16 − probes). Port 9988 sole-owned by PID 14172 (`bank_server_v2_app.py`).
Probe script artifact: `bank-war/def6_probe.py`.
