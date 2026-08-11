# Motion-Graphics & Data-Viz Pattern Catalog for Automated Explainers (verified Aug 2026)

Research output for a headless HTML/GSAP → video pipeline (HyperFrames-style). 15 patterns ranked by **wow ÷ implementation effort**, each with best tool + headless-production path. Every URL below was live-fetched during research (status codes in the fact list at the end). Full deliverable also on disk: `C:\Users\HP\motion_graphics_pattern_catalog.md`.

## Production-path tiers

| Tier | Path | Tools (all live-verified) |
|---|---|---|
| A — Web-native (best fit) | HTML+JS (D3/GSAP/SVG) in one file → frame-seek → headless Chrome (Puppeteer/Playwright) → ffmpeg → MP4 | D3, GSAP, Chart.js, ECharts, CountUp.js, Puppeteer, Playwright, ffmpeg |
| B — Code-driven video frameworks | Declarative scene code compiled to video headlessly (no screen capture) | Remotion (React→MP4), Motion Canvas (TSX→MP4) |
| C — SaaS template tools | No-code templates; automation via developer API; video/GIF export in logged-in app | Flourish (dev portal), Datawrapper (API — static chart export) |
| D — AE templates | Designer-in-the-loop; not headless; style reference only | VideoHive/Envato |

## The catalog (ranked by wow ÷ effort)

1. **Count-up number + ring/odometer** (effort 1, wow 3) — hero stat counts 0→value, ring fills via SVG `stroke-dashoffset`. Tool: GSAP `gsap.to()` on a proxy object, or CountUp.js (dependency-free). Headless: A. URL: https://gsap.com/docs/v3/GSAP/gsap.to() · https://inorganik.github.io/countUp.js/
2. **Kinetic typography — word-by-word pop** (2, 4) — SplitText splits chars/words/lines; stagger scale+blur; punch-word accents (Vox/Johnny Harris title beats). Tool: GSAP SplitText. Headless: A. URL: https://gsap.com/docs/v3/Plugins/SplitText/
3. **Line chart draw-on (stroke reveal)** (2, 4) — line draws L→R, area fades, highlight dot rides the line. Tool: D3 geometry + GSAP DrawSVGPlugin (or `stroke-dashoffset`). Headless: A. URL: https://observablehq.com/@d3/line-chart · https://gsap.com/docs/v3/Plugins/DrawSVGPlugin
4. **Bar chart race** (3, 5) — bars re-sort over time, #1 flash, date counter. Tool: D3 bar-chart-race (canonical Observable notebook) for code; Flourish "Bar chart race" template (CSV→animate) for no-code. Headless: A (D3) / C (Flourish, app export). URL: https://observablehq.com/@d3/bar-chart-race · https://flourish.studio/visualisations/bar-chart-race/ ("Make a bar chart race without coding")
5. **Map route / connection path draw** (3, 5) — route/arc draws across a map, dash-flow pulse, traveling dots (Johnny Harris signature). Tool: D3 (topojson basemap + path gen) + GSAP DrawSVGPlugin; Flourish "Maps" as no-code. Headless: A. URL: https://d3-graph-gallery.com/connectionmap · https://flourish.studio/visualisations/
6. **Text scramble / typewriter** (1, 3) — GSAP TextPlugin (`scrambleText`, `type`). Headless: A. URL: https://gsap.com/docs/v3/Plugins/TextPlugin/
7. **Animated choropleth** (3, 4) — regions fill sequentially or smoothly re-color; legend animates (elections/GDP/demographics). Tool: D3 choropleth + GSAP stagger; Datawrapper maps as no-code. Headless: A. URL: https://observablehq.com/@d3/choropleth · https://www.datawrapper.de/maps
8. **Map camera moves (pan/zoom over baked map)** (3, 4) — paper-map style camera flythrough (Borders-series staple). Tool: GSAP transform tween on oversized map container (or D3 projection interpolation). Headless: A.
9. **FLIP infographic morph** (3, 4) — number→bar→pie transitions (First-Last-Invert-Play). Tool: GSAP Flip plugin. Headless: A (DOM-based, timeline-driven). URL: https://gsap.com/docs/v3/Plugins/Flip/
10. **Scatter/bubble race (Gapminder-style)** (4, 5) — points drift across axes with year counter (Hans Rosling "200 Years"). Tool: custom D3 (per-frame interpolation); Flourish "Bubble charts" no-code. Headless: A / C. URL: https://www.gapminder.org/ · https://flourish.studio/visualisations/
11. **Line chart race (horserace)** (1–3, 4) — lines race to the top, ranks flip (markets/standings). Tool: Flourish "Line chart race" template (no-code, minimal cost); custom D3 multi-line + y-scale remap. Headless: C / A. URL: https://flourish.studio/visualisations/
12. **Pictogram fill** (2, 3) — icon grid fills 1-by-1 ("1 in 4 people"). Tool: SVG icon grid + GSAP stagger (mask/clip); Flourish "Pictogram charts". Headless: A. URL: https://flourish.studio/visualisations/
13. **Gauge / speedometer dial** (2, 3) — needle sweep + count-up (policy/finance beats). Tool: SVG arc + rotation tween + CountUp.js. Headless: A.
14. **Animated area/streamgraph flow** (4, 4) — stacked areas undulate (energy mix, audience share). Tool: custom D3 streamgraph; Flourish "Streamgraphs". Headless: A / C. URL: https://flourish.studio/visualisations/
15. **Sankey / flow animation** (4, 4) — money/energy flows between nodes (canonical financial-explainers diagram). Tool: custom D3 Sankey; Flourish "Sankey charts". Headless: A / C. URL: https://flourish.studio/visualisations/

