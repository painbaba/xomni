---
name: asan-libfuzzer-verification
description: Verify memory-safety bugs with ASAN+libFuzzer; fuzz more.
---

# ASAN + libFuzzer verification and bug hunting

Use when a crash/double-free/UAF finding needs airtight sanitizer proof ("verify under real ASAN"), when fuzzing a C/C++ library for additional bugs, or when building a libFuzzer harness for a library with a vendored/AOSP source tree. Often runs against a remote Linux VM (Kali) via paramiko — see §6.

## 1. Mirror the target's REAL build config — not the tree's default Makefile

The single most important step. Check the project's actual build definition (Android.bp, CMake, platform Makefile) for:
- **Compile flags** (e.g. `-DHAVE_REALLOCARRAY`) that change which libc functions are used.
- **Which source files are actually compiled.** AOSP example: `Android.bp` builds giflib with `-DHAVE_REALLOCARRAY` and does NOT compile the vendored `openbsd-reallocarray.c`; the tree's own Makefile DOES compile it. These two configs behave completely differently (see §2).

Vendored shim files can MASK bugs on your build host. Compile what the target platform builds, not what the tree's default build does.

## 2. realloc(p, 0) / reallocarray(ptr, 0) semantics trap

`realloc(p, 0)` behavior is implementation-defined and decides whether "realloc-to-0 dangling pointer" bugs (like giflib's `DGifDecreaseImageCounter`) actually double-free:

| Platform / allocator | realloc(p, 0) | reallocarray(ptr, 0) |
|---|---|---|
| glibc (Linux) | frees p, returns NULL | same (no special-case) |
| UCRT / MSVC (Windows) | frees p, returns NULL | same |
| scudo (Android ≥11, bionic default) | deallocates + returns NULL | bionic: plain realloc(ptr, n*m) |
| OpenBSD | unique zero-size protected pointer (NO free) | same |
| vendored shims (e.g. AOSP openbsd-reallocarray.c) | often `if (nmemb==0) return NULL` WITHOUT freeing | masks the bug |

A double-free/UAF via `if (new_ptr != NULL) ptr = new_ptr;` only fires where realloc(p,0) actually frees. Before concluding "bug does/doesn't reproduce", verify which semantic your build uses (compile a tiny probe, or read the shim source).

**Proving Android reachability without a device** (source-verifiable):
- bionic `libc/include/malloc.h`: reallocarray = `realloc(ptr, count*size)`, no zero special-case.
- scudo `standalone/wrappers_c.inc` realloc: `if (size == 0) { deallocate(ptr); return nullptr; }`.
- Android.bp `cflags` — check whether the vendored reallocarray shim is even built.

## 3. Build the harness

- `LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`; feed input via a memory-read callback stored in the library's user-data hook (giflib: `GifFileType->UserData` + `InputFunc`). Do NOT write to disk.
- **Compile C sources with `clang` (C mode), link with `clang++`** for the libFuzzer main:
  ```
  clang -O1 -g -fno-omit-frame-pointer -fsanitize=address,fuzzer-no-link -DHAVE_REALLOCARRAY -I lib -c lib/*.c
  clang++ -O1 -g -fno-omit-frame-pointer -fsanitize=address,fuzzer -I lib fuzz_entry.cpp *.o -o fuzz_asan
  ```
  Compiling .c with clang++ fails: `register` keyword (C++17), void*→char* assignments, const mismatches. `-fsanitize=fuzzer-no-link` instruments coverage without a main; the fuzzer main comes from the clang++ link.
- Compile ONLY the files on the decode/parse path. Utility programs in the tree have `main()` and break the link; encoder/utility-only files are dead weight.

## 4. Seed repro under ASAN

`mkdir corpus && cp trigger.bin corpus/ && ./fuzz_asan corpus/ -runs=1 -max_len=4096` → deterministic ASAN report with full stack (alloc site, freed-by site, SUMMARY line). Save the whole log.

## 4b. Severity triage: reached-UB vs executing fault (3 evidence layers)

A sanitizer hit proves UB is REACHED — it does NOT prove a fault executes.
Before claiming crash-class severity ("deterministic segfault on the target"),
stack three layers of evidence (worked example:
`references/libhevc-null-offset-verification.md`):

1. **Recover-mode UBSAN proves reach + full UB inventory.** Build the unpatched
   tree with plain `-fsanitize=undefined` (do NOT pass `-fno-sanitize-recover`),
   run with `UBSAN_OPTIONS=halt_on_error=0:print_stacktrace=1`, then
   `grep 'runtime error:' | sort | uniq -c` to enumerate ALL UB sites at once.
   **HALT-mode UBSAN dies on the FIRST hit and silently masks every later
   finding** — e.g. it can die on an early shift-UB (parse_residual.c:758) and
   never reach a more interesting NULL-deref site later in the same decode.
   Distinguish halt vs recover builds via `strings <bin> | grep __ubsan_handle`
   (`*_abort` variants = halt). Note: `_abort` handlers' Die() exits with code 1
   (not 134) on some clang versions — capture stderr text, don't trust exit code.

2. **ASAN build of the SAME tree proves fault-or-not.** If ASAN runs clean
   (exit 0, no report) where UBSAN fired, the bad access never executed.
   Control experiment: a bare `*(int*)0x400 = 1;` compiled with the same clang
   ASAN must produce DEADLYSIGNAL SEGV "zero page, WRITE access" — this proves
   the toolchain WOULD flag the access if it ran, so ASAN silence is meaningful
   (and rules out "ASAN just doesn't catch low-address writes").

3. **fprintf-instrumented diagnostic build proves WHICH pointer + WHICH branch.**
   Copy the tree (never patch the pristine one), add `fprintf(stderr, ...)` at
   function entry printing all pointer args + size/count args, and before each
   call site; rebuild just that one object and relink. This distinguishes
   "NULL-derived pointer computed but never dereferenced" (arithmetic-only UB —
   silent on real hardware, x86 AND ARM) from "NULL-derived pointer passed to a
   conversion/store" (executing fault). UBSAN's "applying non-zero offset N to
 null pointer" fires on pointer ARITHMETIC — that is not the same as the store
 executing. A NULL plane that the taken branch never touches is dead UB, not a
 crash. If the harness picks output config from input bytes (color format /
 cores / arch), mutate those bytes to force alternative branches and confirm
 the fault class is (or isn't) branch-dependent before writing the verdict.

 4. **Harness-artifact check FIRST — is the NULL buffer even a decoder state?**
 Fuzz harnesses allocate the app's output buffers in FORMAT-DEPENDENT counts,
 so NULL planes can exist BY DESIGN. AOSP `hevc_dec_fuzzer.cpp::allocFrame()`:
 420SP → `num_bufs=2` (Y + interleaved UV) → `bufs[2]` (V) is NEVER allocated;
 fmt_conv then receives `v_dst=NULL` on every 420SP input, and the
 "crash-class NULL write" turns out to be dead arithmetic for exactly that
 format. Read the harness's output-buffer allocation (the switch on color
 format) before attributing a NULL dst to a decoder bug. Real-world apps
 (Android mediaserver/gralloc) always supply complete buffer sets, so a
 harness-only NULL plane usually does not reproduce on the real target.

 5. **Custom allocators that return NULL can break the codec ENTIRELY — a clean
 exit then proves NOTHING.** Guard-page allocators that reject allocations
 not fitting one page (e.g. `size > 4096 → NULL`) reject the codec's main
 memtab (68 KB here) → create "succeeds" but every decode is a no-op
 (err=0x2015, nothing parses, headers never resolve). Running such a build
 and seeing "no crash" is vacuous. Aliveness check: a UB that fires
 RELIABLY in the working build (e.g. shift-UB at parse_residual.c:758) is a
 "codec is alive" beacon — its absence in a modified build proves the codec
 broke, not that the bug vanished. Debug-print create result, per-alloc
 size→result, and per-decode error codes to confirm the pipeline is live.

 6. **Compiler DCE asymmetry is a dead-value signature.** Windows clang-cl kept
 the UBSAN null check on a DEAD GEP (the check fires on the operands, so it
 survives even when the result is unused); Linux clang eliminated the dead
 computation AND its check — even at -O0, because LLVM backend
 dead-instruction elimination runs at every -O level. Consequences:
 (a) a UBSAN null-arithmetic panic is NOT evidence the value is live or
 stored; (b) a panic reproducing on one compiler/target but not another is a
 strong dead-value signal; (c) -O0 builds do NOT defeat this — verify which
 branch USES the pointer, not which branch computes it; (d) the plain build
 exiting 0 where UBSAN fired remains the decisive "no executing store"
 evidence (the Windows plain build exited 0 on the same triggers).

 7. **Isolate the check under test with null-only UBSAN:**
 `-fsanitize=null -fno-sanitize-recover=all` (optionally + ASAN). All-checks
 halt-mode builds are CONTAMINATED: earlier unrelated UBs (function-pointer
 type mismatch at ihevcd_inter_pred.c:417, shift-UB at parse_residual.c:758)
 halt the process before the site of interest, so "UBSAN didn't fire at
 fmt_conv" is meaningless in that build.

 8. **Reachability probes when the state won't reproduce single-shot** (all
 three give negative evidence when clean): (a) ASAN fuzz campaign — does any
 input execute the write? (b) null-only UBSAN fuzz campaign — is the
 arithmetic reachable at all? (c) sweep the ENTIRE prior corpus through the
 single-shot binary with a per-input timeout. Here: 669 ASAN runs + 952
 null-UBSAN runs + 1426-seed sweep, ZERO hits → the NULL-dst state is
 unreachable in this build. Use a SMALL curated corpus (triggers + real
 seeds) for quick campaigns — a 1400-file corpus dir makes `-runs=1` hang on
 corpus init (one slow seed) before fuzzing even starts.

 9. **Mine the original artifacts before theorizing.** The finding's own logs
 (`fuzz_hevc_log*.txt`) pin the exact panic line + source context
 (fmt_conv.c:782 = `pu1_v_dst_tmp = pu1_v_dst + (cur_row/2)*disp_strd/2`).
 Line-number discipline: patched vs unpatched trees differ by the patch's
 line count — reconstruct numbering from the reverted tree (`sed -n` on the
 unpatched copy); the original AOSP tree may differ from the local copy too.
 Also: later "guard allocator" builds in the audit dir may postdate the
 finding (their header comments say why) — check build chronology before
 assuming the original runs used them.

