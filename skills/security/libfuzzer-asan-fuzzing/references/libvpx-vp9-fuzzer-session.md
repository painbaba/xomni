# libvpx VP8/VP9 decoder fuzzer session (Kali VM, resumed mid-task)

Worked example of a full libvpx VP8/VP9 decoder ASAN+libFuzzer campaign driven over
paramiko SSH from Windows. Resumed a state where the bundle was extracted and seeds
transferred, but the link was broken.

## Resume-state checklist (`~/fuzz` on Kali)
- `ls ~/fuzz/` — look for `vpx_bundle.tgz` (extracted to `libvpx/`), `build_vpx.sh`,
  `vpx_seeds/`, `obj/*.o`, and any `fuzz_vpx*` binary.
- Prior agent's build script referenced `libvpx/examples/vpx_dec_fuzzer.cc` — NOT in the
  bundle (examples/ wasn't shipped) → link dies. Write your own IVF harness instead.
- `obj/` may already hold compiled objects (`-fsanitize=fuzzer-no-link`) — reusable for
  the link step; you may only need to fix the source list and relink.
- Seeds may already be in place; verify with `ls vpx_seeds/`.

## Environment (Kali 7.0.12, clang 21.1.8, 8 cores, 9.2 GB RAM)
- CPU flags: sse2 ssse3 sse4_1, NO avx/avx2 → `-msse4.1`
- `ffmpeg` present (`which ffmpeg`) — can generate extra IVF seeds if needed
- libvpx config (from `config/generic/vpx_config.h`): `VPX_ARCH_X86=0`,
  `CONFIG_RUNTIME_CPU_DETECT=0`, `CONFIG_POSTPROC=0`, `CONFIG_VP9_POSTPROC=0`,
  `CONFIG_VP9_HIGHBITDEPTH=1`, configure string `--target=generic-gnu
  --enable-realtime-only --enable-pic --size-limit=4096x3072 --enable-vp9-highbitdepth`

## Build (two-pass)
C sources: `clang -O1 -g -msse4.1 -fsanitize=address,fuzzer-no-link -fno-omit-frame-pointer -pthread -c`
Link: `clang++ -O1 -g -msse4.1 -fsanitize=address,fuzzer -fno-omit-frame-pointer -pthread fuzz_vpx_entry.cpp obj/*.o -lm -o fuzz_vpx_asan`

Source list (`find -maxdepth 1 -name '*.c'` over decoder/common dirs + explicit adds):
- dirs: `vp9/{decoder,common}` `vp8/{decoder,common}` `vpx_dsp` `vpx_scale` `vpx_mem`
  `vpx_ports` `vpx_util` `vpx/src`
- exclude: `vp9_mfqe.c`, `vpx/src/vpx_encoder.c`, `*_cpudetect.c`
- add: `vpx_scale/generic/*.c`, `vp8/common/generic/systemdependent.c`,
  `vp9/vp9_dx_iface.c`, `vp9/vp9_iface_common.c`, `vp8/vp8_dx_iface.c`,
  `config/generic/vpx_config.c`

## Link errors hit + fixes
1. `multiple definition of arm_cpu_caps` (aarch32_cpudetect.c + aarch64_cpudetect.c)
   → exclude ALL `*_cpudetect.c` (they are non-host arch probes).
2. `undefined reference to vp8_machine_specific_config` → found via `grep -rln` in
   `vp8/common/generic/systemdependent.c` → add that file to SRCS.
3. Four files fail to compile, all safe to drop (link stays clean):
   - `vp8/common/mfqe.c` (`no member named 'post_proc_buffer'`) — CONFIG_POSTPROC=0
   - `vp8/decoder/error_concealment.c` (`no member 'overlaps'/'prev_mi'`) — EC off
   - `vpx_dsp/ssim.c` (encoder metrics), `vpx_ports/emms_mmx.c` (x86-only)

## Harness (fuzz_vpx_entry.cpp — see templates/fuzz_entry_ivf_vpx.cpp)
IVF: 32B file header, then per frame 4B LE size + 8B timestamp + payload.
`vpx_codec_dec_init(&codec, vpx_codec_vp9_dx(), &cfg{threads=1}, 0)` → loop
`vpx_codec_decode(&codec, p, frame_sz, NULL, 0)` (ignore errors — corrupt-frame
tolerance is the decoder's job) → drain `vpx_codec_get_frame` → `vpx_codec_destroy`.
Uses `mem_get_le32` from `vpx_ports/mem_ops.h`.

## Launch + poll
`cd ~/fuzz && nohup timeout 3600 ./fuzz_vpx_asan vpx_seeds/ -max_len=300000 -timeout=10 -rss_limit_mb=3000 -artifact_prefix=vpx_ > fuzz_vpx.log 2>&1 &`
Poll: `ps aux | grep -v grep | grep fuzz_vpx_asan`, `tail fuzz_vpx.log`, `ls vpx_crash-*`.

Status at ~10.5 min: 5,622 execs, cov 2232, ft 12,296, ~10 exec/s, RSS 402 MB,
0 ASAN hits. Smoke run `-runs=200` INTO the seed dir grew the corpus 4 → 91 files
before launch.
