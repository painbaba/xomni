# libhevc (AOSP H.265/HEVC) coverage fuzzer — build recipe + findings (2026-08-08)

libhevc is the campaign's GOLDMINE target: HEVC is auto-decoded in modern
messaging video (WhatsApp/YouTube via MediaCodec c2.hevc on devices without
hardware decode), and it is FAR less OSS-Fuzz-hardened than libavc/libwebp.
Discovery rate measured: **854 new edges in 3K iters, corpus 5→94** — best of
the whole campaign (vs animated-WebP 166, static-WebP 137/899K). Two real UBs
found in the INITIAL coverage pass on REAL ffmpeg streams, before any mutation.

## Clone & sources
- Repo: `https://android.googlesource.com/platform/external/libhevc` (exists; NOT libheif — that path 404s)
- `decoder/` (27 .c incl. ihevcd_bitstream.c, ihevcd_parse_residual.c, ihevcd_process_slice.c), `common/` (34), `decoder/x86/` + `common/x86/` (SIMD), `fuzzer/hevc_dec_fuzzer.cpp` (official harness, LLVMFuzzerTestOneInput)

## Build (verified working command)
Driver: `fuzz_hevc_driver.cpp` = copy of the libavc driver with names swapped
(hevc_crash_last.bin, [cov-hevc]) — same set-based novelty, same mutate engine.

```
zig c++ -O1 -g -fsanitize=undefined -fno-sanitize=shift,alignment \
  -fsanitize-coverage=trace-pc -Wno-error=date-time -Wno-date-time -DDISABLE_AVX2 \
  -I libhevc -I libhevc/decoder -I libhevc/common -I libhevc/common/x86 \
  -I libhevc/decoder/x86 -I libhevc/fuzzer \
  fuzz_hevc_driver.cpp libhevc/fuzzer/hevc_dec_fuzzer.cpp \
  libhevc/decoder/*.c libhevc/decoder/x86/*.c libhevc/common/*.c libhevc/common/x86/*.c \
  posix_memalign_shim.c -o fuzz_hevc_cov.exe
```

### The three non-obvious flags
1. **`-DDISABLE_AVX2`** — decoder/x86/ihevcd_function_selector.c references
   `ihevcd_init_function_ptr_avx2` which has NO definition in the checked-in
   tree (generator-missing-file, same family as the libaom rtcd maze). The
   selector already has `#ifndef DISABLE_AVX2` fallback to sse42 — just define it.
2. **`-fno-sanitize=shift,alignment`** — CRITICAL. Without it the UBSAN build
   ABORTS ON EVERY REAL SEED (both findings below fire on real ffmpeg streams in
   the initial pass), so the fuzzer dies before fuzzing. zig requires
   `-fsanitize=undefined` paired with coverage to link the UBSAN runtime, so you
   can't drop UBSAN entirely — disable just the two noisy checks.
3. Windows aligned-alloc patches to the harness (same as libavc): inline
   posix_memalign shim (do NOT use -D macro), and BOTH free sites →
   `_aligned_free` (iv_aligned_free line ~85, Codec::freeFrame line ~221).
   Without the freeFrame fix, teardown crashes masquerade as decoder bugs.

## Seeds (real streams, ffmpeg libx265)
```
ffmpeg -f lavfi -i "testsrc2=size=176x144:rate=10:duration=2" -c:v libx265 \
  -preset ultrafast -x265-params "log-level=error" -f hevc hevc_176x144.h265
```
5 seeds: 64x64, 128x96 bars, 176x144, 352x288, 640x360. Real x265 streams
trigger the UBs — crafted mutations are NOT needed for the initial hits.

## FINDING A — signed-shift UB (LOW severity)
`ihevcd_parse_residual.c:758`:
```c
u4_coeff_sign_map = value << (32 - num_coeff);   // value: UWORD32 from CABAC
```
UBSAN: "left shift of 30 by 27 places cannot be represented in type 'WORD32'".
num_coeff ∈ [1,16] (guarded at line 637; shift amount [16,31] — never the
shift-by-32 UB, but the RESULT overflows signed int). On real compilers the
UWORD32 sign map wraps silently (mod 2^32) and downstream use
(`(map >> 31) & 1`, `map <<= 1` at 864-867) decodes correct signs — no memory
corruption. Hygiene fix: cast to UWORD32 before shifting.

