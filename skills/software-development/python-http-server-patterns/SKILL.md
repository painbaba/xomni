---
name: python-http-server-patterns
description: Fix Python http.server handler hangs and body-loss bugs.
---

# Python stdlib http.server: subclassing & debugging patterns

Class-level playbook for extending `BaseHTTPRequestHandler`/`ThreadingHTTPServer`
and for the classic "server accepts connections but never responds" failure.

## The pre-read trap (root cause of most handler hangs)
If you override `handle_one_request()` and pre-read `self.rfile` (e.g. to enforce
a header-budget cap), you CONSUME the request line + headers. The stdlib
`super().handle_one_request()` then does `self.raw_requestline = self.rfile.readline(65537)`
— which blocks on the now-empty socket until the socket timeout, then closes.

Symptoms (all three together = this bug):
- curl: `HTTP 000` / exit 28, then exit 52 (empty reply) at EXACTLY the socket
  timeout (e.g. 10.002s when `timeout = 10` on the handler class).
- The server logs nothing for the request (do_GET/do_POST never run).
- GET and POST both hang; the server starts fine and prints its "listening" line.

Fix options:
1. Don't pre-read: parse the request line stdlib-style first, budget the headers
   after, reconstruct via `http.client.parse_headers(io.BytesIO(hdr))`, then
   dispatch to `do_*` directly — the clean-room approach (incident example in
   references/bank-recovery-incident.md).
2. Or pre-read into a buffer and feed it back with a chained reader (below).

## Chained reader pattern (feed consumed bytes back to the parser)
```python
class _PrefixedReader(io.RawIOBase):
    def __init__(self, prefix, tail):
        super().__init__()
        self._head = io.BytesIO(prefix)
        self._tail = tail          # original socket makefile (BufferedReader)
    def readable(self): return True
    def readinto(self, b):
        n = self._head.readinto(b)
        return n if n else self._tail.readinto(b)
    def readline(self, size=-1):
        line = self._head.readline(size)
        return line if line else self._tail.readline(size)
# in handler: self.rfile = _PrefixedReader(header_block, self.rfile)
```
CRITICAL: never wrap this in `io.BufferedReader`. Its read-ahead over-reads the
socket; when the raw reports 0 (client closed / EOF) BufferedReader auto-closes
itself → later reads raise `ValueError: readline of closed file`, or POST body
reads block in `socket.recv_into`. A `RawIOBase` subclass with its own
`readline()` avoids both. Note: this pattern keeps the socket tail, so POST
bodies survive — a plain `io.BytesIO(block)` swap breaks every body read with
`{"error": "read failed"}`.

## Diagnosis order for "accepts but never responds"
1. `netstat -ano | grep :PORT | grep LISTENING` — check for MULTIPLE listeners.
   Windows permits double binds (SO_REUSEADDR); the NEWEST binder wins new
   connections. Two instances = requests route to the newer one; killing the
   wrong PID leaves the hang. Kill ALL instances, verify the port is free, relaunch.
2. Watch for auto-relaunching supervisors/watchdogs that resurrect the process
   within seconds of a kill (they race your relaunch). Kill the launcher too, or
   launch and verify within the same command.
3. Raw-socket probe: connect, send a request, wait. If the connection closes at
   exactly the socket timeout with zero bytes, the handler is blocked in a READ
   (pre-read trap or rfile rewrap bug) — not the accept loop. If it never closes
   and never responds, suspect a stuck accept/dispatch path instead.
4. GET works but POST returns "read failed" / hangs: body bytes are being lost —
   the rfile replacement dropped the socket tail.
5. Behavior contradicts the source (runtime SyntaxError the source does NOT
   have, or a code fix that has no effect): STALE/TAMPERED `__pycache__`.
   A .pyc can be stale or deliberately poisoned while the .py is clean — the
   classic symptom is "compiles fine, then throws at line N on a line that is
   obviously valid". Run with `-B` (no bytecode cache), purge `__pycache__/`,
   re-copy the source, retest. Verify which file actually loads:
   `python -c "import module; print(module.__file__)"` — and `grep -c` the
   expected symbol in BOTH the .py and the .pyc's source (a module that lost
   a class/function while the canonical .py still has it = stale cache/old copy).
6. Capture the stuck thread's stack with the stdlib alone (no py-spy on
   Windows): `import faulthandler; faulthandler.dump_traceback_later(12, exit=True)`
   at import time, then make the failing request. The dump names the exact
   blocking call (e.g. `_read_body -> _PrefixedReader.readinto -> socket.recv_into`)
   and instantly separates "stuck in body read" from "stuck in accept loop".

## Multi-instance watchdog write-war (the subtle "accepts but never responds")
Root-caused on the hardened bank (Aug 2026): a server that starts fine, prints "listening", accepts TCP, but EVERY request hangs until timeout — with NO pre-read/re-wrap bug in the handler. The cause was TWO instances sharing one SQLite DB, where each instance derives a RANDOM per-boot internal secret (a canonical salt for its integrity watchdog). Each watchdog then sees the OTHER instance's admin row as "tampered" and rewrites it every ~2s; the two watchdogs fight over the DB in an endless write war. That permanent SQLite write churn starves every DB-touching request on the lock (`_db_lock`) → TCP accepted, request hangs.

