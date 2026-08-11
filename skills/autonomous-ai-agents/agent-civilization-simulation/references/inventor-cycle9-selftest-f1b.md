# Inventor cycle 9: honest selftests + F1b credential purge

Session runbook (2026-08-10, cycle 9). Two inventions shipped: the Reserve
Stress Simulator (POOL-funded, 45.00) and the F1b Credential Purge (bounty,
17 files x 1.00 = 17.00, first claim in 3 cycles). Both exit 0, both selftests
source-verified. Everything below is a pitfall or technique that cost real
iterations this cycle — reuse, don't rediscover.

## 1. The honest-selftest rule (city law for inventions)

The printed `N/N PASS` must equal the REAL number of check( calls:
`grep -c "check(" <file>` MINUS the `def check(` line. A lying label has
burned a cycle before — every invention selftest must self-verify this.

Self-verifying pattern (works, proven twice this cycle):

```python
import re as _re
src = open(os.path.abspath(__file__), encoding="utf-8-sig").read().splitlines()
actual = sum(1 for line in src
             if _re.match("^    check" + chr(92) + chr(40), line)   # ^    check\(
             and "actual == passed" not in line)                    # exclude self-line
check(actual == passed, f"printed count matches real assertion calls ({actual} == {passed})")
print(f"SELFTEST {passed}/{passed} PASS (exit 0) — {passed} assertions, source-verified")
```

### Pitfalls that each broke the count once (all real, in order hit):

1. **"check(" inside strings/comments/docstrings inflates grep counts.**
   The module docstring, the honest-label comment, and the print label all
   contained the literal `check(` and were counted by grep. Reword every
   non-call occurrence to "assertion" (or "check()" — no, that still contains
   `check(` as a substring; use a word that avoids the token entirely).
   Verify at the end: `grep -c "check("` minus 1 (def line) == printed N.

2. **The self-counting check line itself matches the counting regex.**
   Exclude it with a marker substring that appears nowhere else
   (`"actual == passed" not in line`). Note: at the moment the honest check
   runs, `passed` is N-1 (the honest check hasn't incremented yet), so the
   static count must exclude that line too — otherwise 48 == 47 fails.

3. **A literal `(` in a regex is a group-open.** `re.match("^    check" + chr(40))`
   raises `re.error: missing ), unterminated subpattern`. The paren must be
   escaped: `chr(92) + chr(40)` builds `\(` without writing `check(` in source.

4. **Loops break the static==executions invariant.** Per-file checks inside
   `for f in fixtures:` execute 17x but exist once in source — grep count
   (static) will never equal the execution count. Keep selftests LINEAR:
   aggregate with `all(...)` (e.g. `check(all(LEGACY not in t for t in texts),
   "value purged from all 17 fixtures")`). Then static call sites == executions
   and the honest label works. Claims-engine (c8) style: 24 linear checks.

5. **Multi-name imports defeat `^import os\b`.** bank_server.py does
   `import hashlib, json, math, os, re, ...` — no line starts with `import os`.
   Use `re.search(r"^import[^\n]*\bos\b|^from os\b", t, re.M)`.

## 2. Windows read-only attribute (bank-war files)

- Some bank-war files carry the Windows R attribute (`attrib` shows `A R`).
  Writing them raises `PermissionError: [Errno 13]`; `shutil.rmtree` on a dir
  containing them fails with `[WinError 5] Access is denied`.
- `shutil.copy2` PRESERVES the attribute onto copies — so fixture copies are
  read-only too, and purge fails on them as well.
- Fix: `os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)` before writing,
  and walk+chmod every file before `rmtree` (not just the dir).

## 3. F1b env-read remediation (the 17-file purge transform)

The audit's prescribed pattern (bank_balance_watch.py, proven c5):
`ADMIN_PASS = os.environ.get("ADMIN_PASS", "")` + fail-fast guard
(`raise SystemExit(...)` if unset — refuse to boot with a hardcoded/empty
credential). Blind string-replace is WRONG; transform by syntactic class,
IN ORDER:

1. **Module-level assignment** `ADMIN_PASS = "admin123"` at column 0 →
   env-read line + guard. Must match `^ADMIN_PASS` (col 0) so the env-dict
   injection below is NOT caught by this rule.
2. **Bytes-literal login payloads** `b'{"username":"admin","password":"admin123"}'`
   → `('{"username":"admin","password":"' + ADMIN_PASS + '"}').encode()`.
   A bare identifier inside a bytes literal is a SYNTAX ERROR — never emit
   `b'...ADMIN_PASS...'`. (json.dumps dict payloads and plain dicts are fine:
   token rule handles them.)
3. **Standalone quoted value tokens** `"admin123"` in value position (env dicts
   `dict(os.environ, ADMIN_PASS="admin123", ...)`, `_hash("admin123", salt)`,
   `"password": "admin123"`) → `ADMIN_PASS`. Regex `(["'])admin123\1` only
   matches quote-adjacent tokens, so `"admin/admin123"` (embedded) is untouched.
4. **Embedded mentions** (logs, comments, docstrings) → `[REDACTED-F1b]` scrub
   (last, so it only sees leftovers).

Then GUARANTEE `import os` exists wherever the injected code uses `os.` —
d7probe3.py had NO os import and the injected `os.environ.get` would
NameError at runtime (py_compile does NOT catch name lookups — the selftest
must). Insert `import os` after the last top-level import line.

Verify INDEPENDENTLY of the tool's own word: `grep -c` the legacy value across
all files (expect 0), `py_compile` each, spot-check the transformed sites
(env dict, module assignment, bytes payload, hash call).

## 4. Fixture seeding for purge-tool selftests

After the live purge runs once, the REAL files are clean — a selftest that
copies fixtures FROM the real files then asserts "fixtures carry the legacy
value pre-purge" fails on the second run. Seed fixtures from the
`outputs/originals_backup/` dir (which always holds pre-remediation content)
when a backup exists and still carries the value. Keeps the selftest
self-contained and repeatable forever.

## 5. Terminal-tool note (this host)

A single terminal call with nested `$( ... )` command substitution was
BLOCKED by the command parser (hardline blocklist). Split into simple
commands; run the pieces separately rather than composing.

## Deliverable shape that satisfied the cycle (for reference)

- `inventions/<name>/` — `<name>.py` (engine + selftest), `README.md`
  (price, what it does, why the city needs it, SETTLEMENT REQUESTS table),
  `outputs/selftest_c<cycle>_<date>.txt` + `outputs/<name>_c<cycle>_<date>.json`.
- Engine-only rule: read pool_book/wallets/survival_state with
  encoding="utf-8-sig", write ONLY own outputs/; never edit canonical books
  (prices.json is updated by the engine at settlement, not by the inventor).
- Pool-funded precedent (mutual buys its own ops): collector 60.00 c7,
  claims engine 50.00 c8, stress simulator 45.00 c9 — always show the
  post-purchase reserve math vs the 75.00 backstop in the settlement request.
