# Video MCP servers — verified landscape (Aug 10, 2026)

Knowledge bank from the deep GitHub hunt for video-related MCP servers (deliverable: ranked top-15 for an agent-driven documentary pipeline). Every star count is point-in-time (2026-08-10) from the GitHub search API; every repo URL live-checked. Core API was rate-limited (shared IP 49.36.18.125) — all metadata came from the search pool + raw.githubusercontent.com + HTML redirect checks.

## Ranked top-15 (documentary pipeline: source → narrate → visuals → edit → QA/captions)

| # | Repo | ★ | Last push | Lang | Pipeline role / install |
|---|------|-----|-----------|------|------------------------|
| 1 | samuelgursky/davinci-resolve-mcp | 2,056 | 2026-08-09 | Python | Pro assembly/color; 34-tool Compound server; `npx davinci-resolve-mcp setup`; needs Resolve Studio |
| 2 | MCPBlender/blender-mcp | 25,680 | 2026-08-09 | Python | 3D/motion B-roll; `uvx blender-mcp` + Blender addon, click Connect |
| 3 | elevenlabs/elevenlabs-mcp | 1,513 | 2026-08-04 | Python | Narration; `pip install elevenlabs-mcp` / `uvx elevenlabs-mcp` + ELEVENLABS_API_KEY |
| 4 | KyaniteLabs/kinocut | 104 | 2026-08-09 | Python | Guardrailed ffmpeg editing (trim, burned captions, audio normalize, fail-closed gates); `uvx --from kinocut kino`; README example: "Trim this interview into a 45-second vertical clip, add burned captions…" |
| 5 | artokun/comfyui-mcp | 532 | 2026-08-09 | TypeScript | AI image/video visuals; `npx -y comfyui-mcp@latest`; agent auto-downloads checkpoints/builds workflows |
| 6 | palmier-io/palmier-pro | 13,322 | 2026-08-09 | Swift | macOS AI timeline editor exposing HTTP MCP at `127.0.0.1:19789/mcp`; `claude mcp add --transport http` |
| 7 | MiniMax-AI/MiniMax-MCP | 1,557 | 2026-05-21 | Python | Official; voice_design, generate_video (Hailuo-02 6s), music_generation; `uvx minimax-mcp -y` |
| 8 | hetpatel-11/Adobe_Premiere_Pro_MCP | 449 | 2026-08-05 | TypeScript | 283 tools via CEP bridge; `npm install -g adobe-premiere-pro-mcp` |
| 9 | jordanrendric/claude-video-vision | 1,177 | 2026-08-07 | TypeScript | Agent QA; tools video_watch/analyze/detail/info; local Whisper option |
| 10 | kimtaeyoon83/mcp-server-youtube-transcript | 582 | 2026-07-21 | TypeScript | Source research; `npx -y @kimtaeyoon83/mcp-server-youtube-transcript`; optional analyze_video via TwelveLabs |
| 11 | oxbshw/watch-skill | 271 | 2026-08-09 | Python | Footage indexing/self-verification; `uvx --from "watch-skill[standard]" watch-skill serve` |
| 12 | ZubeidHendricks/youtube-mcp-server | 561 | 2026-08-08 | TypeScript | 43 tools, YouTube API (up to 3 keys); `npm install -g zubeid-youtube-mcp-server` |
| 13 | guimatheus92/mcp-video-analyzer | 42 | 2026-08-04 | TypeScript | Any URL/local video → transcript (VTT), key frames, scene-change detection; `npx mcp-video-analyzer@latest` |
| 14 | anaisbetts/mcp-youtube | 538 | 2026-06-19 | JavaScript | yt-dlp-backed grab; README minimal (522 ch) — check tool surface before committing |
| 15 | abhiemj/manim-mcp-server | 629 | 2025-05-19 ⚠️ | Python | 3b1b-style explainers; STALE — active alt: paulnegz/manim-mcp (17★, 2026-02-25, multi-agent `--mode advanced`, `pip install -e ".[rag]"`) |