## 4c. Prove an OOB READ is ASAN-invisible — the bound-check patch probe

When a code-level OOB read (CWE-125) never fires ASAN (single-shot clean,
guard-page clean, crashes only under fuzzer-context heap dynamics), run this
experiment to decide FINAL whether the read is genuinely inside the target's
own padded allocation (undetectable by ASAN) or was only masked by the
harness. Worked example: `references/bounds-check-probe-uev-case.md`
(libavc ih264d_uev, verdict: NOT ASAN-detectable — final).

1. **Copy the tree** (`cp -r libavc libavc_patched`) and add a bounds check AT
   the read site: before the load that can read past valid data, test
   `u4_ofst + READ_BITS > u4_max_ofst` and early-return an error value
   (`return (UWORD32)-1;`). Grep the real struct first — e.g. libavc
   `dec_bit_stream_t { u4_ofst; pu4_buffer; u4_max_ofst; pv_codec_handle; }`
   (ih264d_bitstrm.h:57-63), `u4_max_ofst` = RBSP bit length (ih264d_nal.c:347).
2. **Expect raw-pointer functions** (not struct-takers): add the max offset as a
   NEW parameter, update the header prototype, and mechanically rewrite every
   call site (regex `fn(pu4_bitstrm_ofst, pu4_bitstrm_buf)` → append
   `, ps_bitstrm->u4_max_ofst`; ~65 sites in libavc). A few sites reach the
   struct through a different path (`ps_dec->ps_bitstrm` not `ps_bitstrm` in
   scope) — the compiler is the verifier: build, fix stragglers by name,
   rebuild.
