---
name: libfuzzer-asan-fuzzing
description: Use when fuzzing C/C++ libraries with ASAN+libFuzzer.
---

# ASAN + libFuzzer fuzzing of C/C++ libraries

Build and run libFuzzer+ASAN fuzzers for C/C++ libraries (video converters, codecs, parsers), including the common case of running the campaign on a remote Linux VM (Kali etc.) driven over paramiko SSH from Windows. Goal is usually OOB read/write discovery in bug classes like stride/dimension mismatch (e.g. libyuv CVE-2017-13189 family).

## Workflow

1. **Get the source** — check the layout first (`ls`), then tar only the needed dirs (typically `source/` + `include/`) into ONE tarball, SFTP it, extract on the target. Keep the tarball path where both sides can see it (see pitfall: git-bash `/tmp`).

2. **Check the target CPU's SIMD flags BEFORE choosing build flags** (on the VM):
   `grep -m1 '^flags' /proc/cpuinfo | tr ' ' '\n' | grep -E '^(sse2|ssse3|sse4_1|avx|avx2)$' | sort -u`
   This decides the whole build. See the `-mavx2` SIGILL pitfall below.

3. **Write the harness** — `extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size)`.
   - Header bytes → dimensions, clamped to a small range (`(rd32(data) % 255) + 2` gives uniform 2..256 coverage; a plain clamp makes everything 256).
   - Require `size >= header + exact plane bytes`; return 0 otherwise.
   - All dst buffers `malloc`'d to EXACTLY the size the library is told (via the strides you pass) → any over-write trips ASAN as a genuine library bug.
   - Read src planes from the input buffer itself — over-reads past the input hit the ASAN redzone.
   - Exercise the bug surface: odd dimensions, multiple conversion directions, scale paths with several factors and filter modes, plus a padded-stride variant.

4. **Verify libFuzzer runtime** before the real build: compile a `main(){return 0;}` with `-fsanitize=fuzzer,address`. Expected: link error `undefined reference to LLVMFuzzerTestOneInput` + `multiple definition of main` — that error MEANS the fuzzer runtime is present and working.

5. **Build** (template, adjust flags per step 2):
   `clang++ -O1 -g -fsanitize=address,fuzzer -fno-omit-frame-pointer -msse4.1 -I <lib>/include fuzz_entry.cpp <lib>/source/*.cc -o fuzz_asan`
   Glob-compiling `source/*.cc` works for libraries whose arch-specific files are `#if defined(__ARM_NEON__)`-style guarded (they become empty TUs on x86_64) and whose optional deps (libjpeg etc.) are `#ifdef HAVE_JPEG`-guarded.

6. **Seeds** — generate with python; size must match the harness's EXACT byte consumption, not a naive formula (e.g. I420 with header w/h needs `8 + w*h + 2*((w+1)/2)*((h+1)/2)` bytes — odd dims need more than `1.5*w*h`). Any random bytes work when dims come from the header.

7. **Smoke test 20-30s** against the seed dir before committing to the long run — catches SIGILL/build/seed-size issues instantly.

8. **Launch** (long campaign):
   `cd ~/fuzz && nohup timeout 3600 ./fuzz_asan seeds/ -max_len=100000 -timeout=10 -rss_limit_mb=3000 -artifact_prefix=fuzz_ > fuzz.log 2>&1 &`
   `timeout 3600` guarantees auto-kill; `-artifact_prefix` names crash files for SFTP back.

9. **Poll**: `ps aux | grep -v grep | grep fuzz_asan` (check alive + CPU%) and `tail -5 fuzz.log` (exec/s, cov, ft, rss) and `ls fuzz_crash-*` for artifacts. A few polls over 10 min is a reasonable checkpoint.

## Multi-arch C codebases (libvpx, dav1d, etc.)

Codebases with per-arch subdirs (`vp9/common/arm`, `vpx_dsp/x86`, ...) plus a GENERATED
generic config need a different build shape than the all-`.cc` glob above:

- **Read the config BEFORE choosing flags.** `config/generic/vpx_config.h` tells all:
  `VPX_ARCH_X86 0` + `CONFIG_RUNTIME_CPU_DETECT 0` means pure-C build — RTCD maps every
  dispatch to `_c` functions, `-msse4.1` is harmless-but-unused, and the `*_rtcd.c`
  files in the source tree (NOT the config dir) are the real definitions. The configure
  string is embedded in `vpx_config.c` (`vpx_codec_build_config`), e.g.
  `--enable-realtime-only --size-limit=4096x3072 --enable-vp9-highbitdepth`.
