# FREE Assembly + Motion-Graphics + Subtitle Stack (live-verified Aug 9, 2026)

Verified during a full hunt for the documentary pipeline on Windows (pipeline already runs HyperFrames + FFmpeg). Every license via GitHub API (`api.github.com/repos/<r>` → `license.spdx_id`), every version via PyPI JSON, every claim from official docs/source. All URLs were fetched at verify time.

## The stack in one sentence
MoviePy/FFmpeg orchestrates assembly; Manim makes explainers; ECharts SSR (+ D3/Chart.js/GSAP via headless Chrome) makes charts & motion design; faster-whisper/whisper.cpp make SRTs; FFmpeg burns subs and delivers. Every step is a CLI or Python call an agent can issue. Nothing replaces HyperFrames — these fill the layers around it.

## Assembly / editing

| Tool | License | Windows | Headless / agent fit |
|---|---|---|---|
| FFmpeg | LGPL-2.1+ with GPL-2+ optional parts ("not available under any other licensing terms") | yes | 100% CLI. concat demuxer, filters, amix, subtitles/ass burn-in |
| MoviePy 2.2.1 | MIT (PyPI `py3-none-any` wheel) | yes | `pip install moviepy`; programmatic timeline → renders via FFmpeg. THE agent assembly layer |
| Shotcut v26.8.1 | GPL-3.0 | yes | GUI-only, NO headless CLI. But export runs `melt` subprocess (src/main.cpp ~L521) → render its .mlt XML with melt |
| MLT / melt 7.40 | LGPL-2.1 | yes (ships with Shotcut) | headless CLI: `melt file.mlt -consumer avformat:out.mp4` ("author, play, and encode multitrack audio/video compositions") |
| OpenShot / libopenshot | openshot-qt GPL-3.0 (COPYING); libopenshot LGPL-3.0-or-later | yes | GUI no; `import openshot` Python bindings render headless (multi-layer, curves, audio mix) — more setup than MoviePy |
| DaVinci Resolve 21 Free | proprietary freeware (NOT OSS); Studio $295 | yes | **Not headless.** Scripting API exists but GUI app must run; free-tier API access disputed — pydavinci README: "External scripting with PyDavinci requires Resolve Studio 18 (Free version does not allow API access)". Use for human color/finishing only |

## Motion graphics

| Tool | License | Windows | Headless / agent fit |
|---|---|---|---|
| Manim (ManimCommunity) | MIT (double: 3b1b LLC + community) | yes (`pip install manim`) | `manim render -ql scene.py MyScene` → mp4/frames. Agent writes scene code → CLI |
| Apache ECharts | Apache-2.0 | n/a (Node) | **Official SSR**: server-side SVG string rendering, no browser (`echarts.init(null,null,{renderer:'svg',ssr:true})`) — best agent data-viz |
| D3.js | ISC | n/a (JS) | headless Chrome screenshots or Node+jsdom → SVG |
| Chart.js | MIT | n/a (JS) | headless Chrome / node-canvas |
| GSAP | "100% free for all users" (gsap.com/pricing, Webflow-supported) — no-cost commercial license, NOT OSI | n/a (JS) | no renderer of its own; animate DOM → Playwright frame grabs |
| Motion Canvas | MIT | yes (Node) | **NO headless render** — docs: rendering "depends on the capabilities of your browser", click RENDER in editor, frames to /output. Human tool only |
| Remotion | custom "Remotion License" (source-available, NOT OSI): free for individuals / for-profit ≤3 employees / non-profits, commercial OK; paid company license above (remotion.pro) | yes (Node) | `npx remotion render` headless Chrome, batch rendering. Only free if org qualifies |

## Subtitles / captions

| Tool | License | Windows | Headless / agent fit |
|---|---|---|---|
| openai-whisper 20250625 | MIT | yes (py ≥3.8, needs ffmpeg) | `whisper file --model turbo --output_format srt` |
| faster-whisper 1.2.1 | MIT | yes (ctranslate2 win_amd64 cp310–cp313 wheels on PyPI) | ~4× faster, int8, word timestamps. **Default engine** |
| whisper.cpp | MIT | yes (MSVC + MinGW) | single binary, CPU: `main -m model.bin -f audio.wav -osrt` |
| whisperX | BSD-2-Clause | yes (pip) | word-level + diarization: `whisperx audio --output_format srt --diarize` |
| whisper-timestamped | **AGPL-3.0** | yes | ⚠️ AVOID (AGPL obligations) |
| Subtitle Edit | MIT (repo metadata) | yes | GUI polish only, no real CLI |
| video-subtitle-generator (YaoFANGUK) | Apache-2.0 | yes | local Whisper-based, low priority |

