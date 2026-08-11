# Coverage Fuzzing libavc (AOSP H.264 decoder) — build + crash triage (2026-08-08)

Companion to `coverage-fuzzing.md` (the generic PNG/GIF recipe). This is the
libavc-specific build and the Windows-harness porting pitfalls, plus the
crash-capture workflow that produced REAL finding #2.

## Build recipe (zig on Windows, VERIFIED)
```
zig c++ -O1 -g -fsanitize=undefined -fsanitize-coverage=trace-pc \
  -Wno-error=date-time -Wno-date-time \
  -I libavc -I libavc/decoder -I libavc/common -I libavc/common/x86 \
  -I libavc/decoder/x86 -I libavc/fuzzer \
  fuzz_avc_driver.cpp libavc/fuzzer/avc_dec_fuzzer.cpp \
  libavc/decoder/*.c libavc/decoder/x86/*.c libavc/common/*.c libavc/common/x86/*.c \
  posix_memalign_shim.c -o fuzz_avc_cov.exe
```
- USE the OFFICIAL AOSP harness `libavc/fuzzer/avc_dec_fuzzer.cpp` — its
  `LLVMFuzzerTestOneInput` is the complete decode sequence (create → setArch →
  decodeHeader → setParams → allocFrame → decodeFrame loop → freeFrame →
  deleteCodec). Your driver only supplies `main()` + `__sanitizer_cov_trace_pc`.
- Include dirs that MATTER: `common/x86` (ih264_platform_macros.h — missing =
  "fatal error: ih264_platform_macros.h not found"), `decoder/x86`
  (ih264d_function_selector.c provides ih264d_init_function_ptr /
  ih264d_init_arch — missing = undefined-symbol link errors).
- `-Wno-error=date-time`: ih264d_api.c embeds `__DATE__`; zig's default
  -Werror kills the build otherwise.
- Compile driver + harness as `.cpp` (extern "C" LLVMFuzzerTestOneInput fails
  when the TU is compiled as C).

## Windows porting pitfalls (all hit, all fixed)
1. **posix_memalign → _aligned_malloc shim is NOT enough — the FREE must match.**
   AOSP's harness `iv_aligned_free` calls `free()` (POSIX assumption). On
   Windows, `free()` on `_aligned_malloc` memory = heap corruption → crashes at
   RANDOM points, including at teardown, which masquerades as a decoder bug.
   Fix BOTH: (a) `iv_aligned_free` → `_aligned_free`, and (b) `Codec::freeFrame`
   which also used `free()` on iv_aligned_malloc buffers. The second one was
   only found because the first fix moved the crash to freeFrame.
2. **Do NOT use `-D'posix_memalign(p,a,s)=_aligned_malloc(s,a)'`** — the macro
   rewrites your shim's own function definition → "conflicting types for
   '_aligned_malloc'". Declare the shim inline in the harness under
   `#if defined(_WIN32)` instead (patch avc_dec_fuzzer.cpp once, keep it).
3. After porting, build a NON-coverage `test_avc_one.exe` (single-file main +
   harness, no -fsanitize-coverage) — this is the control that isolates
   coverage-callback issues from real decoder bugs.

## Crash-capture + triage workflow (the part that found a REAL bug)
1. Driver saves EVERY input to `avc_crash_last.bin` immediately before decode.
   Non-zero exit → the last file IS the crash input. (No coverage-guided
   minimization needed to get started.)
2. Reproduce standalone with the NON-coverage build, 5x. Deterministic exit
   127 = real, not a coverage artifact.
3. Add `[dbg]` stderr markers at every pipeline stage (createCodec
   entering/calling/done, decodeHeader, decode loop, cleanup) + fflush. The
   last marker before death pinpoints the stage.
4. RULE for distinguishing harness bug vs decoder bug: crash AFTER "cleanup"
   printed = teardown path = check aligned-free mismatch FIRST (harness bug,
   not a decoder finding). Crash INSIDE the decode loop with a stack pointing
   at a decoder function (e.g. `ih264d_parse_nal_unit`) = REAL decoder bug.

## Real H.264 seeds (ffmpeg IS on this host — use it, don't hand-craft)
```
ffmpeg -y -v error -f lavfi -i "testsrc2=size=176x144:rate=10:duration=2" \
  -c:v libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p -g 10 -f h264 \
  real_baseline_176x144.h264
```
Generate baseline + main + high profiles at small resolutions. Hand-crafted
SPS/PPS/IDR seeds are a fallback but real streams give far better coverage.
Watch MAX_INPUT=65536 in the driver: high-profile 352x288 2s ≈ 58KB (fits),
longer clips need the cap raised or the stream truncated.

