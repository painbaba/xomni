# MCP Registry Hunts — verified recipe + 2026 video/audio MCP landscape

Validated 2026-08-10 on a full "enumerate every MCP server for video/audio/editing" hunt
(33 GitHub queries, 26 mcp.so pages, 24 Glama queries, 18 PulseMCP queries, 51 README fetches).
Full catalog written to `C:\Users\HP\mcp_video_catalog_2026.md`.

## The recipe (use for any MCP/registry landscape hunt)

1. **Curl-probe first**: mcp.so, glama.ai, pulsemcp.com all return `HTTP 200 size=0` to curl
   (Cloudflare). Do NOT retry curl with UA variants — go straight to the Camoufox REST sweep.
2. **Drive Camoufox REST from execute_code** (not browser_navigate — snapshots truncate at ~50
   cards and cost ~5KB context each; REST sweep prints only what you filter):
   - `POST /tabs {"url":..., "userId":"<u>", "listItemId":"<q>"}` → tabId (retry 4-6×, 6-8s apart;
     500 = resource pressure, restart server per §Lifecycle)
   - `POST /tabs/{id}/evaluate {"userId":"<u>","expression":"..."}` → result (poll until non-empty)
   - `DELETE /tabs/{id}` after each query; `DELETE /sessions/{u}` at the end.
3. **mcp.so**: internal search API rejects JSON (`{"error":"Only HTML requests are supported here"}`)
   → navigate per query. Card extractor (works in evaluate):
   `(function(){var out=[];var as=document.querySelectorAll('main a[href]');for(var i=0;i<as.length;i++){var a=as[i];var h3=a.querySelector('h3');if(!h3)continue;var p=a.querySelector('p');out.push(h3.textContent.trim()+' :: '+a.href+' :: '+(p?p.textContent.trim().slice(0,130):''));}return out.join('\\n');})()`
   Filter lines in Python by domain keywords; ~10-50 cards per query, many irrelevant.
4. **Glama.ai**: same-origin `fetch('/api/mcp/v1/servers?query=<q>&limit=25',{headers:{'accept':'application/json'}})` works INSIDE the browser. **Batch 20+ queries in ONE evaluate** (array of async IIFEs, sequential awaits, `return res.join('\\n')`). JSON shape: `{pageInfo, servers:[{name, url, description, attributes}]}`. Curl to same endpoint = 200/0 bytes.
5. **PulseMCP**: no JSON API (`/api/servers?q=`, `/api/search?q=`, `/api/v1/...` all 404) → per-query
   navigation + card extraction:
   `(function(){...document.querySelectorAll('a[href*="/servers/"]')... h2,h3,h4 title + anchor textContent (holds description), dedupe via seen-map...})()`
   Cards carry "Classification official|community" + "Est Visitors (Week)" — official status is a useful signal.
6. **GitHub search API** (unauth 10/min pool): 16-20 queries × 7.5s sleeps fits the 5-min execute_code
   budget (33 queries total across two calls). Collect full_name, stargazers_count, pushed_at, description.
7. **README detail pass**: urllib to raw.githubusercontent.com HANGS from execute_code (killed the
   5-min budget with zero output). Use a terminal call instead: bash loop `curl -sL --max-time 12
   raw.githubusercontent.com/<o>/<r>/{HEAD|main|master}/README.md` into a scratch dir, then a python
   heredoc parses the SAME call (fetch+parse+print in one call — inter-call files vanish on this host).
   Extract: install lines (npx|uvx|docker|pip|brew|git clone), tool names
   (`[a-z][a-z0-9_]*(?:_tool|_video|_audio|_transcript|_subtitle|_render|_edit|_tts|_clip|_concat|_trim|_extract|_download|_search|_generate|_create|_list|_get)[a-z0-9_]*`),
   agent mentions (Claude Code|Claude Desktop|Codex|Cursor|Windsurf|Gemini CLI|OpenClaw|Cline|Zed).

## execute_code budget rules (learned the hard way)
- **stdout is lost on timeout-kill if unflushed**: a 19-query sweep hit the 300s kill with ZERO output
  (all buffered). Always `print(..., flush=True)` in long sweeps.
- Batch ≤7 registry queries per execute_code call (tab-create ~5-10s + load ~5s + evaluate each).
- Reduce eval-attempt loops (8 attempts × 3s) — they silently eat the budget.

## Camofox lifecycle (mid-hunt)
- Symptom: `tab create timed out after 30000ms` (HTTP 500) on EVERY tab after a killed scripted sweep
  (orphan sessions). Health still says `browserConnected:true`.