## Agent recipes
```bash
whisper audio.mp3 --output_format srt --model turbo        # or faster-whisper (py) / whisper.cpp main -osrt
manim render -ql scenes.py IntroScene                     # explainers
node chart.js --ssr > chart.svg                           # ECharts SSR, no browser
playwright screenshot scene.html frame_001.png            # GSAP/D3/Chart.js frames (loop per frame)
python assemble.py                                        # MoviePy: concat, crossfades, voiceover mix, deliver
melt timeline.mlt -consumer avformat:final.mp4            # MLT timeline engine
ffmpeg -i cut.mp4 -vf "ass=subs.ass" -c:a aac final.mp4   # burn subs + final encode
```

## Verification method (reusable)
- License batch: `api.github.com/repos/<owner>/<repo>` → `license.spdx_id` + stars + archived + pushed_at; `NOASSERTION` = custom/undetected license → read LICENSE.md/COPYING from `raw.githubusercontent.com/<r>/HEAD/<file>` (Remotion, FFmpeg mirror, OpenShot).
- Windows support: PyPI JSON `pypi.org/pypi/<pkg>/json` → `urls[].filename` — `win_amd64` wheel = native (check the NATIVE dep, e.g. ctranslate2 for faster-whisper); `py3-none-any` = pure Python.
- Headless claims: grep source/docs, don't trust marketing (Shotcut src/main.cpp "melt export subprocess"; Motion Canvas docs "depends on the capabilities of your browser"; ECharts handbook SSR page).
- Search engines were all bot-blocked this session (DDG captcha, Google sorry, Bing timeout) — the URL-known verification path needs none of them.

## LIVE-VERIFIED URL index (all fetched 2026-08-09)
- https://ffmpeg.org/legal.html (LGPL/GPL dual) · https://github.com/Zulko/moviepy · https://pypi.org/project/moviepy/ (2.2.1 MIT)
- https://github.com/mltframework/shotcut (GPL-3.0, v26.8.1) · https://shotcut.org · https://github.com/mltframework/shotcut/blob/master/src/main.cpp (melt subprocess)
- https://github.com/mltframework/mlt/blob/master/docs/melt.1 (melt 7.40 man page)
- https://github.com/OpenShot/openshot-qt (COPYING) · https://github.com/OpenShot/libopenshot (LGPL-3.0-or-later, Python bindings)
- https://www.blackmagicdesign.com/products/davinciresolve (Free + Studio $295) · https://github.com/pedrolabonia/pydavinci (free-tier scripting dispute)
- https://github.com/ManimCommunity/manim (MIT) · https://docs.manim.community/en/stable/installation.html (pip, Windows)
- https://gsap.com/pricing/ ("100% free for all users") · https://github.com/d3/d3 (ISC) · https://github.com/chartjs/Chart.js (MIT)
- https://github.com/apache/echarts (Apache-2.0) · https://echarts.apache.org/handbook/en/how-to/cross-platform/server/ (SSR)
- https://github.com/motion-canvas/motion-canvas (MIT) · https://motioncanvas.io/docs/rendering/ (browser-bound)
- https://github.com/remotion-dev/remotion/blob/main/LICENSE.md (≤3 employees) · https://www.remotion.dev/docs/cli (200) · https://www.remotion.pro/license
- https://github.com/openai/whisper (MIT) · https://github.com/SYSTRAN/faster-whisper (MIT) · https://github.com/ggml-org/whisper.cpp (MIT) · https://github.com/m-bain/whisperX (BSD-2-Clause) · https://github.com/linto-ai/whisper-timestamped (AGPL ⚠️) · https://github.com/SubtitleEdit/subtitleedit (MIT) · https://github.com/YaoFANGUK/video-subtitle-generator (Apache-2.0)
