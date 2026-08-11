# DEFENDER-4 R2 — transport/protocol + resilience (ACME bank, port 9988)

Session role: transport hardening + "supervisor respawns the bank within seconds of any kill".
Validated on scratch port 9997, then deployed under live fire (freezer pins app source to clean
c3f3a3d5 every 3s; 18× d10_duo_guard respawners; GHOST-2 deleted-file kill daemons).

## 1. Raw-socket transport probe battery (def4_r2_probe.py pattern)
Send raw bytes over a socket (NOT urllib) to test parser-level behavior. Test list + what healthy looks like:
- CL.TE / TE.CL / TE:chunked / TE:gzip → 400 (any Transfer-Encoding != identity must be rejected BEFORE Content-Length trust)
- duplicate Content-Length (same + differing), non-numeric CL, negative CL → 400; huge CL → 413
- CRLF in a header VALUE (`X-Evil: a\r\nSet-Cookie: admin=1`) → must NOT be reflected in the response
- 200KB header block → 431 (stdlib http.server has NO header-size cap; 200 = open memory DoS)
- 100KB request line → 414 (stdlib caps request line at 65537)
- unknown methods (BREW/CONNECT/PROPFIND) → 501; TRACE/OPTIONS/DELETE/PATCH → 405 (or your override); method/path mismatch (GET /transfer, POST /balance) → 404
- versionless / HTTP/0.9 request line → stdlib http.server ACCEPTS it and serves 200 (open); HTTP/2.0 request line → 400/501 (reject non-1.x)
- HTTP/1.0 + `Connection: keep-alive` with TWO pipelined requests → exactly ONE response (HTTP/1.0 closes after one request; if the server processes the second, you have a smuggling/pipelining primitive)
- slowloris: send partial request, measure when the server closes (Handler.timeout=15 → close ~13.5-15s; RST is fine, must NOT stay open 25s+)
- connection flood: N parallel connections (250) → server must stay alive; with a cap, held-connection saturation must produce 503, and after the hold timeout the port serves 200 again

## 2. Working transport patches (Python http.server; all scratch-verified, full suite green)
- **Header-block cap WITHOUT the pre-read bug**: wrap `self.rfile` in a capped reader ONLY around
  `super().parse_request()` and restore it in a `finally` (parse_request reads request line + headers
  only; the body is read later via the original rfile). Capped reader raises a custom
  `_HeaderTooLarge(ValueError)` when cumulative bytes > cap; handler writes a raw
  `HTTP/1.0 431 ... Connection: close` and returns False. The alternative — readline-looping the
  whole request BEFORE super() — consumes the body stream and breaks every POST/PUT (documented
  pitfall in SKILL.md; this is the working variant).
- **HTTP/0.9 rejection**: after `super().parse_request()` returns True, `if self.request_version == "HTTP/0.9": send_error(400); return False`. urllib/verify suites send HTTP/1.1 so the contract is safe.
- **Connection cap with clean FIN (not RST)**: `ThreadingHTTPServer` subclass with
  `threading.BoundedSemaphore(MAX_CONN)`; acquire non-blocking in `process_request`, release in
  `process_request_thread` finally. On cap-exceed: `sendall(b"HTTP/1.0 503 ...")` →
  `shutdown(socket.SHUT_WR)` → drain recv with `settimeout(0.3)` → `close()`. Naive `close()`
  with unread buffered request bytes → RST (client sees WinError 10053 / ConnectionAbortedError).
- **SO_EXCLUSIVEADDRUSE** in `server_bind()` (Windows): a second instance REFUSES to bind →
  double-bind/split-brain becomes impossible (verified: dup spawn tracebacks at bind).
- **Cold-start canonicalization (always-wipe)**: clean build's `init_db` seeds only when users table
  is EMPTY → a leftover/planted DB balance is silently ADOPTED on restart (observed live: tampered
  384,540.12 served; later a drained 0.01 instance served /balance). Fix: every boot
  `DELETE FROM transfers/accounts/users` + `INSERT OR REPLACE` exactly admin @ BASELINE with a fresh
  salt. External DB-pinning guards re-anchor on the salt change (verified convergent). Planted
  ghost77+0.01 → boot → exactly [(admin)] @ baseline, ghost77 login 401.
- SOCK_TIMEOUT env wiring: `Handler.timeout = SOCK_TIMEOUT` (env default) instead of hardcoded 15.

