# XOMNI Quickstart — running in 5 minutes

XOMNI = the Hermes host + 17 plugins (647 tests), 170 bundled skills, 25
verified free models, a 311-server MCP catalog, and a sponsorship engine that
pays you for installs. No API keys required.

**Prerequisites:** Python 3.11+ with `hermes` on PATH (`hermes --version`);
Node.js 18+ (only for npx-based MCP servers, step 6).

## 1. Install (one command)
```bash
run.cmd      # Windows (cmd or git-bash)
./run.sh     # POSIX / git-bash
```
Starts the Hermes host with all 17 plugins loaded and best-effort boots the
bundled Ollama runtime so local models work with zero extra installs.

## 2. First launch — what you see

`[XOMNI] starting host + 17 plugins...`, then the interactive prompt, a status
line in the terminal title bar (`title-statusline`), and a **sponsor line**
while the agent works (that line pays you — see step 7).

## 3. Check the free models
```
/models              # live status + list of the 25 verified free models
/models coding       # filter: fast | reasoning | coding | vision | frontier
```
`/provider` prints the ready-to-paste config snippet for every agent in the
stack (Hermes/OpenCode/Codex/Aider/Goose).

## 4. Try a skill

All 170 skills (42 domains) in `skills/` load automatically — just ask:

- **docx** — "create a Word document with a title and a table"
- **youtube-content** — "summarize this YouTube video's transcript"
- **cloudflare** — "deploy a Worker to Cloudflare"

## 5. Run a first task
```bash
run.cmd chat -q "List the files in this repo and summarize what XOMNI is."
run.cmd --continue    # resume your last session
```
## 6. Connect an MCP server (real example from the 311-server catalog)

From `data/mcp/catalog.json`, entry **`filesystem`** (official reference
server, FREE, no API keys — secure file ops scoped to an allowlist):
```json
{
  "name": "filesystem",
  "category": "MISC",
  "price_model": "FREE",
  "install_command": "npx -y @modelcontextprotocol/server-filesystem /path/to/allowed/files",
  "connect_steps": [
    "hermes mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem <allowed-dir>",
    "Restrict to the directories the agent may touch",
    "Restart and verify: ask the agent to list files in the allowed directory"
  ]
}
```
Copy-paste, restricted to this repo:
```bash
hermes mcp add filesystem -- npx -y @modelcontextprotocol/server-filesystem C:/Users/HP/xomni
hermes mcp list          # confirm filesystem shows up
```
Restart (or `/reload-mcp`), then verify with a read-only tool call:
```
List the files in C:/Users/HP/xomni
```
Windows npx note: use config.yaml `mcp_servers.filesystem: {command: "cmd",
args: ["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem",
"C:/path/to/allowed"]}`.

## 7. The sponsor line, explained

`waitperk` + `perkline` plugins count one **impression** per agent work event
(LLM or tool call) while the line is on screen. Your earnings are
`0.5 × P × (your impressions / total network impressions)` — 50% of the
sponsor's payment, capped at `0.5 × P`, with signed receipts and escrow.
`/sponsor` shows your ledger.

## 8. Verify the install
```bash
cd plugins/repomap && python -m unittest tests.test_core -v   # 15 tests
```
Full suite: 647/647 pass. See `docs/VALIDATION.md`.

## Next steps

- `docs/FEATURES.md` — everything the 17 plugins do · `docs/SELLING.md` — the
  go-to-market plan · `data/mcp/catalog.json` — all 311 servers
  (`hermes mcp add <name> -- <install_command>`)
