# WebP + AV1 coverage fuzzers (AOSP, Windows/zig) — validated 2026-08-08

Built AFTER the PNG/GIF fuzzers (see coverage-fuzzing.md). Rationale from the reach
assessment: giflib finding is deterministic but legacy-reach (Android.bp
sdk_version:"9"); the modern zero-click auto-decode surfaces are WebP and AV1
(messaging, Chrome, Gboard, MediaCodec). Both are less-hardened than the OSS-Fuzz
big-four (expat/libyuv/jpeg/vpx).

## AOSP repo names CHANGED — probe before cloning
`platform/external/libwebp` and `platform/external/libaom` are GONE (404).
Current names: `platform/external/webp`, `platform/external/libaom`.
libheif and libavif do NOT exist in platform/external (modern Android HEIC/AVIF
decode lives in frameworks/av MediaCodec + Skia, not a standalone external lib).
Always probe first:
```
for repo in "platform/external/webp" "platform/external/libaom" \
            "platform/external/libheif" "platform/external/libavif"; do
  timeout 20 git ls-remote "https://android.googlesource.com/$repo" HEAD >/dev/null 2>&1 \
    && echo "FOUND: $repo" || echo "no: $repo"
done
```
(git ls-remote HEAD probe works even when curl to googlesource is blocked.)

## WebP fuzzer — clean build first try (after one char-narrowing fix)
Sources: ONLY `src/dec/*.c src/dsp/*.c src/utils/*.c` (no enc/mux/demux needed for decode).
Include: `-I libwebp` (headers under src/webp/).
Decode entry: the PUBLIC API `WebPDecode(data, size, &config)` after
`WebPInitDecoderConfig` — this is what Android apps actually call, not internal
symbols. Free output with `WebPFreeDecBuffer` only on OK/OOM statuses
(VP8_STATUS_SUSPENDED/USER_ABORT = harness abort per official fuzzer).
```
zig c++ -O1 -g -fsanitize=undefined -fsanitize-coverage=trace-pc -I libwebp \
  fuzz_webp_driver.cpp libwebp/src/dec/*.c libwebp/src/dsp/*.c libwebp/src/utils/*.c \
  -o fuzz_webp_cov.exe
```
Seeds: `libwebp/fuzz_seed_corpus/*.webp` — 136 REAL images (lossy + lossless +
alpha variants), far better than generated ones.
PERFORMANCE: ~90 iters/s (vs PNG ~25/s) — WebP decode is lighter; 5M budget ≈ 90 min.
Measured: 133 seeds → corpus 176 in 3K iters, 97 new edges, 0 crashes.

## AV1 (libaom) fuzzer — the 7-iteration arch-filtering saga
DO NOT compile the full Android.bp source list naively: it covers ALL arches and
fails on x86_64 with ARM/PPC/RISCV errors (arm_neon.h, altivec.h, sys/auxv.h).
Filter the Android.bp srcs list to x86/generic ONLY:
```
SRCS=$(cd libaom && grep -oE '"[a-z_0-9/]+\.c"' Android.bp | tr -d '"' \
  | grep -vE "/arm/|/arm64/|/riscv/|_neon\.c|cdef_block_ssse3|highbd_|/ppc/|/powerpc/|altivec|_vsx\.c|/mips/|riscv_cpudetect|aarch32_cpudetect|arm_cpudetect|cpudetect" \
  | sed 's|^|libaom/|' | tr '\n' ' ')
```
Each exclusion was a real build error:
- arm/arm64/riscv + _neon.c → arm_neon.h "intended only for ARM"
- /ppc/ /powerpc/ altivec _vsx.c → altivec.h "AltiVec support not enabled"
- cdef_block_ssse3.c → "included for compatibility with 32-bit x86 only"
- highbd_* → high-bitdepth variants (CONFIG_AV1_HIGHBITDEPTH off)
- *cpudetect.c (riscv/aarch32/arm) → sys/auxv.h missing on Windows
Include dirs (the config layout is confusing):
```
-I libaom -I libaom/config -I libaom/config/x86_64 -I libaom/config/x86_64/config
```
`-I libaom/config` is what resolves `#include "config/aom_version.h"`
(aom_version.h lives at libaom/config/config/aom_version.h; `config/` prefix needs
the PARENT of config/, i.e. libaom/config — `-I libaom/config/config` does NOT work).
Defines: `-D'CONFIG_RUNTIME_CPU_DETECT=0'` (no arch cpudetect on Windows),
`-D'FORCE_HIGHBITDEPTH_DECODING=0' -D'CONFIG_AV1_DECODER=1' -D'CONFIG_AV1_ENCODER=0'`.
Harness: replicate the OFFICIAL `libaom/examples/av1_dec_fuzzer.cc` decode loop
(aom_codec_av1_dx → dec_init → IVF-header strip → per-frame mem_get_le32 size +
aom_codec_decode + drain get_frame). IVF header is 32 bytes, frame header 12.
Build takes ~3-4 min (300+ files) — run in background with notify_on_complete.
Seeds: ffmpeg-generated real AV1 IVF:
```
ffmpeg -f lavfi -i "testsrc2=size=176x144:rate=10:duration=2" \
  -c:v libaom-av1 -cpu-used 8 -row-mt 1 -g 10 -f ivf av1_176x144.ivf
```
Include a TINY seed (smptebars 128x96, ~1KB) — better mutation base than
large files. Watch MAX_INPUT (131072 fine for these).

