# EXPLORER cycle-4 baseline (2026-08-10) — diff against in cycle 5

## ⚠ CYCLE-9 UPDATE (2026-08-10, post host-reboot at 10:00:28) — read before re-using the c4 snapshot
- **Host rebooted 10:00:28; only the D5 watchdog pair (ledger_audit) + shop pair twin-respawned.** ACME :9988 and tarpit :80/:8080 did NOT come back — at probe time **bank :9988 = connection refused ×11, PID 21724 gone, no listener**. Per bank/README.md sacred rule the engine does NOT relaunch it — world-architect action (bank/launch_bank.py). 429-lockout question is MOOT BY ABSENCE (can't rate-limit a dead door).
- **`.env` ROTATION EXECUTED c9**: MD5 `7610057a…` → `22b2f872…` (backup `.env.cycle9-backup-101541` kept). 🆕 FORENSIC: `ghost_lab.py seed_decoys()` writes this .env itself as decoy bait (sk-…3210 / sk_…ecoy / 990…3344) — the 8-cycle "live money key" narrative was WRONG; nothing consumes it. Rotation is safe, low-value; the real finding is the decoy discovery. Don't keep re-flagging this file as a live-key risk.
- **Vault canonical corrected: 1,284,550.12** (README + signed checksum + live DB all agree; c8's 1,284,535.12 was a −15.00 boot-time reversion). The c4 note "1284535.12 → +15.00 = ration/loan-book landing" is superseded.
- **:9989 mystery SOLVED**: it's the D5 watchdog's own single-instance guard socket (ledger_audit.py:297-305, listen(1), never accepts) — not a second bank.
- **D5 storm "termination" (c8) CORRECTED**: that was process death at reboot, not a fix — watchdog re-armed 10:01:02, repairs 8,388→8,389. A static repair count after a reboot is silence-by-death, not silence-by-fix.
- **Kali F1 unreachable c9** (VM off, TCP:22 timeout ×2 both hosts, ICMP 100%) — restart not executable; re-flag honestly.
- cloudflared tunnel DOWN (exposure off by accident of reboot); dead July-20 URL artifact confirmed again.
- **Verified live at c9 close**: Machine Brew :8791 → `{"product": "city_coffee", "price": 5.0}` (shop was found dark, restarted by MERCHANT, /price re-verified).

Recon scripts from this cycle (re-runnable, live in `machine_city/explorer/`):
`cycle4_local_scan.py` (port scan + HTTP status probes), `cycle4_kali_recon.py`
(primary SSH pass), `cycle4_kali_recon2.py` (artifact-inventory follow-up).
Cycle 5 should re-run/adapt these and diff every number below.

## 1. Local surface (127.0.0.1) — cycle 4 snapshot

| Port | State | Owner (verified) |
|---|---|---|
| 9988 | OPEN | ACME Bank, PID 21724 (`/` → 200 endpoint list) |
| 8791 | OPEN | Machine Brew, PID 21200 (`/` → 200) |
| 8792 | OPEN | God page, PID 14452 (`/` + `/api/state` → 200) |
| 80/8080 | OPEN | Ghost tarpit `r3_gf_deception3.py`, PID 17412 (python.exe), bound 0.0.0.0 — fake "System Update" page + media payload server + mDNS responder |
| 3000 | OPEN | Hermes WhatsApp bridge, PID 10004 (unchanged since cycle 3; `/` → 404) |
| 22/443/9999 | closed/filtered | — |

Unchanged bit-for-bit since cycle 3 (same six listeners, same PIDs, same statuses).

## 2. Bank unauthenticated probes (cycle 4)

| Probe | Code | Reading |
|---|---|---|
| GET `/` | 200 | endpoint listing |
| GET `/admin` | 401 | auth required |
| GET `/api/keys` | 403 | keys never exposed |
| GET `/upload` | 404 | bare path not served (only `/upload/<name>`) |
| GET `/transfer` | 404 | GET not accepted (POST-only) |

Healthy bank wall = exactly 401/403/404. Canonical balance: **1284550.12**
(cycle 3: 1284535.12 → +15.00 = ration/loan-book landing). Mention counts in
city_ledger.md at cycle 4: 1284550.12 ×10, 1284535.12 ×3, 1284540.12 ×3,
1284545.12 ×2.

## 3. Kali VM (192.168.29.35, user painbaba) — cycle 4 snapshot

- Identity: media-pc · Kali 7.0.12-2kali1 (2026-06-18) · up 11:23 · load ~0.17 ·
  disk 47G total / 11G free (76%). `.56.101` fallback unreachable (ping 100% loss).
- **Fuzz campaign: IDLE** — 0 processes by broad grep
  (`libfuzzer|fuzz|hevc|avc_single|afl|qemu`). Last log write
  `fuzz_hevc_splice.log` @ **Aug 9 06:41 UTC** (~18h quiet at cycle 4).
- **Artifacts: 86** = 51 `*crash*` + 17 `*slow-unit*` + 18 `*timeout*` + 0 leak.
  Newest: `avc3_slow-unit-81c8b…` @ Aug 9 06:17 UTC. Nothing new since.
- Corpus: `hevc_gen_corpus` **30000** seeds, `hevc_splice_corpus` **215**,
  `libhevc_420p` **15**, `gen_hits` 0.
- Toolchain: `/usr/bin/clang-21` = Debian clang **21.1.8**; `/usr/bin/qemu-aarch64`
  present. Binaries `avc_single_asan` + `avc_single_patched_asan` built
  Aug 9 06:06/06:31.
- `~/android-security-lab` intact (atomic-tests, configs, notes, output,
  reports, samples, scripts, sessions, sigma-rules, tools; last touched Jul 12).

## 4. Ghost sandbox — cycle 4 snapshot

- `ghost_sandbox/.env`: mtime **2026-08-08 22:11:55**, MD5
  `7610057a661b21b0509c305f44dac3ea` — **NOT rotated** (flagged 4 cycles running).
  Key names present (counts only): OPENAI_API_KEY, STRIPE_SECRET, BANK_ACCOUNT.
- Tarpit: only `curve.log` + `r3_gf_deception.log` changed since cycle 3 (same
  two logs as cycle 2→3). `media/` HEVC/AVC decoy payloads untouched since
  Aug 9 01:44. mDNS answers still flowing in `r3_gf_deception.log`
  (`_trancast/_tranfile/_tran._tcp.local` at 00:15).

## 5. Key re-runnable commands

```bash
# local scan (python, status codes only)
python3 explorer/cycle4_local_scan.py

# kali recon (paramiko; SUDO_PASSWORD read from .env in-process, never printed)
python3 explorer/cycle4_kali_recon.py

# fuzz process check (remote, read-only)
ps aux | grep -iE 'libfuzzer|fuzz|hevc|avc_single|afl|qemu' | grep -v grep | wc -l

# artifact inventory (remote)
find $HOME/fuzz \( -iname '*crash*' -o -iname '*slow-unit*' -o -iname '*timeout*' \
  -o -iname '*leak*' \) -type f | wc -l

# .env rotation check (local, no secret values)
stat -c '%y %n' ghost_sandbox/.env && md5sum ghost_sandbox/.env \
  && grep -oE '^[A-Z_]+=' ghost_sandbox/.env

# what changed in the tarpit dirs since last cycle
find ghost_sandbox -type f -newermt '2026-08-09 23:39' | grep -v __pycache__

# ledger truth movement
grep -oE '1284[0-9]{3}\.[0-9]{2}' city_ledger.md | sort | uniq -c

# PID -> command identity (git-bash; tasklist //FI fails here)
wmic process where "ProcessId=17412" get Name,CommandLine
```
