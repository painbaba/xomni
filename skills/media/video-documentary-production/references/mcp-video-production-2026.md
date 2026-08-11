# MCP Servers for Video Production — Research Bank + Wiring Recipe (verified 2026-08-10)

6-agent MCP deep-hunt swarm (registry, top-12 dive, mega YT hunt, web/Reddit/HN, GitHub,
wiring). Full reports on disk: `C:\Users\HP\mcp_video_production_patterns_2026.md` (18.9KB,
50+ sources), `C:\Users\HP\video-mcp-recipe.md` (13KB wiring), `C:\Users\HP\claude-code-video-hunt.md`
(71 verified videos), `C:\Users\HP\gh_video_repos.json`.

## The verdicts that matter (live-verified)

1. **Skills BEAT MCPs for the creative-authoring core.** Remotion DEPRECATED its own MCP
   (shutdown ≤ Aug 31 2026, "data can be less current") in favor of Agent Skills — the viral
   8.3M-view launch was the skill, not the MCP. `remotion.dev/docs/mcp` now 404s. Do NOT
   install a Remotion MCP. Our HyperFrames stack is already the skill-native pattern.
2. **MCPs win where the agent drives stateful/vendor apps**: ElevenLabs MCP = "the one that
   actually works end-to-end" (script→voice→audio, per the 4-MCP Reddit shootout; tools seen:
   get_voice, voice_clone, isolate_audio, check_subscription, create_agent, add_knowledge...).
3. **FFmpeg via typed MCP tools with receipts**: kinocut (guardrailed — "not invented FFmpeg
   flags", quality gates), beambuilder (async processing for >1GB files to avoid timeouts).
4. **Higgsfield MCP** = best model coverage ("sora 2, veo 3.1, kling, seedance, nano banana")
   but FAILURE MODE: Claude free-picks the most expensive model — pin the model in the prompt.

## Ranked repos by pipeline stage (stars point-in-time Aug 2026)

| Stage | Repo | ★ | Notes |
|---|---|---|---|
| Finishing/assembly | samuelgursky/davinci-resolve-mcp | 2,056 | Pro assembly; Resolve GUI must run |
| 3D/motion b-roll | MCPBlender/blender-mcp | 25,680 | Blender as motion-graphics engine |
| Narration | elevenlabs/elevenlabs-mcp | 1,513 | The working voice path |
| Guardrailed editing | KyaniteLabs/kinocut | 104 | ffmpeg with receipts |
| Local gen | Comfy-Org/comfy-mcp (official) | — | Wan 2.2 / image workflows; NOTE: `Comfy-Org/comfyui-mcp` 404s — use `comfy-mcp` |

Dead/404: `tuanle96/ffmpeg-mcp`, `modelcontextprotocol/server-ffmpeg`, `remotion.dev/docs/mcp`.

## Hermes wiring recipe (from video-mcp-recipe.md, verified against local config)

- Config file: `C:\Users\HP\AppData\Local\hermes\config.yaml` → top-level `mcp_servers:` dict.
- stdio server schema: `command` (req), `args` (list), `env` (dict); HTTP: `url`, `headers`,
  `transport: sse`, `auth: oauth`. Common: `enabled`, `timeout` (300), `tools.include/exclude`,
  `trust: full|untrusted`.
- Tool naming: `mcp_<server>_<tool>` (hyphens/dots → underscores).
- Prereqs: `pip install mcp` (else silently disabled), Node for npx, uv for uvx; on Windows use
  `npx.cmd` / `uvx.exe` if bare names aren't on PATH.
- Apply: restart or auto-reload + `/reload-mcp`. CLI: `hermes mcp add <name> -- <command...>`.
- Interpolation: `${env:VAR}`; secrets → `.env`.

## YouTube references for agent→video (verified URLs)

David Ondrej `fOY0_WCR3eY` ("Claude Code can now make videos"), Jason Cooperson `XeTAlZiIWHE`
(full HyperFrames pipeline automation), Chronixel `oWkUwno6b0E` (Remotion tutorial), Cole Medin
`Ya51a1EJPZk` (full workflow). Full 71-video catalog in claude-code-video-hunt.md.

## Why this matters (user direction 2026-08-10)

User's stated turning point: "we have to use something avatar or one like the pros in yt and
pull up overlays... stock footages don't work, we have to create our own quality assets. So
the major turning point will come from ongoing research." The MCP layer (ElevenLabs voice,
ComfyUI local gen, davinci finishing) + HeyGen avatars (we're on the HeyGen stack) + kinetic
captions from the script = the pro hybrid. Wire the MCPs when the user green-lights; start
with elevenlabs-mcp + comfy-mcp.
