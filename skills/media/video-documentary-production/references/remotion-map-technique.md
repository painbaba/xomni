# Remotion country-map technique (d3-geo + world-atlas, build-time path gen)

Working recipe from the UPI trailer (Aug 2026): animated country outline that draws
itself on + city pulse dots, overlaid on footage. Zero runtime deps beyond dev-time
node packages; the map is precompiled to an SVG path string at build time.

## 1. Dev-time deps + data (one-time per project)
```
npm i -D d3-geo topojson-client @types/d3-geo @types/topojson-client
curl -sL -o /tmp/countries-110m.json "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
```
(world-atlas is TopoJSON of Natural Earth; countries-110m.json ≈ 700KB. The npm CDN
URL avoids GitHub raw redirects.)

## 2. Generate `src/<country>Path.ts` (node, build-time)
```js
const fs = require('fs');
const topojson = require('topojson-client');
const d3 = require('d3-geo');
const world = JSON.parse(fs.readFileSync('/tmp/countries-110m.json', 'utf8'));
const country = topojson.feature(world, world.objects.countries)
  .features.find(f => f.id === '356');               // ISO 3166-1 numeric: India = 356
const proj = d3.geoMercator().fitSize([1200, 1200], country);   // 1:1 viewBox coords
const cities = { Delhi: [77.2, 28.6], Mumbai: [72.9, 19.1],
                 Bengaluru: [77.6, 12.9], Patna: [85.1, 25.6] };  // lon, lat
const cityArr = Object.entries(cities).map(([n, [lon, lat]]) => {
  const p = proj([lon, lat]); return { name: n, x: Math.round(p[0]), y: Math.round(p[1]) };
});
fs.writeFileSync('src/indiaPath.ts',
  'export const INDIA_PATH = ' + JSON.stringify(d3.geoPath(proj)(country)) + ';\n' +
  'export const INDIA_CITIES = ' + JSON.stringify(cityArr) + ';\n');
```
- `fitSize` returns a MERCATOR projection — fine for mid-latitudes; polar regions would
  want geoNaturalEarth1. City coords come out in the SAME 1200×1200 space as the path,
  so the SVG can place dots at `(c.x/1200)*size` without further math.

## 3. Draw-on + pulse component (Remotion, deterministic — no hooks)
```tsx
const total = 3000; // must exceed the path's true length; overshoot is invisible
const drawn = interpolate(frame, [0, 48], [total, 0], {
  extrapolateLeft: "clamp", extrapolateRight: "clamp",
  easing: Easing.inOut(Easing.cubic),
});
// <path d={PATH} strokeDasharray={total} strokeDashoffset={drawn} />
// + drop-shadow filter for the glow; fill rgba(gold, 0.06) for a subtle landmass tint
// city dots: per-city t0 = 42 + i*17; scale 0->1 (out cubic), opacity 1->0 pulse
```
- stroke-dashoffset draw-on needs NO path-length measurement — a dasharray larger than
  the path just starts fully hidden. Works for any country.
- City pulses: `scale` interpolate for the pop, a separate `opacity` keyframe that
  decays after ~0.6s — looks like a broadcast "ping".
- Overlay placement: absolute right/bottom of the scene, ~470px box, `pointerEvents:
  none`, over the footage with the scene's existing scrim for readability.

## 4. Scene wiring
- Add `map?: boolean` to the Scene type; render `{s.map ? <IndiaMap /> : null}` in
  SceneContent (local frame via useCurrentFrame inside the scene Sequence).
- Verify: `npx tsc --noEmit` + `npx remotion render` (see scripts/verify-remotion.py).

Other techniques from the swarm report (`C:\Users\HP\remotion_pro_techniques_2026.md`,
verified Aug 2026): bar-chart race = pure React + spring stagger (no lib; the old
template-barchartrace repo is 404-dead), gradient text = background-clip + animated
background-position, transition alternatives = wipe/glitch via clip-path keyframes.
MoSidd's Vox-style tutorial (youtube.com/watch?v=7wuYBfE131U, 130K views) is the best
single demo for the whole class.