## FINDING B — misaligned 32-bit load (UB — severity CORRECTED DOWN 2026-08-09)
`ihevcd_process_slice.c:1069`:
```c
*(UWORD32 *)(ps_proc->pu1_pic_no_loop_filter_flag + (bit_pos >> 3)) >> (bit_pos & 7)
```
bit_pos derived from CTB coordinates (attacker-influenced via SPS dims/slice
data). UBSAN: "load of misaligned address ... for type 'UWORD32', requires 4
byte alignment". Triggered by ALL real streams ≥176x144 — pervasive in the
deblock path.
**VERIFIED ON REAL aarch64 (qemu-user cross-build, 2026-08-09): ARM64 does NOT
fault on unaligned loads in normal memory — they silently succeed.** Cross-
compiled libhevc for aarch64 + ran under qemu-user: micro-repro off=0..7 all
read correct values (no SIGBUS), full decoder build decoded all real seeds
rc=0. UBSAN-instrumented aarch64 build still reports the UB at 1069:87 — it IS
real UB, but NOT a crash on modern ARM hardware. **Severity: UB-only (LOW-MED),
same class as the shift-UB — do NOT claim ARM crash-class for unaligned
loads on aarch64** (only ARMv5-and-older faults). This is the value of
cross-arch verification: it prevents over-claiming an ARM fault that ARM
silently permits.

## FINDING C — NULL-pointer + offset write in fmt_conv (STRONGEST, single-shot trigger FOUND)
`ihevcd_fmt_conv.c:778`:
```c
pu4_rgb_dst_tmp  = (UWORD32 *)pu1_y_dst;      // pu1_y_dst may be NULL
pu4_rgb_dst_tmp  += cur_row * ps_codec->i4_disp_strd;   // NULL + nonzero = UB
```
UBSAN (null check): "applying non-zero offset 1408/2816/4224 to null pointer"
(3 threads, 3 offsets in run 1). pu1_y_dst comes from
`ps_out_buffer->pu1_bufs[0]` (process_slice.c:1669) — NULL when the frame's
display buffer wasn't allocated (resolution-change / empty-DPB window). The
downstream store at fmt_conv.c:927 passes the pointer into a write — on ARM
(real Android mediaserver) a NULL+offset store is a translation fault; on x86
it writes silently to low memory (plain build exits 0 — that's expected, not a
negative result).

### SINGLE-SHOT TRIGGERS (the milestone — first in the whole Ittiam campaign)
- `hevc_crash_mut.bin` (3204B: VPS+SPS+PPS+multi-slice, valid structure,
  mutated from a real seed): UBSAN build panics 3/3 and 5/5 fresh-process
  (offsets 1024/2048). libavc's uev bug was context-only; THIS one is
  single-shot reproducible.
- `hevc_crash_mut2.bin` (3395B, DIFFERENT mutation — head starts with a partial
  byte before the start code): 3/3 stable (offset 1024).
- `hevc_crash_mut3.bin` (8136B, clean VPS start `00 00 00 01 40 01 2c...`):
  3/3 stable (offset 512).
- → the trigger surface is BROAD, not one lucky mutation: **6/6 long runs
  crashed on DISTINCT inputs** at varying iteration counts (run1 @104.5K,
  run2 @12.5K, run3 @9K, run4 @19K, run5 @38K, v2 seed-set @29K), offsets
  512/1024/2048/1408/2816/4224. It fires on EVERY seed set (even with the
  176x144 seed excluded) — it is the DOMINANT bug of this decoder and blocks
  exploration of everything else (see triage-patch below).
- Truncation-minimization NEGATIVE (do not re-attempt): cuts at 300/500/1000/
  1500/2000/2500 bytes all fail (exit 1, 0 panics) — the full multi-slice
  structure (incl. later slice NALs at offsets ~1889-1990) is required.

### DOMINANT BUG BLOCKS EXPLORATION → TRIAGE-PATCH TECHNIQUE (class-level)
When the SAME sanitizer panic kills every run before the fuzzer explores deep
(6/6 runs died at 9-29K iters), locally PATCH the known bug and re-fuzz to find
OTHER bugs:
- Patch `ihevcd_fmt_conv.c`: insert `if(pu1_y_dst == NULL || pu1_u_dst == NULL
  || pu1_v_dst == NULL) return ret;` BEFORE the pointer arithmetic (the UB is
  the arithmetic at line 778, NOT the later store — guarding inside the
  threading block below does nothing). Check ALL THREE dst pointers; the null
  can be y, u, or v.
