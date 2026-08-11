---
name: hermes-gateway-pairing
description: "Use when pairing a Hermes gateway QR (WhatsApp/Baileys)."
---

# Hermes Gateway QR Pairing (WhatsApp/Baileys + pattern)

## When to use
The user wants Hermes reachable on a messaging platform — WhatsApp personal
account ("connect to my whtaspp"), re-pairing after a WhatsApp protocol
update, or any gateway that pairs via a QR scan. This is the recipe that
actually gets the QR into the user's hands when the terminal relay mangles
it. (The bundled `hermes-agent` skill covers gateway config broadly; this
skill is the pairing-specific recipe that took a full debugging session to
work out.)

## The two WhatsApp paths
- `hermes whatsapp` — Baileys bridge, PERSONAL account, QR pairing, no Meta
  account. This is the one for a personal number. Ban risk exists (unofficial
  bridge) — keep usage conversational, no bulk.
- `hermes whatsapp-cloud` — official Meta Business Cloud API; needs a
  Business account + public webhook URL. Not for personal use.
Prereq: Node 18+ (`node --version`; v24 present on the user's box).

## Wizard flow (`hermes whatsapp`, interactive — run in a PTY)
1. Mode: `1` separate bot number (needs a SECOND number) vs `2` personal
   self-chat (message yourself). User's personal account → `2`.
2. Phone whitelist: self-chat asks for the user's own number in
   international digits (`9198...`). Empty input = NO allowlist = the agent
   replies to ALL incoming messages (warning printed). Number can be set
   later by re-running the wizard.
3. npm install of bridge deps (first run, can take minutes — the process
   looks frozen with ~0 CPU while installing; be patient, check
   `Get-Process node` for a new node PID).
4. QR pairing (see capture technique below).

## PTY input quirk (Windows) — CR, not LF
The wizard's `input()` prompts can STALL on a plain `submit("2")` — the
echo shows the char but the prompt never advances. Fix: `submit("\r")`
(a bare carriage return) — the process tool sends data+Enter, but on this
PTY the Enter alone doesn't register; an explicit `\r` flush advances the
prompt. After every wizard input, poll to confirm the prompt moved before
sending the next value.

## THE core technique — QR relay that survives chat
Do NOT copy the ASCII QR from the process output into your reply — the
terminal relay TRUNCATES it and the scan fails ("its trimmed"). Instead:

1. Killing the wizard mid-QR is fine (it leaves no broken state — the
   wizard only writes WHATSAPP_ENABLED after successful pairing).
2. Run the bridge directly with raw-QR JSON output, in a PTY:
   `node "<HERMES_HOME>\hermes-agent\scripts\whatsapp-bridge\bridge.js" --pair-only --pair-json --session "<HERMES_HOME>\whatsapp\session"`
   (background=true + pty=true; watch_patterns `["\"event\":\"qr\""]`).
   It emits JSON lines: `{"ts":...,"event":"qr","qr":"<raw payload>"}`.
   The `qr` string is WRAPPED across lines in the PTY output — the payload
   is one continuous string; join the fragments before rendering.
3. Render a real PNG: `python3 -m pip install qrcode pillow` (note: `pip`
   alone may target a DIFFERENT interpreter than `python3` on Windows —
   always `python3 -m pip`), then `scripts/qr_png.py "<joined payload>"`.
4. Open the PNG for the user — `cmd //c start "" "path"` and
   `explorer.exe "path"` BOTH failed to show the image on this box
   (cmd printed a banner with no visible window; explorer exited 1, no
   window). The VERIFIED opener is
   `powershell.exe -NoProfile -Command "Start-Process 'C:/path/whatsapp_qr.png'"`
   (forward slashes). They scan with WhatsApp → Settings → Linked
   devices → Link a device. (For ACTIVE scanning skip the PNG entirely —
   use the LIVE QR server section below; static PNGs lag the 20s
   rotation and the user scans an expired code → "Can't link device".)
5. QR ROTATION: Baileys rotates ~every 20-30s; each rotation emits a new
   `qr` event (same pairing session = same middle fields, only the ref
   changes; after `{"event":"disconnected","reason":408}` = pairing
   TIMEOUT, a NEW session starts = all fields change). On rotation,
   re-render + reopen the PNG with the LATEST event. On `reason:408`,
   the old PNG is dead — immediately render the new session's QR.

## LIVE QR server — the reliable path for ACTIVE scanning
Static PNGs go stale: the QR rotates every ~20s and by the time the user
actually looks at the rendered PNG it is usually ALREADY EXPIRED —
scanning it makes WhatsApp say "Can't link device", and re-render/reopen
loops frustrate the user. When the user is at the phone NOW, run a live
server instead: a browser tab that re-renders every 3s from the latest
payload, so what's on screen is always current (verified working, the
pipeline that ended the failure loop):

1. Write the joined payload (whitespace stripped, one continuous string)
   to `<hermes-home>/whatsapp/qr_payload_live.txt`.
2. Start the server (deployed at `<hermes-home>/whatsapp/qr_server.py`,
   verified 2026-08-09):
   `cd <hermes-home>/whatsapp && python3 "C:/Users/HP/AppData/Local/hermes/whatsapp/qr_server.py"`
   (background=true). Port 8765; renders the QR from the payload file on
   EVERY request — no restart needed when the payload changes.