## 3. Supervisor design (resilience deliverable; measured respawn 2-7s across 5 kill-tests)
Conservative loop, poll 2s — the opposite of a kill-all supervisor (which caused 6-listener wars):
- Port dead → restore source integrity, kill stray `*bank_server*` procs, spawn ONE. Recheck the port
  IMMEDIATELY before `Popen` — with N sibling respawners racing you, someone else may have just bound
  it; skip if so ("respawn skipped").
- Listener up → contract probe `POST /login admin/admin123`: **200 = healthy (dedup if >1 listener,
  keep NEWEST pid — most likely your own spawn); 429 = LOCKOUT STORM, NOT a hijack — leave alone
  (killing on 429 loops forever while the attacker wrong-pass floods); 401/403/5xx/conn-refused =
  hijacked/misconfigured build → kill + respawn**.
- FAIL_WAIT grace (~10s) between respawn events so a churny ecosystem doesn't self-amplify.
- Source sha-gate at spawn: if app file hash is neither the clean sha nor your hardened sha → restore
  clean from .CLEAN before spawning (poison-source TTP). Verified: poisoned app.py + kill → clean
  restored, /ghost 404, healthy in 7s.
- Single-instance lock file with stale-PID tolerance (`os.kill(pid,0)` in try/except; dead PID → proceed).
- **Self-respawning launcher**: wrap the supervisor in a `while: check-alive (wmic cmdline grep);
  sleep 2` loop; spawn children with `creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`,
  `stdin=DEVNULL`. Battle evidence: plain bash-background children of the agent session died 3× at
  ~60-90s with exit 127 and NO output (externally killed, not crashed) while hostile daemons ran;
  the launcher+detached supervisor survived 140s+ immediately after the daemons vanished.

## 4. Hostile kill-daemons (GHOST-2, observed)
- `gf2_keeper.py`, `svc_health.py`, `svc_watch.py` processes ran with cmdlines whose script files
  exist NOWHERE on disk (filesystem search = 0 hits) — the wave-1 `sys_health_agent` disguise.
  Their presence correlated exactly with defender-tool deaths (~60-90s cycles); they vanished ~00:44
  (swept by another defender) and my supervisor+launcher stopped dying.
- Detection recipe: `wmic process where "name like '%python%'" get ProcessId,CommandLine` →
  for every process whose script name you don't recognize, search the filesystem for that file.
  A running process with no on-disk script = deleted-file daemon = hostile (legit defenders' scripts
  exist as files).
- Report them in the intel channel with the cmdline patterns so other defenders sweep them.

## 5. Windows / git-bash battle quirks (re-verified this session)
- `taskkill //F //PID <pid>` FAILS in git-bash ("Invalid argument/option - '//F'"); `cmd //c` is
  flaky. Reliable one-liner: `powershell -NoProfile -Command "Stop-Process -Id <pid> -Force"`.
  Python `subprocess.run(["taskkill","/F","/PID",...])` is fine (no MSYS mangling).
- Other defenders' restore/sweep tools taskkill ANY process whose cmdline matches `*bank_server*`
  (d8_watchdog sweep) — a scratch test copy named `bank_server_v2_app_def4_r2.py` gets killed mid-test.
  Name scratch copies so the cmdline does NOT match the product pattern (e.g. `d4r2_scratch_app.py`
  still matched — go further: `transport_scratch.py`).
- Bash bg sessions report exit 127 / empty output for externally-killed children — check
  `wmic process` + your own log file (last loop line) for liveness, never trust the bg session status.
- Multi-guard churn makes verify_v2 flap: require EXACTLY one listener, then run verify twice — both
  green = real. F3 flake mid-churn is a port-war artifact, not a regression.

## 6. Results at handoff
- verify_v2 = FUNCTIONAL 3/3, VULNERABILITIES 0/16 (2 of 3 runs fully green; 1 F3 flake during churn).
- Balance canonical ledger (1,254,490.12 = baseline - legit suite drains); single listener;
  supervisor + launcher alive; hardened build snapshot + supervisor scripts on disk in bank-war/.
- Files: `bank_server_v2_app_def4_r2.py` (hardened), `defender4_supervisor.py`,
  `defender4_supervisor_launcher.py`, `def4_r2_probe.py`.