- Fix: find PID `netstat -ano | grep ':9377'` → `powershell -Command "Stop-Process -Id <pid> -Force"` →
  relaunch `cd /c/Users/HP/camofox && npx camofox-browser` (background) → wait for
  `"browserConnected":true` (~15s).
- **Path pitfall**: background terminal MANGLES `cd C:\\Users\\HP\\camofox` to `C:UsersHPcamofox`
  (no such dir) — always use MSYS paths `/c/Users/HP/camofox` in background commands.

## 2026 video/audio/editing MCP landscape (condensed; stars = GitHub @ fetch time)
**Official vendor MCPs**: ElevenLabs (elevenlabs/elevenlabs-mcp 1.5K★, uvx), MiniMax (MiniMax-AI/MiniMax-MCP 1.6K★, uvx — `generate_video`, `text_to_audio`, `voice_clone`, `list_voices`), Runway (runwayml/runway-api-mcp-server 22★ — `runway_generate/edit/get/list`), Luma (lumalabs luma-api-mcp on mcp.so), Mux (pulsemcp official + NoBanks/mux-mcp), VideoDB (pulsemcp official), Synthesia (NoBanks/synthesia-mcp 0★, 8 tools). No official MCP: HeyGen, D-ID, Pika (has Claude Code plugin instead), Storyblocks/Pixabay/Videvo (none at all).
**Official modelcontextprotocol/servers repo: ZERO video/audio reference servers** (verified live).
**Remotion official MCP deprecated** ≤ Aug 31 2026 → /remotion-docs agent skill.

Top community servers by category (stars):
- NLE: samuelgursky/davinci-resolve-mcp 2.1K★ (npx setup), hetpatel-11/Adobe_Premiere_Pro_MCP 449★ (282 tools), leancoderkavy/premiere-pro-mcp 177★ (279 tools, CEP+UXP), Dakkshin/after-effects-mcp 538★, fancyboi999/capcut-mcp 94★, 0xsline/OpenChatCut 911★, ronak-create/FableCut 582★, pireel/pireel 916★, KyaniteLabs/kinocut 104★, burningion/video-editing-mcp 284★, FireRedTeam/FireRed-OpenStoryline 3.2K★ (agent), VelornLabs/velorn 391★.
- Rendering: abhiemj/manim-mcp-server 629★, heygen-com/hyperframes 40K★ (skills now), gyoridavid/short-video-maker 1.3K★ (docker), DojoCodingLabs/remotion-superpowers 94★, stephengpope/remotion-media-mcp 33★.
- FFmpeg: kevinwatt/ffmpeg-mcp-lite 26★ (uvx), video-creator FFmpeg-MCP 137★ (mcp.so), ~15 total variants.
- TTS/audio: mberg/kokoro-tts-mcp 81★, blacktop/mcp-tts 64★, allvoicelab/AllVoiceLab-MCP 57★, SamurAIGPT/Generative-Media-Skills 4K★ (muapi, npx skills add), luminarylane/fal-mcp-server 52★, deepfates/mcp-replicate 95★.
- Video gen (i2v/t2v): Doriandarko/sora-mcp 209★ (`create-video` etc., Sora 2), 199-mcp/mcp-kling 40★, mario-andreschak/mcp-veo2 32★, vericontext/vibeframe 164★ (Seedance/Runway/Veo/Kling, cost cap), apinetwork/piapi-mcp-server 73★, Anil-matcha/Wan-3.0-API 74★, jau123/MeiGen-AI-Design-MCP 1.7K★ (npx meigen).
- ComfyUI: artokun/comfyui-mcp 532★ (npx -y comfyui-mcp@latest), joenorton/comfyui-mcp-server 397★, heshengtao/comfyui_LLM_party 2.3K★, ATH-MaaS/Pixelle-MCP 1.1K★, aqm857886159/Nomi 404★.
- YouTube: kimtaeyoon83/mcp-server-youtube-transcript 582★, ZubeidHendricks/youtube-mcp-server 561★, anaisbetts/youtube-mcp 532★, eat-pray-ai/yutu 606★ (docker), yzfly/douyin-mcp-server 1.2K★, guimatheus92/mcp-video-analyzer 42★ (yt-dlp, 1000+ platforms).
- Whisper/subs: samson-art/transcriptor-mcp 18★ (docker), oxbshw/watch-skill 271★ (uvx), GongRzhe/opencv-mcp-server 112★ (40+ tools).
- Stock: garylab/pexels-mcp-server 19★ (uvx), stock-image-mcp (Unsplash+Pexels+Pixabay+Flickr, glama).
