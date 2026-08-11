---
name: mcp-server-wiring
description: "Use when wiring MCP servers into agents (Hermes, Claude)."
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, configuration, hermes, claude-code, video, tools, integration]
---

# MCP Server Wiring

How to connect MCP servers to MCP-capable agents and **verify the commands before handing them to the user**. Covers Hermes Agent's native MCP client (config schema, CLI, catalog), Claude Code's `.mcp.json`/`claude mcp add` model, and a live-verification workflow so every pasted command is actually runnable. The verified video-MCP recipe (Remotion, FFmpeg, ElevenLabs, ComfyUI, YouTube-transcript) lives in `references/video-mcp-recipe.md`.

## When to use

- User asks to add/configure an MCP server in Hermes, or asks which MCP to use for a capability (video, audio, images, media).
- Comparing Hermes vs Claude Code MCP configuration, or migrating between them.
- Verifying that an MCP command from a README/docs page actually works (package exists, bin name matches, not deprecated).

## Hermes Agent (native MCP client)

**Config file:** `$HERMES_HOME/config.yaml` — top-level `mcp_servers:` dict of `name: config`. On Windows this is typically `C:\Users\<user>\AppData\Local\hermes\config.yaml`. Resolve from `$HERMES_HOME`, never hardcode `~/.hermes`. Confirm with `hermes mcp list` (empty = no servers configured yet).

**Schema per server** (stdio `command` OR HTTP `url`, never both):

```yaml
mcp_servers:
  server_name:
    command: "npx"              # stdio: required
    args: ["-y", "pkg-name"]    # stdio: list
    env:                        # stdio: subprocess env (Hermes passes a FILTERED env — only PATH/HOME/USER/LANG/TERM etc. plus what you list here; secrets MUST be listed here or in .env)
      SOME_API_KEY: "${env:SOME_API_KEY}"
    # --- OR ---
    url: "https://host/mcp"     # HTTP/StreamableHTTP: required
    headers: { Authorization: "Bearer ..." }
    auth: oauth                 # HTTP: OAuth 2.1 PKCE (browser flow on first connect)
    transport: sse              # HTTP: optional, force SSE instead of Streamable HTTP
    # --- common ---
    enabled: true
    timeout: 300                # per-tool-call, seconds
    connect_timeout: 60
    tools: { include: [], exclude: [] }   # filter; use ORIGINAL MCP tool names (hyphens/dots)
    trust: full | untrusted     # untrusted = every write-capable tool requires approval
    sampling: { enabled: true } # server-initiated LLM requests (disable for untrusted)
```

**Interpolation:** `${VAR}` and `${env:VAR}` work in any string value (env, headers, args, url); Cursor-style `${userHome}`, `${workspaceFolder}`, `${pathSeparator}` too. Secrets go in `~/.hermes/.env` (referenced via `${env:VAR}`), never plaintext in config.yaml — config is settings, `.env` is secrets.

**Tool naming:** every discovered tool registers as **`mcp__<server>__<tool>`** (DOUBLE underscore delimiter; components sanitized `[^A-Za-z0-9_]` → `_`), e.g. server `ffmpeg` tool `clip_video` → `mcp__ffmpeg__clip_video`. Verified in source: `tools/mcp_tool.py` `mcp_prefixed_tool_name()` / `MCP_TOOL_NAME_PREFIX = "mcp__"`. The convention is shared with Claude Code, Codex, and OpenCode and matches the Anthropic-OAuth wire form. (Older notes saying `mcp_<server>_<tool>` single-underscore are STALE.)

**CLI** (verify current flags with `hermes mcp --help`):
- `hermes mcp add <name> --command <cmd> --args ...` — **`--args` must be the LAST flag**; everything after it is argv
- `hermes mcp add <name> --url <URL>` | `--preset <name>` | `--auth {oauth,header}` | `--env KEY=VALUE` | `--connect-timeout <sec>`
- `hermes mcp list | test | remove | configure | catalog | install <name>`
- `hermes mcp` (no args) = interactive catalog picker
- Catalog entries are Nous-approved; e.g. `comfy-cloud` is in the catalog → `hermes mcp install comfy-cloud`
- ⚠️ **`hermes mcp add` is INTERACTIVE** — after resolving the package it prompts
  "Enable all N tools? [Y/n/select]" and a non-TTY run CANCELS silently with no server
  added. For scripted/agent installs ALWAYS pipe an answer:
  `echo Y | hermes --accept-hooks mcp add ffmpeg --command npx --args -y ffmpeg-mcp`
  then confirm with `hermes mcp list` (verified 2026-08-10: ffmpeg-mcp +
  @kimtaeyoon83/mcp-server-youtube-transcript installed this way). New tools load in
  the NEXT session — don't expect them mid-session.

