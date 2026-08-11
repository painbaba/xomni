---
name: hermes-messaging-pairing
description: "Use when pairing Hermes gateway bridges (WhatsApp QR)."
---

# Hermes Messaging Bridge Pairing (Windows)

## Why this skill exists
Pairing a personal WhatsApp (or other QR-paired messaging platform) to the
Hermes gateway on Windows has three traps that cost a session each: the
interactive wizard's Enter doesn't register over a managed PTY, relaying the
ASCII QR through chat corrupts it (user: "its trimmed"), and the first
attempts die on "stdin is not a tty". The robust path is to skip the wizard
and drive the bridge directly in its machine-readable mode, then render the
QR to a real PNG.

## The three traps (measured 2026-08)

1. **PTY Enter doesn't register.** `terminal(pty=true, background=true)` +
   `process submit` sends `\n`; the wizard's `input()` on Windows needs a
   bare carriage return. Symptom: the mode choice echoes (":2") but the
   wizard never advances; `process wait` shows the SAME frozen output.
   FIX: `process submit` with data = a bare `\r` (bytes_written: 2) to
   flush, then re-submit the actual answer. After the flush the wizard
   advances visibly ("✓ Mode: personal number (self-chat)").
2. **ASCII QR relayed through chat is corrupt.** The wizard renders the QR
   with qrcode-terminal; copying the block chars into a reply wraps/trims
   lines and the phone won't scan it. Never relay ASCII QRs — deliver a
   rendered image instead (see recipe below).
3. **Bridge dies without a TTY.** Running `node bridge.js --pair-only`
   with stdout redirected to a file exits with `stdin is not a tty`
   (exit 1, 19-byte file). Run bridge commands with `pty=true`.

## The robust recipe (WhatsApp, measured working)

```bash
# 1. Prereqs: Node v18+ (checked), python3 with qrcode+pillow
python3 -m pip install qrcode pillow     # NB: plain `pip` may target a
                                         # DIFFERENT python (pip->3.14,
                                         # python3->3.13 on this host)
# 2. Session dir + launch the bridge in raw-JSON mode (PTY, no redirect)
cd /c/Users/HP/AppData/Local/hermes/hermes-agent/scripts/whatsapp-bridge
mkdir -p /c/Users/HP/AppData/Local/hermes/whatsapp/session
node bridge.js --pair-only --pair-json \
  --session "C:\Users\HP\AppData\Local\hermes\whatsapp\session"
#   run via terminal(background=true, pty=true, watch_patterns=["\"event\":\"qr\""])
```
The bridge then emits JSON lines to stdout:
`{"ts":..., "event":"qr", "qr":"https://wa.me/settings/linked_devices#2@...,...,1"}`
- `--pair-json` (bridge.js:110) switches from ASCII QR to raw JSON emit
  (`emitPairEvent`, bridge.js:389-394); WITHOUT it you get qrcode-terminal.
- The raw `qr` string is the WHOLE WhatsApp pairing payload, wrapped by the
  PTY display into multiple lines — **strip the newlines before encoding**
  (the payload is one continuous line; 4 commas = 5 parts).
- QRs rotate every ~20-30s; the bridge keeps emitting fresh `qr` events —
  re-render the LATEST one if the user missed it. Do not restart the bridge
  per attempt.

```python
# 3. Render the QR to a PNG (strip terminal line-wraps first!)
import qrcode
raw = "https://wa.me/...#2@... ,...,1"   # single line, newlines removed
qrcode.make(raw).save(r'C:\Users\HP\recon\whatsapp_qr.png')
```
Then open it for the user and let them scan:
```bash
cmd //c start "" "C:\Users\HP\recon\whatsapp_qr.png"
```
User action: WhatsApp → Settings → Linked devices → Link a device → scan.
The scan flow: `creds.json` appears in the session dir → pairing succeeded.

## Post-pairing
- The wizard path (`hermes whatsapp`, self-chat mode) sets WHATSAPP_MODE +
  WHATSAPP_ALLOWED_USERS + WHATSAPP_ENABLED in .env and prints next steps.
  When driving the bridge directly, set WHATSAPP_ENABLED=true yourself so
  the gateway picks the platform up.
- Start the gateway: `hermes gateway run` (foreground) or
  `hermes gateway install` (Windows Scheduled Task auto-start). Check with
  `hermes gateway status`.
- Self-chat mode: user messages themselves; replies are prefixed
  "⚕ Hermes Agent". The allowlist (WHATSAPP_ALLOWED_USERS) can be left
  empty ("responds to ALL incoming messages" warning) or set later.
- Re-pairing: `hermes whatsapp` again, or delete the session dir
  (hermes/whatsapp/session) + run the bridge recipe fresh. WhatsApp
  protocol updates occasionally break Baileys bridges → re-pair after
  pulling the latest Hermes.

## Pitfalls
- NEVER relay ASCII QR through the conversation — always PNG (or a file the
  user opens). Truncated QRs look scannable and waste the rotation window.
- `process wait` output preview can stay frozen on the wizard even while
  it waits for input — poll/log, and when in doubt submit `\r` to flush.
- The wizard's output AFTER a successful input can be invisible in the
  preview until the next flush — the "✓ Mode" line appeared only after the
  bare-`\r` submit.
- `python3 -m pip install` (not bare `pip`) — this host's `pip` belongs to
  a different interpreter (python3.14 vs python3=3.13). ModuleNotFoundError
  after a successful-looking pip install = wrong interpreter target.
- Multi-line JS in one evaluate 500s the camofox evaluate endpoint; keep
  expressions small (reuse: camofox-server-ops skill for the server API).
- QR pairing is inherently interactive: the ONLY human step is the phone
  scan. Everything else (choice, number, rendering) is automatable.