- Result: patched fuzzer (fuzz_hevc_patched.exe) went 175K+ iters / 6000+ new
  edges / ZERO panics — 10-20x deeper than any unpatched run. In this case the
  rest of the decoder came back clean (the NULL+offset WAS the dominant bug),
  but the technique is what lets you FIND that out instead of assuming.
- Patch verification (hermes-verify script pattern): (1) patched build compiles,
  (2) all known triggers now produce 0 panics, (3) a real seed still fuzz-smokes
  to DONE (no regression). See the verification-pitfalls section below.
- Revert/keep: this is a LOCAL triage patch only — never claim it as the real
  fix; the real fix belongs upstream (guard the null before arithmetic).

### Exit-code triage trap (hit repeatedly — read carefully)
With a SHORT fuzz budget (FUZZ_ITERS=30) the UBSAN panic fires deterministically
(2 panics per run, 5/5) but exit=0 — the sanitizer abort on the decoder's
WORKER thread doesn't propagate to the main-loop exit code on short runs. Long
runs accumulate state and exit 3. VERDICT RULE: judge the trigger by the panic
lines in the log, not the exit code. 5/5 panic = stable trigger; exit-code
variance is a harness detail.

### Severity reasoning (FINAL VERDICT 2026-08-09 — CORRECTED DOWN, ASAN cross-check)
NULL+offset at fmt_conv.c:778 is **UB-ARITHMETIC-ONLY — the store NEVER
executes**. Evidence (Kali VM, w4-2 agent): unpatched ASAN build + single-shot
triggers + gdb + color-format variants (420P/RGBA/RGB565) — UBSAN null-check
fires at the arithmetic, but no write to NULL+offset ever happens: the
downstream store at :927 is behind the flush-mode/threading guard at :786 which
returns early. **Severity FINAL: LOW-MED (UB address arithmetic on NULL), NOT a
crash/write primitive.** Do NOT claim mediaserver crash-class for this. The
multiplier i4_disp_strd IS attacker-influenced (SPS-derived display width,
parse_headers.c:1979/1986) but that is moot — the write never fires. RCE was
already excluded (NULL page unmapped on modern Android).

### NVD NOVELTY CHECK — the gate before claiming a find (class-level technique)
Before claiming any codec find as novel, check the NVD REST API:
`curl "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch=libhevc&resultsPerPage=20"`
libhevc's documented history: 10 CVEs in 2017 (the mediaserver RCE wave —
CVE-2017-0406/0407/0539/0540/0589/0590/0637 etc., the original zero-click
class this campaign targets), 2018 NEON/resource-exhaustion, 2019
uninitialized-data info-disclosure wave + CVE-2019-9420 (OOB read from integer
overflow). NONE of the 18 describe the fmt_conv NULL+offset write, the
process_slice.c:1069 misaligned load, or the parse_residual.c:758 shift-UB →
all three findings are NOVEL vs documented history. The NULL+offset is in the
SAME component class as the 2017 RCEs (mediaserver HEVC decode) — a modern
re-find of that attack surface ~9 years later.

## Lesson: judge alignment/UB findings against the ARM TARGET — but VERIFY, don't assume
x86 tolerates unaligned loads. **Do NOT assume ARM faults — VERIFY with a real
cross-build.** aarch64 (every modern Android device) silently allows unaligned
loads in normal memory; only ARMv5-and-older faults. Verified 2026-08-09:
qemu-user cross-build of the full decoder ran all real seeds rc=0 (see FINDING B).
The verification ladder that settled all three libhevc findings: (1) UBSAN on
x86 (catches the UB), (2) real aarch64 cross-build + qemu-user (does the UB
fault on the target arch?), (3) ASAN cross-check patched-vs-unpatched (does the
UB arithmetic ever reach an executing store?), (4) NVD novelty gate. UBSAN's
alignment check on x86 is a SIGNAL for review, not a crash proof — the cross-arch
step decides. Conversely, shift-overflow that wraps silently stays LOW regardless
of platform.

## Windows verification-script pitfalls (hermes-verify scripts, hit repeatedly)
1. **Forward-slash paths for zig via shell=True** — backslash paths get mangled
   by cmd ("no input files" with a valid list). Convert with `.replace("\\","/")`
   on every -I and source path before joining the command.
2. **Expand globs in Python, not the shell** — `zig c++ ... decoder/*.c` via
   cmd.exe does NOT expand the glob (CacheCheckFailed on literal `*.c`). Use
   `glob.glob()` and pass explicit file lists.
