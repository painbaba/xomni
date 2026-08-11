---
name: hermes-whatsapp-pairing
description: Pair Hermes to personal WhatsApp via Baileys bridge QR.
---

# Hermes WhatsApp Pairing (Baileys bridge)

Use when connecting a personal WhatsApp account to Hermes (`hermes whatsapp`,
`hermes gateway setup` → WhatsApp), or resuming a pairing that was parked.
The hermes-agent bundled skill is the general reference; this captures the
bridge mechanics measured 2026-08.

## Entry points
- `hermes whatsapp` — interactive wizard: mode → phone number → bridge
  deps install → QR scan → writes WHATSAPP_ENABLED. This is the personal-
  account path (WhatsApp-Web emulation via Baileys; no Meta account).
- `hermes whatsapp-cloud` — Meta Business Cloud API (needs a business
  account + public webhook URL) — NOT for personal accounts.
- `hermes gateway run` (foreground) / `hermes gateway install` (Windows
  Scheduled Task) — start the gateway AFTER pairing succeeds.

## The wizard flow (interactive — drive via a PTY)
1. Mode: `1` = separate bot number (needs a 2nd number) / `2` = personal
   self-chat (message yourself). User's case = 2.
2. Phone number (self-chat allowlist, digits only e.g. 9198xxxxxx): empty
   = no allowlist (agent answers ALL inbound) — safe to skip and set later
   via re-running the wizard (it prompts "Update allowed users?").
3. Bridge deps install (npm, one-time; silent — give it 60s+).
4. QR pairing (see below).
5. After pairing: WHATSAPP_ENABLED=true is written to .env ONLY on
   success — the wizard is abort-safe by design; killing it at any point
   leaves no half-state (next run starts clean).

## Remote/relayed pairing — the PNG pipeline (the reliable path)
Relaying the ASCII QR through chat CORRUPTS it (terminal line-wrap
truncates; user sees "its trimmed"). Always render a real PNG from the
raw payload:

1. Run the bridge directly with JSON output (needs a TTY — see pitfall):
   ```
   cd <hermes-home>/hermes-agent/scripts/whatsapp-bridge
   node bridge.js --pair-only --pair-json --session "C:\...\whatsapp\session"
   ```
   (session dir = `<hermes-home>/whatsapp/session`; run via
   terminal background=true + pty=true, then `process wait/poll`.)
2. Each line is JSON: `{"ts":..., "event":"qr", "qr":"https://wa.me/
   settings/linked_devices#2@ref,pubkey,identity,secret,1"}`.
3. Render: python qrcode + pillow, `qrcode.make(raw)`, resize 400-700px,
   save to a fixed path. **Strip the terminal line-wrap newlines from the
   raw payload first** — the PTY wraps long base64 (~75 chars); the true
   payload is one continuous string (exactly 4 commas = 5 fields). A
   wrapped payload renders a QR that won't scan. Prefer the hardened
   pipeline in the hermes-gateway-pairing skill (its `scripts/qr_png.py`
   strips whitespace itself; note the argv order — `-` for stdin — and
   pass Windows-style `C:/...` paths, native Windows python3 can't read
   MSYS `$HOME/...` paths).
4. Open it: `powershell.exe -NoProfile -Command "Start-Process
   'C:\path\qr.png'"` (Windows). `cmd //c start "" "file"` is UNRELIABLE
   from git-bash — silently fails or opens a stray cmd window (measured:
   user never saw the image). Windows Photos does NOT auto-reload a
   changed file — re-run Start-Process after each re-render on rotation.
5. QR ROTATION: a new `qr` event every ~20s (only the first `ref` field
   rotates while the pubkey/identity/secret stay constant within a
   pairing session). `"event":"disconnected","reason":408` = pairing
   timeout → bridge starts a NEW session (all fields change). Re-render +
   reopen on each rotation; keep a 700px render for easier scanning.
6. Success signal: `creds.json` appears in the session dir; then start
   the gateway and have the user self-chat to verify (agent replies are
   prefixed '⚕ Hermes Agent').