Symptoms:
- `GET /` connects but returns 0 bytes until socket timeout (like the pre-read trap, but handler code is clean).
- Log shows doubled/alternating `INTEGRITY REPAIR` lines (two writers repairing each other's "tampering").
- Killing one instance makes requests work again instantly — the write war stops.
- Reproduces on MULTIPLE Python versions (3.11 + 3.14) — it's a logic bug, not interpreter state.

Fixes (all four together = verified working):
1. **Derive the salt DETERMINISTICALLY from a stable input** (e.g. ADMIN_PASS env value), not `os.urandom()` at boot — all instances converge to the same secret and stop flagging each other.
2. Make watchdog repair **convergent/targeted** (repair the specific tampered row, never full-table wipes) so repairs can't race.
3. `PRAGMA journal_mode=WAL` on the DB connection — reduces lock contention between readers/writers.
4. `allow_reuse_address = False` on the server class so a second instance FAILS TO BIND instead of double-binding the port (kills the zombie-instance class entirely).

When a "fixed" server still hangs: check for a second listener FIRST (`netstat`), then check the log for doubled integrity-repair lines before assuming the handler is broken.

## Hostile stdlib hooks (argv-conditional in-process patches)
`http.server` can be patched AT THE STDLIB LEVEL: a hook appended to
`Lib/http/server.py` runs on import and, when `os.path.basename(sys.argv[0])`
matches the target (e.g. `bank_server_v2_app.py`), monkeypatches the app's
Handler in-process (master backdoor login, drained balance, neutered watchdogs).
Symptom: the server behaves differently when run under its own name vs. under
a launcher — and `inspect.getsource` of the handler shows clean stdlib code.
Defenses:
- Run the app through a launcher script (different argv[0]) so the hook's
  condition never arms — `python -B launch_bank.py` instead of the raw file.
- Verify stdlib provenance before trusting behavior:
  `python -c "import http.server; print(http.server.__file__)"` then grep that
  file for hook markers; also remember a VENV SHARES ITS BASE INTERPRETER'S
  STDLIB — "switch to the venv python" does NOT escape a poisoned stdlib, only
  a different python.org install does (check with `py --list`).

## Tracing a handler WITHOUT editing the server source
String-patching a copy of the source (sed-style `src.replace`) breaks
indentation and leaves stale files that poison later imports. Instead, load
the module under a fresh name and monkeypatch the class:
```python
import importlib.util
spec = importlib.util.spec_from_file_location("svc", r"C:\path\server.py")
svc = importlib.util.module_from_spec(spec); spec.loader.exec_module(svc)
def traced(self): print("enter", flush=True); return orig(self)
svc.Handler.handle_one_request = traced
import threading; threading.Thread(target=svc.serve, daemon=True).start()
```
Run with `python -B` so a poisoned pyc of the copy never loads. When the trace
shows `setup -> handle_one_request -> (hang)` with no do_* entry, the block is
between request-line read and dispatch — the rewrap or the pre-read.

## Clean-room handle_one_request: set self.requestline
If you reimplement `handle_one_request` and skip `self.requestline`, the first
`send_response()` call raises `AttributeError: 'Handler' object has no
attribute 'requestline'` (via `log_request`) — surfaced to clients as a bare
`RemoteDisconnected`. Set `self.requestline = raw_requestline.decode(...)` as
soon as you parse the request line.

## Socketpair test harness (no port races)
```python
s1, s2 = socket.socketpair()
# client thread: s2.sendall(req); s2.recv(...)
h = Handler(s1, ('127.0.0.1', 0), None)
h.handle_one_request()
```
Instantiate the handler directly over a socketpair and drive it in-process —
catches pre-read/rewrap bugs in seconds without binding ports or fighting
supervisors. Runnable copy: scripts/socketpair_handler_test.py

## Verify global declarations with ast.parse
After moving `global X` statements to function tops, verify structurally:
```python
import ast
src = open(f, encoding='utf-8').read()
ast.parse(src)  # SyntaxError check
tree = ast.parse(src)
for n in ast.walk(tree):
    if isinstance(n, ast.FunctionDef) and n.name in ('setup', 'finish'):
        print(n.name, [t.names for t in n.body if isinstance(t, ast.Global)])
```
Also grep for stray `global` lines inside `with:` blocks — a `global` declared
after the name is used in the same function is itself a SyntaxError.

## Windows git-bash + curl traps
- Windows-native curl does NOT understand MSYS `/tmp` paths: `-c /tmp/ck.txt`
  fails with curl exit 23 (cookie-jar write error) and breaks `&&` chains —
  use relative paths or `C:/...` absolute paths.
- On this host use `powershell -Command "Stop-Process -Id X -Force"` rather than
  `taskkill //PID ...` (git-bash mangles `//`-prefixed flags).

## References
- references/bank-recovery-incident.md — full incident write-up (machine-city
  ACME bank recovery, 2026-08): dual bug, first-fix failure, multi-instance war.
- references/stale-pyc-and-stdlib-hooks.md — pyc poisoning defeating code fixes,
  argv-conditional stdlib hook (zsysmon2), interpreter inventory, the
  faulthandler stack that pinned the body-read hang, minimal-repro ladder.
