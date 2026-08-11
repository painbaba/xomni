# AOSP libjpeg-turbo decoder — ASAN+libFuzzer session (worked example)

Campaign: fuzz the JPEG decoder that Android's BitmapFactory/ImageDecoder runs on every
incoming image. Source = AOSP jpeg tree (old IJG-based, ~jpeg 8 + tile-decode mods), not
modern libjpeg-turbo. Host Windows → Kali VM (painbaba@192.168.29.35, 8 cores, 9GB) via
paramiko helper scripts (ssh_kali.py / sftp_kali.py, host fallback list, password auth).

## Layout discovery

- AOSP jpeg tree has EVERYTHING at the root: `jd*.c jc*.c jmem*.c jerror.c jutils.c` +
  `jconfig.h jmorecfg.h jpeglib.h jerror.h jdct.h jmemsys.h jinclude.h`. No `config/linux`
  subdir needed — the root `jconfig.h` IS the android/generic config (`HAVE_PROTOTYPES`,
  `HAVE_UNSIGNED_CHAR`, `HAVE_STDDEF_H`, `HAVE_STDLIB_H` — right for Linux/clang).
- `Android.mk` shows the build shape: `jmemmgr.c jmemnobs.c` (no-backing-store mem mgr —
  correct for a fuzzer), `-DAVOID_TABLES`, `-DANDROID_TILE_BASED_DECODE` (this define gates
  the C++-incompatible code in jdphuff.c).
- Tar EVERYTHING except `.git` (`tar czf jpeg_src.tgz --exclude=.git -C jpeg .` → 159 files,
  695KB). The compile-time file list controls what actually gets built; don't try to prune
  the tarball.

## Decode-only source list (28 files)

    jdapimin.c jdapistd.c jdatasrc.c jdcoefct.c jdcolor.c jddctmgr.c jdhuff.c jdinput.c
    jdmainct.c jdmarker.c jdmaster.c jdmerge.c jdphuff.c jdpostct.c jdsample.c jdtrans.c
    jerror.c jutils.c jmemmgr.c jmemnobs.c jcomapi.c jcapimin.c jcmarker.c
    jidctflt.c jidctfst.c jidctint.c jidctred.c jquant1.c jquant2.c

- jidct*.c (IDCT routines) and jquant*.c (1/2-pass quantizers) are pulled in by
  jddctmgr/jdmaster — the "obvious" decode list without them fails to link.
- jcmarker.c added only because the task-mandated jcapimin.c references `jinit_marker_writer`.
- Do NOT glob `jpeg/*.c` — cjpeg.c/djpeg.c/example.c bring `main()`.

## Build iterations (each failure → fix)

1. `clang++ -O1 -g -fsanitize=address,fuzzer -fno-omit-frame-pointer -I jpeg fuzz_jpeg_entry.cpp jpeg/*.c`
   → `ISO C++17 does not allow 'register'` ×20 (jquant2.c etc.). Fix: `-std=gnu++14`.
2. Still `BUILD_EXIT=1` with only warnings visible → the script's own `| tail -50` was hiding
   errors. Capture full output: `clang++ ... > build_jpeg.log 2>&1`. Real errors:
   - `jpeglib.h:974: unknown type name 'FILE'` → add `#include <stdio.h>` to the harness.
   - `jdphuff.c:724: assigning to 'huffman_scan_header *' from incompatible type 'void *'`
     → AOSP tile-decode code does `index->scan = realloc(...)` (C++ needs a cast).
     Fix: `sed -i 's/index->scan = realloc(/index->scan = (huffman_scan_header*) realloc(/' jpeg/jdphuff.c`
   - **Pitfall**: re-running the build script re-extracted the tarball and clobbered the sed.
     Make extraction conditional: `if [ ! -f jpeg/jpeglib.h ]; then tar xzf ...; sed ...; fi`.
3. Link: `undefined reference to jinit_marker_writer` (from jcapimin.c) → add jcmarker.c.
4. BUILD OK — binary ~3.3MB, 29 harmless `register`-deprecated warnings.

## Harness (see templates/fuzz_jpeg_entry.cpp)

- This old jpeglib.h has NO `jpeg_mem_src` → custom `jpeg_source_mgr` reading the fuzzer
  buffer, with the classic `static JOCTET eoi[2] = {0xFF,0xD9}` EOF fallback.
- `jerr.error_exit = longjmp` handler; setjmp wraps create→header→start→scanlines→finish.
- Dimension cap: see "Two run-killers" below.

## Seeds

- 4 AOSP test JPEGs (testimg/testimgp/testorig/testprog.jpg) transferred from Windows.
- +5 ffmpeg: `ffmpeg -loglevel error -f lavfi -i testsrc2=size=WxH -frames:v 1 sWxH.jpg`
  for 1920x1080, 640x480, 256x256, 64x64, plus `-pix_fmt gray` 320x240 (grayscale path).

## Two run-killers (both diagnosed from the log, both harness-side)

1. **Fake crash ~150s in**: `ERROR: AddressSanitizer: global-buffer-overflow` READ of size 1
   in `next_marker()` (jdmarker.c), stack `jpeg_finish_decompress → consume_markers →
   read_markers → next_marker`. Shadow `f9` = global redzone; the read was at eoi[2]+1 —
   my static EOI array. Root cause: single-fill `skip_input_data` underflowed
   `bytes_in_buffer` and walked `next_input_byte` past the 2-byte fallback. NOT a jpeg bug.
   Deterministic repro: `./fuzz_jpeg_asan <artifact>` (reproduced; fixed version exits clean).
   Fix = standard IJG loop. Artifact kept as proof: `jpeg_crash_harnessbug.bin` (7.7KB).
2. **Campaign died at 21 min**: process gone, `SUMMARY: libFuzzer: timeout` in log, a
   `jpeg_timeout-*` artifact. A mutated SOF header claimed ~65535×65535 → decoder grinds
   ~119M MCU blocks (each with error recovery + "Corrupt JPEG data" spam) → >10s → libFuzzer
   treats per-input timeout as fatal and ABORTS. My scale_denom=8 cap was useless — it only
   shrinks the output sarray, not the full-res decode work. Fix: hard-reject
   `image_width|height > 4096` before start_decompress (return 0). Coverage impact ~nil;
   exec/s roughly doubled (24 → 52-86).

## Launch + poll

    cd ~/fuzz && nohup timeout 3600 ./fuzz_jpeg_asan jpeg_seeds/ \
      -max_len=300000 -timeout=10 -rss_limit_mb=3000 -artifact_prefix=jpeg_ > fuzz_jpeg.log 2>&1 &

Poll: `ps aux | grep -v grep | grep fuzz_jpeg_asan` (CPU/RSS), `grep -E '^#[0-9]+' fuzz_jpeg.log | tail -1`
(exec/s, cov, ft, corp, rss), `grep -c 'ERROR: AddressSanitizer' fuzz_jpeg.log` (0 = clean),
`ls jpeg_crash-* jpeg_timeout-*`. Keep per-poll sleeps ≤ ~150s (terminal-tool timeout cuts
longer sleeps; SSH occasionally hangs — split and retry).

## Final status (run 2, ~13 min in)

`#60314 execs, 86 exec/s, cov: 965, ft: 3764, corp: 714/5.6MB, rss ~400MB, 0 ASAN hits`.
Coverage plateaued ~965 → consistent with OSS-Fuzz-hardened status of jpeg-turbo; reported
honestly as "no genuine findings". Note: 6 concurrent fuzz campaigns on the same VM
(avc/hevc/vpx/yuv/expat) cause CPU contention — exec/s varies, validity unaffected.
