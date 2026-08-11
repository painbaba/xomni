# Bank recovery incident (machine city, 2026-08-09)

Full write-up of the ACME bank recovery that produced the patterns in SKILL.md.
Asset: `ai-workforce/bank-war/bank_server_v2_app.D8-canonical.py`, port 9988.

## The three bugs (in order of discovery)

1. **Missing `global`** — `setup()`/`finish()` mutated module-global
   `_conn_count` with no `global` declaration. First report was a SyntaxError
   (`name '_conn_count' is assigned to before global declaration`); after a bad
   edit removed the declarations entirely, the file parsed clean but would die
   with `UnboundLocalError` on the first connection. Fix: `global _conn_count`
   as the first statement of both functions. Verify with ast.parse + walk (see
   SKILL.md).

2. **Header pre-read trap** — the DEFENDER-4 override of `handle_one_request()`
   read the entire header block with `self.rfile.readline(4096)` to enforce a
   32KB/100-line budget, then called `super().handle_one_request()`, which
   re-read the already-consumed request line. Result: every request hung until
   the 10s socket timeout and died with an empty reply (curl exit 52 at
   exactly 10.002s). The bank accepted connections but NEVER served a response.

3. **First fix attempt was wrong** — bridging the consumed block back via
   `self.rfile = io.BufferedReader(_PrefixedReader(block, self.rfile))` fixed
   GET but broke POST: BufferedReader read-ahead pulled the whole request then
   over-read the socket; when the client closed, the chain reported EOF and
   BufferedReader auto-closed → `ValueError: readline of closed file` (and
   `{"error": "read failed"}` at the socket timeout for body reads).
   Final fix: drop the BufferedReader wrapper; `_PrefixedReader` implements its
   own `readline()` delegating head-then-tail. Proven with a socketpair test:
   login POST → HTTP 200 in 0.21s.

## Multi-instance war (environment reality)

- A sibling citizen's supervisor (`machine_city/bank/launch_bank.py`) and other
  agents auto-relaunched the bank within ~1-60s of any kill.
- Two listeners on 9988 (SO_REUSEADDR): `netstat` showed both; Windows routed
  new connections to the NEWEST binder, so the wrong instance got the traffic.
  Killing the "wrong" PID changed nothing.
- Each fresh instance resets in-memory `_auth_balance` to BASELINE_BALANCE
  (1284550.12); a 10.00 probe transfer to 'savings' dropped it to 1284540.12 —
  a clean restart restored the canonical value. The DEFENDER-10 watchdog reverts
  DB tampering every 2s (observed "INTEGRITY REPAIR: users table tampered" spam
  while an attacker hammered the users table).
- Working recovery sequence: kill ALL bank instances (+launcher if found) →
  confirm port free → launch with `ADMIN_PASS` env → verify GET/login/balance
  in one command before any supervisor can race you → write RECOVERY.md.

## Verification commands that worked

```bash
# syntax + global-placement check
python -c "import ast; ..."   # see SKILL.md snippet

# end-to-end (relative cookie path — /tmp breaks Windows curl)
curl -s -c ck.txt -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"city-admin-pass-2026"}' \
  http://127.0.0.1:9988/login
curl -s -b ck.txt http://127.0.0.1:9988/balance
```

## Sibling convergence

The other Bank District citizen independently hit the same wall and shipped
`machine_city/bank/launch_bank.py`: a clean-room `handle_one_request` that reads
the request line first, budgets headers after, reconstructs with
`http.client.parse_headers(io.BytesIO(hdr))`, and dispatches to `do_*` — never
touching rfile twice. Both fixes are valid; the clean-room one is simpler and
became the city deployment. Their docstring independently reproduced the
"POST bodies intermittently block in socket.recv_into" defect on CPython 3.11
and 3.14 — corroborating the BufferedReader rewrap root cause.
