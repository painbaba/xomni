# Phone-Trap / Decoy-Bait Playbook (battle rounds)

Use when a battle round mission is: send believable bait to a target phone
number (creator-owned / authorized), lure it to a decoy link, watch the
decoy log for the hit, coordinate with a sibling agent via intel.md.

## 0. Channel audit FIRST — never assume an outbound channel exists
- hermes WhatsApp is paired ONLY if `~/AppData/Local/hermes/whatsapp/session/creds.json`
  exists AND `WHATSAPP_ENABLED=true` in `.env`. Empty session dir = bridge NOT
  connected (pairing parked; needs a human QR scan — impossible autonomously).
- SMS/API: grep `.env` for real provider creds. On this host the .env keys are
  DECOYS (`sk-fak...`, `sk_liv...ecoy`) — verify, don't trust.
- If no outbound channel: say so plainly, then make the REAL channel = live
  decoy + public URL; the creator taps from their phone (LAN IP on WiFi,
  public URL on mobile data).

## 1. Bring the decoy UP — verify, don't trust "LIVE"
- Mission context may claim the decoy is live. Prove it: `netstat -ano | grep
  -E ':(80|8080) '` plus `curl -s -o /dev/null -w '%{http_code}'` (000 = dead).
- Decoy server: `ai-workforce/ghost-lab/ghost_sandbox/r3_gf_deception3.py` —
  fake "System update" page on :80/:8080 + media/HEVC payload server
  (`/media/*`) + mDNS responder :5353 advertising `AndroidUpdate`.
  Restart: `cd ghost_sandbox && python r3_gf_deception3.py` (background=true,
  long-lived server — silent is correct).
- Confirm live: `/video.html` and `/` both 200.

## 2. Public path with NO credentials — cloudflared quick tunnel
- LAN IP (e.g. http://192.168.29.55:8080) only works when the target phone is
  on the same WiFi. Mobile data needs a public URL.
- `cloudflared tunnel --url http://localhost:8080 --no-autoupdate`
  (background=true) → anonymous trycloudflare.com URL, no account/creds.
  Grab it from the process log line "Your quick Tunnel has been created!".
  Prefer `--no-autoupdate` (Windows can't auto-update anyway).
- Verify the public URL returns 200 BEFORE putting it in the bait.

## 3. Bait drafting
- Pretext must match the decoy page (page says "System update available" →
  use a JioFiber / router-firmware-update pretext, not a random one).
- MSG-1: short, believable, low-pressure; include BOTH links (LAN + public).
- MSG-2 follow-up ~60s later: OTP-style urgency ("update window closes in
  5 min", concrete consequence like speed cap) — urgency is what gets the tap.

## 4. Coordinate via intel.md — APPEND ONLY
- `ghost-lab/ghost_sandbox/intel.md` is the shared battle channel. It carries
  a standing warning: GF once OVERWROTE it by accident — always append
  (`cat >> ... << 'EOF'`), never rewrite, mark your section with a header
  (agent + target + timestamp).
- Post: channel audit result, decoy status, both URLs, full bait text,
  follow-up text, expected tap-payload signals, watchdog note. Ask siblings
  (e.g. GHOST-2) to post their bait URL so hits get attributed by IP/UA.

## 5. Watch the decoy log for the hit
- `r3_gf_deception.log` logs every request with IP + UA.
- SELF-PROBES POLLUTE: your own curl checks log as 127.0.0.1. Filter with
  `grep -v '127.0.0.1'` — only non-localhost entries are real-device hits.
- Hit signals to report:
  - `POST /apply` (Install-now button) → `*** HUMAN TAPPED ***`
  - captive-portal probes (`/generate_204`, `/connectivitycheck`) →
    `*** ANDROID DEVICE DETECTED ***` (phone auto-hits these on WiFi join)
  - `/video.html` → autoplay MP4 + H.265 (libhevc:758 UB vector) + `/rtcproof`
    (camera-permission proof)
  - mDNS QUERY from a real IP reveals the device model in the service name.
- Leave decoy + tunnel running when done (long-lived servers); report status
  honestly if no hit yet.
