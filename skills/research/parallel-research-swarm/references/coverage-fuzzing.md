# Coverage-guided fuzzing on Windows via zig (libFuzzer-style) — validated recipe

Built 2026-08-08: PNG fuzzer (libpng+zlib) and GIF fuzzer (giflib) against REAL AOSP
source. This is the upgrade over mutation-only fuzzing — it measures decoder-path
discovery and keeps inputs that reach NEW code. On hardened targets (expat, libjpeg),
mutation-only runs 100K+ iters with zero signal; coverage-guided grows its corpus and
shows new edges immediately.

## The three zig build flags that matter (all discovered the hard way)
1. `-fsanitize-coverage=trace-pc` — NOT trace-pc-guard.
   trace-pc-guard on Windows/zig fails at link: `undefined symbol: __start___sancov_guards`
   and `__stop___sancov_guards` — lld does not auto-generate the section markers on COFF.
   trace-pc calls a plain callback with no guard arrays — works.
2. Pair with `-fsanitize=undefined` — coverage ALONE fails at link:
   `could not open 'liblibclang_rt.ubsan_standalone.a'` (zig's runtime resolution on
   Windows needs the sanitizer paired). `-fsanitize=undefined -fsanitize-coverage=trace-pc`
   links clean. This also gives you UBSAN crash detection for free.
3. NEVER use git-bash /tmp paths with zig cc: `zig cc ... /tmp/x.c` → `CacheCheckFailed`.
   Use real Windows paths (C:\Users\... or the repo dir). This cost several debug cycles.

## Driver skeleton (the parts that matter)

```c
/* coverage bitmap */
#define COV_BITS (1 << 20)
static unsigned char cov_map[COV_BITS / 8];
static unsigned char cov_all[COV_BITS / 8];   /* union of ALL edges ever seen */
static unsigned int cov_guard_idx = 0;

/* trace-pc callback: hash return address into bitmap (no guard arrays needed) */
void __sanitizer_cov_trace_pc(void) {
    uintptr_t pc = (uintptr_t)__builtin_return_address(0);
    unsigned int idx = (unsigned int)((pc >> 4) ^ (pc >> 16)) & 0xFFFFFF;
    cov_map[(idx >> 3) & ((COV_BITS / 8) - 1)] |= (unsigned char)(1 << (idx & 7));
}
void cov_reset(void) { memset(cov_map, 0, sizeof(cov_map)); }
void cov_union_into_all(void) { for (int i = 0; i < COV_BITS/8; i++) cov_all[i] |= cov_map[i]; }
int cov_new_edges(void) {
    int n = 0;
    for (int i = 0; i < COV_BITS/8; i++) { unsigned char nb = cov_map[i] & ~cov_all[i]; if (nb) n++; }
    return n;
}
```

## THE critical novelty rule: set-based, NOT count-based
Count-based novelty (keep input only if edge COUNT exceeds all history) STALLS:
`new=0` forever once seeds cover the common paths, because a new input that sets a
DIFFERENT set of bits at the same count is discarded. Measured: 54 seeds, 5K iters,
`new=0` the whole run.
Set-based novelty (keep input if ANY previously-unseen edge BIT is set — compare
`cov_map[i] & ~cov_all[i]`) fixes it: corpus 54→102, edges 0→100 in 3K iters.
Per iteration: `cov_reset(); decode(buf); if (cov_new_edges() > 0) { add to corpus; cov_union_into_all(); }`

## Slow-decode watchdog (mandatory)
A mutated input can create a pathological decode (pixel-bomb / huge-dimension PNG).
Without a watchdog the fuzzer appears HUNG on iteration 1 (timeout exit 124, user-time 0).
Add per-iteration timing; if a single decode > 10s, SKIP the input (continue), don't
abort. `clock()` around the decode call is enough. Keep the threshold generous — UBSAN +
coverage instrumentation makes legit decodes ~10x slower than release.

## Build commands (validated)

