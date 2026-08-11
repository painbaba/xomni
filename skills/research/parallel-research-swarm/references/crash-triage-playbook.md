# Crash Triage Playbook — from "fuzzer exited 127" to proven root cause

Methodology used 2026-08-08 to turn a coverage-fuzzer crash in AOSP giflib into a
proven double-free with an upstream-fix confirmation (FINDING_giflib_doublefree.md).
Reuse for ANY fuzzer crash on real code.

## Phase 0 — Is it really a crash? (pipe-artifact trap)
- `cmd | head -N; echo "exit=$?"` — $? is HEAD's exit, not the fuzzer's. A fuzzer
  killed by SIGPIPE when head closes stdout looks like a clean exit-0. ALWAYS run
  to a FILE (`> out.txt 2>&1`) and read `$?` from the direct invocation.
- git-bash exit 127 from a Windows exe = process died via exception (access
  violation). NOT "command not found" — that's also 127, so verify the binary ran
  (its startup prints appear in the log BEFORE the crash point).
- Distinguish crash-in-loop from crash-in-decode: if heartbeat prints stop right
  after "initial done" and before iteration 1000, the crash is INSIDE decode of a
  mutated input, not the driver.

## Phase 1 — Capture the exact crashing input
- Save EVERY input to a fixed file just before decode (`gif_crash_last.bin`). The
  crash input is the LAST file written. Saving every N-th input is NOT enough —
  the snapshot lags the crash and sends you down wrong paths (spent a cycle on a
  benign version-byte mutation because of a lagging snapshot).
- Verify by replay: feed the saved file through a plain decode loop; a real
  crasher reproduces with exit 127, a benign mutation returns rc=1 gracefully.

## Phase 2 — Localize the crash function (step-marker instrumentation)
- Replicate DGifCloseFile's cleanup steps manually with `fprintf(stderr, "stepN: ...")`
  markers between each free. The LAST marker printed before the crash names the
  crashing function. (giflib: crashed inside GifFreeSavedImages with ImageCount=0 —
  the loop should have been skipped, so the crash had to be the free of a dangling
  SavedImages pointer.)
- Remember library semantics: giflib rc=0 is GIF_ERROR, GIF_OK=1. "Slurp rc=0"
  in a triage build is an ERROR RETURN, not success — that's the error path that
  called DGifDecreaseImageCounter.

## Phase 3 — Prove the mechanism (tracking-shim allocator)
UBSAN does NOT catch use-after-free/double-free on Windows (no ASAN runtime for
zig cc). Replace the target's allocator with a tracking shim:
- For giflib: its `reallocarray` macro maps to `openbsd_reallocarray` — provide
  that symbol with a shim that logs every alloc/realloc/free and flags any free
  of an address no longer in its live table ("[DF] DOUBLE-FREE or wild free").
- Key trick: `realloc(ptr, 0)` on UCRT/glibc FREES the block and returns NULL.
  Log it explicitly — that's the moment the dangling pointer is born.
- The shim output IS the proof: `reallocarray(NULL -> 0x..4AA0, 100)` (alloc),
  `reallocarray(0x..1860, 0) -> freeing block`, then `DOUBLE-FREE of 0x..1860`
  when GifFreeSavedImages frees the stale pointer. No ASAN needed.
- Note: shim overhead shifts heap layout — run 1 crashes at the double-free, run 2
  may survive but still flags `[DF]`. Both runs showing the same signature = proven.

## Phase 4 — Upstream comparison (vendor-lag check)
- AOSP giflib is 5.2-lineage; upstream is 6.x. `git clone --depth 1` of AOSP gives
  HEAD — the bug being present in HEAD is the finding, but you must check upstream.
- sources.debian.org raw-data URLs (`https://sources.debian.org/data/main/g/giflib/<ver>/dgif_lib.c`)
  render as PLAIN TEXT in the browser — the full file lands in the snapshot file;
  grep the saved snapshot for the function. curl to that host returns empty (blocked),
  the browser works.
- Upstream 6.1.3 HAS the fix: explicit `if (GifFile->ImageCount <= 0) { free(SavedImages);
  SavedImages = NULL; return; }` with comment "Avoid a dodgy edge casse in reallocarray()".
  AOSP lacks it = confirmed vendor-lag → reportable to upstream (sync reminder) +
  Google ASR (crash class).

