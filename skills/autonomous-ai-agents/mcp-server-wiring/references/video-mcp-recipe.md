# Top-5 Video MCP Servers — Live-Verified Recipe

Verified 2026-08 against the URLs listed (live-web-verified; local Hermes inspection on a Windows host, Hermes v0.19.1). Every command was checked against npm/PyPI registries and/or vendor docs — not memory.

## Quick table

| MCP | Status | Hermes `mcp_servers:` entry | Claude Code equivalent |
|---|---|---|---|
| **Remotion** | ⚠️ **DEPRECATED** — hosted MCP shuts down no earlier than **2026-08-31**; do NOT recommend new installs. Replacement: Remotion Agent Skills (`npx remotion skills add` → `/remotion-docs` skill) | Legacy only: `command: npx`, `args: [-y, @remotion/mcp]` | `claude mcp add --transport stdio remotion -- npx -y @remotion/mcp` (legacy) |
| **FFmpeg** (egoist/ffmpeg-mcp) | ✅ active | `command: npx`, `args: [-y, ffmpeg-mcp]`; optional `env.FFMPEG_PATH` (defaults to system PATH; needs ffmpeg installed) | `claude mcp add --transport stdio ffmpeg -- npx -y ffmpeg-mcp` |
| **ElevenLabs** (official) | ✅ active | `command: uvx`, `args: [elevenlabs-mcp]`, `env: {ELEVENLABS_API_KEY: "${env:ELEVENLABS_API_KEY}"}` | `claude mcp add --transport stdio elevenlabs -e ELEVENLABS_API_KEY=KEY -- uvx elevenlabs-mcp` |
| **ComfyUI Cloud** (official) | ✅ active (public beta, OAuth); **in Hermes catalog** as `comfy-cloud` | `url: "https://cloud.comfy.org/mcp"`, `auth: oauth` — or `hermes mcp install comfy-cloud` | `claude mcp add --transport http comfy-cloud https://cloud.comfy.org/mcp` |
| **ComfyUI Local** (official `comfy-mcp`) | ✅ active — first: `pip install "comfy-cli>=1.14.0"`, `comfy install`, `pip install comfy-mcp`, `comfy launch` | `command: comfy-mcp`; optional `env.COMFY_BIN` (absolute path to comfy if not on client env PATH) | `claude mcp add --transport stdio comfy-mcp -e COMFY_BIN=/path/to/venv/bin/comfy -- comfy-mcp` |
| **YouTube-transcript** | ✅ active | `command: npx`, `args: [-y, @kimtaeyoon83/mcp-server-youtube-transcript]`; optional `env.TWELVELABS_API_KEY` (enables `analyze_video` tool) | `claude mcp add --transport stdio youtube-transcript -- npx -y @kimtaeyoon83/mcp-server-youtube-transcript` |

## Full paste-ready Hermes `config.yaml` block

```yaml
mcp_servers:
  remotion:                     # ⚠️ DEPRECATED — use `npx remotion skills add` instead
    command: "npx"
    args: ["-y", "@remotion/mcp"]
  ffmpeg:
    command: "npx"
    args: ["-y", "ffmpeg-mcp"]
    # env:
    #   FFMPEG_PATH: "C:\\ffmpeg\\bin\\ffmpeg.exe"   # optional, defaults to PATH
  elevenlabs:
    command: "uvx"
    args: ["elevenlabs-mcp"]
    env:
      ELEVENLABS_API_KEY: "${env:ELEVENLABS_API_KEY}"   # set in ~/.hermes/.env
  comfy-cloud:                  # official Comfy Cloud (OAuth browser flow on first connect)
    url: "https://cloud.comfy.org/mcp"
    auth: oauth
  comfy-mcp:                    # official local ComfyUI server (needs comfy-cli + running ComfyUI)
    command: "comfy-mcp"
    # env:
    #   COMFY_BIN: "C:\\path\\to\\venv\\Scripts\\comfy.exe"
  youtube-transcript:
    command: "npx"
    args: ["-y", "@kimtaeyoon83/mcp-server-youtube-transcript"]
    # env:
    #   TWELVELABS_API_KEY: "${env:TWELVELABS_API_KEY}"   # optional
```

Apply: `hermes mcp test <name>` / `hermes mcp list` / restart or `/reload-mcp` (auto-reload default on). Tools appear as `mcp_ffmpeg_clip_video`, `mcp_elevenlabs_text_to_speech`, `mcp_youtube_transcript_get_transcript`, etc.

## Per-server notes

- **Remotion** — npm `@remotion/mcp` v4.0.507 exists (bin `remotion-mcp`) but the vendor deprecates it: "The hosted MCP will shut down no earlier than August 31, 2026. New installations are not recommended." Follow GitHub issue remotion-dev/remotion#9055. Migrate to `npx remotion skills add` (installs Agent Skills; `/remotion-docs`).
- **FFmpeg (egoist/ffmpeg-mcp)** — npm `ffmpeg-mcp` 0.0.3, bin `ffmpeg-mcp`. Requires ffmpeg on PATH; `FFMPEG_PATH` env overrides. Tools include clip/concat/overlay/scale/extract-frames via ffmpeg CLI. macOS-only alternatives exist (video-creator/ffmpeg-mcp) but are not cross-platform — prefer egoist's.
- **ElevenLabs (official)** — PyPI `elevenlabs-mcp` 0.12.2, requires Python ≥3.11, run via `uvx elevenlabs-mcp`. Free tier 10k credits/mo. Optional `ELEVENLABS_MCP_BASE_PATH` (file I/O security boundary, default `~/Desktop`) and `ELEVENLABS_MCP_OUTPUT_MODE` (`files` default).
- **ComfyUI Cloud** — hosted at `https://cloud.comfy.org/mcp`, OAuth sign-in with Comfy account (new users get 5 free runs). Closed-beta waitlist historically; check docs.
- **ComfyUI Local** — `comfy-mcp` is Comfy's first-party local server; engine is `comfy-cli` (≥1.14.0). Server does NOT launch ComfyUI itself — run `comfy launch` first. Tools: `server_info`, `run_workflow`, etc.
- **YouTube-transcript** — `@kimtaeyoon83/mcp-server-youtube-transcript`; main tool `get_transcript(url, lang, include_timestamps, strip_ads)`; optional `analyze_video` needs `TWELVELABS_API_KEY`. Zero deps for transcript fetching.

## LIVE-VERIFIED FACTS (URLs)

- Hermes MCP config: `$HERMES_HOME/config.yaml` + `mcp_servers` schema + CLI — local `hermes mcp --help`/`add --help`/`catalog`, source `hermes_cli/mcp_config.py`; docs https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp and https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference
- Claude Code scopes/.mcp.json/`claude mcp add` forms — https://code.claude.com/docs/en/mcp
- Remotion deprecation + Agent Skills migration — https://www.remotion.dev/docs/ai/mcp ; npm https://registry.npmjs.org/@remotion/mcp
- FFmpeg — https://github.com/egoist/ffmpeg-mcp ; npm https://registry.npmjs.org/ffmpeg-mcp
- ElevenLabs — https://github.com/elevenlabs/elevenlabs-mcp ; PyPI https://pypi.org/pypi/elevenlabs-mcp/json
- Comfy MCP (cloud + local) — https://docs.comfy.org/agent-tools/mcp (old installer repo: https://github.com/Comfy-Org/comfy-cloud-mcp, deprecated in favor of docs)
- YouTube-transcript — https://github.com/kimtaeyoon83/mcp-server-youtube-transcript