3. **Fuzz the patched build ≥30 min** on a merged corpus (all prior campaigns'
   corpora + known crash triggers in a fresh dir).
   - ASAN fires heap-buffer-overflow READS → the read crosses the real
     allocation: capture inputs, replay through the UNPATCHED single-shot
     harness (`-fsanitize=address` WITHOUT `,fuzzer`, tiny main calling
     LLVMFuzzerTestOneInput) — a crash there upgrades the finding to
     deterministic.
   - Run clean (0 ASAN, 0 artifacts) → the read stays inside the decoder's own
     padded allocation (libavc: 256KB zeroed dynamic bitstream buffer +
     EXTRA_BS_OFFSET slack) — ASAN can never see it. Verdict FINAL: not
     ASAN-detectable; keep DoS-class severity, don't chase it further.
4. **Prove the check actually FIRED** (else the experiment is vacuous):
   - Unit probe, no gdb needed: compile the REAL patched .c + tiny main with
     `clang -ffunction-sections -fdata-sections` and link
     `-Wl,--gc-sections` → only the probed function survives the GC; call it
     with offsets that should fire/pass. ~10 s build vs 4 min full build.
   - Behavioral flip: known crash triggers that crashed the unpatched fuzzer
     must now decode cleanly on the patched build.
   - Final OOB-WRITE hunt: replay the campaign's NEW corpus units (identify via
     `comm -13 <pre-launch-name-set> <current-name-set>`) through the
     UNPATCHED single-shot harness (0/825 here).

