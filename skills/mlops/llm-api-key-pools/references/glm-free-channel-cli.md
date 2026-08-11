# GLM free-channel CLI: Puter + NIM dual backend (verified 2026-08-07)

## The `glm` terminal tool
Built at C:\Users\HP\glm-tool (user machine): `glm "question"` or
`echo q | glm` → Puter path first (free, no queue), NIM rotation fallback.
`glm --nim "q"` forces NIM. Verify with `npm run test` (deterministic,
network-free) and `npm run test:live` (needs authenticated channel).

Files: `glm` (bash wrapper), `glm_puter.js` (Node + @heyputer/puter.js),
`glm_nim.py` (NIM rotation single-shot), test.sh / test_live.sh.

## Puter auth token resolution (Windows)
Puter CLI (`npm i -g puter-cli`) stores credentials at:
`%APPDATA%\puter-cli-nodejs\Config\config.json`
→ `{"profiles":[{"host":"https://puter.com","username":"...","token":"<jwt>"}]}`
NOT ~/.puter or ~/.config/puter. `puter login` = browser OAuth (user step).
In Node: `init(token)` from `@heyputer/puter.js/src/init.cjs`, then
`puter.ai.chat(messages, {model:'z-ai/glm-5.2', ...})`.

## MSYS → Windows path bug (bit TWICE this session)
Bash wrappers on git-bash passing `$DIR` (MSYS `/c/Users/...`) to Windows
binaries (node, python3) fail: node reports
`Cannot find module 'C:\c\Users\...'`, python3 `can't open file`.
Fix — convert once in the wrapper:
```bash
WINDIR="$(cygpath -w "$DIR" 2>/dev/null || echo "$DIR")"
node "$WINDIR/tool.js" ...
```
Same class of bug: python3 one-liners on Windows can't open MSYS paths —
use `C:/Users/...` forward-slash Windows paths in python, MSYS paths in bash.

## Deterministic testing with a real token present
Tests that need the no-token error path break once a real token exists on
the machine (env var nulled but file lookup still finds it). Fix: honor a
force flag that skips ALL resolution:
```js
let token = null;
if (!process.env.PUTER_FORCE_NO_TOKEN) { token = process.env.PUTER_AUTH_TOKEN; if (!token) { ...file candidates... } }
```
test.sh runs `PUTER_FORCE_NO_TOKEN=1 node tool.js` for the deterministic
branch.

## NIM vs Puter routing facts
- NIM (integrate.api.nvidia.com) z-ai/glm-5.2: free, but shared worker
  pool saturates daytime — 60s probe timeouts observed for all 6 keys.
  Off-peak (00:00-06:00 IST) only. ai.api.nvidia.com alternate host is
  dead (404).
- Puter: free, rate-limited per user, Z.AI is a first-class vendor
  (model z-ai/glm-5.2). No queue observed. Best free daytime channel.
- z.ai direct (api.z.ai/api/paas/v4): valid key + zero credits = error
  1113 "no resource package"; GLM Coding Plan is paid (Lite $12.6/mo,
  ~43-87M GLM-5.2 tokens/wk). Don't send users to sign up expecting a
  free tier.