## Phase 5 — Severity discrimination (the libavc lesson: fuzzer crash ≠ single-shot crash)
A coverage-fuzzer crash in a LONG run is NOT automatically a single-shot decoder
bug. libavc SEI input crashed the fuzz loop repeatedly (exit 3 with a symbolized
stack in ih264d_uev@ih264d_parse_cavlc.c:94) — but rigorous re-verification
showed the decode alone never crashes. Run the full ladder BEFORE claiming severity:
1. **Teardown-skip build**: `sed` out freeFrame/deleteCodec/delete from the
   harness, rebuild. If the input now exits 0, the earlier crash was TEARDOWN
   (often a harness alloc/free mismatch on the port, see coverage-fuzzing-libavc.md),
   not the decoder. giflib: crash survived teardown-skip → real.
2. **Guard-page single-shot**: place the input at the END of a VirtualAlloc page
   with the next page PAGE_GUARD|PAGE_READONLY. No fault = the over-read stays
   inside a padded internal buffer (libavc copies input into a MIN-256KB zeroed
   dynamic buffer, ih264d_api.c:2523-2540 — absorbs ≤64-bit over-reads into
   zeroed slack). Fault = true OOB reach in the buffer model as-is.
3. **Long-run decode-only** (teardown skipped, 20K+ iters, real seeds): segfault
   here = real OOB read, but heap-state-DEPENDENT — freed/reused blocks
   eventually put unmapped memory at the over-read offset. Iteration count to
   crash varies (50s with real H.264 seeds vs clean 20K on one PoC seed).
4. **Pristine rebuild**: re-test with a PLAIN shim (reallocarray→realloc, no
   tracking/poisoning). 5/5 still crashes → the bug is native to the code +
   libc semantics, not a shim artifact (giflib: realloc(ptr,0) frees+returns
   NULL on UCRT is real libc behavior).
5. **Trigger-condition map** (for heap-state-dependent findings, libavc 2026-08-08):
   build THREE harness variants to map exactly WHEN it crashes:
   - single-input loop: `loop N file` — decode the SAME input N times in one
     process (fresh codec per call). 5000x clean = repetition alone doesn't trigger.
   - mixed-input loop: `mixed N file1 file2 file3` — rotate a few STATIC inputs.
     5000x clean = static input diversity alone doesn't trigger either.
   - NOSEI seed: strip SEI NALs from the seed (start-code splitter, keep all
     types != 6) and re-fuzz. Still crashes → SPS-path uev is sufficient, the
     finding is SEI-independent and broader than first thought.
   If static inputs never crash but the FUZZER (mutated corpus + heap churn)
   crashes every relaunch: the bug is real (code-proven OOB) but ONLY a
   fuzzer-context deliverable — DoS under repeated diverse decode, not a
   single-shot PoC. Document that as the verdict; do NOT hand the user a
   single input claiming it always crashes.
VERDICT TEMPLATE: real-bug-but-heap-state-dependent = LOW-MED severity
(OOB read into zeroed slack; DoS under repeated decode; NOT a clean single-shot
trigger). Only giflib's double-free earned "deterministic single-shot". An
initial over-claim here ("deterministic 3/3") was corrected — the ladder is
what separates a reportable finding from an artifact.

## Phase 6 — Report it
- FINDING doc format (FINDING_giflib_doublefree.md): trigger hex + minimal bytes,
  crash chain numbered, root cause with exact lines, proof (shim output), impact,
  PoC files list, upstream comparison, report targets. Include the honest severity:
  crash/DoS class unless heap-grooming to RCE is demonstrated.

## General lessons
- The fuzzer that found this is the coverage-guided one (set-based novelty) pointed
  at a LESS-hardened target (giflib), not the mutation-only ones on hardened targets.
- A 52-byte trigger is the sweet spot for a parser bug — tiny inputs are trivially
  deliverable in messaging/sticker/keyboard auto-decode flows.
- When the LLM audit says "CONFIRMED" on a memory bug, still verify — but when the
  crash is REAL (exit 127, deterministic, no-coverage build too), the triage above
  is the fastest path to a defensible writeup.
- **Windows glob-expansion gotcha in Python-driven builds**: when invoking `zig cc/c++`
  via Python subprocess (`shell=True` on Windows), DO NOT pass glob patterns like
  `decoder/*.c` in the command string — the Windows shell does NOT expand them and
  zig fails with `CacheCheckFailed` on the literal path. Expand with `glob.glob()`
  in Python and pass the explicit file list. Same trap hits `$(find ...)` in
  git-bash background commands — use explicit paths or Python expansion.
- **Reach check before claiming zero-click**: after confirming a real AOSP parser bug,
  verify what actually consumes the library on modern Android — check the repo's
  Android.bp (`sdk_version`, `cc_library_static` vs `cc_library`) and who links it.
  giflib ships as `cc_library_static sdk_version: "9"` (legacy-only); modern Android
  decodes GIF via Skia/ImageDecoder. A real vendor-lag bug can still have near-zero
  modern-device reach — state that honestly in the FINDING doc.