## 5. Fuzz for ADDITIONAL bugs

- **Use `-fork=N` mode** — the parent survives child crashes, saves every artifact, keeps fuzzing. `-ignore_crashes` (and `-ignore_timeouts`) only apply in fork mode; semantics vary by clang version, so check `./fuzz_asan -help=1 | grep -i ignore` first. Non-fork mode dies on the first crash.
- **Seed corpus = known-crash seed + diverse VALID inputs.** A crash-only corpus keeps mutations in the crash neighborhood (low coverage). Generate valid inputs with a small Python writer (multi-frame, interlaced, local colormaps, extensions, transparent colors) — see `templates/gen_valid_seeds.py`.
- Flags: `-max_total_time=1800 -artifact_prefix=crash_ -max_len=8192 -timeout=10 -use_value_profile=1`, `ASAN_OPTIONS=abort_on_error=1:symbolize=1:detect_leaks=0`. Launch via nohup; poll the log.
- **Classify crashes without re-running thousands of artifacts** (each ASAN run is slow → paramiko timeouts): count distinct `ERROR: AddressSanitizer: <type>` lines in the fuzz log; `sha256sum crash_* | sort -k1,1 -u` to hash-dedupe; sample-run 5–12 unique ones and compare top frames. 100% one error type + identical frames = no new bugs.
- Report both: coverage delta (blocks/features), total execs, crash count, distinct classes, and the "no additional bugs found" verdict explicitly.

## 5b. Minimize a confirmed trigger (systematic + structural)

Once a crash is ASAN-proven, shrink the trigger to its floor — smaller triggers = better
disclosure. Three moves, in order (worked example: `references/giflib-minimization-case.md`,
52B → 24B):

1. **Structural floor analysis from source FIRST** (cheap, often decisive). Read the parser
   to find what it MUST consume before the buggy state is reached. giflib: `DGifGetImageDesc`
   only increments `ImageCount` AFTER the full 10-byte image descriptor parses (incl. the
   LZW-min byte read by `DGifSetupDecompress`), and the double-free needs `ImageCount` 1→0.
   ⇒ floor = magic(6; only the "GIF" prefix is validated) + screen-descriptor(7) + record
   byte(1) + full descriptor(10) = **24 bytes**; anything shorter can't reach the buggy call.
   Construct candidates AT the floor and ONE byte below it — the below-floor candidate NOT
   crashing is the empirical floor proof. Check what the magic/header validation actually
   checks (giflib: `strncmp(..., GIF_VERSION_POS=3)` → junk version bytes still parse).