## Driver refinements from this session
- SAVE corpus inputs during the INITIAL coverage pass too (before the mutation
  loop): the crash can happen on seed i of the initial pass, before the loop's
  save-every-iteration ever runs — without this, the crasher file is stale.
- Completing the heap-state trigger-map (libavc uev OOB): crash needs FUZZER
  CONTEXT, not repetition. Verified: same input 5000x in one process = CLEAN;
  mixed 3 static inputs 5000x = CLEAN; fuzzer-corpus (mutated inputs growing the
  corpus) = crashes every relaunch. So a heap-state-dependent bug is NOT
  reproducible by looping a static input — only by input DIVERSITY + heap churn.
  Document this before claiming "deterministic".
- Guard-page single-shot test (Windows): VirtualAlloc 2 pages, PAGE_GUARD on the
  second, input at the END of page 1 — ANY over-read faults deterministically.
  Clean result proves the decoder copies input into a padded internal buffer
  (libavc: 256KB zeroed dynamic bitstream buffer) and the over-read stays in-bounds
  single-shot. This is the single strongest severity-discriminator.

## Status at session end (2026-08-08, CORRECTED)
- fuzz_webp_cov.exe: long campaign ran clean to 244K+ iters, corpus 189, 118 new
  edges, 0 crashes — WebP is OSS-Fuzz-hardened; steady edge discovery is the
  signal to keep it running, not a crash. Log: fuzz_webp_log.txt.
- fuzz_aom_cov.exe: the Android.bp-filtered build (aom_build7.log and later)
  NEVER fully linked — the x86_64 config's `*_rtcd.h` headers hardwire
  `#define foo foo_sse2|ssse3|avx2` dispatch aliases referencing symbols ABSENT
  from the checked-in .c files (the rtcd_defs.pl generator produces them at
  build time). `-DCONFIG_RUNTIME_CPU_DETECT=0` is overridden by the header's
  unconditional re-define; sed-stripping the aliases breaks highbd declarations
  (undeclared aom_highbd_lpf_vertical_6_dual). The AOSP tree is a generator maze
  for manual builds — DON'T fight it, use UPSTREAM (below).

## AV1 via UPSTREAM cmake — THE working path (pip cmake+ninja)
- Clone upstream: `git clone --depth 1 --branch v3.11.0 https://aomedia.googlesource.com/aom aom_upstream`
- Host has no cmake/ninja: `pip install cmake ninja` (cmake 4.x + ninja land in
  Python Scripts dir; verify `cmake --version` / `ninja --version`).
- zig as cmake compiler on Windows: cmake CANNOT execute .sh wrappers — make
  `.bat` wrappers and pass their Windows paths:
  - zig_cc.bat → `"C:\...\zig.exe" cc %*`
  - zig_cxx.bat → `"C:\...\zig.exe" c++ %*`