## Channel-style synthesis (verified context)
- **Johnny Harris / Vox "Borders"**: Wikipedia (verified) — "fast-paced, visually-driven style… produced the Borders series for… Vox" (https://en.wikipedia.org/wiki/Johnny_Harris_(journalist)). Observable toolkit: paper-map aesthetics, route/connection paths, camera moves, kinetic type, count-ups. NOTE: johnnyharris.com + papermaps.co were connection-refused from research network — no site-level citations.
- **Financial explainers**: count-ups + big-number reveals, line draw-ons, bar races, Sankey money flows, gauge/odometer.
- **Data-documentary staples**: choropleth reveals, scatter races, horserace line charts.

## Tool guidance for HTML/GSAP pipeline (Tier A)
- D3 v7 (https://d3js.org/) — geometry + scales; pair with GSAP for motion; Observable examples are canonical, copy-able.
- GSAP (https://gsap.com/docs/v3/) — core + SplitText, DrawSVGPlugin, TextPlugin, Flip. All DOM/SVG → frame-seekable → headless-renderable.
- Chart.js (https://www.chartjs.org/docs/latest/configuration/animations.html) / ECharts (https://echarts.apache.org/en/index.html) — drop-in animated charts; ECharts adds SSR.
- Remotion (https://www.remotion.dev/docs/render) / Motion Canvas (https://motioncanvas.io/docs/rendering) — Tier B headless code→video alternatives.
- SaaS: Flourish dev portal (https://developers.flourish.studio/) + help (https://help.flourish.studio/); Datawrapper API (https://developer.datawrapper.de/).
- Capture: Puppeteer (https://pptr.dev/) / Playwright (https://playwright.dev/) + ffmpeg (https://ffmpeg.org/).

## LIVE-VERIFIED FACTS (fetched Aug 2026)
- https://observablehq.com/@d3/bar-chart-race — 200 (client-rendered; status = signal)
- https://observablehq.com/@d3/choropleth — 200 (client-rendered)
- https://observablehq.com/@d3/line-chart — 200 (client-rendered)
- https://observablehq.com/plot/ — 200
- https://d3js.org/ — 200 · https://github.com/d3/d3 — 200
- https://flourish.studio/visualisations/ — 200; template list verified: Bar chart race, Line chart race (horserace), Bubble charts, Streamgraphs, Sankey charts, Pictogram charts, Maps
- https://flourish.studio/visualisations/bar-chart-race/ — 200, title "Make a bar chart race without coding | Flourish"
- https://flourish.studio/ — 200 · https://developers.flourish.studio/ — 200 · https://help.flourish.studio/ — 200
- https://www.datawrapper.de/charts — 200, "Charts | Datawrapper" · https://www.datawrapper.de/maps — 200 · https://developer.datawrapper.de/ — 200
- https://gsap.com/docs/v3/ — 200 · gsap.to() — 200 · SplitText/ — 200 · DrawSVGPlugin — 200 (note: `/DrawSVG` without "Plugin" 404s) · TextPlugin/ — 200 · Flip/ — 200
- https://inorganik.github.io/countUp.js/ — 200, "CountUp.js" · https://www.npmjs.com/package/countup.js — 200
- https://www.chartjs.org/docs/latest/configuration/animations.html — 200, "Animations | Chart.js" · https://echarts.apache.org/en/index.html — 200, "Apache ECharts"
- https://www.remotion.dev/ — 200 · /docs/ — 200 · /docs/render — 200 · /templates — 200 · /docs/the-fundamentals — 200
- https://motioncanvas.io/ — 200 · /examples/ — 200 · /docs/quick-start — 200 · /docs/rendering — 200 · https://github.com/motion-canvas/motion-canvas — 200
- https://d3-graph-gallery.com/connectionmap — 200, "Connection map | the D3 Graph Gallery" · https://d3-graph-gallery.com/barplot — 200
- https://www.gapminder.org/ — 200
- https://pptr.dev/ — 200 · https://playwright.dev/ — 200 · https://ffmpeg.org/ — 200
- https://videohive.net/search/data%20visualization — 200, "Data Visualization Video Effects & Stock Videos | VideoHive"
- https://en.wikipedia.org/wiki/Johnny_Harris_(journalist) — 200 (extract via rest_v1 summary API: "fast-paced, visually-driven style… Borders series for… Vox")
- **Not verifiable from this network:** johnnyharris.com / papermaps.co (connection refused 000); DDG html/lite + Bing SERPs (captcha-walled, curl AND browser); Flourish singular-path `/visualisation/<name>/` (404 — correct is plural `/visualisations/<name>/`); observablehq.com/@d3/us-airports, /flight-connections, /airports (404) — the classic Bostock flight-route notebooks are not on those slugs anymore.
