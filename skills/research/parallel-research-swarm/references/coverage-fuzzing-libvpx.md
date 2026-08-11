# libvpx (VP9) coverage fuzzer — build state & pitfalls (2026-08-08)

Target: AOSP external/libvpx (VP9/VP8 decode — auto-decoded in YouTube,
Chrome, messaging video; VP9 is the OTHER modern auto-decode surface not yet
fuzzed in this campaign). Driver: `fuzz_vpx_driver.cpp` (IVF-aware, same
coverage-callback + set-based-novelty engine as the other drivers; decode via
`vpx_codec_dec_init(vpx_codec_vp9_dx())` + frame loop with 12B IVF frame
headers).

## Seeds
No bundled test vectors in the repo. Generate with ffmpeg:
```
ffmpeg -y -v error -f lavfi -i "testsrc2=size=176x144:rate=10:duration=2" -c:v libvpx-vp9 -b:v 200k -f ivf vp9_176x144.ivf
```
4 seeds (176x144, 352x288, 640x360, 128x96 bars ~1KB) are in `seeds_vpx/`.
VP9 encode is SLOW — budget seed generation time (~1-2s/frame at small sizes).

## Build pitfalls (verified)
1. **vpx_config.h is NOT at the repo root** — the AOSP tree has per-arch config
   dirs: `config/generic/`, `config/x86/`, `config/x86_64/`, `config/arm/`,
   `config/arm64/`. The file is `config/<arch>/vpx_config.h` (+ vpx_version.h,
   vp8_rtcd.h, vp9_rtcd.h, vpx_dsp_rtcd.h, vpx_scale_rtcd.h — all needed).
   Build with `-I libvpx/config/generic` and ALSO compile
   `libvpx/config/generic/vpx_config.c` (it defines the version symbol).
2. **vp9_mfqe.c must be EXCLUDED** — it's post-processing code that only
   compiles with CONFIG_VP9_POSTPROC, which the generic config has OFF
   (`vp9_filter_by_weight16x16` undeclared, `postproc_state` member missing).
   It's not on the decode path — safe to drop.
3. **vp8/decoder/error_concealment.c must be EXCLUDED** — it references
   `struct VP8D_COMP.overlaps`, a field that only exists with
   CONFIG_ERROR_CONCEALMENT (off in generic config). Drop it; the VP8 decoder
   still links without error concealment.

## Status
Build was IN PROGRESS at session end — the two exclusions above were the
remaining blockers identified; link not yet verified after exclusion. Do NOT
treat as a validated recipe until a clean link + smoke test passes. The
generic-config exclusions mirror the libaom experience (arch-specific source
filtering); expect further exclusion candidates (e.g. x86 SIMD files if the
generic rtcd headers don't reference them — unlike libaom, libvpx generic
rtcd headers are NOT dispatch tables, so plain C builds should link).

## Why VP9 matters (campaign context)
The four Google/Alliance codecs (libwebp, libaom, libjpeg, expat) all ran
CLEAN 55K-913K iters. The Ittiam codecs (libavc, libhevc) were the goldmine.
libvpx sits between: Google-maintained and OSS-Fuzz'd, but VP9 decode is a
bigger surface than VP8 and historically CVE-rich (the LLM audit refuted 2
libvpx candidates earlier — tile_buffers[4] and vp8dx_bool_decoder_fill —
but that was audit, not coverage-fuzz). Expect hardened-but-not-impossible:
the win signal is steady edge discovery + any sanitizer panic, not fast crashes.