- Configure (decoder-only, NO assembler needed — verified configuring OK):
  ```
  cmake -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo -DAOM_TARGET_CPU=generic \
    -DCONFIG_AV1_ENCODER=0 -DCONFIG_AV1_DECODER=1 -DCONFIG_RUNTIME_CPU_DETECT=0 \
    -DENABLE_TESTS=0 -DENABLE_TOOLS=0 -DENABLE_EXAMPLES=0 -DENABLE_DOCS=0 \
    -DCMAKE_C_COMPILER="...\zig_cc.bat" -DCMAKE_CXX_COMPILER="...\zig_cxx.bat" ..
  ```
  `-DAOM_TARGET_CPU=generic` is what skips the yasm/nasm FATAL_ERROR.
- `ninja aom`: all decoder objects COMPILE. Dies at the FINAL archive step
  (libaom_version.a): `'CMAKE_AR-NOTFOUND' is not recognized` because bare
  zig.exe rejects ar flags ("unknown command: -o").
- COMPLETED 2026-08-08 (the full working sequence):
  1. Create zig_ar.bat (`zig.exe ar %*`) AND zig_ranlib.bat (`zig.exe ranlib %*`)
     — RANLIB must be `zig ranlib`, NOT zig_cc.bat: zig cc on an .a tries to
     LINK it as an exe → `lld-link: error: undefined symbol: WinMain`.
  2. CMAKE_AR/RANLIB MUST be passed at FIRST configure. Adding them later via
     `cmake -DCMAKE_AR=...` leaves `CMAKE_AR-NOTFOUND` baked into build.ninja
     (ninja doesn't re-read the cache) — must `rm -rf build_gen` (sleep 3 first;
     "Device or resource busy" = dir lock from the dead build) and reconfigure
     fresh with AR+RANLIB in the initial command.
  3. `ninja aom` → libaom.a 5.5MB (exit 0). Then:
     `zig c++ -O1 -g -fsanitize=undefined -fsanitize-coverage=trace-pc \
       -I aom_upstream -I aom_upstream/build_gen fuzz_aom_driver.cpp \
       aom_upstream/build_gen/libaom.a -o fuzz_aom_cov.exe` → links clean, 2MB.
  4. Smoke: 4 IVF seeds, 2000 iters clean, corpus 4→6. AV1 decode ~10x heavier
     than WebP (~25/s) — budget long runs.
- IVF-AWARE MUTATION (KEY: generic mutation stalls AV1): blind bit-flips/splices
  corrupt the 32-byte IVF file header + 12-byte frame headers → decode fails at
  parse → coverage stalls at ~4 new edges / 3000 iters. FIX: ≥50% of mutations
  keep bytes 0..43 intact and flip only OBU payload bytes after offset 44.
  Format-aware mutation is the general lesson for container formats: preserve
  the container envelope, mutate the payload region.
- Fuzzer housekeeping: a killed fuzzer leaves its .exe locked → rebuild fails
  "Permission denied" — kill by name via
  `powershell -Command "Get-Process fuzz_* -ErrorAction SilentlyContinue | Stop-Process -Force"`
  before rebuilding.
- fuzz_aom_driver.cpp is ready (IVF loop per the official av1_dec_fuzzer.cc);
  seeds in seeds_av1/ (4 real ffmpeg AV1 IVFs incl. a ~1KB bars file).

## AV1 OUTCOME (session end, 2026-08-08) — THREAD STALLED, deprioritized
Built + launched + killed as a slow-burn dead-end:
- Long runs stalled at 2 new edges / 72-74K iters despite 12 diverse IVF seeds
  (tiles, long-GOP, 64x64→640x360) + IVF-aware mutation. AV1's OBU parse is
  strict — mutations rarely survive to deep decode; the decoder is heavy
  (~25/s) so coverage crawls.
- VERDICT: libaom (upstream fuzzed by OSS-Fuzz) is a low-yield target on this
  box. The libhevc (H.265) fuzzer — same codec family, FAR less hardened —
  produces 854 edges/3K iters vs libaom's 2 edges/3K iters. When choosing
  between Ittiam vs AOMedia codecs for discovery, Ittiam (libavc H.264,
  libhevc H.265) wins decisively — see coverage-fuzzing-libhevc.md.
- Keep fuzz_aom_cov.exe + seeds for reference; don't re-invest runtime unless
  the user explicitly wants AV1 depth.
