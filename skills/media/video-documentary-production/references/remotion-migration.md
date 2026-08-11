# Remotion migration — concrete recipe (measured 2026-08-10, videos/upi-remotion)

Why: research verdict (26-agent swarm) — Remotion is the better agent-driven render core
(deterministic frames, parallel render, captions SDK, official Agent Skills) once you can
pay the React/TS re-authoring cost. HyperFrames keeps the edge for GSAP-heavy motion.
Working reference implementation: `C:\Users\HP\videos\upi-remotion` (8-scene UPI trailer,
crossfades, Ken Burns, word captions, full audio mix).

## Project scaffold
- package.json deps: `remotion`, `@remotion/cli`, `@remotion/captions`, `@remotion/transitions`
  (all same version), `react`, `react-dom`, dev: `typescript`, `@types/react`.
- **NEVER guess versions** — `npm view remotion version` (was 4.0.507). Guessed 4.0.0 →
  `ETARGET No matching version found for @remotion/captions@4.0.0`; guessed typescript 5.6.0
  → ETARGET too. Check npm view for every package before install.
- Files: `src/index.ts` (registerRoot), `src/Root.tsx` (<Composition id fps width height
  durationInFrames>), `src/<Name>.tsx` (the composition), `remotion.config.ts`
  (Config.setConcurrency / setOverwriteOutput), `tsconfig.json` (jsx react-jsx,
  moduleResolution Bundler, noEmit).
- Assets: everything under `public/` — referenced via `staticFile('footage/x.mp4')`.
  Layout used: public/{narration,audio,sfx,footage}.

## Pitfalls (all hit + fixed)
- **`<Audio>` has NO `from` prop** (TS2322). Delay audio by wrapping in
  `<Sequence from={n}><Audio src={...} volume={...}/></Sequence>`. `startAt` TRIMS the source
  start — wrong for scheduling (startAt={k*0.3} on a 0.08s tick = silence).
- **`Easing.power2` does not exist** in Remotion — use `Easing.out(Easing.cubic)` etc.
- **`remotion skills add` → spawn EINVAL on Windows**: the CLI spawns bare `npx` (no .cmd,
  no shell). Workaround — run the underlying command directly:
  `npx --loglevel=error skills@1.5.20 add remotion-dev/skills --yes`
  Installs 12 official Remotion Agent Skills into `<project>/.agents/skills/` (the
  research-recommended replacement for the DEPRECATED Remotion MCP).
- **useCurrentFrame() inside a <Sequence> returns the LOCAL frame** (sequence-relative) —
  everything (Ken Burns, captions, count-ups) just works with local timing.
- **TransitionSeries total-duration math is ambiguous** (sequence durations minus transition
  durations — easy to overflow the Composition). Simpler deterministic crossfades: let
  scenes be OVERLAPPING <Sequence from={startF[i]}> where startF[i] = cumulative - i*15f,
  Composition total = sum(sceneDur) - (n-1)*15; each scene fades in over first 15f and out
  over last 15f via `opacity = interp([0,15],[0,1]) * interp([d-15,d],[1,0])`. Media+text
  inside the sequence clip to their own window. Clean, no framework math.
- First render downloads Chrome Headless Shell (~130MB) automatically.
- Windows subprocess note: native python3 subprocess can't exec `npx` (needs `npx.cmd`);
  same class of bug as the skills-add spawn issue.

## Composition patterns that carried over from the HyperFrames cut
- Media bg: <Video muted> or <Img> with objectFit cover, Ken Burns scale
  `interpolate(frame, [0, durF], [1.06, 1.22], {easing: Easing.inOut(Easing.ease)})`,
  scrim gradient div on top, then text.
- Count-up: `interpolate(frame, [start, start+54], [0, target], {clamp, Easing.out(cubic)})`
  → `Math.round(v).toLocaleString('en-IN')`.
- Word captions: split text, per-word opacity + gold `.active` color by frame window —
  no Whisper needed (script IS the transcript).
- Audio: narration <Sequence from={12}>, boom from={21}, riser from={0}, 6 ticks
  from={28+k*9}; music bed full-length with volume interpolate fade in/out.
