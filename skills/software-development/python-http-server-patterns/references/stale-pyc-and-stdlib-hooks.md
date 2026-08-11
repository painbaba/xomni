# Stale pyc poisoning + stdlib hook — machine_city bank debugging (2026-08)

Incident addendum to bank-recovery-incident.md: after the code fix, the server
STILL hung. Two environment-level causes, both reproducible.

## 1. Poisoned/stale __pycache__ defeats every code fix
Sequence that wasted the most time:
- `python bank_server_v2_app.D8-canonical.py` (fresh copy of a clean source)
  → `SyntaxError: name '_conn_count' is assigned to before global declaration`
  at line 338, a line that was valid in the source.
- `ast.parse(src)` on the SAME file → OK. `py_compile` → OK. Runtime → broken.
- After re-copying the file AND deleting `__pycache__/`, running with `-B`
  → server works. A stale/tampered `.pyc` was shadowing the clean source.
- Worse: an imported COPY (`bank_dbg.py`) that had silently lost a class
  (`grep -c _PrefixedReader` → 0 while the canonical file had 2) kept the hang
  alive for several more rounds — the import used the stale module, so "the
  fix" had no effect.

Rules that fall out:
- If runtime behavior contradicts the current source, suspect bytecode cache
  FIRST. `python -B` + `rm -rf __pycache__` is the fastest control.
- After copying a server file for debugging, delete its `__pycache__` too.
- Verify what actually loaded: `module.__file__`, and grep the expected symbol
  in the file on disk.

## 2. Hostile stdlib hook (zsysmon2) — arms by argv[0] basename
`C:\Users\HP\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\Lib\http\server.py`
had an appended hook: on import, if `basename(argv[0]) == "bank_server_v2_app.py"`,
it starts a poller that monkeypatches the app's Handler (ghost master login
`ghost2/GH0ST-MASTER-2026`, `/balance` forced to 0.01, transfers faked, in-bank
watchdogs neutered, keeper thread re-tampering the DB every 2.5s).
- `inspect.getsource(Handler.handle_one_request)` shows pristine stdlib — the
  hook patches INSTANCE methods at runtime, not the source.
- Fix: launcher with a different argv (`launch_bank.py` imports the canonical
  file via `importlib.util.spec_from_file_location`) — condition never arms.

## 3. Interpreter inventory on this host (which python is which)
- `python` in git-bash → uv cpython 3.11 (base; stdlib carries the hook above).
- hermes venv python → built ON TOP of the uv 3.11 base → SAME stdlib
  (`http.server.__file__` points into the uv tree). No escape.
- `py -3.14` / `C:\Users\HP\AppData\Local\Programs\Python\Python314\python.exe`
  → python.org build, pristine stdlib (only installed python.org copy).
- `python --version` in different shells resolved to DIFFERENT interpreters —
  always `which python` + `sys.executable` before blaming the code.

## 4. faulthandler stack that ended the hunt
```
faulthandler.dump_traceback_later(12, exit=True)  # at import, before serve()
```
Dump (trimmed): handler thread in
`_read_body -> _json_body -> _handle_login -> do_POST -> handle_one_request`,
blocked at `_PrefixedReader.readinto -> self._tail.readinto(b) ->
socket.recv_into` — i.e. POST body read through the rewrap chain blocked on the
socket even though the client had sent the body. That pinpointed the fix
(clean-room handler: read request line + headers with budget, rebuild headers
via `http.client.parse_headers(io.BytesIO(...))`, restore the ORIGINAL rfile
for body reads, set `self.requestline`).

## 5. Minimal-repro ladder that isolated stdlib vs app code
1. Minimal stdlib `ThreadingHTTPServer` on another port → works? stdlib OK.
2. Minimal + `timeout` class attr + setup/finish overrides → works? not those.
3. Minimal + custom `handle_one_request` pre-read/rewrap → works? then the app
   module context matters (stale import / stdlib hook), not the pattern alone.
4. Import app module under a fresh name (spec_from_file_location), monkeypatch
   Handler methods with `print(..., flush=True)` wrappers, `serve()` in a
   daemon thread → observe exactly which stage blocks.
