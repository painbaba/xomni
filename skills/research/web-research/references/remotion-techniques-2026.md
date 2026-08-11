# Remotion Pro Techniques — verified knowledge bank (Aug 10, 2026, v4.0.507)

Research output for "how to make a Remotion composition look pro" (animated maps, bar-chart races,
transitions, particles, text, perf on weak GPUs). Full deliverable on disk:
`C:\Users\HP\remotion_pro_techniques_2026.md`. Every YouTube URL below was oEmbed-verified at compile
time (canonical title + author returned); every remotion.dev path returned HTTP 200; npm versions
confirmed at 4.0.507.

## Technique → verified tutorial URLs (oEmbed-verified 2026-08-10)

**Animated maps (Vox-style):**
- MoSidd "I Made Vox-Style Motion Graphics Using Only Claude Code & Remotion" (130K) — https://www.youtube.com/watch?v=7wuYBfE131U
- MoSidd "I Built a Vox Explainer Using Claude Code & Remotion (No Plugins)" — https://www.youtube.com/watch?v=Y6mOBK5peDU
- Buried Signals "Map Animation with Remotion" — https://www.youtube.com/watch?v=IRuJp3-omnM (only dedicated map-in-Remotion tutorial found)
- Style reference: Vox "Why all world maps are wrong" (23.4M) — https://www.youtube.com/watch?v=kIID5FDi2JQ

**Bar-chart race / animated charts:**
- MoSidd "Create Animated Charts and Graphics Instantly with AI & Remotion" — https://www.youtube.com/watch?v=dBakc0BdHjY
- The Mr Dev Loper "Nifty 50 Chart Animation with Claude Code + Remotion" — https://www.youtube.com/watch?v=o7-00FK408k
- AiTLDR "Remotion + Claude Code: Build Animated Charts…" — https://www.youtube.com/watch?v=ye9s8kYAHuE
- Official prompt recipe: https://www.remotion.dev/prompts/bar-line-chart-combined

**Transitions:**
- Remotion (official) "Create video transitions with Remotion" — https://www.youtube.com/watch?v=e9H5MEGVJBI (canonical)
- fivenine-design 12-transition gallery (Japanese) — https://www.youtube.com/watch?v=BqlYhHGh9Gg

**Particles/dust:** NO dedicated Remotion particles tutorial exists on YouTube (verified via multiple query angles). The technique is demonstrated inside: Fireship "This video was made with code. But how?" (882K) — https://www.youtube.com/watch?v=deg8bOoziaE · Andy Lo "Everything Claude Code + Remotion Can Do in 2026" — https://www.youtube.com/watch?v=OX80FZjHJ7o

**Text animation:**
- Make Task Easy "How to Animate Text with Remotion in React" — https://www.youtube.com/watch?v=kNtG8YWduIw
- TECH DROP "Remotion to Automate CapCut Text Animation (Viral Style)" — https://www.youtube.com/watch?v=klcpQA-BWY0

**Performance:**
- Remotion (official) "Optimizing Remotion Lambda renders for cost and speed" — https://www.youtube.com/watch?v=GUsjj1jsLhw
- FRMWRKD-EXPLAINED "Remotion Masterclass: The VERY ADVANCED System Behind AI Motion Graphics" — https://www.youtube.com/watch?v=PFHVxq1S6F0

**3D (bonus, heavy GPU):** Lukas Margerie "Full 3D Animation using Remotion with Claude Code" — https://www.youtube.com/watch?v=NTfXwQ85suw · prompt: https://www.remotion.dev/prompts/travel-route-on-map-with-3d-landmarks

## API facts verified at 4.0.507 (docs live-fetched, HTTP 200)

- **`@remotion/transitions`** (since v4.0.53, ships in 4.0.507): `TransitionSeries` + presentations `fade()`, `pushCut()`, `slide()`, `wipe()`, `flip()`, `clockWipe()`, `iris()`, and HTML-in-canvas set `zoomBlur()`, `dreamyZoom()`, `filmBurn()`, `linearBlur()`, `bookFlip()` (page-curl!), `zoomInOut()`, `dissolve()`. Custom transitions via `TransitionPresentation` + `useTransitionProgress()` (gradient wipe / glitch). Usage: `TransitionSeries.Sequence` + `TransitionSeries.Transition presentation=… timing={linearTiming({durationInFrames})}`.
- **`@remotion/noise`** (MIT): `noise2D/3D/4D` are deterministic (same frame → same value) → headless-render safe. Particle recipe = seeded `random(\`dust-${i}\`)` for stable per-particle state + noise2D for drift. Docs: remotion.dev/docs/noise.
- **Official Maps page exists now**: remotion.dev/docs/maps recommends **MapLibre GL JS + Turf.js** (`npm i maplibre-gl @turf/turf`, `import 'maplibre-gl/dist/maplibre-gl.css'`, `useDelayRender()` for map load, Turf `greatCircle()` for geodesic arcs). Lighter alternative: `d3-geo` geoMercator + GeoJSON → SVG `<path>` (fully deterministic, best for headless).
- **Performance (remotion.dev/docs/performance)**: `npx remotion benchmark` to find optimal concurrency (too high AND too low both hurt); `--scale 0.5` for iteration renders; `--log=verbose` lists slowest frames; GPU-heavy culprits = WebGL (three/skia/p5/mapbox), 2D canvas, `box-shadow`/`text-shadow`/gradients — on 4GB VRAM use concurrency 2–4, plain circles + one blurred overlay instead of per-particle shadows, `React.memo` static subtrees; prefer `<Video>` from `@remotion/media` for footage.
- npm exact versions at compile time: `@remotion/transitions`, `@remotion/noise`, `@remotion/three`, `@remotion/shapes`, `@remotion/google-fonts` all 4.0.507.

## Pitfalls / negative finds

- **`remotion-dev/template-barchartrace` is DEAD (404)** — do not reference it; build bar races from the pure-React pattern (sorted bars + per-index `spring` stagger + count-up ticks).
- No dedicated Remotion particles tutorial on YouTube — don't burn turns searching; point users at the Fireship/Andy Lo showcases.
- Remotion's official Prompt Showcase (`remotion.dev/prompts/*`) is a goldmine of exact spec-style prompts (bar+line chart with spring timing, map routes with 3D landmarks) — check it before writing a composition from scratch.
- Old remotion.dev slugs churn: `/docs/templates` and `/docs/svg` 404; the sitemap (`remotion.dev/sitemap.xml`) is the reliable index.

## Method notes (what worked)

- Docs-first: sitemap → grep for chart/map/text/anim/perf → fetch pages, extract `<pre>` code blocks (Docusaurus renders code in `<pre>`, plain tag-strip loses it).
- Technique-specific YT discovery: search `ytInitialData` with queries shaped `<tool> <technique>` ("remotion map animation d3", "remotion bar chart race", "remotion transitions wipe") — generic queries ("remotion particles") surface off-topic results (After Effects / TouchDesigner tutorials).
- Verify every candidate ID via oEmbed batch; npm registry `/latest` + GitHub API for package/repo liveness (dead template caught this way).