- **Compile only top-level `*.c`** — `find <dir> <dir> ... -maxdepth 1 -name '*.c'` skips
  arch subdirs that need asm/config the generic build lacks. Compile C files with
  `clang -fsanitize=fuzzer-no-link` in parallel batches (`&` + `wait` every N cores),
  link with `clang++ -fsanitize=fuzzer` + the C++ harness. (C files must NOT go through
  clang++ — it treats them as C++.)
- **Exclude non-host `*_cpudetect.c`** — `aarch32_cpudetect.c` + `aarch64_cpudetect.c`
  BOTH define `arm_cpu_caps` → duplicate symbol at link. Drop all of
  `aarch32|aarch64|loongarch|mips|ppc` on x86.
- **Undefined symbol → grep the tree.** `vp8_machine_specific_config` lived in
  `vp8/common/generic/systemdependent.c`, a subdir the `-maxdepth 1` find skipped.
  `grep -rln '<symbol>' <tree>/` finds the defining file; add it explicitly to SRCS.
- **CONFIG-gated files fail to compile — safe to drop when off-path.** With
  `CONFIG_POSTPROC=0 CONFIG_VP9_POSTPROC=0`: `vp9_mfqe.c`, `vp8/common/mfqe.c`
  (`no member named 'post_proc_buffer'`), `vp8/decoder/error_concealment.c`
  (`no member 'overlaps'/'prev_mi'`) all error — they are postproc/error-concealment
  only, never on the VP9 decode path, and the link stays clean without them. Same for
  x86-only/encoder metrics (`vpx_dsp/ssim.c`, `vpx_ports/emms_mmx.c`).
- **Resuming a half-dead build: verify referenced files exist.** A prior build script
  linked `libvpx/examples/vpx_dec_fuzzer.cc` but `examples/` was NOT in the shipped
  bundle subset → link dies with "No such file". Check non-glob references in the
  script exist before re-running it; if not, write your own harness.

## Pitfalls

- **Parallel build can fail silently despite "compiled N" echo.** A `for f; do clang ... & wait every 8; done` loop with `set -e` may lose failed TUs (4 of 107 files errored here, yet the script printed "compiled 107"). Always cross-check `ls obj/*.o | wc -l` against the source count and grep the build log for `error:`; confirm each failed file is genuinely off-path (postproc/encoder/metrics) before trusting the link.

- **Smoke-testing INTO the seed dir enriches the real corpus.** Running the fuzzer with `-runs=200 <seeddir>/` writes NEW corpus entries back into the seed dir (4 seeds → 91 files) — a free corpus upgrade for the long campaign that follows.

- **`-mavx2` (or `-mavx`) on a CPU without AVX2 → SIGILL on first execution.** clang emits AVX2 instructions into GENERIC TUs (macros, row wrappers, scalar loops), not just the intrinsics files. Symptom: libFuzzer `ERROR: libFuzzer: deadly signal` in a SIMD-named function during seed loading, with NO ASAN report (SIGILL is not a memory error). Diagnosis: check `/proc/cpuinfo` flags. Fix: build with `-msse4.1` (SSSE3+SSE4.1 intrinsics still compile and get used via runtime CPU detection), or apply `-mavx2` per-file ONLY to the intrinsics TUs (`*_gcc.cc`), never globally. Distinguish "deadly signal" (build/CPU problem) from a real ASAN `heap-buffer-overflow` report (actual finding).

- **Harness-induced false positives kill the fuzz.** Passing strides inconsistent with the actual allocation (e.g. chroma stride = full width against a minimal 1.5·w·h I420 layout) guarantees an OOB read on EVERY input — fuzzer "finds a bug" on input #1 and the campaign is dead noise. The library isn't at fault; the harness lied about the layout. To exercise a stride-mismatch surface meaningfully, size the planes consistently with the strides you pass (padded chroma layout), so any ASAN hit is a genuine library bug.

- **Namespaces**: libyuv wraps its whole API in `namespace libyuv` — add `using namespace libyuv;` after `#include "libyuv.h"` or every call fails to compile with "use of undeclared identifier... did you mean libyuv::".

- **git-bash/MSYS paths are invisible to Windows-native python** (paramiko `sftp.put`/`sftp.get`). `/tmp` files AND `/c/Users/...` paths must be referenced by their real Windows path — `cygpath -w /tmp/foo.tgz` → `C:\Users\<user>\AppData\Local\Temp\foo.tgz`, or pass `C:\Users\...` style directly (paramiko `sftp.get` throws `FileNotFoundError` on a `/c/...` local path). Same trap for any Windows tool (python, node) called from git-bash.

- **A "hit" during seed loading ≠ discovery.** `I422ToARGBRow_Any_SSSE3`-style crashes while `ReadAndExecuteSeedCorpora` runs are usually the SIGILL above; reproduce the artifact with `./fuzz_asan <artifact>` and read whether ASAN printed a report before concluding.