## Findings status (2026-08-08, VERIFICATION COMPLETED)
- **REAL BUG #2 (libavc) — VERIFIED, SEVERITY CORRECTED DOWN**: the SEI-family
  crash (16-byte `00000001060003000000004001100000`, 11-byte minimal
  `0000000106000000020000`, plus 0xff-payload-type variants like
  `000000010642ff001e...`) is a REAL OOB read, code-proven and upstream-identical
  (ittiam-systems/libavc clone diffs clean on ih264d_uev + SEI check), BUT:
  - SINGLE-SHOT: NO crash — guard-page input placement (VirtualAlloc page +
    PAGE_GUARD neighbor) does not fault. Reason: after header decode libavc
    copies input into a MIN-256KB zeroed dynamic buffer (+EXTRA_BS_OFFSET slack,
    ih264d_api.c:2523-2540); the uev over-read (ih264d_parse_cavlc.c:94,
    GETBITS reads pu4_buf[w] and [w+1] unchecked after CLZ jump) stays inside
    the padded zeroed buffer.
  - LONG-RUN decode-only (teardown SKIPPED): SEGFAULT 139 — real but
    heap-state-dependent; crash time varies (50s with real ffmpeg seeds, clean
    through 20K iters on a single PoC seed).
  - Verdict: LOW-MED severity OOB read (≤64-bit over-read into zeroed slack;
    DoS under repeated decode; NOT a clean single-shot trigger). Stronger than
    an LLM candidate (empirically crashes the decoder) but NOT the giflib-class
    deterministic finding. Docs: FINDING_libavc_sei_uev_oob.md (corrected section).
- **The 5/5 repro was a harness-teardown artifact, correctly caught**: the early
  exit-127 reproductions used a STALE test_avc_one.exe built before the
  freeFrame `_aligned_free` fix — those died in teardown (crash AFTER "cleanup"
  printed), not decode. The severity-discrimination ladder (teardown-skip build
  → guard-page single-shot → long-run decode-only → pristine shim) is the
  mandatory sequence before claiming any fuzzer crash as a decoder bug; full
  ladder in references/crash-triage-playbook.md Phase 5.
- **SECOND, DISTINCT crash signature (discovered at session end, triage
  INCOMPLETE)**: the decode-only (teardown-skipped) fuzzer on REAL ffmpeg seeds
  crashed 3/3 runs (exit 3, access violation) with the SAME stack every time:
  `ih264d_create_pic_buffers` (ih264d_utils.c:1818 — the ALIGN64 luma/chroma
  buffer walk) ← `ih264d_init_pic` (utils.c:882) ← `ih264d_start_of_pic`
  (parse_slice.c:341) ← `ih264d_parse_decode_slice` (parse_slice.c:1566).
  This is the picture-buffer allocation path during slice decode — a DIFFERENT
  bug from the SEI/uev OOB (no SEI involved; the trigger is a mutated slice
  NAL from a real stream). Likely resolution-change related: dynamic-buf
  realloc (ih264d_allocate_dynamic_bufs) runs before create_pic_buffers, so
  check whether a mid-stream SPS dimension change leaves the walk using
  stale/oversized u2_frm_wd_y*ht against a smaller base. Crash was FASTER on
  real seeds (~50s) than on the SEI PoC seed (clean through 20K) — real
  streams are the better crash trigger for this signature. NOT yet line-pinned;
  next session: capture the exact input (the fuzzer overwrites
  avc_crash_last.bin per iteration — add STOP-ON-CRASH or snapshot-to-dir),
  minimize, and test with pristine upstream build.
- **Driving zig builds from Python on Windows: expand globs IN PYTHON.** A
  subprocess shell cmd with `"path\*.c"` passes the literal glob to zig →
  `CacheCheckFailed` errors. `sorted(glob.glob())` the .c lists first, then
  join into the command. (Hit in the hermes-verify script; the interactive
  git-bash shell expands globs fine, Python subprocess does not.)
- 6 libavc LLM-audit candidates: candidate (a) GETBITS/uev OOB now CONFIRMED
  real (the bug above); b/c/d still pending empirical check.
- **REAL FINDING #1 (giflib)**: DGifDecreaseImageCounter realloc-to-zero →
  dangling SavedImages → double-free at DGifCloseFile; 52-byte trigger
  (gif_crash_last.bin); upstream giflib 6.1.3 has the `ImageCount <= 0` guard,
  AOSP 5.2-lineage lacks it = confirmed vendor-lag. PRISTINE-BUILD PROOF:
  re-verified 5/5 exit 127 with the PLAIN reallocarray→realloc shim (no
  tracking, no poisoning) — the double-free is native to AOSP giflib 5.2 +
  Windows UCRT semantics (realloc(ptr,0) frees + returns NULL; giflib keeps
  the dangling pointer because it only updates `if (correct_saved_images !=
  NULL)`), NOT a tracking-shim artifact. Deterministic single-shot — the
  strong finding. See FINDING_giflib_doublefree.md.

## Campaign tally (through this session)
10 LLM audit candidates → 9 refuted with evidence (each by a DIFFERENT defense
layer; see verdicts_decoders.md), 6 libavc pending. Coverage-guided fuzzing
produced the 2 REAL crashes (giflib + libavc) plus a SECOND unconfirmed libavc
crash signature (create_pic_buffers walk, 3/3 reproducible, triage incomplete).
The method is now proven twice: LLM audit refutes candidates, coverage-guided
fuzzing discovers real bugs — and real bugs live in the LESS-hardened targets
(giflib, libavc > libpng > jpeg/expat). png closed as a clean negative (55K
iters, 0 crashes); jpeg closed clean (474K iters).
