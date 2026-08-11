---
name: aarch64-qemu-verification
description: "Use when verifying fault/UB claims via qemu-aarch64."
---

# aarch64 / qemu verification of arch-dependent findings

When an audit or fuzz finding claims a crash (or different behavior) on ARM/Android, VERIFY it on real aarch64 semantics before reporting severity. x86 results do not transfer — but neither do naive "ARM faults on everything unaligned" assumptions.

## Core facts (verified 2026-08-09: qemu-aarch64 11.0.1, aarch64-linux-gnu-gcc 15, Kali VM)
- **Unaligned 32-bit loads DO NOT fault on aarch64 Linux userspace.** Micro-repro: `*(uint32_t*)(buf + off)` for off=0..7 on a heap byte buffer — all load correctly (little-endian), rc=0, no SIGBUS. AArch64 userspace runs with SCTLR.A=0 (alignment check off); unaligned access to normal memory is architecturally permitted. qemu-user faithfully matches real Linux/Android arm64 behavior here.
- **Therefore "misaligned load = alignment fault on ARM" is usually WRONG for Linux/Android arm64** (and ARM32 with SCTLR.A=0). Such findings stay UB-class (UBSAN-detectable), NOT crash-class. Alignment faults on ARM64 need SCTLR.A=1 (non-default embedded kernels), device/strongly-ordered memory, or exclusive/atomic ops.
- **NULL-deref / NULL+offset writes DO fault on ARM** (translation fault), same crash-class as x86 segfault. A real NULL write is a hard crash on Android mediaserver.
- UBSAN misaligned-load reports on x86 builds prove the load EXECUTES — they do not prove it crashes on ARM. Run the ARM build to find out.

## Workflow
1. **VM access (Windows host, paramiko in execute_code):** read SUDO_PASSWORD from `C:\Users\HP\AppData\Local\hermes\.env` inside the script, never print it; retry connect 3x with ~8s timeouts; try primary IP then fallback (e.g. 192.168.29.35 → 192.168.56.101). paramiko 5.x ships in the Hermes venv.
2. **Toolchain:** `echo "$PW" | sudo -S apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu` — the g++ cross package is separate and needed for C++ harnesses; `libubsan.a` for aarch64 ships with it. qemu-user: `qemu-aarch64`.
3. **Micro-repro first** (minutes, conclusive for pure semantics questions): see `templates/unaligned_microrepro.c`; compile `aarch64-linux-gnu-gcc -static -O1`, run `qemu-aarch64 ./a.out`. Record rc + output for every offset.
4. **Full project cross-build:** compile every `.c` with `aarch64-linux-gnu-gcc`, every `.cpp` with `aarch64-linux-gnu-g++`, link `-static ... -lpthread`; write a tiny `main.cpp` that reads the seed file and calls the harness symbol (`LLVMFuzzerTestOneInput`). `file(1)` the binary to confirm `ELF ... ARM aarch64`.
5. **UBSAN-on-ARM proof (the killer technique):** rebuild ONLY the target `.c` with `-fsanitize=undefined -fno-sanitize-recover=all`, relink (excluding the old object), run the real seed under qemu. The UBSAN "runtime error" line proves the buggy statement executes on ARM; the plain build's rc=0 proves the hardware tolerates it. This converts a severity guess into an evidence-backed verdict.
6. Run EVERY seed; capture `file` output, stdout, rc. Report the exact qemu + gcc versions.

## Pitfalls
- **zsh on the Kali VM:** `echo ===X===` gets glob/`=cmd`-expanded (breaks markers); unquoted `$VAR` does NOT word-split in zsh (a multi-flag variable becomes ONE `-I...` blob). Wrap multi-variable commands in `bash -c '...'`.
- **execute_code 5-min cap:** long apt/builds must run via `nohup ... &` on the VM, then poll the log file from later calls. Never block a 60-file compile inline.
- **Mangled sources:** files previously written via heredoc may contain CRLF/literal-escape corruption (e.g. `\n` inside a printf string) — rewrite via SFTP instead of sed.
- **Missing arch-dispatch symbols:** big C projects use arch dispatcher functions (e.g. `ihevcd_init_arch`, `ihevcd_init_function_ptr`) defined only in arch-specific dirs. Write a small shim routing them to the generic implementation rather than compiling the x86/NEON dispatchers.
- **Static link** keeps qemu runs independent of guest libraries and avoids qemu dynamic-loader surprises.
- Header include ORDER matters in Ittiam-style code: type-def headers (`ihevc_typedefs.h`, `iv.h`, `ivd.h`) must precede selector headers that use their types.

## References
- `references/libhevc-aarch64-crossbuild.md` — full recipe for cross-building the Ittiam libhevc (AOSP HEVC decoder) for aarch64: arch-selector structure, shim code, harness wiring, include flags, results.
- `templates/unaligned_microrepro.c` — the canonical unaligned-32-bit-load micro-repro (off 0..7, prints values).