## LIVE QR SERVER — preferred over static PNG renders
Static PNG renders die within the ~20s rotation; the user ends up scanning
an expired code and WhatsApp says "can't link" (measured 2026-08-09).
Built: `C:\Users\HP\AppData\Local\hermes\whatsapp\qr_server.py` (canonical copy: this skill's `scripts/qr_server.py`) — serves
http://127.0.0.1:8765; the page re-renders the QR every 3s from
`qr_payload_live.txt` (joined payload, one line, no whitespace). On each
bridge rotation, just overwrite that file with the latest joined payload —
the open browser tab updates itself, no reopen needed. Start:
`python3 qr_server.py` (background), open tab:
`powershell Start-Process 'http://127.0.0.1:8765'`. Verify with curl
(`/` → 200 html, `/qr.png` → 200 png) before handing to the user.

## Pitfalls (measured)
- BEFORE sending via the gateway, verify pairing state: `creds.json` present in the session dir AND `WHATSAPP_ENABLED=true` in .env. An EMPTY session dir = bridge not connected (pairing parked; needs a human QR scan — impossible autonomously). Report that honestly and use a different real channel rather than claiming a WhatsApp send.
- The bridge process dies with "stdin is not a tty" when stdout is
  redirected to a file in a plain background shell — it needs a PTY.
  Use terminal background=true + pty=true; read JSON lines via
  `process poll/log`, not a file.
- Windows PTY input: a bare `process submit` of `"2"` echoed but the
  Enter didn't register — a bare `\r` (carriage-return-only submit)
  flushed it and the wizard advanced. If a wizard looks stuck after an
  answer, submit `\r` before re-answering.
- `pip install qrcode pillow` goes to the wrong interpreter in a
  mismatched env — use `python3 -m pip install qrcode pillow` with the
  SAME interpreter you run the render script with.
- Stale `watch_patterns` notifications keep firing from KILLED bridge
  processes (buffered QR output) — they self-disable after 3 rate-limit
  windows; ignore them, watch the live process only.
- WhatsApp bans third-party bridges on spam/bulk use — conversational use
  only; prefer a dedicated number for anything beyond self-chat testing.
- Unfinished pairing leaves no broken state (abort-safe wizard): to
  resume, just re-run the bridge with --pair-json and re-render.
- User reports WhatsApp "can't link" on scan: almost always a STALE QR
  (they scanned a render older than the ~20s rotation) or a temporary
  per-number cooldown after repeated expired-QR attempts. Re-sync the
  newest session payload to the live server and retry once; if it still
  refuses, wait ~10 min or restart the bridge for a clean session.
- Allowlist semantics (bridge.js): WHATSAPP_ALLOWED_USERS unset = ALL
  incoming messages REJECTED (secure default); "*" = explicit open bot;
  set the user's own international number (e.g. 918602852438) for
  self-chat. Set it in .env BEFORE `hermes gateway run`, or self-chat
  gets silence.

## State (as of 2026-08-09, late)
PAIRED and CONNECTED (creds.json + full session keys in
C:\Users\HP\AppData\Local\hermes\whatsapp\session; user
918602852438:11@s.whatsapp.net). The scan landed via the LIVE QR tab
after several failed static-PNG attempts — live server + fresh-session
sync is the winning path. .env set via sed -i: WHATSAPP_ENABLED=true and
WHATSAPP_ALLOWED_USERS=918602852438 (direct --pair-only bridge does NOT
write .env — only the wizard does; set manually). `hermes gateway run`
shows "[Whatsapp] Bridge ready (status: connected)" + "Bridge started on
port 3000" and is running as a background process (proc_398d5a2549ca).
AUTO-START INSTALLED (2026-08-09): `hermes --accept-hooks gateway
install` — UAC skipped → Startup-folder fallback: Hermes_Gateway.vbs in
C:\Users\HP\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\
Startup\ (task script gateway-service\Hermes_Gateway.cmd). NOTE:
--accept-hooks is a GLOBAL flag — goes BEFORE `gateway install`, not
after. Usage: user self-chats on WhatsApp (Message
Yourself); replies prefixed '⚕ Hermes Agent'. Cron jobs can now
deliver='whatsapp'.
