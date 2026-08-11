# PoC-First Verification — Candidate Findings Must Be Tested

The rule that turned a near-false-positive into a clean ledger entry:
hypothesis → deterministic test → verdict. Refuted candidates get marked
REFUTED so nothing re-chases them.

## Worked example: just-bash symlink-escape (vercel/eve, 2026-08-07)

### The hypothesis (looked like a real sandbox escape)
Evidence chain from `packages/eve/src`:
1. `bindings/just-bash-runtime.ts:96` — ReadWriteFs created with
   `allowSymlinks: true`, `maxFileReadSize: MAX_SAFE_INTEGER`, root = a
   cache dir (host file-backed virtual FS).
2. `just-bash-runtime.ts:112` — `Sandbox.create({ ..., network: {
   dangerouslyAllowFullInternetAccess: true } })` — full egress.
3. `just-bash-runtime.ts:131-137` — `readFileBytes(path)` calls
   `filesystem.readFileBuffer(path)` with the model-supplied path.
4. `local-backend-utils.ts:50-55` — `resolveWorkspacePath` returns
   absolute paths UNCHANGED (`/etc/passwd` stays absolute).
5. Model controls bash (`ln -s`), file writes, and read_file paths.
Attack sketch: prompt-injected message or malicious repo plants a symlink
(`.env -> /host/.ssh/id_rsa`), read_file follows it, host content leaks
and exfiltrates via the full egress.

### The PoC (20 lines, assert-based)
```js
// install: cd scratch && npm install just-bash
const { ReadWriteFs } = require("just-bash");
// rwfs = new ReadWriteFs({ allowSymlinks: true, root: <sandbox root> })
// fs.symlinkSync(<host secret file>, <root>/link-to-host)  // absolute target
// buf = await rwfs.readFileBuffer("link-to-host")
// leaked = buf.toString().includes(secretMarker)
// exit 0 = blocked (defense holds)  |  exit 1 = escape confirmed
```

### The verdict
```
blocked: EACCES: permission denied, 'link-to-host' resolves outside sandbox
PASS: symlink outside root is confined (no escape)   (exit 0)
```
just-bash's ReadWriteFs resolves symlink targets and REJECTS anything
outside root. Sandbox holds. Candidate marked REFUTED in
`C:\Users\HP\vercel-audit\findings.md` with the PoC path; regression test
lives at `C:\Users\HP\vercel-audit\poc\symlink-escape.js` (`npm run test`
→ PASS).

### Why the hypothesis failed (the lesson)
The flags (`allowSymlinks: true`, absolute-path passthrough, full egress)
LOOK like an escape but the external library enforces confinement at
resolution time. Framework-level grep evidence is not proof — the actual
dependency's behavior is the ground truth. Always test the dependency,
not just the caller.

## General recipe
1. Grep chain builds a hypothesis with file:line evidence.
2. Identify the ONE external behavior the finding depends on (symlink
   resolution, quoting, signature compare, path join).
3. Install the dependency in a scratch dir; write a deterministic assert
   test (exit 0 = safe, exit 1 = vulnerable); run it.
4. Wire it as `npm run test` in the scratch package.json so the verdict is
   repeatable and citable in the findings log.
5. Verdict: CONFIRMED (write finding with PoC attached) or REFUTED (mark
   in findings.md, keep the test as a documented security property).
