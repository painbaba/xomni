# libhevc NULL+offset severity verification (worked example, 2026-08-09)

The 3-layer triage of §4b applied to a real AOSP finding. Shows how a
UBSAN-flagged NULL+offset was PROVEN arithmetic-only (no executing write) —
downgrading it from "crash-class controlled-offset NULL write / deterministic
mediaserver crash" to "real UB, silent on real hardware".

## Finding under test
`ihevcd_fmt_conv.c:782` (AOSP libhevc H.265 decoder, mediaserver path):
```c
pu1_v_dst_tmp = pu1_v_dst + (cur_row / 2) * ps_codec->i4_disp_strd / 2;  // v_dst = NULL
```
3 single-shot triggers (mut/mut2/mut3, 3204/3395/8136 B mutations of a real
HEVC seed) made the Windows UBSAN build (null-check on) panic 3/3:
`applying non-zero offset 1024/1024/512 to null pointer`. The prior finding doc
framed it as a crash-class controlled-offset NULL write.

## Setup
- Kali VM (painbaba@192.168.29.35), clang 21, paramiko orchestration.
- Two trees: `~/fuzz/libhevc` (patched: NULL-dst guard) and
  `~/fuzz/libhevc_unpatched` (guard removed). Verify the diff is exactly the
  patch lines — a stray diff invalidates the whole A/B comparison.
- Identical build recipe for BOTH binaries (tiny main `hevc_one_main.cpp`:
  read file → one `LLVMFuzzerTestOneInput` call → return 0):
  ```
  clang  -O1 -g -fno-omit-frame-pointer -fsanitize=address -DDISABLE_AVX2 -msse4.2 \
         -I decoder -I common -I decoder/x86 -I common/x86 -I fuzzer -I . \
         -c decoder/*.c decoder/x86/*.c common/*.c common/x86/*.c
  clang++ -O1 -g -fno-omit-frame-pointer -fsanitize=address -DDISABLE_AVX2 -msse4.2 \
         -c fuzzer/hevc_dec_fuzzer.cpp  +  hevc_one_main.cpp
  clang++ -fsanitize=address *.o -o fuzz_hevc_unpatched_asan
  ```
- Recover-mode UBSAN build of the unpatched tree: same but `-fsanitize=undefined`
  (NO `-fno-sanitize-recover`).
- Diagnostic build: scratch copy of the tree (never patch pristine), add
  `fprintf(stderr,...)` at fmt_conv entry (all pointer args + cur_row/num_rows +
  e_chroma_fmt/disp_strd) and before each conversion call; rebuild only that .o,
  relink. CRLF: normalize `\r\n` before anchoring patches.
- Verify transfer integrity: sha256sum local vs remote for every trigger + seed.

## Results
| input              | patched ASAN | unpatched ASAN |
|--------------------|--------------|----------------|
| hevc_crash_mut.bin | 0 (clean)    | 0 (clean)      |
| hevc_crash_mut2.bin| 0 (clean)    | 0 (clean)      |
| hevc_crash_mut3.bin| 0 (clean)    | 0 (clean)      |
| hevc_352x288.h265  | 0 (clean)    | 0 (clean)      |

The unpatched ASAN build does NOT crash on any trigger. Control probe —
`*(int*)0x400 = 1;` under the same clang ASAN → `DEADLYSIGNAL SEGV ... WRITE
memory access ... zero page` (plain gcc → 139). So ASAN would flag an executing
NULL write; its silence is meaningful.

## Why no crash — the 3 layers
1. **Recover-mode UBSAN** (halt_on_error=0, print_stacktrace=1): mut/mut2/mut3
   DO fire `fmt_conv.c:782:36: applying non-zero offset 1024/1024/512 to null
   pointer` — the UB is genuinely reached (previous halt-mode UBSAN builds had
   missed it: they died on the earlier shift-UB at parse_residual.c:758 first).
2. **ASAN unpatched**: clean on all → no executing fault.
3. **Diagnostic build**: every fmt_conv call has y_dst/u_dst = VALID heap
   pointers, v_dst = NULL; the taken branch is 420sp→420sp (e_chroma_fmt 0xb/0xc),
   which receives the VALID y/uv dst pointers. The NULL-derived v_dst_tmp is
   computed but NEVER dereferenced. Forcing other output formats via harness
   byte data[6] (→420P, RGB565, RGBA8888 variants): same outcome — the branch
   that runs always writes through valid base pointers; NULL planes are exactly
   the planes that format doesn't touch.

## Verdict
Real, deterministic UB (UBSAN-proven) but ARITHMETIC-ONLY: the NULL+offset
pointer is never stored through. Same class as the shift-UB / misaligned-load
findings — silent on real hardware, x86 and ARM. Crash would require y_dst
itself NULL in a branch that dereferences it; no trigger (or format-forced
variant) reaches that state. Severity downgraded, finding doc updated with the
exit-code table + mechanism.

