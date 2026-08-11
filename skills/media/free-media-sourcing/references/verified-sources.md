# Verified free media sources (checked live 2026-08; re-verify HEAD before shipping)

All archive.org URLs below returned HTTP 200 on HEAD at verification time. Durations from
archive.org metadata or ffprobe. Re-run `scripts/verify_direct_urls.py` on any URL list
before delivering — CDN items can vanish.

## archive.org — API cheat sheet

- Search: `https://archive.org/advancedsearch.php?q=<Q> AND mediatype:audio&fl[]=identifier&fl[]=title&fl[]=downloads&fl[]=creator&fl[]=licenseurl&sort[]=downloads+desc&rows=25&output=json`
- Metadata (file list + `length` seconds + `licenseurl`): `https://archive.org/metadata/<identifier>`
- Direct file: `https://archive.org/download/<id>/<folder>/<file>` — encode spaces `%20`, `;` `%3B`, `&` `%26`
- Item license lives in metadata `licenseurl`; description may contradict it — quote both.

## SSE Library — CC0 SFX packs (best free SFX find; all items CC0 = https://creativecommons.org/publicdomain/zero/1.0/)

Packs (all `licenseurl: CC0` verified in metadata): SSE_Library_SWOOSHES, EXPLOSIONS, SCIFI,
MACHINES, ALARMS, BELLS, WEAPONS, FIRE, WIND, CARTOON, MAGIC, GUNS, VOICES, AMBIENCE, ANIMALS,
VEHICLES, FOLEY, WEATHER, CROWDS, WATER, BULLETS, CREATURES, ALARMS, MACHINES.

Verified direct files (boom / whoosh / riser / tick for trailer work):

- BOOM — `https://archive.org/download/SSE_Library_EXPLOSIONS/DESIGNED/EXPLDsgn_Bomb%20whine%20and%20explosion_CHS_USC.mp3` (11s, whine→impact)
  - `.../SSE_Library_EXPLOSIONS/REAL/EXPLReal_Atom%20bomb%20explosion_CS_USC.mp3` (60s)
  - `.../SSE_Library_EXPLOSIONS/REAL/EXPLReal_Explosion%3B%20good_CS_USC.mp3` (4s)
- WHOOSH — `https://archive.org/download/SSE_Library_SWOOSHES/WHOOSH/WHSH_Scifi%20swish%20by_CS_USC.mp3` (60s)
  - `.../SSE_Library_SWOOSHES/SWISH/SWSH_Processed%20swishes_CS_USC.mp3` (26s)
  - `https://archive.org/download/SSE_Library_SCIFI/DOOR/SCIDoor_Original%20Star%20Trek%20door%20swish_CS_USC.mp3` (1s)
- RISER — `https://archive.org/download/SSE_Library_SCIFI/MACHINE/SCIMach_Pulsing%20rising%20machine%20sound%20with%20roar%20from_CS_USC.mp3` (54s)
  - `.../SSE_Library_SCIFI/MISC/SCIMisc-FIREBALL_Fireball%20pass%20by%3B%20rise%20%26%20fall%3B%20two%20takes_CS_USC.mp3` (90s)
- TICK — `https://archive.org/download/SSE_Library_MACHINES/AMUSEMENT/MACHAmus_Wheel%20of%20fortune%20spins%20and%20stops%3B%202%20takes_CS_USC.mp3` (45s ratchet ticks)
  - `https://archive.org/download/SSE_Library_ALARMS/CLOCK/ALRMClok_Mechanical%20alarm%20clock%20ringing%3B%20two%20different_CS_USC.mp3` (28s)
  - `https://archive.org/download/SSE_Library_BELLS/MISC/BELLMisc-NAVY_Ship%3Fs%20time%20bells_CS_USC.mp3` (44s)

## Frank Schlimbach — cinematic/trailer music library (archive.org)

- Item: `monster-in-the-closet-main` — "Crime, Trailer, Horror, Cinematic Music Mix", 3,478 files
  (MP3/FLAC/WAV per track). Item page: https://archive.org/details/monster-in-the-closet-main
- License: item `licenseurl` = **CC BY 4.0** BUT description says "Free for personal use!"
  — **flag this contradiction** for commercial use; pair with a zero-caveat alternate.