3. **Env vars via `env=` param, NEVER `VAR=x cmd` prefix** — cmd.exe rejects the
   POSIX `FUZZ_ITERS=1000 prog` prefix ("'FUZZ_ITERS' is not recognized").
   `subprocess.run(..., env=dict(os.environ, FUZZ_ITERS="1000"))`.
4. Run smoke tests from the project cwd (driver writes crash-last files
   relative to cwd); `cwd=TMP` breaks the relative file expectations.
5. A fuzzer that was killed holds its exe — `powershell Get-Process fuzz_* |
   Stop-Process -Force` before rebuilding, or lld-link fails with Permission
   denied writing the output.

## TWO binaries: fuzzing build vs verification build (critical distinction)
- `fuzz_hevc_cov.exe` = the fuzz build (`-fno-sanitize=shift,alignment`). It CANNOT
  catch the shift UB — that's the point (without disabling, it aborts on every real
  seed before fuzzing). It writes `hevc_crash_last.bin` on hard crashes only.
- **To VERIFY a shift-UB trigger, rebuild with shift sanitizer ENABLED** (drop the
  `-fno-sanitize=shift,alignment` flag entirely, keep `-fsanitize=undefined` +
  `-fsanitize-coverage=trace-pc`): `fuzz_hevc_ubsan.exe`. Full-UBSAN panics with
  "left shift of N by M places ... ihevcd_parse_residual.c:758" on ANY real
  libx265 stream in the FIRST decode pass — proven with fresh ffmpeg builds:
  `trigger_176x144.h265` → "511 by 23", residual-heavy `trigger_noise.h265` →
  "1009 by 22", sibling-fuzzer seed → the canonical "30 by 27". The UB fires on
  the whole seed class, not one crafted file.
- Pitfall: the full-UBSAN exe and the fuzz exe must not fight over output — a
  killed fuzzer holds its exe (powershell Stop-Process before rebuild, see below).

## Building trigger videos (ffmpeg libx265) — 2026-08-09 verified
Raw Annex-B (media players, `<video src>` fallback):
```
ffmpeg -f lavfi -i testsrc2=duration=2:size=176x144:rate=15 -c:v libx265 \
  -preset fast -crf 28 -pix_fmt yuv420p -x265-params "log-level=error" -f hevc trigger_176x144.h265
```
Residual-heavy (more residual blocks = more line-758 hits; measured 1009<<22):
```
ffmpeg -f lavfi -i testsrc2=duration=2:size=352x288:rate=15 -f lavfi -i \
  "nullsrc=s=352x288:d=2,geq=random(1)*255:128:128" \
  -filter_complex "[0:v][1:v]blend=all_mode=addition" -c:v libx265 -preset medium \
  -crf 30 -pix_fmt yuv420p -x265-params "log-level=error" -f hevc trigger_noise.h265
```
MP4 container (WhatsApp-able, autoplay-able): same commands + `-movflags +faststart`,
output `.mp4`. Verify on host: `ffprobe -v error -show_entries stream=codec_name,width,height`
then decode `ffmpeg -v error -i file -f null -` (must exit 0). Note: real x265
streams trigger the UB — crafted mutations are NOT needed (matches seeds section).

## Running the verification harness from git-bash (pitfalls)
- `zig c++` in a bash heredoc script: use `C:/Users/...` Windows-style paths for
  -I/-o args, NOT `/c/Users/...` — zig rejects MSYS paths with "unable to open
  output directory '/c/...': FileNotFound" (hit with a first build script).
- Passing an MSYS path (`/c/.../seed.h265`) as argv[1] → driver says "no seeds!".
  Use `cygpath -w "$PWD/file.h265"` or cd into the file's dir and pass the bare
  filename. (The archive's known-good seed runs fine because it's invoked from cwd.)

## Sibling-fuzzer collisions (multi-agent campaigns)
Other agents may run `fuzz_hevc_cov.exe` concurrently and OVERWRITE
`hevc_crash_last.bin` (it's a fixed name). `cp` it to your own name immediately
after capture or re-verify it before staging; treat its contents as volatile.

## Docs
- `aosp-audit/FINDING_libhevc_shift_ub.md` — both UBs with full analysis
- Drivers/binaries: `aosp-audit/fuzz_hevc_driver.cpp`, `fuzz_hevc_cov.exe` (fuzz),
  `fuzz_hevc_ubsan.exe` (full-UBSAN verification build)
- Seeds: `aosp-audit/seeds_hevc/*.h265`; staged trigger corpus in
  `ghost-lab/ghost_sandbox/media/` (h265 + mp4 + HEVC-appended png/jpg polyglots)
