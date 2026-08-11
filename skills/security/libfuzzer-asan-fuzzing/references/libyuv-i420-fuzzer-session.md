# Worked example: libyuv (AOSP) I420 fuzzer on Kali VM

Session: Aug 2026. Fuzzed AOSP libyuv (git commit daeff19, 2025-03-26) for the
CVE-2017-13189 class (OOB in I420ToARGB family from stride/dimension mismatch).
Ran on Kali VM `painbaba@192.168.29.35` (fallback `.56.101`) via paramiko from
Windows. Result: build clean, 1.35M execs / ~2070 exec/s, ZERO ASAN hits,
coverage plateaued at 390 cov / 1574 ft. Recent libyuv appears clean in this
class.

## Environment facts

- Kali 7.0.12 (kernel 7.0.12+kali-amd64), 8 cores, ~9GB RAM (4GB available).
- clang 21.1.8 (Debian), libFuzzer runtime present (`libclang_rt.fuzzer-x86_64.a`).
- **CPU SIMD flags: sse2, ssse3, sse4_1 — NO avx, NO avx2.** This is the key fact.

## Commands that worked

Local (Windows git-bash): tar source + include only:
```
cd /c/Users/HP/ai-workforce/aosp-audit/libyuv && tar czf /tmp/libyuv_src.tgz source include
cygpath -w /tmp/libyuv_src.tgz   # -> C:\Users\HP\AppData\Local\Temp\libyuv_src.tgz (for python/paramiko)
```

Remote build (the winner — `-msse4.1` only, NOT -mavx2):
```
cd ~/fuzz && clang++ -O1 -g -fsanitize=address,fuzzer -fno-omit-frame-pointer \
  -msse4.1 -I libyuv/include fuzz_yuv_entry.cpp libyuv/source/*.cc -o fuzz_yuv_asan
```
First build attempt used the task's suggested `-mavx2` and crashed instantly
(SIGILL, see below).

Seeds (30 files, 14B..98KB) — sizes MUST match harness consumption for odd dims:
```python
import os, struct
for i, (w, h) in enumerate([(16,16),(17,17),(31,31),(33,33),(63,63),(65,65),
                            (127,127),(129,129),(255,255),(256,256),(3,3),(5,7),
                            (33,65),(65,33),(256,2),(2,256), ...]):
    need = 8 + w*h + 2*((w+1)//2)*((h+1)//2)
    open(f'yuv_seeds/seed_{i:02d}_{w}x{h}','wb').write(struct.pack('<II',w,h)+os.urandom(need-8))
```

Launch + poll:
```
cd ~/fuzz && nohup timeout 3600 ./fuzz_yuv_asan yuv_seeds/ -max_len=100000 \
  -timeout=10 -rss_limit_mb=3000 -artifact_prefix=yuv_ > fuzz_yuv.log 2>&1 &
ps aux | grep -v grep | grep fuzz_yuv_asan    # alive? cpu%, rss
tail -5 fuzz_yuv.log                           # #execs, cov, ft, exec/s, rss
ls yuv_crash-*                                 # artifacts
```

## The SIGILL debug path (the interesting part)

1. Build with `-mavx2` global. Smoke test 20s: libFuzzer `ERROR: libFuzzer:
   deadly signal` at `#0 I422ToARGBRow_Any_SSSE3 row_any.cc:364` ←
   `I420ToARGBMatrix convert_argb.cc:153` during seed loading (12 units in).
   No ASAN report at all — just the signal trace.
2. Reproduced with the written artifact; same trace. Still no ASAN report.
3. Checked `/proc/cpuinfo` flags: **no avx2**. Root cause: clang with global
   `-mavx2` emits AVX2 instructions in generic TUs — here inside the `ANY31C`
   macro in row_any.cc that wraps the SSSE3 row function. CPU can't execute
   them → SIGILL (reported by libFuzzer as generic "deadly signal").
4. Rebuilt with `-msse4.1` only (CPU supports sse4_1). Smoke test: 18k execs,
   ~760 exec/s, 505 new units, no crash. Real campaign then ran 1.35M execs clean.

Lessons: (a) always read `/proc/cpuinfo` flags before choosing `-m` flags;
(b) "deadly signal" with no ASAN report ≈ SIGILL/build problem, not a finding;
(c) if you want AVX2 coverage, apply `-mavx2` only to `*_gcc.cc` intrinsics TUs.

## libyuv-specific notes

- Whole API is in `namespace libyuv` → `using namespace libyuv;` required.
- `source/*.cc` glob-compiles fine on x86_64: neon/msa/rvv/lsx/sme files are
  `#if defined(...)`-guarded (empty TUs), mjpeg files are `#ifdef HAVE_JPEG`
  (no libjpeg needed).
- I420 plane math for the harness: Y = w*h, U = V = ((w+1)/2)*((h+1)/2),
  total = w*h + 2*ceil(w/2)*ceil(h/2) (odd dims exceed the naive 1.5*w*h).
- `I420ToARGB(src_y, src_stride_y, src_u, src_stride_u, src_v, src_stride_v,
  dst_argb, dst_stride_argb, width, height)`; chroma rows advance on `y & 1`
  (convert_argb.cc I420ToARGBMatrix loop).
- Harness integrity: passing chroma stride = full width with a minimal
  (1.5*w*h) layout guarantees OOB read on EVERY input — a harness artifact,
  not a libyuv bug. Kept that surface with a padded chroma layout (planes
  sized w*uh) so any hit would be real. This is the single most important
  design decision for this bug class.

## Status numbers at report time

- 1.35M execs, ~2065-2072 exec/s, cov 390, ft 1574, corpus 210 files/123KB,
  RSS 464MB (limit 3000MB), artifacts: none.
- Fuzzer launched 03:07, `timeout 3600` auto-kill ~04:07; check
  `~/fuzz/fuzz_yuv.log` final stats after.