**Prereqs & apply:**
- `pip install mcp` required — without it MCP support is SILENTLY disabled (check startup logs if tools don't appear).
- Node.js for npx servers, `uv` for uvx servers. Windows: use `npx.cmd`/`uvx.exe` as `command` if bare names aren't on PATH.
- Apply: restart, or rely on auto-reload (`mcp.auto_reload_on_config_change`, default true) + `/reload-mcp` slash command. Removed servers need a restart.
- `hermes import-agent claude-code` migrates Claude Code's `mcpServers` (from `~/.claude.json`) into `mcp_servers` automatically.

**Runtime / programmatic access** (source of truth: `tools/mcp_tool.py`, `tools/registry.py`, `hermes_cli/mcp_config.py` in the hermes-agent repo):

- Runtime client is `tools/mcp_tool.py`: each configured server runs as an `MCPServerTask` on a shared asyncio loop (`_connect_server`); `_make_tool_handler(server, tool, timeout)` returns the sync registry handler `fn(args_dict) -> str` (circuit breaker + auto-reconnect built in).
- **Invoke a tool from code:** `tools.mcp_tool.mcp_prefixed_tool_name(server, tool)` builds the name, `tools.registry.registry.get_entry(name)` checks registration, `tools.registry.registry.dispatch(name, args)` executes (async bridged, exceptions normalized to `{"error": ...}`). This is the PUBLIC dispatch path — a plugin/script should use it, never `_make_tool_handler` directly.
- **Live tool discovery:** `hermes_cli.mcp_config._probe_single_server(name, config)` — the same probe `hermes mcp test` runs; connects, lists `[(tool_name, description), ...]`, shuts down. Takes a bare `{command, args, env}` dict, so it works for servers NOT yet in config.yaml.
- **Security gate:** `hermes_cli.mcp_security.validate_mcp_server_entry(name, config)` blocks exfiltration-shaped stdio commands (shell+egress payloads) before a server is saved — both the CLI and dashboard save paths run it.
- **Curated catalog internals:** `hermes_cli/mcp_catalog.py` + `optional-mcps/<name>/manifest.yaml` (manifest_version 1; `transport: {stdio|http}` with pinned command/args, `auth: {api_key|oauth|none}` with prompted env vars → `~/.hermes/.env`, optional `install: git` pin + bootstrap, `tools.default_enabled`). Entries ship disabled; `hermes mcp install <name>` enables. Pins follow supply-chain rules: exact versions for `uvx pkg==X`/`npx pkg@X`, full SHAs for git refs.
- Current MCP spec revision used by Hermes: `2025-06-18`; stdio transport is newline-delimited JSON-RPC 2.0 (`initialize` → `notifications/initialized` → `tools/list` → `tools/call`).

## Claude Code (for comparison / migration)

- **Scopes:** `local` (default → `~/.claude.json` under the project entry), `project` (→ `.mcp.json` at repo root, shared via VCS), `user` (→ `~/.claude.json`, all projects).
- `claude mcp add --transport http <name> <url> [--header "Authorization: Bearer ..."]`
- `claude mcp add --transport stdio <name> -- <command> <args...>` — everything after `--` goes to the server; `-e KEY=VAL` env; `--scope local|project|user`.
- `.mcp.json`: `{"mcpServers": {"name": {"command": "npx", "args": [...]}}}` or `{"type":"http","url":...}`; `${VAR}`/`${VAR:-default}` expansion in command/args/env/url/headers.
- Official reference: https://code.claude.com/docs/en/mcp (verify live; scope/flag details drift).

## Live-verification workflow (before pasting any MCP command)

MCP-land churns fast — packages rename, repos 404, servers get deprecated. Never paste a command from memory or from an unverified README. Order of operations:

1. **Official vendor docs first** (e.g. remotion.dev/docs/ai/mcp, docs.comfy.org/agent-tools/mcp) over third-party directories (glama, mcp.so, smithery).
2. **Check for deprecation banners.** Remotion's MCP is deprecated (hosted server shutdown ≥ 2026-08-31; replacement is `npx remotion skills add` → `/remotion-docs` skill). Comfy's old installer repo (Comfy-Org/comfy-cloud-mcp) is deprecated in favor of docs.
3. **Verify the command's package exists and its bin matches what the client runs:**
   - npm: `curl -s https://registry.npmjs.org/<pkg>` → check `dist-tags.latest` and `versions[latest].bin` (bin name = what `npx -y <pkg>` executes). Many packages have no README in the registry JSON — fetch raw README from GitHub instead.
   - PyPI: `curl -s https://pypi.org/pypi/<pkg>/json` → `info.version`, `info.requires_python`, `info.project_urls`.
   - GitHub README: `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md` — try `main`, then `master`.
4. **GitHub API (`api.github.com`) rate-limits unauthenticated requests fast (~60/hr).** Prefer the registry endpoints above; use the API sparingly (e.g. `/orgs/X/repos?per_page=100` to list a vendor's repos, `/search/repositories?q=...` for discovery).
5. **When a known repo 404s, don't assume it's dead — search npm/PyPI/GitHub for the real one.** Real-world example: `tuanle96/ffmpeg-mcp` and `Comfy-Org/comfyui-mcp` don't exist; the working servers are `egoist/ffmpeg-mcp` (npx) and Comfy's official `comfy-mcp` (pip) / `comfy-cloud-mcp` (cloud).
6. **glama.ai server pages are JS-rendered — curl returns empty HTML.** Not usable for extracting config; use GitHub/npm/PyPI sources instead.

## Pitfalls

- **Windows PATH:** bare `npx`/`uvx` in `command:` can fail inside Hermes' filtered subprocess env — use full path or `.cmd` form, and pass any API keys via `env:` (Hermes does NOT inherit your shell env for stdio servers).
- **`--args` ordering** in `hermes mcp add` — must be last; flags after it are swallowed as argv.
- **Deprecation drift:** re-verify Remotion's MCP status before recommending it; the shutdown banner date moves.
- **Secrets in config.yaml** — never; `.env` + `${env:VAR}` reference instead.

## References

- `references/video-mcp-recipe.md` — live-verified paste-ready configs for the top-5 video MCPs (Remotion ⚠️deprecated, FFmpeg, ElevenLabs, ComfyUI Cloud+Local, YouTube-transcript): Hermes YAML blocks, `claude mcp add` equivalents, full URLs, and the LIVE-VERIFIED FACTS list.
