# libavc / libhevc campaign notes (AOSP codec audits, Kali VM)

State as of the full sweep on Aug 9 2026 ~03:55 EDT (`KALI_FUZZ_STATUS.md`
in the Windows audit dir has the complete per-fuzzer table + artifact list).

## Targets & context
- libavc = Ittiam H.264/AVC decoder (AOSP). libhevc = same family (HEVC);
  libhevc already yielded **3 bugs**. libavc is the follow-on target.
- Goal class: OOB WRITE / memory-corruption bugs. ASAN catches them where the
  Windows UBSAN build could not.
- Known-bug marker file on Kali: `~/fuzz/known_uev_11.bin` (UEV = infinite
  ue(v) loop family — the known `ih264d_uev` bug; watch for it in triage).

## Corpus layout on Kali (~/fuzz)
- `corpus_avc/` — first corpus (ffmpeg seeds + fuzzer mutations); ~650+ files
  after a few hours, growing.
- `corpus_avc2/` — second corpus seeded by `scripts/gen_h264_seeds.sh`
  (10 seeds, 5×Baseline + 5×Main, 39–167 KB); grows as F2 mutates.
- `fuzz_avc_asan` — ASAN+libFuzzer binary. Logs: `fuzz_avc_asan.log` (F1),
  `fuzz_avc_asan2.log` (F2), plus per-worker `fuzz-0..7.log`.
- Artifact prefixes in use: `avc2_` (F2, relative → lands in ~/fuzz) and
  absolute `/home/painbaba/fuzz/` (F1).

## Running instances (state after Aug 9 03:55 sweep)
- **RUNNING:** `fuzz_yuv_asan` (yuv_seeds/, #8.5M, ~3113 exec/s), `fuzz_expat_asan`
  (xml_seeds/, #1.24M, ~608 exec/s, log = `fuzz_expat.log` — note the log is NOT
  named `*_asan.log`), `fuzz_vpx_asan` (launched 03:49, **vpx_seeds/ was EMPTY** —
  vpx_seeds.tgz/vpx_bundle.tgz present but not extracted; needs seeds).
- **DEAD / needs relaunch:** `fuzz_hevc_asan` (interrupted ~03:17, cov 4336) and
  `fuzz_hevc_asan2` (interrupted ~03:33, cov 3871) — the PRIMARY libhevc hunt
  target has no running fuzzer. `fuzz_avc_asan` F1 (timeout-exit 02:37),
  F2 `avc2_` instance (timeout-exit 03:29), and the corpus_avc3 `-jobs=8` run
  (killed 03:48 by its `timeout 1800` wrapper; workers fuzz-0/1/3/5/7 had
  already died of startup timeouts, fuzz-2/4/6 survived to ~#1555, cov 4775).
- **BUILDING:** `fuzz_jpeg_asan` (clang compile ran 03:45→03:56+ under load).
- Other binaries on box: `fuzz_expat_spec`, `fuzz_hevc_unpatched_{one,ub,null}`
  (sibling agents' unpatched-variant builds), `fuzz_vpx_asan` (build fixed 03:48
  after a 6-error failure; `build_vpx_fixed.sh`).

## Findings so far
- **0 `ERROR: AddressSanitizer` across ALL logs (hevc, avc, expat, yuv, workers)
  — the heap OOB WRITE hunt in libhevc/libavc is still open.** giflib
  double-free remains the only proven bug.
- **All 26 libFuzzer artifacts are timeouts/slow-units (hang-class), and 21 of
  26 are sha1-identical to seeds or corpus members** → benign config artifacts
  (ASAN ~2–4× slowdown + scheduler starvation tripping `-timeout=10`). Only 3
  unmatched: `avc2_timeout-e78fc738...` (94,681 B), `avc2_slow-unit-ba892753...`
  (166,759 B), `avc2_timeout-d2549df3...` (65,494 B) — worth a plain-harness
  check, but not memory bugs.
- Known slow path reconfirmed: timeout stacks end in `ih264d_video_decode`
  (ih264d_api.c:2759) → `Codec::decodeFrame` (avc_dec_fuzzer_nodbg.cpp:329) →
  `LLVMFuzzerTestOneInput:378`, `SUMMARY: libFuzzer: timeout`.
- `avc2_slow-unit-24eb4a3f...` (167,427 B) CONFIRMED = seed_08.h264 itself.
- **The 8 manual `*_crash_*.bin` saves (avc_crash_verified/last/snapshot/x50/
  sps9, hevc_crash_mut/mut2/mut3) do NOT crash the ASAN builds** — all rc=0 in
  single-input repros (`./fuzzer <file> -runs=1 -timeout=25`). They are
  UBSAN/plain-build artifacts, not ASAN findings.

## Aug 9 late-night AVC push (4 campaigns, ~16 core-hrs) — 0 ASAN crashes

- C1 (corpus_avc/, 16 curated seeds, max_len=200000, -jobs=8): cov 3279→4719,
  corpus→800 units. C2 (relaunch on the grown 800-unit corpus): crawled —
  RELOAD-stalled workers at #128–#512, cov 4781. C3 (FRESH corpus_avc3/ from
  the 16 original seeds, max_len=60000): cov 4782, corpus 817. C4 (fresh
  corpus_avc4/ + `avc_dec_fuzzer.dict`, timeout=15): cov 4694, corpus 609.
- **Peak coverage 4782/9680 counters (~49.4%)**; exec/s stayed 0–4/worker
  (harness creates+destroys a full codec per input, ≤100 decode calls/input).
- **0 `ERROR: AddressSanitizer` — heap OOB WRITE / UAF hunt still open.** All
  13 `timeout-*` artifacts were the slow big seeds (58–122 KB × 100 decode
  calls each exceed -timeout on the loaded box), sha1-matching seeds, benign.
- **Known uev READ bug proven ASAN-invisible via the official harness**:
  `known_uev_11.bin` + all 5 avc_crash_*.bin passed rc=0 on `fuzz_avc_asan`
  AND on `exact_alloc_test` (exact-size malloc repro driver, built from
  `exact_alloc_driver.cpp` + `avc_dec_fuzzer_nodbg.cpp`). Cause: decodeHeader
  phase consumes short SEI inputs pre-frame-decode + libFuzzer input-buffer
  slack keeps small OOB reads inside the allocation. Not evidence of a fix.
- Build recipe that actually links (x86 dirs required): see SKILL.md "Rebuild
  recipe" — adds `-I libavc/common/x86 -I libavc/decoder/x86` and the
  `libavc/{decoder,common}/x86/*.c` sources. No _aligned_free sed needed.

## Windows mirror
- Seeds: `C:\Users\HP\ai-workforce\aosp-audit\seeds_avc\corpus_avc2\`
- Artifacts: `C:\Users\HP\ai-workforce\aosp-audit\avc2_timeout-*`,
  `avc2_slow-unit-*`; sweep mirror files named `<fuzzer>_timeout_<hash8>.bin`
  (29 files mirrored Aug 9, 0 failures).
- Helpers: `kali_ssh.py` (commands), `kali_xfer.py` (SFTP) — keep these two
  separate; sibling agents rewrite shared helper files.
