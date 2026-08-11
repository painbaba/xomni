---
name: windows-gitbash-terminal
description: Use when git-bash calls Windows python/node from this host.
---

# Windows git-bash terminal ops

## When to load
- Any terminal command on this Windows host that mixes bash (git-bash/MSYS) with native Windows binaries (python3, python, node, npm).
- Error signatures to recognize instantly:
  - `python3: can't open file 'C:\c\Users\...'` — python received an MSYS path.
  - `node: Cannot find module 'C:\c\Users\...'` — same class of bug for node.
  - `FileNotFoundError` on `/c/Users/...` from a python one-liner, while bash `cat` reads the same file fine.
  - `curl -o /tmp/x.html` prints HTTP 200 but `wc -c /tmp/x.html` says "No such file or directory" — native Windows curl.exe misparses `/tmp/` and writes where bash's MSYS `/tmp` isn't. Same class of bug, opposite direction: the tool wrote somewhere bash can't see.

## The core rule
bash builtins and MSYS tools understand `/c/Users/...` paths; native Windows binaries do NOT — they misparse `/c/` as `C:\c\`. Any script that passes an absolute path to python3/node MUST convert it first.

## Proven fixes
1. In bash wrappers (the durable fix):
   ```
   DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   WINDIR="$(cygpath -w "$DIR" 2>/dev/null || echo "$DIR")"
   python3 "$WINDIR/script.py" ...   # cygpath -w: /c/Users/X -> C:\Users\X
   ```
2. For python argv: pass forward-slash Windows paths (`C:/Users/...`) — python accepts them; MSYS paths are rejected.
3. Cheapest: `cd` into the dir and use relative paths — `node --check script.js`, `python3 -m py_compile script.py` work fine relative.

## Interpreter facts on this host
- `python3` = 3.13 (WindowsApps app-execution alias); `python` = 3.11; pip may bind to a DIFFERENT version — check before pip installs.
- `node` = v24 (native). npm sometimes needs `--force` (engine-strict vs npm 10).
- Deterministic verification pattern: `node --check`, `python3 -m py_compile`, `bash -n` — no network, no auth.

## Driving interactive CLI wizards through the process tool (PTY mode, Windows)
When a wizard runs via terminal(background=true, pty=true) and you drive it
with process(action='submit'):
- The FIRST submit often fails to register the Enter — the echoed chars
  appear (e.g. `Choose [1/2]:2`) but the prompt never advances. Fix: submit
  a bare carriage return (`"\r"` via data) — that flushes the pending Enter
  and the wizard advances. (Measured 2026-08 driving `hermes whatsapp`.)
  This is the PTY CR/LF echo quirk, not a broken wizard.
- Output previews can stay STALE (same text on repeated polls) even while
  the wizard waits at a later prompt — poll after each submit, and check
  the process is alive + the node/python subprocess CPU before assuming a
  hang.
- Wizards that render a QR code (pairing flows, TOTP) draw it as ASCII
  block chars in the PTY the USER CANNOT SEE. RELAY THE QR AS A PNG, not
  verbatim ASCII: relaying the block chars through chat TRUNCATES/corrupts
  it and the scan fails (measured driving hermes whatsapp). Reliable
  pipeline:
  1. Find the underlying bridge's machine-readable QR mode — grep the
     bridge script for a JSON/`--pair-json`-style flag; it emits
     `{"event":"qr","qr":"<raw pairing payload>"}` lines to stdout. The
     RAW payload (not the ASCII art) is what you re-encode.
  2. `python3 -m pip install qrcode pillow` (mind the interpreter: pip may
     bind to a different python than `python3` — install per-interpreter),
     then `qrcode.make(raw).resize((500,500)).save(r'...\qr.png')` —
     strip terminal line-wrap artifacts from the payload first (the PTY
     wraps long base64; join the pieces back into one string).
  3. Open it for the user: `cmd //c start "" "C:\path\qr.png"`.
  4. WhatsApp/Baileys QRs rotate every ~20s and pairing sessions
     408-timeout after ~50-90s (bridge auto-starts a fresh session with
     NEW keys). If the user is slow/away, don't churn: render the latest
     on demand, or kill the bridge (abort-safe wizards leave no broken
     state) and re-pair when they're back.
- Bridges that print "stdin is not a tty" and exit when stdout is
  redirected to a file in a plain background process REQUIRE a PTY —
  always run such bridges with pty=true and read the JSON lines from the
  process output (no file redirection). The "not a tty" message can also
  be bash's own "no job control" noise; verify by checking the file/exit
  code, not the message source.
- Abort-safety: if the user goes away mid-wizard, check the wizard is
  designed to leave no broken state before killing it (hermes whatsapp
  writes WHATSAPP_ENABLED only AFTER successful pairing — aborting early
  is safe).

## Pitfalls
- Don't patch the symptom (hardcode a path, copy the file); fix the conversion — it recurs in every wrapper.
- write_file / read_file tools handle either path style fine; the trap is ONLY at runtime inside native binaries.
- Host-level env facts (hermes home, .env protection, camofox, search_files quirks) live in memory; this skill is the how-to for the path-conversion class.