libpng + zlib (PNG is Android's image path):
```
zig cc -O1 -g -fsanitize=undefined -fsanitize-coverage=trace-pc -I libpng -I zlib \
  fuzz_png_cov.c libpng/png.c libpng/pngerror.c libpng/pngget.c libpng/pngmem.c \
  libpng/pngpread.c libpng/pngread.c libpng/pngrio.c libpng/pngrtran.c \
  libpng/pngrutil.c libpng/pngset.c libpng/pngtrans.c libpng/pngwrite.c \
  libpng/pngwio.c libpng/pngwutil.c libpng/pngwtran.c \
  zlib/adler32.c zlib/compress.c zlib/crc32.c zlib/deflate.c zlib/infback.c \
  zlib/inffast.c zlib/inflate.c zlib/inftrees.c zlib/trees.c zlib/uncompr.c zlib/zutil.c \
  -o fuzz_png_cov.exe
```
(ALL libpng .c files needed — pngset.c references png_save_uint_32 which lives in
pngwrite/pngwutil; partial file lists cause undefined symbols.)
Seed corpus: libpng/contrib/pngsuite/*.png (51 files) — rich coverage from the start.
Decode path: png_create_read_struct + png_set_read_fn(mem reader) + setjmp error handler,
png_set_expand/strip_16/gray_to_rgb/palette_to_rgb/tRNS_to_alpha/interlace_handling,
then png_read_row loop. Cap w/h at 16384 to avoid pixel-bomb allocations.

giflib: needs the openbsd_reallocarray shim (giflib's gif_lib_private.h does
`#define reallocarray openbsd_reallocarray` — the symbol MUST be named openbsd_reallocarray):
```c
/* reallocarray_shim.c */
void *openbsd_reallocarray(void *ptr, size_t nmemb, size_t size) {
    if (nmemb != 0 && size > (size_t)-1 / nmemb) return NULL;
    return realloc(ptr, nmemb * size);
}
```
```
zig cc -O1 -g -fsanitize=undefined -fsanitize-coverage=trace-pc -I giflib \
  fuzz_gif_cov.c giflib/dgif_lib.c giflib/gif_err.c giflib/gif_hash.c \
  giflib/gifalloc.c giflib/egif_lib.c reallocarray_shim.c -o fuzz_gif_cov.exe
```
Decode: DGifOpen(io_ptr, mem_read_fn) + DGifSlurp — the full frame/extension parse.
Seed: giflib/doc/whatsinagif/*.gif.

## Performance reality
~25 iters/s on PNG with UBSAN + coverage (in-process, 128KB bitmap). A 3M-iteration
campaign ≈ 90 min. Do NOT set 2M-iteration budgets expecting quick results — the per-basic-block
callback is the cost. Progress print every 1000 iters to stderr; the run shows corpus
growth + new-edge accumulation.

## Crash detection
A real bug = process dies (SIGSEGV/UBSAN trap) with the input that caused it still in
`work[]`. For reproducible artifacts: write the current `work` buffer to a file before
each decode (or on signal handler), or accept that the in-process driver loses the exact
input on crash and switch to write-every-N strategy. Mutation-only subprocess fuzzers
(expat: 186K iters/0 crashes; jpeg: 400K+/0) never find anything on these targets —
coverage-guided at least proves it is exploring.

## CRASH TRIAGE methodology (validated 2026-08-08 — first REAL bug found)
The GIF fuzzer crashed within ~500 iters; the following sequence isolated it to a real
giflib bug. This is the repeatable playbook:

1. **exit=127 in git-bash does NOT mean "command not found"** — on Windows/git-bash a
   crashed process (access violation) reports 127. The binary ran (printed its startup
   lines) then died = CRASH, not missing binary. Also: `cmd | head; echo $?` reports
   HEAD's exit code, not the program's — pipe artifacts made the first two runs look
   like clean exits. Redirect to a file (`> log.txt 2>&1`) and read the file instead.
2. **Isolate harness-vs-target**: rebuild WITHOUT `-fsanitize-coverage` (plain `zig cc
   -fsanitize=undefined`). If the no-cov build still crashes, the bug is in the TARGET
   library, not the coverage callback. (Did this for giflib — crash reproduced without
   coverage → real library bug.)
3. **Capture the exact crashing input**: write `work[]` to a file BEFORE EVERY decode
   (not every N-th iteration — the N-th snapshot is the input at that iteration, which
   is NOT the crasher; measured: 69-byte snapshot vs real 52-byte crasher). The file on
   disk right before death IS the reproducer.
4. **Minimal standalone reproducer**: small main() that reads the file, runs
   open→slurp→close with fprintf(stderr, ...) progress markers BETWEEN every API call.
   The last marker printed before the crash names the crashing call. For giflib:
   DGifOpen OK → DGifSlurp rc=0 ImageCount=0 → DGifCloseFile → GifFreeSavedImages →
   CRASH.
5. **Step-instrument the suspected function** by replicating its cleanup sequence with
   markers (don't trust a single call boundary). giflib: manually ran
   Image.ColorMap→SColorMap→SavedImages→GifFreeExtensions in order; crash landed inside
   GifFreeSavedImages with ImageCount=0.
6. **Mechanism from code + state**: crash in GifFreeSavedImages with ImageCount=0 means
   the `for(sp < SavedImages + 0)` loop is skipped and `free(SavedImages)` hits a
   DANGLING pointer. Cause: DGifDecreaseImageCounter (dgif_lib.c:1153) error path does
   `reallocarray(SavedImages, ImageCount=0, ...)`; on most allocators realloc(ptr,0)
   FREES and returns NULL, but the code only updates SavedImages `if (non-NULL)` →
   stale pointer to freed memory → double-free at close. The reallocarray shim
   (nmemb*size=0 → realloc(ptr,0)) made it reachable on Windows.
7. **Poison-allocator caveat**: the poisoning-realloc UAF technique (from real-code-audit)
   only works when the library routes ALL its allocations through the injected memory
   suite. giflib allocates internally with plain malloc — the poison allocator was
   silently not wired in (memory looked zeroed, not poisoned 0xBB). For libs that don't
   take an allocator callback, rely on step 4-5 instrumentation instead.

## Result: first real bug (giflib DGifDecreaseImageCounter double-free/UAF)
- Reproducer: `C:\Users\HP\ai-workforce\aosp-audit\gif_crash_last.bin` (52 bytes; a
  truncated sample_1.gif — image-parse error path triggered).
- Class: use-after-free + double-free on the error path of a zero-touch-reachable
  decoder (GIFs auto-decode in messaging stickers, image previews, keyboard GIFs).
- Status at session end: mechanism proven to the double-free point; NOT yet confirmed
  exploitable to code execution (heap grooming unproven), NOT yet checked against
  current Android giflib tags / CVE tracking, NOT yet reported. Next steps: prove with
  an allocator that returns NULL on realloc(ptr,0), diff against latest AOSP tag, write
  the finding doc (Google ASR + giflib upstream), map zero-click delivery surfaces.
- LESSON: LLM source-audit refutes candidates; coverage-guided fuzzing DISCOVERS bugs.
  The real bugs were in the least-hardened target (giflib), not the OSS-Fuzz-covereds
  (expat/libyuv/jpeg). Target selection = where OSS-Fuzz has NOT been: GIF/HEIF/NFC
  parsers, not the big four.

## Where files live
C:\Users\HP\ai-workforce\aosp-audit\ — fuzz_png_cov.c/.exe (running long campaign),
fuzz_gif_cov.c/.exe, reallocarray_shim.c, libpng/ zlib/ giflib/ jpeg/ libvpx/ expat/
clones. Lab6 (kernel/GPU sims) was superseded by this real-code approach for actual
discovery.
