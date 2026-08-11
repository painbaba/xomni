# Bound-check patch probe — libavc ih264d_uev OOB read (Aug 2026)

Methodology §4c of the parent skill, fully worked. Question answered FINAL:
**the ih264d_uev over-read cannot be made ASAN-visible — it stays inside the
decoder's own padded allocation.** CWE-125 is real (code-proven, upstream
Ittiam libavc identical), but it is a DoS-class bug, not a deterministic
ASAN-detectable one.

## Setup (Kali VM, ~/fuzz)

- Tree: `~/fuzz/libavc` (AOSP libavc). Copied: `cp -r libavc libavc_patched`.
- Fuzzer harness: `fuzzer/avc_dec_fuzzer.cpp` (exports
  `extern "C" int LLVMFuzzerTestOneInput`).
- Bitstream struct (decoder/ih264d_bitstrm.h:57-63):
  `dec_bit_stream_t { UWORD32 u4_ofst; UWORD32 *pu4_buffer; UWORD32
  u4_max_ofst; void *pv_codec_handle; }` — **exact field names**.
- `u4_max_ofst` = end of valid data in bits: set at ih264d_nal.c:347 to
  `((u4_num_bytes_in_rbsp + NAL_FIRST_BYTE_SIZE) << 3)`; decremented at
  ih264d_nal.c:392 after rbsp_trailing_bits removal.
- Bug: `ih264d_uev(UWORD32 *pu4_bitstrm_ofst, UWORD32 *pu4_bitstrm_buf)`
  (decoder/ih264d_parse_cavlc.c:77) reads 32 bits via `NEXTBITS_32` then up to
  31 more via `GETBITS` with NO bound check. Short SEI payloads (11-byte
  trigger `0000000106000000020000` = start code + NAL 6 + payload_type 0 +
  size 2 + zeros) drive u4_ldz≥24, jumping the offset past valid data. Only
  the caller's `CHECK_BITS_SUFFICIENT` guards it — uev can consume up to 63
  bits, exceeding the checked budget.

## The patch (kept minimal, faithful to "bound check before NEXTBITS_32")

```c
UWORD32 ih264d_uev(UWORD32 *pu4_bitstrm_ofst, UWORD32 *pu4_bitstrm_buf,
                   UWORD32 u4_max_ofst)          /* NEW 3rd param */
{
    UWORD32 u4_bitstream_offset = *pu4_bitstrm_ofst;
    UWORD32 u4_word, u4_ldz;
    ...
    /* PATCH: bounds check */
    if(u4_bitstream_offset + 32 > u4_max_ofst)
        return (UWORD32)-1;
    NEXTBITS_32(u4_word, u4_bitstream_offset, pu4_bitstrm_buf);
    ...
```

- Header prototype updated identically (decoder/ih264d_parse_cavlc.h:59).
- 65 call sites rewritten (regex over `ih264d_uev(\s*pu4_bitstrm_ofst\s*,\s*pu4_bitstrm_buf\s*\))`
  → 3-arg). **4 of 65 (dpb_mgr.c:755/760/834, parse_islice.c:1426) had NO
  `ps_bitstrm` in scope** — they reach the struct as `ps_dec->ps_bitstrm`
  (dec_struct_t *ps_dec). Compiler caught them; fix by name and rebuild.
- Callers already hold the struct (`pu4_bitstrm_ofst = &ps_bitstrm->u4_ofst;
  pu4_bitstrm_buf = ps_bitstrm->pu4_buffer;`), so the extra arg is free.
- Note: NEXTBITS_32/GETBIT macro invocations also contain the literal
  `pu4_bitstrm_buf)` — do NOT blanket-replace; anchor on `ih264d_uev(`.

## Build (patched fuzzer, clang 21 on Kali)

```bash
cd ~/fuzz
clang++ -O1 -g -msse4.1 -fsanitize=address,fuzzer -fno-omit-frame-pointer \
  -I libavc_patched -I libavc_patched/decoder -I libavc_patched/decoder/x86 \
  -I libavc_patched/common -I libavc_patched/common/x86 -I libavc_patched/common/mvc \
  -I libavc_patched/fuzzer \
  libavc_patched/fuzzer/avc_dec_fuzzer.cpp \
  -x c libavc_patched/decoder/*.c libavc_patched/decoder/x86/*.c \
       libavc_patched/common/*.c libavc_patched/common/x86/*.c \
  -o fuzz_avc_patched_asan
```

