# libhevc 420P variant (Aug 9, 2026) — session record

Goal: force IV_YUV_420P output so the fmt_conv V-plane write path
(`ihevcd_fmt_conv_420sp_to_420p`, fmt_conv.c:857-891 — writes `pu1_v_dst[j]`)
becomes live ASAN surface. In 420SP mode that code was dead: allocFrame gave
2 buffers (Y + interleaved UV) with bufs[2]=NULL by design.

## Harness diff (2 hunks in hevc_dec_fuzzer.cpp)

1. LLVMFuzzerTestOneInput: replaced
   `colorFormatIdx = data[6] % 6; colorFormat = supportedColorFormats[idx]`
   with `IV_COLOR_FORMAT_T colorFormat = IV_YUV_420P;` (pinned).
2. allocFrame(): replaced the mColorFormat switch with unconditional
   `sizes[0]=W*H; sizes[1]=W*H>>2; sizes[2]=W*H>>2; num_bufs=3;` — one
   `iv_aligned_malloc(NULL, 16, size)` per plane.

Enums (common/iv.h): IV_YUV_420P=0x1, IV_YUV_420SP_UV=0xb, IV_YUV_420SP_VU=0xc.
Format chain verified: create_ip.e_output_format → ihevcd_api.c:1212
`ps_codec->e_chroma_fmt = e_output_format` → fmt_conv dispatch
`else if(IV_YUV_420P == ps_codec->e_chroma_fmt)` → 420sp_to_420p.

## Build (VM, clang 21.1.8, ~3.5 min, survived SSH client timeout)

```
cd ~/fuzz && clang++ -O1 -g -msse4.1 -fsanitize=address,fuzzer \
  -fno-omit-frame-pointer -DDISABLE_AVX2 \
  -I libhevc_420p -I libhevc_420p/decoder -I libhevc_420p/common \
  -I libhevc_420p/common/x86 -I libhevc_420p/decoder/x86 -I libhevc_420p/fuzzer \
  libhevc_420p/fuzzer/hevc_dec_fuzzer.cpp \
  -x c libhevc_420p/decoder/*.c libhevc_420p/decoder/x86/*.c \
  libhevc_420p/common/*.c libhevc_420p/common/x86/*.c \
  -o fuzz_hevc_420p_asan
```
BUILD_RC=0, 6.68 MB, 11908 PCs. Smoke: `./fuzz_hevc_420p_asan
hevc_352x288.h265 -runs=1` → rc=0, 2422 ms, no ASAN.

## Launch

`cp -r seeds_hevc seeds_hevc_420p` (hevc3 instance was live-writing
seeds_hevc/ — two writers on one corpus dir clobber state files).
`setsid nohup timeout 3600 ./fuzz_hevc_420p_asan seeds_hevc_420p/
-max_len=100000 -timeout=30 -rss_limit_mb=3000 -artifact_prefix=hevc420p_ >
fuzz_hevc_420p.log 2>&1 < /dev/null &`

## Results (last poll #2048, ~33 min in, box loaded with 3 fuzzers)

| Metric | 420P run | 420SP run (fuzz_hevc_asan F1, prior) |
|---|---|---|
| cov | 4761 | 4336 max |
| ft | 27098 | 24620 |
| corp | 1154/30Mb | 1381/66Mb |
| exec/s | 1 (CPU-starved) | 1 |
| ASAN errors / artifacts | 0 / 0 | 0 / — |

**Finding: no ASAN hit.** The V-plane path executed with 3 real buffers — the
retracted NULL+offset condition did not fire because bufs[2] is now a real
allocation (the old NULL V-buffer is gone by design). Coverage +425 edges over
the 420SP ceiling = new reachable surface confirmed, but no new bug surfaced
in the window.

## Local files (Windows C:\Users\HP\ai-workforce\aosp-audit\)

- `hevc_420p_harness.patch` (exact diff), `hevc_dec_fuzzer_vm.cpp` (patched),
  `hevc_dec_fuzzer_orig.cpp` (stock), `fuzz_hevc_420p.log` (mirror),
  `HEVC_420P_RUN_REPORT.md`.

## Follow-up ideas

- `-focus_function=ihevcd_fmt_conv_420sp_to_420p` concentrates mutations on
  the V-plane path.
- `-jobs=2` once sibling fuzzers die (box oversubscribed → exec/s 1).
