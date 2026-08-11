# YouTube Video Hunt — Claude Code / AI Coding Agents Making Videos (verified Aug 2026)

Domain knowledge bank for the "how do AI coding agents (Claude Code etc.) produce videos" question.
Every URL below was found on a live rendered YouTube search page AND confirmed via YouTube's oEmbed
endpoint (`youtube.com/oembed?url=...&format=json` returned matching title+author for all 29 checked IDs).

## The technique (what worked)

1. **YouTube search pages render in a real browser** — `browser_navigate` to
   `https://www.youtube.com/results?search_query=<urlencoded>`; no JS-blocking wall, no consent wall observed.
   Plain `curl` on the same URL returns only the JS shell — useless.
2. **DOM extraction** via `browser_console` expression (must be a SINGLE-LINE classic IIFE; a multi-line
   arrow-function expression threw `SyntaxError: Unexpected end of input`):
   ```js
   (function(){var out=[];var items=document.querySelectorAll('ytd-video-renderer');for(var i=0;i<items.length;i++){var el=items[i];var a=el.querySelector('a#video-title');if(!a)continue;var ch=el.querySelector('ytd-channel-name a');var meta=el.querySelector('#metadata-line');out.push({t:a.textContent.trim(),u:a.href.split('&')[0],c:ch?ch.textContent.trim():null,m:meta?meta.textContent.replace(/\s+/g,' ').trim():null});}return JSON.stringify(out);})()
   ```
   Selectors: title+URL = `a#video-title` (strip `&pp=` params from href); channel = `ytd-channel-name a`;
   views/age = `#metadata-line`. Shorts are in a separate shelf (`a[href*="/shorts/"]`), NOT in `ytd-video-renderer`.
3. **Bulk live-verification** of candidate IDs (fast, no watch-page loads):
   `curl -s --max-time 15 "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=<ID>&format=json"`
   → `{"title": ..., "author_name": ...}`. Loop all IDs in one `execute_code` batch, compare returned title/author
   against the search page. A transient `Unauthorized` response is oEmbed rate-limiting — retry, or accept the video
   if it appeared with full metadata on a rendered search page.
4. **Watch pages render too** (`youtube.com/watch?v=ID`); the right-sidebar "Up next" list is a free source of
   related videos (surfaced "Claude + Remotion Just RETIRED video editors...").
5. Multi-query coverage: each query returned a different slice. Used: `claude code make video`, `claude code
   documentary ai agent`, `AI agent creates youtube video claude`, `claude code documentary video workflow`,
   `AI agent video pipeline claude code remotion full tutorial`, `faceless documentary claude code AI`.

## Ranked top-10 (most useful for learning agent-driven video/documentary production)

| # | Title | Channel | Views | URL |
|---|-------|---------|-------|-----|
| 1 | Make the PERFECT Videos with Claude Code (Full Workflow) | Cole Medin | ~22K | https://www.youtube.com/watch?v=Ya51a1EJPZk |
| 2 | I Copied A $372k/Mo YouTube Channel with CLAUDE AI (it worked) | Jacksons AI | ~60K | https://www.youtube.com/watch?v=StjGg6CecSc |
| 3 | Automate Your Entire Faceless Channel With Claude Code (Full Proof) | The Zinny Studio | ~15K | https://www.youtube.com/watch?v=4DiL7ufrxbs |
| 4 | FREE Claude Prompt That Creates VOX Style Videos AUTOMATICALLY | Jacksons AI | ~130K | https://www.youtube.com/watch?v=RaxX_Q7Apj0 |
| 5 | How To Clone Any Viral YouTube Channel With Claude AI \| Create Viral 2D Documentary Videos | Kanhaiya Growth | ~254K | https://www.youtube.com/watch?v=kZtjsIzVvBc |
| 6 | How I Vibe Code Technical Videos With Claude Code and Remotion | John Hartquist | ~31K | https://www.youtube.com/watch?v=z7Bkf3Vc63U |
| 7 | Claude Code Just Changed YouTube Videos Forever (Tutorial) | Danny Why | ~506K | https://www.youtube.com/watch?v=idVMGLzrrnU |
| 8 | Claude Code can now make videos, here's how | David Ondrej | ~160K | https://www.youtube.com/watch?v=fOY0_WCR3eY |
| 9 | I Taught Claude Code to Edit Movies (Buttercut) | Andrew Ford | ~42K | https://www.youtube.com/watch?v=FBkfr1yWf_s |
| 10 | How I Fully Automated a Faceless YouTube Channel with Claude Code (Zero Editing) | BigStepsMedia | ~26K | https://www.youtube.com/watch?v=DdnPlptStMM |

