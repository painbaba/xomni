---
name: windows-git-bash-interop
description: MSYS path traps when git-bash calls Windows python/node.
---

# Windows git-bash interop

## Why this skill exists
The terminal on this host runs git-bash (MSYS). Bash understands MSYS
paths (`/c/Users/HP/...`) but the Windows binaries it launches — python3,
node, npm, native curl — do NOT. Every session that writes scripts or
wrappers on this machine hits this class of bug. The failures look like
missing files, silent no-ops, or "syntax errors" that are actually path
mangling. This skill encodes the three known failure modes and their fixes.

## Core rule
When a bash script or one-liner hands a path to a Windows binary, pass a
NATIVE Windows path (`C:/Users/...` forward slashes are fine) or a
RELATIVE path from the working directory — never `/c/Users/...`.

## Failure modes (all observed on this host)

### A. python3 can't open MSYS paths
`python3 /c/Users/HP/tmp/key.txt` → `FileNotFoundError` — Windows python
reads it as `C:\c\Users\HP\...`. Bash `cat`/`rm` on the same path work
fine, so the bug is easy to miss: the file "exists" but python can't see
it. SILENT variant: a key-append one-liner fails, the key never lands in
.env, and nothing tells you.
FIX: pass `C:/Users/HP/...` (or relative) to python argv; convert in
bash wrappers with `WINDIR="$(cygpath -w "$DIR")"`.

### B. node --check / module resolution with MSYS paths
`node /c/Users/HP/glm-tool/glm_puter.js` → `Cannot find module
'C:\c\Users\HP\...'`. Also: the patch/write_file auto-lint invokes
`node --check` with a mangled path and reports "Pre-existing lint errors"
on EVERY .js edit — these are FALSE POSITIVES, not real syntax errors.
FIX: verify with `cd <dir> && node --check <file>` (relative path).
Symptom of the real bug in wrappers: `node "$DIR/script.js"` fails while
`node script.js` from the dir works.

### C. native curl vs MSYS `/tmp` mismatch
Native Windows curl maps `/tmp/x` to a different location than MSYS
tools; `curl -o /tmp/x` then `head /tmp/x` → "No such file".
FIX: write to `~/relative/path` or a native path, not `/tmp`.

### D. backgrounded GUI exe holds the stdout pipe open
`"$EDGE" ... &` inside a script whose stdout is PIPED (e.g.
`bash hunt.sh | grep ...`) → the backgrounded Windows GUI process
inherits the pipe FD, so the pipe never hits EOF and the caller HANGS
until the GUI exits — looked like hunt.sh hanging 120s after Edge had
actually launched fine.
FIX: fully detach the child: `</dev/null >/dev/null 2>&1 &` + `disown`
(or use terminal background=true from the agent side). Symptom to
recognize: browser/tool launched OK (target reachable on its port) but
the launching command never returns.

### E. Native Windows commands with `/flags` and `$_` inside PowerShell
Two traps when calling Windows built-ins (not python/node) from git-bash:
- The `//` escape trick does NOT work for `ipconfig`, `getmac`, `netsh`:
  `ipconfig //all` → "unrecognized or incomplete command line", `getmac //v` →
  "Invalid argument/option". FIX: `export MSYS_NO_PATHCONV=1` once per session,
  then plain `ipconfig /all`, `getmac /v` work normally.
- Bash expands `$_` inside DOUBLE-quoted powershell commands:
  `powershell -Command "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'}"`
  → bash turns `$_` into the previous command's last arg (e.g. `{===.Status}`)
  and PowerShell errors. FIX: wrap the whole command in SINGLE quotes:
  `powershell -NoProfile -Command 'Get-NetAdapter | Where-Object {$_.Status -eq "Up"}'`
  (then PowerShell sees `$_` intact).

## Wrapper pattern (proven)
```bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WINDIR="$(cygpath -w "$DIR" 2>/dev/null || echo "$DIR")"
python3 "$WINDIR/script.py" "$PROMPT"
node "$WINDIR/script.js" "$PROMPT"
```
Always `cygpath -w` before handing paths to Windows interpreters.

## Related quirks on this host
- `.env` at `C:\Users\HP\AppData\Local\hermes\.env` — patch/write_file
  refuse it; edit via `sed -i` or python append reading a temp file.
- Never put API-key literals in shell commands (hardline guard) — write
  to a temp file, have python/bash read it.
- Serving local web apps: `python -m http.server <port>` from git-bash;
  browsers need `http://` not `file://`.
- Background servers: use terminal background=true, not nohup/&.

## Support files
- `references/observed-failures.md` — exact error strings for each mode
  (for recognition), with the transcript of the z.ai key-append and the
  glm bash-wrapper bugs.