- **Coverage plateau is normal.** A recent upstream lib (e.g. 2025 libyuv) may be clean in the classic bug class — report "no hits, N M execs, coverage plateaued" honestly rather than stretching for a finding.

- **A per-input timeout ABORTS the whole campaign.** libFuzzer does not skip slow inputs — one input exceeding `-timeout` ends the run (`SUMMARY: libFuzzer: timeout`, a `timeout-<hash>` artifact, exit). Bound per-input WORK, not just memory. Classic case: JPEG dims. `scale_denom`/scaling only shrinks the OUTPUT buffer — entropy-decode/IDCT work stays full-resolution, so a mutated header claiming 65535×65535 makes the decoder grind ~119M MCU blocks → 10s timeout → campaign death. Fix: hard-REJECT oversized inputs (return 0 before start_decompress; cap ~4096) — all interesting decoder paths are exercised at small dims. Distinguish `timeout-*` artifacts (perf; run-killing) from `crash-*` (findings); a missing process + log tail `SUMMARY: libFuzzer: timeout` is this, not an ASAN hit.

- **Custom source manager + single-fill `skip_input_data` = fake `global-buffer-overflow`.** Old jpeg trees (AOSP) have no `jpeg_mem_src`; harnesses feed input via a custom `jpeg_source_mgr` with a static `JOCTET eoi[2] = {0xFF,0xD9}` EOF-fallback global. A single-fill skip_input_data (fill once, then subtract the remaining num_bytes from the fresh 2-byte buffer) underflows `bytes_in_buffer` (size_t) and walks `next_input_byte` past the array. ASAN then reports `global-buffer-overflow` READ of size 1 in `next_marker()` at `jpeg_finish_decompress` — a HARNESS bug (the only global in the read path is your eoi array), not a library finding. Use the standard IJG loop: `while (num_bytes > (long)bytes_in_buffer) { num_bytes -= bytes_in_buffer; fill_input_buffer(cinfo); }`. Diagnosis shortcut: `f9` shadow (global redzone) + address near a static you own = yours; re-run the artifact after the fix — clean exit proves it.

- **C libraries compiled as C++ need `-std=gnu++14`** (or older): `register` is an ERROR in C++17 and IJG jpeg is full of it. Expect a few genuine C++ incompatibilities too (AOSP jdphuff.c tile-decode code: `index->scan = realloc(...)` → needs `(huffman_scan_header*)` cast; missing `#include <stdio.h>` in the harness → `unknown type name 'FILE'` from jpeglib.h). Apply casts via sed INSIDE the build script, and make extraction CONDITIONAL (`if [ ! -f jpeg/jpeglib.h ]; then tar xzf ...; sed ...; fi`) — re-running `tar xzf` clobbers the patch on every rebuild iteration (classic "same error after fix").

- **Glob-compiling `lib/*.c` pulls in app mains.** `cjpeg.c`/`djpeg.c`/`example.c` have `main()` → `multiple definition of main` with libFuzzer's. Build an explicit decode-only file list; add encoder files only when the linker complains (e.g. `jcapimin.c` in the list → needs `jcmarker.c` for `jinit_marker_writer`).

- **Remote shell is zsh (Kali)** — unquoted `===` echo separators in ssh one-liners get globbed (`zsh:1: == not found`); quote them. And **poll in short windows** (sleep ≤ ~150s per poll) — long sleeps hit the terminal-tool timeout mid-command and SSH occasionally hangs; split into several polls and retry once.

## Support files

- `references/libyuv-i420-fuzzer-session.md` — full worked example: exact commands, build flags, seeds recipe, SIGILL debug path, status numbers.
- `references/libvpx-vp9-fuzzer-session.md` — libvpx VP8/VP9 decoder campaign: multi-arch source list, link-error fixes (cpudetect dupes, systemdependent.c), resume-state checklist, status numbers.
- `references/jpeg-aosp-fuzzer-session.md` — AOSP libjpeg-turbo decoder campaign: decode-only file list, C++-compat fixes, dims-cap rationale, fake-crash + timeout diagnoses, seeds recipe, status numbers.
- `templates/fuzz_entry_i420.cpp` — known-good libyuv I420/ARGB/Scale harness to copy and adapt for other formats/libraries.
- `templates/fuzz_entry_ivf_vpx.cpp` — known-good libvpx IVF harness (32B file header + 12B frame headers + decode loop + `get_frame` drain) for VP8/VP9-family codecs.
- `templates/fuzz_jpeg_entry.cpp` — known-good jpeg decode harness: custom source manager (old trees lack jpeg_mem_src) with the IJG-loop skip_input_data, setjmp/longjmp error exit, 4096 dims cap.
