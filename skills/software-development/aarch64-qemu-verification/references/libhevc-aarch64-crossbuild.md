# libhevc (AOSP HEVC decoder) aarch64 cross-build — full recipe

Session: 2026-08-09, Kali VM (x86_64 host), qemu-aarch64 11.0.1, aarch64-linux-gnu-gcc/g++ 15. Goal: verify whether the documented misaligned-load finding (ihevcd_process_slice.c:1069) faults on real ARM semantics. **Result: it does NOT fault — unaligned loads are tolerated on aarch64 Linux; the finding is UB-class, not crash-class.**

## Tree layout (relevant parts)
```
libhevc/
  decoder/*.c            (27 files, plain C)
  decoder/x86/           ihevcd_function_selector.c (x86 dispatcher), ..._generic.c, ..._ssse3.c, ..._sse42.c, + x86 intr kernels
  decoder/arm/           ihevcd_function_selector.c (ARM32 dispatcher), _noneon.c, _a9q.c
  decoder/arm64/         ihevcd_function_selector_av8.c  (NEON path)
  decoder/riscv64/       ihevcd_function_selector.c      (generic-only pattern — the template to copy)
  common/*.c             (33 files, plain C)
  common/{x86,arm,arm64,riscv64}/   ihevc_func_selector.h per arch; arm64/ holds ~70 NEON .s files
  fuzzer/hevc_dec_fuzzer.cpp        (AOSP harness, LLVMFuzzerTestOneInput at line 374, NO main)
  common/ihevc_typedefs.h, iv.h, ivd.h, ihevc_defs.h, ihevcd_defs.h, ihevcd_function_selector.h ...
```