- Verify: `npx tsc --noEmit` (0 errors) then render; render failing = bundle or asset issue.

## Static host-card avatar (AvatarPop — the APPROVED avatar look, 2026-08-10)
User rejected the MuseTalk talking-head output ("its fucked up"); the approved look is a
STATIC synthetic-portrait card that pops up at narration moments (u1 hook + u8 endcard),
bottom-right, clear of the centered caption bar. Pattern (works in any scene):

```tsx
const AvatarPop: React.FC<{ durFrames: number }> = ({ durFrames }) => {
  const frame = useCurrentFrame();
  const IN = 10, OUT = 22; // frames
  const slide = interpolate(frame, [0, IN], [160, 0], { extrapolateLeft: "clamp",
    extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const scale = interpolate(frame, [0, IN], [0.82, 1], { extrapolateLeft: "clamp",
    extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
  const opacity = interpolate(frame, [0, IN, durFrames - OUT, durFrames], [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "absolute", right: 84, bottom: 128, display: "flex",
      alignItems: "center", gap: 18, opacity,
      transform: `translateX(${slide}px) scale(${scale})`, fontFamily: "'Segoe UI', sans-serif" }}>
      <img src={staticFile("avatar/presenter.jpg")} style={{ width: 148, height: 148,
        borderRadius: "50%", objectFit: "cover", border: "3px solid rgba(217,164,65,0.92)",
        boxShadow: "0 10px 34px rgba(0,0,0,0.5)" }} alt="" />
      <div style={{ background: "rgba(13,17,24,0.82)", borderLeft: "4px solid #d9a441",
        borderRadius: 8, padding: "14px 22px" }}>
        <div style={{ fontSize: 21, letterSpacing: "0.22em", color: "#d9a441", fontWeight: 700 }}>THE NARRATOR</div>
        <div style={{ fontSize: 16, color: "#dfe5ef", marginTop: 5 }}>UPI — The Quiet Revolution</div>
      </div>
    </div>
  );
};
// render inside the scene's AbsoluteFill: {s.popAvatar ? <AvatarPop durFrames={d} /> : null}
```
Scene data carries `popAvatar?: boolean`; the media layer stays full-frame (the card
overlays it). Portrait asset: AI-generated synthetic face (never a real person) — see
`references/musetalk-local-avatar.md` for the face-generation + validation rules.

## Render reliability on this laptop (measured 2026-08-10 — cost two failed runs)
- **ALWAYS render in background** (`terminal(background=true, notify_on_complete=true)`,
  output to a log file: `npx remotion render ... > /tmp/r.log 2>&1; echo EXIT:$? >> /tmp/r.log`).
  A foreground `terminal()` with a 580s timeout KILLS the render mid-run and Remotion
  writes the mp4 only at the end — no partial file, total loss (hit twice).
- **Real speed on the RTX 3050 Laptop 4GB with 1080p footage ≈ 1 fps** (825 frames in
  ~14 min, 1529-frame trailer ≈ 25 min). Remotion's own "time remaining" estimate is
  wildly optimistic (showed 5m at frame 5, drifted to 21m) — never trust it for
  scheduling; assume ~1 frame/sec with video scenes and multi-hundred-MB public dir.
- **Transient crashes are transient — RETRY before debugging.** Two distinct failures
  that both resolved on re-run: (a) `commitPassiveMountOnFiber` stack trace right after
  "Copying public dir" — happens when footage files are still being written while the
  render snapshots `public/`; wait for the copy to finish, then render. (b)
  `Timeout.<anonymous>` in `@remotion/renderer/dist/set-props-and-env.js` — a slow-frame
  timeout under 4x concurrency; re-run (the successful run passed frame 825 without it).
  Only chase these as composition bugs if a clean re-run fails at the same frame.
- "Copying public dir 215 MB" — keep `public/` lean (transcode/trim footage first);
  each render re-copies it.
- Concurrency: keep `Config.setConcurrency(4)`; higher concurrency on this machine
  increases slow-frame timeout risk without much speedup.