- Gold: purpose-built **60s trailer cuts** ("Dark Legacy 60 sec", "Epic Glitch 60 sec",
  "Ancient Crime Investigation 60 sec", "Desperate Measures 60 sec", etc.) and **stem
  variants** (No Riser / No Drums / No Strings / Underscore Mix / Ambient Mix) for clean mixing.
- Verified: `https://archive.org/download/monster-in-the-closet-main/Dark%20Legacy%2060%20sec.mp3` (60s)
  - `A%20Metronomic%20Girl.mp3` (70s — metronome tick bed, thematically great for payments/fintech docs)
  - `Wonderous%20World.mp3` (60s hopeful — release-tail splice)
  - `First%20Light%20Of%20Day.mp3` (58s hopeful) · `HopeForTomorrow_Main.mp3` (153s) ·
    `ReflectionsOfHope.mp3` (95s) · `A%20New%20Day%20Rising.mp3` (160s)
  - `Dark%20Legacy%20No%20Riser.mp3` / `Dark%20Legacy%20No%20Drums.mp3` (stem variants, 116s)

## incompetech (Kevin MacLeod) — CC BY 4.0

- Direct pattern: `https://incompetech.com/music/royalty-free/mp3-royaltyfree/<Track%20Name>.mp3`
- License text on site: "Creative Commons: By Attribution 4" → CC BY 4.0. Attribution line:
  `Music: Kevin MacLeod (incompetech.com), CC BY 4.0`.
- JSON index (`/music/royalty-free/JSON/index.json`) returns **404** — measure durations via download+ffprobe.
- Measured durations (2026-08): Rising 2:31 · Impending Boom 2:37 · The Descent 3:12 ·
  Chase 2:13 · Rynos Theme 3:06 · Volatile Reaction 2:45 · Anguish 3:59 · Unseen Horrors 4:11 ·
  Echoes of Time v2 4:45 · Darkest Child 3:59 · Crossing the Chasm 3:17 · Stormfront 5:34 ·
  The Pyre 3:53 · Inspired 4:46
- 404 names (don't reuse): "Achievement", "Ossuary 6 - Rest", "Realness", "Spirit of the Dead"

## Other CC-BY archive items (zero-caveat alternates)

- Hugh Vanet, `Free-Royalty-Free-Music-For-Youtube-Videos` — item license **CC BY 3.0**:
  `https://archive.org/download/Free-Royalty-Free-Music-For-Youtube-Videos/Epic%20Industrial%20Action%20Trailer.mp3` (84s)
- Create Production Music, `CinematicSoundscapes-Cpmcs2011-12` — item license **CC BY 3.0**:
  `https://archive.org/download/CinematicSoundscapes-Cpmcs2011-12/CS16_Fallen_Star_Conor_Tissington.mp3` (77s)
- Serge Quadrado `ActionCinematicMusic` — NO licenseurl on archive (his site says CC-BY 3.0) — skip unless confirmed.

## Kenney (CC0) — game-asset packs

- Zip pattern: extract `href="([^"]+\.zip)"` from `https://kenney.nl/assets/<slug>` →
  `https://kenney.nl/media/pages/assets/<slug>/<hash>/kenney_<slug>.zip` (hash changes per upload).
- Verified: `https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip` (800 KB, CC0 badge on page)
- Pitfall: some asset pages (interface-sounds, ui-audio) are JS shells — no zip in raw HTML; pick another pack.

## Mixkit (free, NOT CC0 — "Mixkit License": free commercial, no attribution, no redistribution)

- Full file: `https://assets.mixkit.co/active_storage/sfx/<id>/<id>.wav`; preview: `<id>-preview.mp3`
- Verified 200 (2026-08): 1279, 1687, 2150, 2180, 2182, 2183, 2198, 2199, 2589, 2599.
- 403 per-ID (drop): 1143, 2152. Download route `/free-sound-effects/download/<id>/` returns an HTML modal, not the file.
- Names live in client-side JSON, not page HTML — present packs by verified IDs, not names.

## Dead sources

- **FreePD.com — CLOSED** (homepage: "FreePD.com - Site Closed", 2026-08). Category pages 404. Do not list.
