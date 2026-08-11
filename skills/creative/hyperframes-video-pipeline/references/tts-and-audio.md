# TTS narration pipeline (edge-tts) and audio-mix verification

## edge-tts (free Microsoft neural voices, offline-friendly)

CLI: `python -m edge_tts --voice <name> --rate=+0% --text "..." --write-media out.mp3`

Documentary narrator pick: **en-US-ChristopherNeural** (male, "Reliable, Authority" — classic doc voice). Alternatives: en-US-AriaNeural (female news), en-US-GuyNeural (energetic).

### Two hard-won quirks
1. **`--rate -12%` breaks argparse** (value starts with `-` is eaten as a flag → "expected one argument"). Always use the `=` form: `--rate=-12%` / `--pitch=-2Hz`.
2. **Subprocess interpreter drift**: inside a script, `subprocess.run(["python", ...])` can resolve to a DIFFERENT python than the one running the script (uv-managed vs PATH) → `ModuleNotFoundError: edge_tts`. Always use `subprocess.run([sys.executable, "-m", "edge_tts", ...])`.

### Calibration (measured)
- Default rate (+0%): ~116-158 wpm depending on text (short sentences/punctuation read slower).
- `--rate=-12%`: ~100-106 wpm (too slow for documentary).
- Rule: never size scenes from word count — generate audio, ffprobe actual duration, then scene_dur = narration_dur + ~6-8s breathing room. The 45s scene ≈ 120 words at default rate.

## Batch pattern

`templates/tts_batch.py` — takes `[{"id","text","rate?","voice?"}]`, writes `outdir/<id>.mp3` + `outdir/durations.json {id: seconds}`. Use durations.json as the single source of truth for scene timing (the chapter generator reads it).

## Audio mixing into HyperFrames renders — verification recipe

HyperFrames mixes all `<audio>` elements in a composition into the rendered MP4 (narration + music + SFX at different volumes). Verify empirically after a test render:

```bash
# speech band present in narration window?
ffmpeg -y -ss 3 -t 2 -i out.mp4 -af "highpass=f=4000" -ac 1 -ar 16000 win-nar.wav
ffmpeg -y -ss 0.2 -t 0.5 -i out.mp4 -af "highpass=f=4000" -ac 1 -ar 16000 win-music.wav
# compare peak/RMS with python wave; narration window should be ~10-20x the music-only window
```

Volume levels that worked: narration data-volume 1.0, music bed 0.22, whoosh 0.55, riser 0.7, boom 0.85. Ducking: tween `volume` on the timeline (`tl.fromTo("#music", {volume: 0}, {volume: 0.22, duration: 2}, 0.2)`) — volume tweens are applied identically in preview and render.

## First-wave smoke test (de-risk before the full build)

Before generating 40+ scenes: build ONE 2-scene test chapter through the whole pipeline (spec → TTS → generate → check → draft render → audio verify). It catches path-resolution, track-collision, and mixing bugs in ~5 minutes instead of after hours of full production.
