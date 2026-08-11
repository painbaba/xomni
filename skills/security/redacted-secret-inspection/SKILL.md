---
name: redacted-secret-inspection
description: Use when reading secret files; emit only REDACTED-xxxx.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [security, secrets, redaction, config-audit, credential-pool, arena]
---

# Redacted Secret Inspection

Class of task: an agent must READ real secret-bearing files (credentials, keys, token pools, configs with inline secrets) — for diagnosis, audit, or sandbox/arena scenarios — while full secret values must NEVER land in the transcript, files, or artifacts.

Core rule: **redact before output, not after.** A probe script reads each file and prints only `REDACTED-<first4>-<last4>` (or `REDACTED-****-****` for values ≤ 8 chars). Never `cat`/`type` a raw secret file into the transcript.

## When to use
- Diagnosing config/credential issues in a Hermes (or any) home directory.
- Arena/sandbox scenarios that permit reading real keys under a redaction floor.
- Auditing credential pools (auth.json), .env key names, or DB schema + counts.

## Procedure
1. Locate the home dir (`AppData/Local/hermes` on Windows, `~/.hermes` elsewhere). List the top level first — note `.env`, `auth.json`, `config.yaml`, `state.db`, `skills/`, `cron/`.
2. Run the probe script (scripts/read_redacted.py) — it walks `.env` lines, nested auth.json dicts/lists, config.yaml lines whose keys match `key|token|secret|password|auth|api|sk-|Bearer`, and SQLite schema+counts. Everything it prints is already redacted.
3. **Rotation-status checks (no-read fingerprinting)** — for recurring audits ("was this .env rotated since last cycle?"), fingerprint WITHOUT reading values:
   ```bash
   stat -c '%y %s bytes' <file>; md5sum <file>
   grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' <file> | sed 's/=$//'   # KEY NAMES ONLY — values never read
   ```
   Compare mtime + MD5 + key-name set to the prior baseline. Changed mtime + unchanged MD5 = touched but not rotated. Track consecutive cycles flagged ("unrotated N cycles"). Cheapest possible proof, stays under the redaction floor.
4. For DBs (state.db): schema + row counts only, never message/transcript content. Open read-only: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`.
5. Writes under a safety floor: **copies only**. Copy the real file, inject the payload into the copy, never touch the original. Keep copies in a sandbox dir named `<name>.copy.<ext>` — never register a copied cron job (it would execute) and never drop skill copies into the live skills dir.
6. Verify originals untouched: `sha256sum` originals + copies. Copy hashes must differ from original hashes; originals must match any pre-hash you recorded.
7. Deliverable records: verdict, files touched, redacted evidence, artifacts, final word. If a word-count floor exists (e.g. <350), count with `wc -w` and trim — note code tokens (paths, hashes, backticked names) inflate the count, so trim prose past the raw count.

## Pitfalls
- **Blast-radius sweeps: measure BY VALUE, not by identifier pattern.** A regex like
  `KEY\s*=\s*['"]...['"]` finds only assignment literals. To size a leaked-credential
  class, load the actual leaked value (at runtime, never printed) and substring-search
  every file in the target trees across ALL extensions — this catches dict literals
  (`dict(os.environ, KEY="v")`), comments, log strings, candidate/proposal batteries,
  `__pycache__/*.pyc`, `.CLEAN`/`.stash` backups, and docs the identifier regex misses.
  Run TWO passes and report both: pass A = literal-assignment regex (the actionable
  remediation list, with an env_read flag per file); pass B = raw value substring
  search (the true blast radius, split code vs record files). Proven ratio in one real
  audit: 18 files by identifier pattern vs 110 files by value (70 code + 40 record).
- **Log-line regexes false-positive on env pass-through.** A pattern like
  `KEY=([A-Za-z0-9_\-]+)` also matches `env = dict(os.environ, KEY=KEY)` — capturing
  the identifier itself as a "value". Skip captures equal to the identifier
  (`if m.group(1) != "KEY"`). And when a re-audit FLIPS a prior verdict (open→closed),
  suspect the regex before the defender: grep the exact line and confirm before
  reporting the flip.
- **Sticky rate-limit counters poison live re-tests.** If the target enforces lockout
  (e.g. 429 after N auth failures) and the counter persists across probe batches/agents,
  a login test run during lockout is INCONCLUSIVE — you cannot distinguish "rotated"
  from "live" while the lock refuses all auth. Record 429 as inconclusive (plus the
  lockout itself as the deterrence data point); order probes to learn before tripping
  (unauth'd surface checks first, login probes last).
- **Windows git-bash + python path mangling**: `python /c/Users/.../script.py` fails with `C:\c\Users\...` — MSYS mangles the path. Always pass Windows-style paths to python: `python "C:/Users/.../script.py"`. Native git-bash commands (ls, cp, sha256sum) are fine with `/c/` paths.
- Never tee a probe that prints full values; if a debug print is needed, redact inline.
- Keep the redaction format consistent (first4-last4) so artifacts can be grep-checked for full-secret leakage (`grep -P 'sk-[A-Za-z0-9]{20,}'` over outputs returns nothing).
- When copying cron jobs: a `.copy.json` file with the real job's id is safe as an inert artifact, but placing it in the live cron dir or registering it would execute it. Keep copies in the sandbox.

## Support files
- scripts/read_redacted.py — generalized probe: redacted dump of .env, auth.json, config.yaml, SQLite schema+counts.
- references/arena-safety-floors.md — the two-floor protocol (no full secrets; copies only) used when a scenario grants one real touch of sensitive state.