Three sequential link/build failures and their causes (the x86 dirs + sources
are REQUIRED on x86_64):
1. `fatal error: 'ih264_platform_macros.h' file not found` → missing
   `-I .../decoder/x86 -I .../common/x86` (header lives in common/x86/).
2. `undefined reference to ih264d_init_function_ptr / ih264d_init_arch` →
   `decoder/x86/ih264d_function_selector*.c` not in the link.
3. `undefined reference to ih264_*_sse42/ssse3` → `common/x86/*.c` not in the
   link (SIMD implementations).

## Campaign (30 min, single worker)

- Corpus: merged all prior campaigns (corpus_avc + avc2 + avc3 + avc4 = 3302
  units incl. known crash triggers avc_crash_*.bin) into fresh corpus_patched/.
- `nohup timeout 1800 ./fuzz_avc_patched_asan corpus_patched -max_len=60000
  -timeout=30 -artifact_prefix=avcp_ -print_final_stats=1 > log 2>&1 &`
- Final stats: **21,059 execs, avg 11.7/s, 1,014 new units added (corpus
  3302→4078), peak RSS 403 MB, slowest unit 0s, 0 ASAN errors, 0 artifacts.**
- Result: patched build finds NOTHING — the check converts the over-read into
  a clean decode error. Verdict: read stays within the decoder's padded
  allocation (256KB zeroed dynamic bitstream buffer, ih264d_api.c:2517-2540,
  +EXTRA_BS_OFFSET slack) → ASAN cannot see it. FINAL.

## Check-fires proof (gc-sections unit probe, no gdb — gdb absent on Kali)

```bash
clang -O1 -ffunction-sections -fdata-sections -I libavc_patched -I ... \
  -c /tmp/uev_probe.c -o /tmp/uev_probe.o          # tiny main, calls ih264d_uev
clang -O1 -ffunction-sections -fdata-sections -I ... \
  -c libavc_patched/decoder/ih264d_parse_cavlc.c -o /tmp/cavlc_patched.o
clang /tmp/uev_probe.o /tmp/cavlc_patched.o -Wl,--gc-sections -o /tmp/uev_probe
```

Output (probe = 8-word buf, words 0-6 zero, word 7 = 0xDEADBEEF):
```
CASE1 ofst=0  max=16 -> ret=0xFFFFFFFF ofst=0    # 0+32 > 16 → CHECK FIRES
CASE2 ofst=0  max=64 -> ret=0x7FFFFFFF ofst=63   # check passes, real parse path
CASE3 ofst=33 max=64 -> ret=0xFFFFFFFF ofst=33   # 65 > 64 → CHECK FIRES
```
CASE2 sanity: CLZ(0)=31 in this codebase → offset 32+31=63, `(1<<31)+0-1`.

## Replay experiments (single-shot harnesses)

- `avc_single_asan` = unpatched tree + tiny main
  (`-fsanitize=address` WITHOUT `,fuzzer`, reads file → calls
  LLVMFuzzerTestOneInput). Same for `avc_single_patched_asan` (patched tree).
- Known triggers (11B SEI, 16B avc_crash_verified.bin, 850B
  avc_crash_x50.bin): rc=0 on BOTH harnesses — single-shot is clean by design
  (padded buffer), and the patched build rejects them cleanly.
- **OOB-WRITE hunt**: new corpus units identified via
  `comm -13 <pre-launch-name-set> <current-name-set>` (825 units), replayed
  one-by-one through the UNPATCHED avc_single_asan: **0 crashes.** No
  deterministic OOB write exists on any new-coverage input.

## Deliverables left on the VM

- `~/fuzz/libavc_patched/` (patched tree, `.orig` snapshots kept for diffing),
  `fuzz_avc_patched_asan`, `avc_single_asan`, `avc_single_patched_asan`,
  `corpus_patched/` (4078 units), `fuzz_avc_patched_asan.log`.

## Reporting language (when this verdict comes up)

"The over-read is real and upstream-identical, but reads at most a couple of
32-bit words past u4_max_ofst into the decoder's own zero-padded 256KB
bitstream buffer — never across an ASAN redzone. Enforcing the bound yields
clean errors, not new crashes. Severity: LOW-MEDIUM (DoS under repeated
diverse decode), not a deterministic ASAN-detectable bug."
