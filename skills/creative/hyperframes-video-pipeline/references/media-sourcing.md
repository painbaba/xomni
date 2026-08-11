# Media sourcing for video projects (verified Aug 2026)

## Music: archive.org CC0 is the reliable source

License-filtered advancedsearch (licenseurl is a searchable field):

```
curl -s "https://archive.org/advancedsearch.php?q=%28licenseurl%3A%22http%3A%2F%2Fcreativecommons.org%2Fpublicdomain%2Fzero%2F1.0%2F%22%29+AND+mediatype%3Aaudio+AND+%28title%3A%28documentary+OR+cinematic+OR+ambient%29%29&fl%5B%5D=identifier&fl%5B%5D=title&fl%5B%5D=licenseurl&rows=10&output=json"
```

Then list files + confirm license:

```
curl -s "https://archive.org/metadata/<identifier>" | python -c "import json,sys; d=json.load(sys.stdin); print(d['metadata'].get('licenseurl')); [print(f['name'], f.get('size')) for f in d['files'] if f['name'].lower().endswith(('.mp3','.ogg','.flac','.wav'))]"
```

Direct download (no API key, fast with curl -L):

```
curl -s -L -o out.mp3 "https://archive.org/download/<identifier>/<url-encoded filename>"
```

Verified working (CC0):
- `8hertzAmbientLoopDrone` — 75-min ambient drone (84MB mp3). Perfect underscore; cut 10-min beds with different filters: dark = lowpass 220Hz, tense = band 40-700Hz, calm = lowpass 300Hz. Loopable, deterministic.

## Dead ends (don't waste time again)

- Openverse API (`api.openverse.org/v1/audio/`) — returned empty for CC0 search.
- Pixabay music — JS-rendered, no CDN URLs in raw HTML.
- Bensound direct mp3 (`bensound.com/bensound-music/bensound-<name>.mp3`) — 301 redirect wall.
- Jamendo mirrors on archive.org — mostly CC BY-NC-ND (unusable for monetized YouTube).
- incompetech (Kevin MacLeod) — no collection on archive.org; site now licensing-walled.
- archive.org items can be metadata-only shells (torrent/xml files, no audio) — always list files before downloading.

## SFX synthesis (ffmpeg, deterministic, no licensing)

```bash
# boom — low sine + fades
ffmpeg -y -f lavfi -i "sine=frequency=80:duration=2.5" -af "afade=t=in:st=0:d=0.4,afade=t=out:st=2.0:d=0.5" boom.wav
# whoosh — pink noise, lowpassed, shaped
ffmpeg -y -f lavfi -i "anoisesrc=color=pink:duration=1.8:amplitude=0.5" -af "lowpass=f=900,afade=t=in:st=0:d=0.1,afade=t=out:st=1.2:d=0.6,volume=1.4" whoosh.wav
# riser — sine with volume ramp (eval=frame; value starting with '-' is fine inside the expression string)
ffmpeg -y -f lavfi -i "sine=frequency=220:duration=1.6" -af "volume='0.0001+0.9999*t/1.6':eval=frame,afade=t=out:st=1.3:d=0.3" riser.wav
# tick — 1kHz 80ms click
ffmpeg -y -f lavfi -i "sine=frequency=1000:duration=0.08" -af "volume=0.6" tick.wav
```

Measured durations: boom 2.5s, whoosh 1.8s, riser 1.6s, tick 0.08s. Use these in composition `data-duration` fields.