2. **Systematic sweep, using the ASAN+libFuzzer binary itself as the oracle** (no separate
   harness): truncations `data[:N]` for every N; byte-removals `data[:i]+data[i+1:]` for
   every i; hand-constructed floor candidates (valid dims + truncated raster, width=0,
   huge dims, junk version…). Each variant → `mkdir c && cp v.bin c/ && ./fuzz_asan -runs=1 c/`
   with `ASAN_OPTIONS=abort_on_error=1:detect_leaks=0`; classify by exit code + marker
   ("attempting double-free"). ~150 variants ≈ 1–2 min.
3. **Run the sweep ON the remote box**, not per-input over SSH: upload ONE Python script
   (writes variants, loops subprocess, prints a results table), run it in a single
   `exec_command`, pull the table. Per-input SSH round-trips are the slow path and risk
   paramiko timeouts. Write the script to a file and upload — inline heredocs with nested
   quotes (e.g. a `run()` helper whose command string contains `"plain exit=$?"`) produce
   SyntaxErrors; a `.sh`/`.py` file avoids the whole class.

**Severity boundary testing (do before reporting):**
- Fully VALID inputs must NOT crash (control group). Generate with PIL/encoders; also grab
  the library's own test files (giflib `tests/wedge.gif`).
- Realistic attack shape = valid-looking input whose failure is in the FIRST unit. giflib
  rule: the double-free fires iff the FIRST image errors (ImageCount 1→0). Any single-frame
  GIF cut mid-raster crashes (test a valid file cut at 70/90% — 30/50% cuts are too short
  to complete the descriptor and DON'T crash); multi-frame GIFs cut AFTER frame 1 are SAFE
  (ImageCount N→N-1, realloc still works). Encode this boundary in the report — it defines
  which real-world inputs (truncated downloads, cut-off attachments) reach the bug.
- **Prove the native crash without sanitizers**: rebuild the same sources plain (tiny main
  feeding the file). glibc aborts `free(): double free detected in tcache 2`; ASAN + plain
  abort on the same input = allocator-independent proof (matches UCRT/Windows behavior).
- **Re-verify old crash artifacts against the CURRENT binary** before citing them — earlier
  runs may have used a different harness, and stale artifacts can mislead (here a 24-byte
  artifact with junk magic "GIFq.M" only crashes because giflib checks just the "GIF" prefix).

## 6. Remote orchestration via paramiko (Kali/VM targets)

See `templates/paramiko_phase.py` for a known-good skeleton. Lessons:
- Host fallback list + connect retries; credentials via constants.
- **`mkdir -p` the remote dir BEFORE `sftp.put`** — put to a missing dir fails `[Errno 2] No such file` (the local file is fine).
- Remote shell is often zsh on Kali: an unquoted glob with no matches (e.g. `rm crash3_*` on empty dir) ABORTS the whole command line. Quote globs or run `bash -c '...'`.
- Flaky network: tar bundles locally, one transfer per bundle, retry each put.
- Split work into phase scripts (upload+build / launch / poll / finalize+pull). A single SSH exec that loops over thousands of items (e.g. re-running 3000 artifacts) hits paramiko `PipeTimeout`.
- Long fuzz: `nohup ./fuzz_asan ... > fuzz.log 2>&1 & echo PID=$!`, then poll with a small script (`pgrep -fc`, last `^#` stats line, artifact count, distinct ASAN error types).
- **A paramiko `exec_command` timeout kills the LOCAL reader; the remote bash often keeps running** (no SIGHUP on channel teardown). Before re-running a long build, poll remote state with a fresh connection (object counts, `pgrep -af`, binary mtime) — the build may already be done or nearly done. Blindly re-running restarts a 15-min compile.
- Always pull evidence logs/artifacts back locally.

## 7. Evidence handling

Save locally: seed-repro ASAN log, full fuzz log, a few artifacts, the corpus, the harness, the verified source file. Append a dated section to the finding doc with exact build commands, the SUMMARY line, the crash taxonomy, and the Android-reachability source citations (bionic malloc.h + scudo wrappers_c.inc).

## Pitfalls checklist

- [ ] Mirrored Android.bp/target build config (flags AND file list), not the tree Makefile
- [ ] Verified realloc(p,0) semantics of the actual libc/shim in use
- [ ] C files via clang, link via clang++ (fuzzer-no-link on the C step)
- [ ] Excluded utility mains from the compile set
- [ ] `-ignore_crashes` confirmed to exist for this clang (fork mode)
- [ ] Diverse valid seeds in corpus, not just the crash trigger
- [ ] Artifact dedupe from log + hash, not by re-running everything
- [ ] Remote: mkdir before sftp.put; zsh globs quoted; nohup + poll; phases split
- [ ] Exec timeout kills local reader only — poll remote state before re-running long builds
- [ ] AOSP/Android trees are CRLF — normalize `\r\n` before sed/grep/patch anchors or they silently miss
- [ ] Verified the built binary actually contains the intended sanitizer (`strings | grep -m1 __asan_init` for ASAN, `__ubsan_handle_*` for UBSAN; tiny-main `usage:` string present)
- [ ] Severity: recovered full UB inventory (recover-mode UBSAN), ASAN-clean proof, diagnostic build pinned WHICH pointer/branch — reached-UB ≠ executing fault
- [ ] Severity: harness output-buffer allocation checked for format-dependent NULL planes (harness artifact vs decoder state); real-target buffer semantics (gralloc/mediaserver) considered
- [ ] Severity: custom-allocator builds verified codec-alive (beacon UB still fires / create+decode debug prints) — clean exit under a broken allocator proves nothing
- [ ] Severity: UBSAN null panic verified as LIVE computation (the taken branch USES the pointer), not a dead GEP — compiler DCE asymmetry (Windows fires / Linux DCEs at -O0) is a dead-value signal
- [ ] Severity: null-only UBSAN (`-fsanitize=null -fno-sanitize-recover=all`) used to isolate the check from earlier unrelated UBs; fuzz-campaign + corpus-sweep reachability probes run when single-shot won't reproduce
- [ ] OOB-read ASAN blind spot proven FINAL via bound-check patch probe (§4c): patched build ≥30-min fuzz clean, check-fires proven (gc-sections unit probe / behavioral flip of known triggers), new-corpus replay sweep for WRITES clean
- [ ] Payloads byte-verified after transfer (sha256sum local vs remote)
- [ ] Minimization: structural floor derived from source; below-floor candidate tested and clean (floor proven)
- [ ] Minimization: fully-valid control inputs clean; realistic truncated-valid shape (first-unit failure) tested
- [ ] Minimization: plain non-ASAN build aborts natively (allocator-independent proof)
- [ ] Minimization: old crash artifacts re-verified against the current binary before citing

Support files:
- `references/bounds-check-probe-uev-case.md` — worked example of §4c: libavc ih264d_uev bound-check patch probe. Real struct/field names, exact diff, 65 call-site rewrite (incl. the `ps_dec->ps_bitstrm` stragglers), build recipe deltas, 30-min campaign stats (21,059 execs, 1014 new units, 0 ASAN), gc-sections unit-probe outputs, 825-unit unpatched replay sweep — verdict FINAL not-ASAN-detectable
- `references/giflib-doublefree-case.md` — full worked example (AOSP giflib double-free, exact commands, stacks, scudo source lines)
- `references/giflib-minimization-case.md` — worked example of §5b: 52B → 24B floor, sweep design, valid-vs-truncated severity matrix, plain-build proof
- `references/libhevc-null-offset-verification.md` — worked example of §4b: 3-layer severity triage (recover-UBSAN vs ASAN-clean vs diagnostic build) that downgraded a NULL+offset finding from crash-class to arithmetic-only UB; libhevc harness control-byte map. Includes the root-cause epilogue: the NULL V-plane is a harness allocFrame artifact (420SP allocates 2 buffers), the custom-allocator trap, and the compiler-DCE asymmetry that explains the Windows-only panic
- `templates/fuzz_entry.cpp` — libFuzzer harness with memory-reader callback
- `templates/gen_valid_seeds.py` — generates diverse valid GIF seeds (adapt for other formats)
- `templates/paramiko_phase.py` — paramiko connect/exec/sftp skeleton with retries and host fallback
