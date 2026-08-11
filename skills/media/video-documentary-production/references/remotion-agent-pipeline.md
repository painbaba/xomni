# Remotion as Agent Render Core (hybrid with HyperFrames)

Session-verified 2026-08-10 (UPI trailer rebuild on Remotion 4.0.507). Research
verdict (17-agent swarm): Remotion is the better render core for agent-driven docs —
deterministic frames, parallel render, captions SDK, 12 official Agent Skills; the
Remotion MCP is DEPRECATED (shuts ≤ Aug 31 2026 — do not install; skills replace it).
HyperFrames keeps the edge for GSAP-heavy motion graphics (OpenMontage splits engines
the same way). Strategy: Remotion for structure/transitions, HyperFrames for motion.

## Scaffold + versions
- NEVER guess versions: `npm view <pkg> version` first (remotion 4.0.507, react 19.2.8,
  typescript 5.9.3 — my 4.0.0/19.0.0/5.6.0 guesses all failed ETARGET).
- package.json deps: remotion, @remotion/cli, @remotion/captions, @remotion/transitions,
  react, react-dom; dev: @types/react, typescript.
- Files: remotion.config.ts, tsconfig.json (moduleResolution Bundler, jsx react-jsx),
  src/index.ts (registerRoot), src/Root.tsx (<Composition id fps=30 1920x1080>),
  src/<Composition>.tsx. Assets under public/ (staticFile('path') resolves there).
- System fonts (Segoe UI/Georgia) render fine in headless Chrome — no font install.

## Remotion 4 pitfalls (all typecheck/render-verified)
- `<Audio from={n}>` does NOT exist — `from` is Sequence-only. Wrap:
  `<Sequence from={n}><Audio src={...} volume={v}/></Sequence>`.
- `Easing.power2` doesn't exist — use `Easing.out(Easing.cubic)` etc.
- `<Video>` needs `muted` (footage is silent; audio tracks are separate <Audio>s).
- `npx remotion skills add` fails on Windows: `spawn EINVAL` (their CLI spawns bare
  `npx` without shell). Workaround — run the underlying command directly:
  `npx --loglevel=error skills@1.5.20 add remotion-dev/skills --yes`
  (installs 12 official skills into .agents/skills/ + symlinks for Claude Code).
- Crossfades WITHOUT TransitionSeries total-duration math: overlapping <Sequence>s,
  scene opacity = `interpolate(local,[0,15],[0,1]) * interpolate(local,[dur-15,dur],[1,0])`.
  Composition duration = sum(sceneDurF) - (n-1)*15.
- Inside a <Sequence>, useCurrentFrame() returns the LOCAL frame — Ken Burns/count-ups/
  captions all use it.
- Typecheck gate: `npx tsc --noEmit` before render.
- Render: `npx remotion render src/index.ts <CompId> out/x.mp4` (first run auto-
  downloads Chrome Headless Shell ~130MB).

## Pro patterns that carried over from the HyperFrames build
- Word captions: same timing math (cap0=18f, step=(durF-42)/nWords), gold `.active`
  class on current word, chip div bottom-left.
- Count-up: `interpolate(frame,[start,start+54],[0,target],{easing:Easing.out(Easing.cubic)})`
  + `Math.round(v).toLocaleString("en-IN")`.
- Ken Burns: `interpolate(frame,[0,durFrames],[1.06,1.22],{easing:Easing.inOut(Easing.ease)})`
  as scale transform on the media element inside an overflow-hidden AbsoluteFill.
- Music bed: one full-length <Sequence> with volume = interpolate fade in/out
  (0→0.22 over 60f, out over last 84f).
- Avatar scenes (MuseTalk clips): <Video muted> as the scene media, narration track
  plays separately = frame-perfect lip sync by construction.