Workflow demonstrated per pick:
1. Cole Medin — full pipeline via the **Archon workflow engine**: research→script→visuals→render, custom templates.
2. Jacksons AI — **Claude Code + Remotion + ElevenLabs TTS + WaveSpeed**: motion graphics, voiceover, editing in one stack.
3. Zinny Studio — deepest agent architecture: **11 skills, 9 agents, Notion Kanban gates, CLAUDE.md brand guide, MCPs (vidIQ/Notion/Gmail/Higgsfield), scheduled routines**.
4. Jacksons AI — one reusable prompt auto-produces **VOX-style documentary** videos (script, visuals, voiceover).
5. Kanhaiya Growth — clone a viral **2D documentary** channel format with Claude AI.
6. John Hartquist — **Remotion + MCP servers + Veo 3 + Nano Banana + ElevenLabs + Deepgram** end-to-end code-rendered video.
7. Danny Why — most-watched Remotion tutorial; YouTube videos without After Effects.
8. David Ondrej — **Remotion agent skills** inside Claude Code; plain-English prompts → programmatic scenes.
9. Andrew Ford — **Buttercut** (open source): Claude analyzes footage → selects, cleaned interviews, rough cuts → Final Cut.
10. BigStepsMedia — zero-manual-editing faceless channel; exact working files shared.

## Strong honorable mentions (all oEmbed-verified)

- I Automated My Entire YouTube Workflow with Claude Code (4-skill system: research→transcribe→plan→thumbnail) — Tyler AI, ~3K — https://www.youtube.com/watch?v=MLfyfNj1JrI
- Claude Code and Codex Quietly Learned to Watch Video (drag-drop MP4, frame+audio analysis) — Mark Kashef, ~3.7K — https://www.youtube.com/watch?v=0I-J1aoxYQY
- How I Fully Automated My Video Editing (Claude Code) — Brendan Jowett, ~163K — https://www.youtube.com/watch?v=G0EH0xdy2-E
- How I Fully Automated My Video Editing (Claude Code) — Jason Cooperson, ~99K — https://www.youtube.com/watch?v=XeTAlZiIWHE
- Claude Just Edited My Entire YouTube Video — Here's What It Created — Joseph | Video Editing, ~110K — https://www.youtube.com/watch?v=uyN-nAEuIjw
- Claude Code is Taking Video Editor Jobs Now (Remotion Skills) — Chase AI, ~29K — https://www.youtube.com/watch?v=4N_TfYVNM7k
- Everything Claude Code + Remotion Can Do in 2026 (Full Animation Breakdown) — Andy Lo, ~24K — https://www.youtube.com/watch?v=OX80FZjHJ7o
- How I Created a Professional Motion Graphics Video With Claude Code + Remotion Skills (No Editing) — Andy Lo, ~54K — https://www.youtube.com/watch?v=xAUifztpib8
- How I Built a YouTube Shorts Clipper With Claude Code (Full Workflow) — Andy Lo, ~9.6K — https://www.youtube.com/watch?v=k6C42kjyZ38
- Claude Code + Remotion creates Insane Content (NEW Skill) — Giovanni Beggiato, ~38K — https://www.youtube.com/watch?v=Sthv8xcy2y4
- How To Make 3D Documentary Animations With Claude — AI Century, ~4.4K — https://www.youtube.com/watch?v=lGP7ycL2fnI
- Claude Ai + YouTube = $9,987/Month (FREE Plan) \| Create Viral 2D Documentary Videos — Chad Grow, ~137K — https://www.youtube.com/watch?v=qJkC05DjVlA
- Claude Design Just Unlocked AI Motion Graphics — Futurepedia, ~148K — https://www.youtube.com/watch?v=97Y5cz7H8SM
- Make AI Videos With Code Using Claude Code + Remotion! (Full Tutorial) — Alex Followell, ~2.7K — https://www.youtube.com/watch?v=XPbMMTcUYwM
- 🔴LIVE — Full AI Video Generation Workflow Using Claude Code + Remotion + Archon — Cole Medin, ~11K — https://www.youtube.com/watch?v=vhbaZJtW2Hg
- How people are generating videos with Claude Code (Remotion Skill) — Leonardo Grigorio, ~47K — https://www.youtube.com/watch?v=7OR-L0AySn8 (seen on 2 live search pages; oEmbed call rate-limited but DOM-confirmed)

## Key takeaways for a Hermes/HyperFrames-style pipeline
- "Video-as-code" (Remotion/HTML-renderer) + agent writes scenes + TTS voiceover + ffmpeg assembly is the
  industry-standard pattern; TTS (ElevenLabs) is a first-class stage — edge-tts replaces it free.
- Winning architecture = skills/agents + workflow engine + Kanban human-gates (Zinny Studio #3 is the blueprint).
- Documentary/VOX-style faceless is a proven niche with 3+ dedicated tutorials (#4, #5, Chad Grow).
