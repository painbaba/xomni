# God-page dashboard: views, rendering pitfalls, and the black-screen saga

The machine-city watch page (`ghost-lab\god_page.py`, stdlib http.server,
port 8792) exposes `/api/state` JSON + three views. This file is the
rendering playbook — every pitfall below cost real debugging time.

## Server essentials

- Serve `/api/state` as JSON: bank status (curl 9988), civilizations
  (dirs+file counts), districts (machine_city subdirs with `population\` and
  `opinions\` counts), census/registry/ledger tails, live delegation stream
  tails (glob `cache\delegation\live\deleg_*\task-*.log`, tail ~500B each),
  and listening ports.
- **Strip query strings in do_GET** (`path = self.path.split("?")[0]`) so
  cache-busting URLs (`/3d?v=99`) don't 404.
- **Send no-store headers on HTML views** (`Cache-Control: no-store,
  no-cache, must-revalidate, max-age=0` + `Pragma: no-cache`) — browsers
  cache aggressively and will show a STALE page forever after the first
  broken version; the user's "still black" was often the cached old file.
- HEAD requests: BaseHTTPRequestHandler returns 501 for methods you don't
  implement — harmless, but know it before diagnosing "server broken".
- One listener per port: kill stale servers (multiple `god_page.py`
  processes accumulate; `netstat -ano | grep :8792` then Stop-Process the
  old PIDs) — a late watch-pattern notification from a KILLED process is
  noise, not a live server.

## The black-screen saga (user sees nothing but black)

Symptoms: page title + HUD render, stats text updates, but the canvas area
is black. Debug ladder in order:

1. **CDN scripts blocked = total failure.** The first version loaded
   three.js from cdnjs/jsdelivr. If the user's browser/network can't reach
   the CDN (or a blocker eats it), `new THREE.Scene()` throws, no canvas is
   ever created, and the near-black page background is all they see. My test
   browser (Browserbase) had internet so it rendered fine while the USER saw
   black. FIX: download three.min.js + OrbitControls.js + GLTFLoader.js
   (~600KB + 26KB + 96KB) ONCE and serve them from the same server under
   `/assets/vendor_*.js`; point the page at local paths. Zero external
   dependencies after that.
2. **WebGL genuinely unavailable** (user's GPU/driver/headless): add a
   guard — `if (!window.WebGLRenderingContext) { show red warning + link to
   the 2D view; return; }` so it's a message, not a black void.
3. **Day/night cycle running absurdly fast.** `dayT += dt*0.008` at 60fps =
   full day in ~2 seconds; the scene flashes through night constantly, so
   most of what the user sees is near-black. FIX: clamp the sun value to
   always-bright (`sun = 0.72 + 0.28*cycle`) and slow the cycle by 20x —
   for a territory DASHBOARD the scene should never go dark at all.
4. **CapsuleGeometry does not exist in three r128.** `new THREE.CapsuleGeometry`
   throws (`CapsuleGeometry is not a constructor` in r128; added ~r132). A
   truthy ternary like `new X ? a : b` still EVALUATES `new X` and throws —
   use plain CylinderGeometry for capsule people.
5. **Fog too dense washes everything out.** FogExp2 density 0.008 at
   distance ~80 = objects fade to the fog color (near black). Use ~0.004 and
   a lighter fog color.
6. **Too-dark baseline**: night sky HSL lightness 0.04 is black; ground
   `0x0b0b18` is black. Raise both so even "night" is a visible dusk.

## The 2D isometric fallback (`/3d2`) — the guaranteed view

When WebGL won't cooperate, render the same territory with PURE Canvas 2D —
works on every browser, no GPU, no dependencies:

- Isometric projection: `sx = (x - z) * 0.866 * S + cx`, `sy = (x + z) * 0.5 * S + cy`
  (S = scale ~22, cx/cy = center + pan).
- `drawBlock(x, z, w, d, h, color)`: three faces — top (lightest),
  left (×0.75), right (×0.55); `shade(hex, f)` scales RGB channels.
- Citizens = ellipse shadow + head circle + body rect, bob with sin(phase).
- Zoom via wheel (`zoom *= 1.1/0.9`), pan via mousedown/mousemove.
- Animate with `setInterval(..., 50)` + re-render; fetch `/api/state` every
  ~5s and rebuild the district/citizen list when the district count changes.
- Layout mirrors the 3D scene: ghost zone (red) at -30,-20, god's zone
  (gold) at 32,22, farm crops, districts on an 8-spaced grid, bank tower at
  0,0 (green when UP, red when DOWN).

## Model assets (free, CC0)

- Khronos glTF-Sample-Models (GitHub) — direct raw GLB URLs:
  `https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/<Name>/glTF-Binary/<Name>.glb`
  (Duck ~120KB, Fox ~163KB, BoomBox ~10MB, Avocado ~8MB). Serve locally via
  the `/assets/` route; load with GLTFLoader; cache the loaded scene and
  `.clone()` for placement.
- Poly Haven API needs exact param format (`?t=objects` with no extra
  filters or you get 400); Kenney pages are JS-rendered (no server-side
  links to scrape) — prefer Khronos raw URLs for reliability.