## libhevc fuzzer harness control bytes (hevc_dec_fuzzer.cpp)
- data[6] (OFFSET_COLOR_FORMAT) % 6 → output color format:
  {420P, 420SP_UV, 420SP_VU, 422ILE, RGB_565, RGBA_8888} (enum 0x1, 0xb, 0xc, 0x5, 0x9, 0xd)
- data[7] → numCores = (data[7] % 4) + 1
- data[8] → arch idx into {ARM_NONEON, ARM_A9Q, ARM_NEONINTR, ARMV8_GENERIC,
  X86_GENERIC, X86_SSSE3, X86_SSE42}; ARM requests fall back on x86 builds.
- fmt_conv signature: `ihevcd_fmt_conv(codec, proc, y_dst, u_dst, v_dst, cur_row, num_rows)`
  with early `if(0 == num_rows) return ret;` — the NULL+offset arithmetic sits
  AFTER that check, so UBSAN firing at it implies num_rows != 0.
- x86 intr files (ssse3/sse42) compile UNCONDITIONALLY — no `#if __SSE4_2__`
  guards — so `-msse4.2` is required and changes which function pointers run;
  always replicate the target build's real flags.

## Root-cause epilogue (follow-up session, 2026-08-09): WHY v_dst is NULL

The follow-up session found the mechanism behind the NULL dst and closed the
"is the write dead?" question with reachability proof:

- **The NULL V-plane is a HARNESS artifact, not a decoder state.**
  `hevc_dec_fuzzer.cpp::allocFrame()` switches on color format:
  `IV_YUV_420SP_UV/VU` → `num_bufs = 2` (Y + interleaved UV only). `bufs[2]`
  is NEVER allocated → `pu1_v_dst = NULL` on EVERY 420SP decode. The muts'
  byte data[6] selects 420SP (0xb/0xc), so fmt_conv always saw `v=(nil)`.
  The taken branch (420sp→420sp) only uses `pu1_y_dst_tmp`/`pu1_uv_dst_tmp`
  (VALID); `pu1_v_dst_tmp` is only used by the 420P branch — where all 3
  bufs ARE allocated. ⇒ no configuration ever stores through a NULL-derived
  pointer. Verified with an fprintf-instrumented fmt_conv entry:
  `[fmt_conv] y=0x…c590 u=0x…f5a0 v=(nil) cur_row=64 num_rows=32 disp_strd=128 … fmt=11`
  on mut2 (and all-three-VALID for real seeds hevc_352x288/176x144, fmt=1).
- **Windows-only panic = compiler DCE asymmetry.** Windows clang-cl kept the
  UBSAN null check on the DEAD GEP (the check reads base+offset operands, so
  it survives when the result is unused); Linux clang eliminated the dead
  computation AND its check — even at -O0 (LLVM backend dead-instruction
  elimination runs at every -O level). So the original Windows panic was a
  dead-value arithmetic check, and the plain Windows build exiting 0 on the
  same triggers was already the "no executing store" proof.
- **Custom-allocator trap (guarded):** replicating the Windows guard allocator
  (`size > 4096 → NULL`) on Linux BROKE the codec entirely — the codec's main
  68 KB memtab alloc was rejected, create "succeeded" but every decode errored
  0x2015 and parsed nothing → fmt_conv unreachable → "clean" runs vacuous.
  Aliveness beacon: mut2/mut3 reliably fire shift-UB at parse_residual.c:758
  in working builds; its absence in the guard-sim build proved the codec was
  dead, not the bug gone. The real Windows guard build (fuzz_hevc_guard.exe,
  960K iters, 0 panics) was likewise decoding nothing.
- **Reachability probes (all negative):** unpatched ASAN fuzz campaign 669
  runs / 901 s → 0 crashes; null-only UBSAN fuzz campaign 952 runs → 0 null
  panics; sweep of all 1426+ prior corpus seeds through the null-UBSAN
  single-shot → 0 panics. Combined with the code analysis: the NULL-dst state
  is unreachable in any working build, and even if reached, the value is dead.
- **Null-only UBSAN isolation:** `-fsanitize=null -fno-sanitize-recover=all`
  was required because all-checks halt-mode UBSAN died earlier on unrelated
  UBs (function-pointer type mismatch ihevcd_inter_pred.c:417 on mut.bin;
  shift-UB parse_residual.c:758 on mut2/mut3) before fmt_conv — "no panic at
  fmt_conv" in that build is meaningless.

Final: all three libhevc findings are UB-only. The finding's crash-class
characterization was over-claimed; severity stays LOW (hygiene fix; the
NULL-guard patch remains fine defense-in-depth).