3. Open the tab: `powershell.exe -NoProfile -Command "Start-Process
   'http://127.0.0.1:8765'"` (the only opener verified to work on this
   box — see item 4 above). Page auto-refreshes every 3s.
4. On every new `qr` event in the bridge log, overwrite
   qr_payload_live.txt with the new joined payload — the open tab picks
   it up within 3s. No Photos, no reopen, no stale scan.
5. After `reason:408` disconnect a NEW session starts: ALL fields change
   (pubkey/identity/secret too). Write the full new payload immediately;
   the old one is dead.

## TTY requirement (measured)
The bridge refuses plain background runs: stdout redirect to a file yields
19 bytes "stdin is not a tty" and exit — the message comes from the bash
wrapper, but the effect is the bridge needs a PTY. Always launch with
pty=true and read the JSON events via process poll/log, not from a file.

## Post-pairing
- Success: `creds.json` appears in the session dir; the wizard writes
  WHATSAPP_ENABLED=true to .env (it does NOT write it before pairing).
- Start the gateway: `hermes gateway run` (foreground) or
  `hermes gateway install` (Windows Scheduled Task, auto-start on login).
- Self-chat usage: open WhatsApp → Message Yourself → agent replies
  (responses prefixed '⚕ Hermes Agent').
- Cron delivery: once paired, cron jobs can `deliver='whatsapp'` — CLI
  sessions have no delivery channel, so this is THE way the user gets
  notified (e.g. nightly audit results).

## Pitfalls
- STALE WATCH-NOTIFICATIONS: after killing a pairing/wizard background
  process, its watch_patterns can keep firing on buffered output for a few
  minutes (rate-limited to one per 15s, then auto-disabled after 3
  windows). They reference the DEAD process — ignore them and poll the
  LIVE bridge process instead of being confused by duplicate "Scan this
  QR" notifications.
- LIVE-PAIRING NOTIFICATION VOLUME: while the bridge is running and
  un-scanned, a `"event":"qr"` watch_pattern fires once per rotation
  (~20s) — each new QR is a fresh match >15s apart, so the 3-window
  auto-disable NEVER triggers. Expect one notification per rotation
  (old timestamps replay out of order too). Treat them as noise: do NOT
  re-render/reopen on every one — only when the user says "refresh" or
  is about to scan. When you DO re-render, take the payload from the
  live process log's LATEST timestamp, not from the notification.
- The wizard's ASCII QR (`qrcode-terminal` style) is fine ON SCREEN but
  corrupts in chat relay — never ship it through the reply; always the
  PNG path.
- If the user misses several rotations, they're likely not at the phone —
  render the latest once and say "refresh" re-pops instantly; don't spam
  reopen windows.
- The QR payload join must happen in the render script, not by hand.
- "CAN'T LINK DEVICE" on the phone = almost always a STALE QR was scanned
  (the PNG on screen was older than ~20s, or the session had 408'd while
  the user still looked at the old image). Repeated expired scans can
  trigger a temporary WhatsApp cooldown on the number — wait a few
  minutes, or kill + restart the bridge for a completely fresh session.
- USER SAYS "WHERE IS THE QR" / image never appeared: the open step
  failed silently (cmd/explorer openers on this box) — verify the open
  actually happened, don't just re-render the same PNG, and switch to
  the live-server tab path. That frustration is a pipeline failure, not
  user error.

## Support files
- `scripts/qr_png.py` — render a scannable PNG from the raw QR payload.
  ARG ORDER MATTERS: argv[1] = payload (use `-` to read stdin), argv[2] =
  output path, argv[3] = size px. Piping stdin while passing the output
  path as argv[1] silently treats the PATH as the payload, so `img.save`
  gets e.g. "700" → "unknown file extension: ''". Correct invocation:
  `cat qr_raw.txt | python3 qr_png.py - qr.png 700`. The script strips
  whitespace/newlines itself, so feed the PTY-wrapped payload raw.
- Native Windows python3 (WindowsApps) can't read MSYS paths from
  git-bash: `$HOME/...` or `/c/...` arguments yield "can't open file
  'C:\c\...'" or a mangled output path. Pass the script and output paths
  in Windows forward-slash form (`C:/Users/...`).
- Validate before opening: payload must start
  `https://wa.me/settings/linked_devices#2@`; split on `#` then `,` =
  exactly 5 fields with the last = "1". Fields 2-4 (pubkey/identity/
  secret) stay constant within a pairing session — compare against the
  previous rendered payload to confirm a rotation vs a NEW session
  (`reason:408` timeout resets all fields; old PNG is dead).
- `scripts/qr_server.py` — LIVE QR server for active scanning: serves an
  auto-refreshing browser page (3s poll, no-store) that draws the QR from
  `qr_payload_live.txt` on every request. Run it from the whatsapp dir,
  open http://127.0.0.1:8765, then just overwrite the payload file on
  each rotation — the open tab stays current. No Photos, no reopen, no
  stale scans. Usage: `cd <hermes-home>/whatsapp && python3
  "<skill_dir>/scripts/qr_server.py" [payload_file] [port]` (defaults:
  ./qr_payload_live.txt, 8765).
