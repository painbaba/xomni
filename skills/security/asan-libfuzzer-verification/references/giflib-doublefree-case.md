# Worked case: AOSP giflib double-free — ASAN verification + 30-min fuzz (2026-08-09)

Full worked example of the umbrella workflow. Context: AOSP external/giflib (5.2-lineage) lacked
the upstream 6.1.3 fix in `DGifDecreaseImageCounter` (no `ImageCount <= 0` guard); a 52-byte
truncated-GIF trigger caused double-free at close on Windows (UCRT). Goal: prove it under real
ASAN on Kali, then fuzz for additional bugs.

## Build config discovery (the critical step)

- `giflib/Android.bp`: `cflags: ["-DHAVE_REALLOCARRAY", ...]`, `srcs: [dgif_lib.c, egif_lib.c, gifalloc.c, gif_err.c, gif_hash.c, quantize.c]` — **vendored `openbsd-reallocarray.c` NOT compiled**.
- `giflib/gif_lib_private.h`: `#ifndef HAVE_REALLOCARRAY` → `#define reallocarray openbsd_reallocarray`.
- Vendored `openbsd-reallocarray.c`: `if (size == 0 || nmemb == 0) return NULL;` — returns NULL **without freeing** → would MASK the bug on Linux builds.
- ⇒ Build with `-DHAVE_REALLOCARRAY`, exclude the vendored file → giflib uses glibc's real reallocarray → realloc(p,0) frees → double-free reproduces. The Windows shim (`reallocarray_shim.c`) was unnecessary on Linux (glibc has reallocarray) and would have caused a duplicate symbol.

## Build commands (Kali, clang 21.1.8)

```bash
clang -O1 -g -fno-omit-frame-pointer -fsanitize=address,fuzzer-no-link \
  -DHAVE_REALLOCARRAY -I giflib -c giflib/dgif_lib.c giflib/gifalloc.c giflib/gif_err.c giflib/gif_hash.c
clang++ -O1 -g -fno-omit-frame-pointer -fsanitize=address,fuzzer -DHAVE_REALLOCARRAY \
  -I giflib fuzz_gif_entry.cpp dgif_lib.o gifalloc.o gif_err.o gif_hash.o -o fuzz_gif_asan
```
Note: first attempt used clang++ for everything → failed on `register` keyword (gifalloc.c),
void*→char* (gif_font.c), const mismatch (egif_lib.c). Split compile/link fixed it. egif_lib/
gif_font/quantize excluded (not on decode path).

## ASAN seed repro — CONFIRMED

```
==11419==ERROR: AddressSanitizer: attempting double-free on 0x7bfedf7e0140 in thread T0:
    #0 free
    #1 GifFreeSavedImages          gifalloc.c:421:2
    #2 DGifCloseFile               dgif_lib.c:698:3
freed by thread T0 here:
    #0 reallocarray                (glibc realloc(p,0): frees + returns NULL)
    #1 DGifDecreaseImageCounter    dgif_lib.c:1160:51
    #2 DGifSlurp                   dgif_lib.c:1247:6
previously allocated by thread T0 here:
    #0 malloc
    #1 DGifGetImageDesc            dgif_lib.c:454:26
    #2 DGifSlurp                   dgif_lib.c:1189:8
SUMMARY: AddressSanitizer: double-free
```

## 30-min fuzz results

- Command: `ASAN_OPTIONS=abort_on_error=1:symbolize=1:detect_leaks=0 nohup ./fuzz_gif_asan -fork=6 -ignore_crashes=1 -ignore_timeouts=1 -artifact_prefix=crash3_ -max_total_time=1800 -max_len=8192 -timeout=10 -use_value_profile=1 corpus3/ > fuzz30.log 2>&1 &`
- 642,866 execs; coverage 121→226 blocks / 504→1,445 features; corpus 12→287.
- 3,100 crashes — 100% `ERROR: AddressSanitizer: attempting` (double-free). 0 overflows, 0
  use-after-poison, 0 timeouts, 0 OOM, 0 deadly signals.
- 3,104 artifacts, all 24–60 bytes, all unique hashes (minimal variants of the same trigger).
  One variant enters DGifDecreaseImageCounter via dgif_lib.c:1199 instead of 1247 (second error path, same bug).
- Verdict: no additional independent bugs in 30 min. The double-free is the dominant reachable bug in this decode path.

## Android reachability (source-verified, no device)

1. bionic `libc/include/malloc.h` (googlesource, refs/heads/main): reallocarray documented as
   `realloc(__ptr, __item_count * __item_size)` — no zero special-case.
2. scudo `standalone/wrappers_c.inc` (AOSP external/scudo main): realloc does
   `if (size == 0) { reportDeallocation(ptr); SCUDO_ALLOCATOR.deallocate(ptr, ...); return nullptr; }`.
3. ⇒ realloc(p,0) frees + NULL on Android's real allocator → the dangling SavedImages pointer
   double-frees. Bug fires on bionic/scudo, glibc, AND UCRT. AOSP's own build config is the vulnerable one.

## Evidence file set (aosp-audit/)

fuzz_gif_entry.cpp, gif_asan_seed_run.log, gif_fuzz30.log, gif_evidence.tar.gz (corpus+50
artifacts+logs), gif_fuzz_artifact_sample.bin, gif_verify_dgif_lib.c, gif_verify_seed.bin,
gif_seeds/ (10 valid GIF seeds). VM copy at ~/gifwork/ on the Kali box.