## Arch-selector mechanics (critical to understand before building)
- Decoder calls `ihevcd_init_arch(ps_codec)` and `ihevcd_init_function_ptr(ps_codec)` (ihevcd_api.c:1125/1127 and 3461). These two symbols are defined ONLY in per-arch dispatchers.
- The riscv64 selector is the minimal pattern: `ihevcd_init_function_ptr` switches on `ps_codec->e_processor_arch` and calls `ihevcd_init_function_ptr_generic`; `ihevcd_init_arch` just sets `ps_codec->e_processor_arch = ARCH_RISCV64_GENERIC`.
- Generic (plain-C) kernels: `decoder/x86/ihevcd_function_selector_generic.c` + `common/x86/ihevc_func_selector.h` (every kernel macro = `C`). The plain-C kernel names (e.g. `ihevc_deblk_chroma_horz`) exist in common/*.c.
- arm64 NEON path (ihevcd_function_selector_av8.c) needs ~70 common/arm64/*.s assembly files — skip unless you must benchmark NEON. The generic path executes the IDENTICAL C source for the buggy statement, which is all a fault-semantics test needs.

## Arch shim (replaces x86 dispatcher; compile with gcc)
```c
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include "ihevc_typedefs.h"
#include "iv.h"
#include "ivd.h"
#include "ihevc_defs.h"
#include "ihevc_debug.h"
#include "ihevc_structs.h"
#include "ihevc_macros.h"
#include "ihevc_platform_macros.h"
#include "ihevc_cabac_tables.h"
#include "ihevc_disp_mgr.h"
#include "ihevc_buf_mgr.h"
#include "ihevc_dpb_mgr.h"
#include "ihevc_error.h"
#include "ihevcd_defs.h"
#include "ihevcd_function_selector.h"
#include "ihevcd_structs.h"

void ihevcd_init_function_ptr(void *pv_codec)
{
    codec_t *ps_codec = (codec_t *)pv_codec;
    switch(ps_codec->e_processor_arch)
    {
        default:
        case ARCH_ARMV8_GENERIC:
        case ARCH_ARM_NEONINTR:
        case ARCH_ARM_A9Q:
        case ARCH_ARM_NONEON:
        case ARCH_X86_GENERIC:
        case ARCH_X86_SSSE3:
        case ARCH_X86_SSE42:
            ihevcd_init_function_ptr_generic(pv_codec);
    }
}
void ihevcd_init_arch(void *pv_codec)
{
    codec_t *ps_codec = (codec_t *)pv_codec;
    ps_codec->e_processor_arch = ARCH_ARMV8_GENERIC;
}
```
Include-order pitfall: `ihevcd_function_selector.h` pulls in `ihevc_deblk.h` which uses UWORD8/WORD32 — the typedef headers MUST come first (mirror the riscv64 selector's include list exactly).

## main.cpp (feeds a seed file to the harness)
```cpp
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);
int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s <file>\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("fopen"); return 2; }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    std::vector<uint8_t> buf((size_t)n);
    if (fread(buf.data(), 1, (size_t)n, f) != (size_t)n) { perror("fread"); return 2; }
    fclose(f);
    int r = LLVMFuzzerTestOneInput(buf.data(), buf.size());
    printf("decode done, rc=%d\n", r);
    return r;
}
```

## Build commands
```bash
INC="-I../libhevc -I../libhevc/decoder -I../libhevc/common -I../libhevc/common/x86 -I../libhevc/decoder/x86 -I../libhevc/fuzzer"
# C files (decoder/*.c, common/*.c, decoder/x86/ihevcd_function_selector_generic.c, arch shim):
aarch64-linux-gnu-gcc -O1 -fno-strict-aliasing $INC -c <file>.c -o <file>.o
# C++ harness + main:
aarch64-linux-gnu-g++ -O1 -fno-strict-aliasing $INC -c hevc_dec_fuzzer.cpp -o hevc_dec_fuzzer.o
aarch64-linux-gnu-g++ -O1 -fno-strict-aliasing $INC -c main.cpp -o main.o
# Link:
aarch64-linux-gnu-g++ -static -O1 -o hevc_dec_arm *.o -lpthread
```
Run: `qemu-aarch64 ./hevc_dec_arm seed.h265`. Harness quirk: input byte[6]=colorFormat, byte[7]=numCores, byte[8]=arch — real seeds still work (arch selection is harmless because every arch routes to generic).

## UBSAN-on-ARM proof (only the target file instrumented)
```bash
aarch64-linux-gnu-gcc -O1 -fno-strict-aliasing -fsanitize=undefined -fno-sanitize-recover=all $INC -c ../libhevc/decoder/ihevcd_process_slice.c -o ihevcd_process_slice_ubsan.o
# relink with that object REPLACING the plain one (exclude both the plain .o and any backup .o):
aarch64-linux-gnu-g++ -static -O1 -fsanitize=undefined -o hevc_dec_arm_ubsan $(ls *.o | grep -v -e 'ihevcd_process_slice.o$' -e 'ihevcd_process_slice_plain.o' | tr '\n' ' ') -lpthread
qemu-aarch64 ./hevc_dec_arm_ubsan seeds_hevc/hevc_352x288.h265
```
Observed output (proves the buggy line executes on ARM):
```
ihevcd_process_slice.c:1069:87: runtime error: load of misaligned address 0x... for type 'UWORD32', which requires 4 byte alignment
```
(rc=1 = UBSAN abort, NOT an ARM alignment fault — the plain build decodes the same seed to rc=0.)

## Results (2026-08-09)
- Micro-repro `misaligned.c` (off 0..7): all loads succeed, rc=0 — no SIGBUS on aarch64/qemu.
- Full decoder build: linked, 1.4 MB static; seeds hevc_352x288/176x144/640x360/64x64/bars_128x96 ALL decode rc=0.
- Verdict: misaligned 32-bit load is UB (UBSAN-detectable) but tolerated on ARM64 Linux — finding severity downgraded from crash-class to hygiene-level. NULL+offset writes (fmt_conv) remain crash-class on ARM (translation fault).