## Ecosystem facts (verified, counter to stale memory)
- **Official MCP org blesses ZERO video/media servers.** `modelcontextprotocol/servers` (89,375★, pushed 2026-08-05) reference list = Everything, Fetch, Filesystem, Git, Memory, Sequential Thinking, Time. Former `modelcontextprotocol/server-ffmpeg` is DELETED (URL 404; `org:modelcontextprotocol ffmpeg` → 0 hits). EverArt (image gen) archived in `servers-archived`. Official discovery is now registry.modelcontextprotocol.io.
- **Comfy-Org has no official MCP**: `comfy-cloud-mcp` (18★) ARCHIVED; `comfy-skills` (134★) = slash commands. Community wins: artokun/comfyui-mcp, joenorton/comfyui-mcp-server (streamable-http on :9000/mcp), ATH-MaaS/Pixelle-MCP (1,099★, 2025-12), aqm857886159/Nomi.
- **Remotion killed its MCP**: remotion.dev/docs/mcp → HTTP 404; Remotion (55,925★) ships Agent Skills instead; community DojoCodingLabs/remotion-superpowers (94★) fills the gap.
- **ahujasid/blender-mcp → MCPBlender/blender-mcp** (live redirect, verified via `curl -sL -w "%{url_effective}"`).
- **heygen-com/hyperframes (40,211★) is NOT MCP** — skills/CLI; `/figma` mentions MCP only for Figma import.
- **Awesome lists**: punkpeye/awesome-mcp-servers 92,010★ canonical (1.3MB README — grep, don't load); wong2 4,253★ still maintained; appcypher 5,737★ ARCHIVED.

## Search-query set that surfaced this (reusable for re-runs)
Round 1 (generic, noisy): `mcp-server video`, `mcp ffmpeg`, `mcp remotion`, `mcp elevenlabs`, `mcp youtube`, `mcp comfyui`, `mcp manim`, `mcp whisper`, `mcp-server editing`, `video mcp` + bonus `mcp davinci`, `mcp subtitle`, `mcp shotstack`, `mcp video editor`.
Round 2 (targeted): `whisper-mcp`, `transcription mcp`, `ComfyMCP`, `modelcontextprotocol ffmpeg`, `remotion mcp`, `yt-dlp mcp`, `mcp obs`, `mcp blender`, `mcp premiere`, `fal mcp`, `replicate mcp`, `mcp moviepy`, `mcp video analysis`, `mcp captions`.
Round 3 (authority): `org:modelcontextprotocol`, `org:modelcontextprotocol ffmpeg`, `org:Comfy-Org mcp`, `awesome mcp servers`, `mcp-server-ffmpeg`, `modelcontextprotocol servers`.
Round 4 (existence): `repo:<owner>/<name>` qualifiers — NOTE: `repo:` on a renamed/deleted repo returns "Validation Failed", not empty.

## Notable honorable mentions (verified)
- FFmpeg wrappers: egoist/ffmpeg-mcp (120★, stale 2025-03), video-creator/ffmpeg-mcp (141★, 8 tools: clip/concat/overlay/scale/extract-frames), kevinwatt/ffmpeg-mcp-lite (26★, uvx), misbahsy/video-audio-mcp (83★, 27 tools)
- Transcription: arcaputo3/mcp-server-whisper (56★, OpenAI whisper, 11 tools), BigUncle/Fast-Whisper-MCP-Server (17★, local faster-whisper, SRT/VTT), samson-art/transcriptor-mcp (18★, yt-dlp, 80 tools, docker), 0xchamin/mcptube (148★, YouTube→KB)
- AI editors: pireel/pireel (916★), 0xsline/OpenChatCut (911★), ronak-create/FableCut (582★), gyoridavid/short-video-maker (1,277★, stale 2025-06)
- Video-gen MCP: vericontext/vibeframe (164★, Seedance/Runway/Veo/Kling, cost-capped), luminarylane/fal-mcp-server (52★)
- Premiere alt: leancoderkavy/premiere-pro-mcp (177★, 279 tools)
- YouTube ops: eat-pray-ai/yutu (606★, active)
- Skills/adjacent (NOT MCP): wilwaldon/Claude-Code-Video-Toolkit (66★), SamurAIGPT/Generative-Media-Skills (4,014★), FireRedTeam/FireRed-OpenStoryline (3,203★)

## Corrections to the table above (second hunt pass, 2026-08-10)
- **Comfy-Org DOES have an official MCP: `comfy-mcp`** (first-party local server, PyPI `pip install comfy-mcp`, repo Comfy-Org/comfy-mcp, docs https://docs.comfy.org/agent-tools/mcp.md + https://comfy.org/mcp). The earlier "no official MCP / comfy-cloud-mcp archived" reading was stale: `comfy-cloud-mcp` (18★, pushed 2026-06-22) is the current CLOUD connection (`https://cloud.comfy.org/mcp`, OAuth, 5 free runs). PyPI `mcp-comfyui` 0.1.0 is a community lookalike (author Lukas Kellerstein).
- **Remotion MCP page is NOT 404 — it moved.** Live at `https://www.remotion.dev/docs/ai/mcp` (HTTP 200): "The Remotion MCP is deprecated… hosted MCP will shut down no earlier than August 31, 2026… issue #9055" (issue live, published 2026-07-15). Old slug `/docs/mcp` 404s — that's a URL move, not a kill. Migrate: `npx remotion skills add`.
- **samuelgursky/davinci-resolve-mcp does NOT require Resolve Studio** — README: tested against Studio 19.1.3/20.3.2/21.0.2 **+ Resolve 21.0.3 FREE via an in-app bridge** ("Free edition (in-app bridge)" section); Windows 11 paths confirmed.
- **egoist/ffmpeg-mcp is DEAD** (404, was 120★) — remove from honorable mentions. Same fate: diegoist/ffmpeg-mcp (was 120★), wshobson/video-editing-mcp, MamoruDS/youtube-data-mcp, replicate/replicate-mcp GitHub (npm `replicate-mcp` 0.9.0 is the official package, docs at replicate.com/docs/reference/mcp).
- **video-creator/ffmpeg-mcp is macOS-only** — "Currently, only macos platforms are supported" — not a Windows option.

## Per-server dossiers (install / config / tools / example / limitations) — verified 2026-08-10

**Comfy MCP (official `comfy-mcp`)** — `pip install "comfy-cli>=1.14.0" && comfy install && pip install comfy-mcp && comfy launch` (Python 3.10+). Config: `claude mcp add comfy-mcp -e COMFY_BIN=C:\path\to\comfy.exe -- comfy-mcp` or `.mcp.json` command `comfy-mcp`. Tools (15): `server_info` (call first), `run_workflow(workflow_path, wait=True)`, `job_status`, `wait_for_job`, `watch_job`, `fetch_outputs`, `launch_comfyui`, `stop_comfyui`, `search_templates`, `fetch_template`, `search_nodes`, `get_node`, `list_nodes`, `search_models`, `validate_workflow`. Public beta. Community alt: artokun/comfyui-mcp (532★, npm 0.50.70) — `npx -y comfyui-mcp`, 37 tools, auto-detects ComfyUI, **`npx -y comfyui-mcp setup hermes` writes `~/.hermes/config.yaml`**.

**samuelgursky/davinci-resolve-mcp (2,056★, npm 2.89.0)** — `npx davinci-resolve-mcp setup`; config `python <path>/src/server.py` (+ `node <path>/bin/davinci-resolve-advanced-mcp.mjs` for the advanced server). **34 compound / 353 granular tools**, 9 capability areas (project control, media pool/ingest, analysis, timeline/conform, review, color, Fusion, Fairlight, render/deliver); 361/361 API methods covered. Optional pip extras: numpy, librosa, openai-whisper, open_clip_torch, transformers, opencv-python. Does NOT pick takes / cut to music / judge cuts / modify source media (first-pass assembly only). Alts: barckley75/resolve-claude-mcp (321★, uv, ~50 tools, MLX tools macOS-only), lordhoell, filmcademy (PyPI).

**elevenlabs/elevenlabs-mcp (1,513★, MIT)** — `pip install elevenlabs-mcp`, run `uvx elevenlabs-mcp`; env `ELEVENLABS_API_KEY`; Windows pitfall "spawn uvx ENOENT" → install uv. **26 tools** (source-verified from `elevenlabs_mcp/server.py`): `text_to_speech`, `speech_to_text`, `text_to_sound_effects`, `search_voices`, `list_models`, `get_voice`, `voice_clone`, `isolate_audio`, `check_subscription`, `create_agent`, `add_knowledge_base_to_agent`, `list_agents`, `get_agent`, `get_conversation`, `simulate_conversation`, `list_conversations`, `speech_to_speech`, `text_to_voice`, `create_voice_from_preview`, `make_outbound_call`, `search_voice_library`, `list_phone_numbers`, `compose_music`, `create_composition_plan`, `video_to_music`, `upload_music_for_inpainting`. `ELEVENLABS_MCP_BASE_PATH` is the file-I/O security boundary. Hosted MCP also exists (docs elevenlabs.io/docs/eleven-agents/operate/hosted-mcp).

**YouTube MCPs** — kimtaeyoon83/mcp-server-youtube-transcript (582★): `npx -y @kimtaeyoon83/mcp-server-youtube-transcript`, tools `get_transcript(url, lang, include_timestamps, strip_ads)` + `analyze_video` (TwelveLabs). jkawamoto/mcp-youtube-transcript (463★): `uvx mcp-youtube-transcript` (PyPI 0.3.5), tools `get_transcript`, `get_timed_transcript`, `get_video_info`, `get_available_languages`. icraft2170/youtube-data-mcp-server (64★): `npx -y youtube-data-mcp-server`, 8 research tools (`getVideoDetails`, `searchVideos`, `getTranscripts`, `getRelatedVideos`, `getChannelStatistics`, `getChannelTopVideos`, `getVideoEngagementRatio`, `getTrendingVideos`) — best for the research phase.

**Whisper/subtitle MCPs** — arcaputo3/mcp-server-whisper (56★, PyPI 1.1.0): `uvx mcp-server-whisper`, 8 tools (`list_audio_files`, `get_latest_audio`, `convert_audio`, `compress_audio`, `transcribe_audio`, `chat_with_audio`, `transcribe_with_enhancement`, `create_audio`) — ⚠️ OpenAI-API-based (whisper-1/gpt-4o-transcribe), NOT local. BigUncle/Fast-Whisper-MCP-Server (17★): LOCAL faster-whisper, tools `get_model_info`/`transcribe`/`batch_transcribe`, Windows `start_server.bat`. Captions best done via Remotion `@remotion/captions` + `@remotion/install-whisper-cpp`; `ffmpeg-mcp-lite` has `ffmpeg_add_subtitles`.

**Manim MCP** — abhiemj/manim-mcp-server (629★, MIT, last push 2025-05): `pip install manim` + `pip install mcp`, run `python src/manim_server.py` with `MANIM_EXECUTABLE` env; tools (source-verified) `execute_manim_code`, `cleanup_manim_temp_dir`. Alt: paulnegz/manim-mcp (17★; npm `manim-mcp` 0.1.1 / PyPI `manim-mcp`).

**After Effects MCP** — Dakkshin/after-effects-mcp (538★, MIT): clone + `npm install` + `npm run build`, `.mcp.json` `node <path>/build/index.js`; 14 tools (`create-composition`, `run-script`, `get-results`, `get-help`, `setLayerKeyframe`, `setLayerExpression`, `setLayerProperties`, `batchSetLayerProperties`, `getLayerInfo`, `createCamera`, `createNullObject`, `duplicateLayer`, `deleteLayer`, `setLayerMask`). npm `after-effects-mcp` 1.10.0 = a-y-ibrahim variant. Needs licensed AE running locally.

**FFmpeg MCPs (Windows verdict)** — kevinwatt/ffmpeg-mcp-lite (26★, PyPI, pure Python): `pip install ffmpeg-mcp-lite`; 8 tools prefixed `ffmpeg_` (`ffmpeg_get_info`, `ffmpeg_convert`, `ffmpeg_compress`, `ffmpeg_trim`, `ffmpeg_merge`, `ffmpeg_extract_audio`, `ffmpeg_extract_frames`, `ffmpeg_add_subtitles`). priyanshum143/MCP-FFMPEG (PyPI `mcp-ffmpeg` 0.1.6, Python 3.13+): job queue + parallel workers. On Windows the agent shelling out to the ffmpeg CLI usually beats all of them.

**Video-gen MCPs** — 199-mcp/mcp-kling (npm 5.2.0): `npx -y mcp-kling@latest` + `KLING_API_KEY`; 12 tools (`generate_video`, `generate_image_to_video`, `check_video_status`, `extend_video`, `create_lipsync`, `apply_video_effect`, `generate_image`, `check_image_status`, `virtual_try_on`, `get_account_balance`, `get_resource_packages`, `list_tasks`); README example: robot-disco → `./downloads/videos/robot_disco_k123456789.mp4`. mario-andreschak/mcp-veo2 (32★): ⚠️ Veo 2 model dead since Jun 30 2026 → legacy. lumalabs/luma-api-mcp (25★): `sh setup.sh`, tools `create_image`/`create_video` (ray-2, 540p–4k, 5s/9s). apinetwork/piapi-mcp-server (73★): one key for Kling/Luma/Hunyuan/Wan/Skyreels/Suno/TTS; video-gen may hit Claude tool timeout. replicate-mcp (official npm 0.9.0): `npx -y replicate-mcp --client=claude --tools=dynamic` + `REPLICATE_API_TOKEN`; dynamic tools `list_api_endpoints`/`get_api_endpoint_schema`/`invoke_api_endpoint` or filtered explicit tools (`--tool/--resource/--operation`).

**Editor MCPs** — hetpatel-11/Adobe_Premiere_Pro_MCP (449★): 283 tools, `"command": "premiere-pro-mcp"`, Windows `npm run setup:win`; ships Claude Code skill. vizionik25/moviepy-mcp (2★) experimental. FireRed-OpenStoryline (3,203★) is an editing AGENT, not MCP.

## Ranked shortlist — top-5 for the documentary pipeline (Windows + Hermes)
1. **Comfy MCP (official `comfy-mcp`)** — generative visuals via local ComfyUI (Wan/LTX/HunyuanVideo) + cloud fallback. `pip install "comfy-cli>=1.14.0" && comfy install && pip install comfy-mcp && comfy launch` → `claude mcp add comfy-mcp -e COMFY_BIN=... -- comfy-mcp`. npm shortcut: `npx -y comfyui-mcp setup hermes`.
2. **samuelgursky/davinci-resolve-mcp** — full NLE control (353 tools), works with FREE Resolve on Windows via in-app bridge. `npx davinci-resolve-mcp setup`.
3. **ElevenLabs MCP** — narration/voice-clone/SFX/music. `pip install elevenlabs-mcp` + `uvx` + `ELEVENLABS_API_KEY`.
4. **YouTube pair** — `npx -y @kimtaeyoon83/mcp-server-youtube-transcript` + `npx -y youtube-data-mcp-server` (transcripts + channel/search/engagement analytics).
5. **mcp-kling** — licensed AI b-roll; `replicate-mcp` as model-agnostic alternative.

## Verification caveats for this dataset
- Core GitHub API rate-limited mid-hunt (shared egress IP) — worked around per the rate-limit-proof hunt section in SKILL.md; no fact here depends on the dead pool.
- `remotion.dev/docs/mcp` 404s to both urllib and curl — consistent with removal, not bot-block.
- Star counts are point-in-time; re-verify before quoting in new reports.
