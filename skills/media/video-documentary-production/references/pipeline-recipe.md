# Documentary pipeline recipe (proven Aug 2026)

End-to-end recipe for a 30-40 min faceless documentary. Reference project:
`C:\Users\HP\videos\mundhe-documentary` (Mundhe/India FDA raids) and
`C:\Users\HP\videos\kimi-k3-capabilities` (48s teaser).

## 0. Research (before writing a word)

Dispatch 3 parallel leaf subagents: (a) subject bio/career, (b) the specific events/2026
crackdown, (c) systemic context. Each must return: facts with outlet + date + URL,
`UNVERIFIED` tags, allegations-vs-established split. Save the full notes to disk
(e.g. `<subject>-research.md`) — subagents hitting the 50-iteration cap lose their summary;
on-disk notes survive. Google News RSS (`https://news.google.com/rss/search?q=...&hl=en-IN&gl=IN&ceid=IN:en`)
is the most reliable search source; DDG/Bing HTML get blocked.

## 1. Scaffold

```bash
npx hyperframes init "videos/<project>" --non-interactive --example=blank --skill=general-video
```

## 2. Narration (edge-tts)

Script: `scripts/tts_batch.py` in this skill. Manifest shape:

```json
[{"id": "a1s1", "text": "Act One. The raid that shook Mumbai..."}]
```

```bash
python scripts/tts_batch.py tools/tts-manifest.json narration
# → narration/<id>.mp3 + narration/durations.json  {"a1s1": 33.12, ...}
```

- Target ~130-140 wpm; default rate (+0%). Measured range across texts: 90-175 wpm.
- 2,900 words ≈ 21 min of voice. For a 30-33 min runtime add ~10s breathing per scene.

## 3. Chapter specs

`chapters/chXX.json` shape (see `scripts/gen_chapter.py` header for full field docs):

```json
{
  "id": "ch01", "title": "ACT ONE", "dur": 300.0, "music": "bed-tense",
  "scenes": [
    {"id":"a1s1","kind":"divider","eyebrow":"Act One","headline":"THE RAID",
     "sub":"...","narration":"a1s1","riser":true},
    {"id":"a1s2","kind":"stat","stat":"1131","statLabel":"inspections in under two months",
     "sub":"...","narration":"a1s2","boom":true,"count":true},
    {"id":"a1s3","kind":"headline","masthead":"As reported · July 2026",
     "headline":"THE ICONS UNDER THE SPOTLIGHT","deck":"...","attr":"...","narration":"a1s3"},
    {"id":"a1s4","kind":"quote","quote":"...","attr":"— The Indian Express","narration":"a1s4"},
    {"id":"a1s5","kind":"timeline","nodes":[{"t":"Jun 2026","label":"..."}],"narration":"a1s5"},
    {"id":"a1s6","kind":"list","items":["...","..."],"narration":"a1s6"},
    {"id":"a1s7","kind":"endcard","headline":"...","credits":"..."}
  ]
}
```

Keep narration text in a separate `narration.py` dict keyed by scene id and inject into the
specs (so structure and script stay reviewable). Scene `dur` is auto-computed from
narration + 10s (min 40) by the generator — hardcoded `dur` is only a fallback.

## 4. Audio assets

Music (CC0):
```bash
curl "https://archive.org/advancedsearch.php?q=%28licenseurl%3A%22http%3A%2F%2Fcreativecommons.org%2Fpublicdomain%2Fzero%2F1.0%2F%22%29+AND+mediatype%3Aaudio+AND+title%3A%28documentary+OR+cinematic+OR+ambient%29&fl%5B%5D=identifier&fl%5B%5D=title&rows=10&output=json"
# download: https://archive.org/download/<identifier>/<url-encoded filename>
```

Drone beds (from one long CC0 drone):
```bash
ffmpeg -y -v error -ss 300 -t 600 -i drone.mp3 -af "lowpass=f=220,volume=0.9" assets/beds/bed-dark.wav
ffmpeg -y -v error -ss 120 -t 600 -i drone.mp3 -af "highpass=f=40,lowpass=f=700,volume=0.8" assets/beds/bed-tense.wav
ffmpeg -y -v error -ss 2400 -t 600 -i drone.mp3 -af "lowpass=f=300,volume=0.7" assets/beds/bed-calm.wav
```

Synthesized SFX (deterministic, no licensing):
```bash
# boom (2.5s): low sine with fades
ffmpeg -y -v error -f lavfi -i "sine=frequency=80:duration=2.5" -af "afade=t=in:st=0:d=0.4,afade=t=out:st=2.0:d=0.5" boom.wav
# whoosh (1.8s): pink noise, lowpassed, swell
ffmpeg -y -v error -f lavfi -i "anoisesrc=color=pink:duration=1.8:amplitude=0.5" -af "lowpass=f=900,afade=t=in:st=0:d=0.1,afade=t=out:st=1.2:d=0.6,volume=1.4" whoosh.wav
# riser (1.6s): rising sine volume
ffmpeg -y -v error -f lavfi -i "sine=frequency=220:duration=1.6" -af "volume='0.0001+0.9999*t/1.6':eval=frame,afade=t=out:st=1.3:d=0.3" riser.wav
# tick (0.08s)
ffmpeg -y -v error -f lavfi -i "sine=frequency=1000:duration=0.08" -af "volume=0.6" tick.wav
```

## 5. Generate + check

```bash
for n in 01 02 03 04 05 06 07 08; do python tools/gen_chapter.py chapters/ch$n.json compositions/ch$n.html narration; done
npm run check        # or npx hyperframes check — project-scoped, scans compositions/ too
```

Known lint noise: `duplicate_audio_track` cross-file false positives (independent chapters
each start at t=0) and `timeline_track_too_dense` — both ignorable; gate on 0 errors.

## 6. Render + concat

2 parallel renders, 3 workers each (memory-safe on 16GB):
```bash
npx hyperframes render -c compositions/ch01.html --quality high -w 3 --output renders/ch01.mp4 &
npx hyperframes render -c compositions/ch02.html --quality high -w 3 --output renders/ch02.mp4 &
wait
# ... repeat pairs ...
ffmpeg -y -v error -f concat -safe 0 -i renders/concat.txt -c copy renders/documentary-full.mp4
# concat.txt: file 'renders/ch01.mp4' ... (one per chapter, quoted)
```

Timing: ~3.8s wall per video-second at 1080p high. 33 min doc ≈ 60-90 min total with
2-parallel. Draft quality is ~5× faster for iteration.

## 7. Verification probes

```bash
ffprobe -v error -show_entries stream=codec_type,codec_name -of csv=p=0 out.mp4   # expect h264,video / aac,audio
ffmpeg -i out.mp4 -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"  # mean ≈ -19..-25 dB
# speech-band proof (narration over bed):
ffmpeg -y -v error -ss 3 -t 2 -i out.mp4 -af "highpass=f=4000" -ac 1 -ar 16000 w.wav
python - <<'EOF'   # compare RMS vs a music-only window; narration window should be >> (≈17× in test)
import wave, struct
w = wave.open('w.wav','rb'); n = w.getnframes(); s = struct.unpack('<%dh'%n, w.readframes(n))
print((sum(x*x for x in s)/n)**0.5)
EOF
```

## 8. De-risk order (do this before the big build)

1. 12s composition with narration + music + SFX overlapping → draft render → confirm AAC
   stream + speech band. This proves HyperFrames mixes audio (it does).
2. One 2-scene chapter through the whole generator → check → draft render.
3. Only then build all chapters. Audio path bugs surface in minutes, not after an hour of render.
