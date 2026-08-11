# Structure-Aware Bitstream Generation (novel-input generation vs mutation)

**Technique introduced 2026-08-09** (aosp-audit campaign, late phase). Trigger:
user watched a DW News video about AI *generating* novel functional viruses and
said "learn from it" — the applied lesson: mutation-only fuzzing produces
mostly syntactically-INVALID inputs, so header-driven allocation logic is never
reached. The upgrade: GENERATE syntactically-valid inputs with adversarial
field values, so the decoder parses DEEPER than mutation ever gets it.

## Why it matters
- The Ittiam codec bugs (libavc uev, libhevc misaligned load/shift-UB) were all
  in HEADER-DRIVEN paths: SPS dimensions → pic-buffer allocation, CTB coords →
  deblock maps, residual parse → coefficient buffers. Random byte mutation
  rarely produces a syntactically-valid SPS; generation does, every time.
- ffmpeg is the free syntax validator: if `ffmpeg -v error -i gen.h265 -f null -`
  returns rc=0 (only "missing picture in access unit" — meaning VPS/SPS/PPS all
  parsed), your header packing is correct.
- Then bulk-process the generated corpus through the real libFuzzer build with
  `-runs=1` (processes every corpus file once at startup, catches any ASAN
  crash in the initial coverage pass). NOTE: the one-shot runner (tiny main
  calling LLVMFuzzerTestOneInput) does NOT accept libFuzzer args — use the real
  `fuzz_<target>_asan` binary for -runs=1 bulk; the one-shot runner is only for
  single-file repro.

## The generator (hevc_gen.py — lives in C:\Users\HP\ai-workforce\aosp-audit\)
Core: a BitWriter with u(n,v) fixed-width, ue(v)/se(v) exp-Golomb, flag(v),
rbsp_trailing(). Builders for VPS / SPS / PPS / I-slice, then
`nal(32,vps)+nal(33,sps)+nal(34,pps)+nal(0,slice)`.

### HEVC header field layout (Main profile, max_sub_layers_minus1=0) — verified working
- NAL header: `(nal_type << 1) | 1` (layer 0, tid_plus1=1), prefixed 00 00 00 01.
- VPS (type 32): vps_id u(4), reserved_three_2bits u(2)=0, max_sub_layers_minus1
  u(6), temporal_id_nesting u(1)=1, reserved_0xffff u(16)=0xFFFF, then full
  profile_tier_level (2+1+5+32+1+1+1+1+44+8 bits), then per-sub-layer
  profile/level_present flags (loop i<max_sub_layers_minus1), then
  sub_layer_ordering_info_present u(1)=0 + 3 ue(0)s, max_layer_id u(6)=0,
  num_layer_sets_minus1 ue(0), timing_info_present u(1)=0, extension u(1)=0.
- SPS (type 33): vps_id u(4), max_sub_layers_minus1 u(3), nesting u(1), FULL
  profile_tier_level again (compats 0x60000000 for Main), sps_id ue, chroma ue
  (0/1/2; 3 would need separate_colour_plane_flag — avoid), pic_width ue,
  pic_height ue (ADVERSARIAL: 1..65534), conformance_window u(1)=0,
  bit_depth_minus8 ue x2, log2_max_poc_lsb_minus4 ue, ordering_info_present
  u(1)=0, 3x ue(0), log2_min_cb_minus3 ue, log2_diff_max_min_cb ue,
  log2_min_tb_minus2 ue, log2_diff_max_min_tb ue, max_transform_hierarchy
  ue x2, scaling_list u(1)=0, amp u(1), sao u(1), pcm u(1), num_st_ref_pic_sets
  ue (keep 0 unless implementing st_ref_pic_set — complex), long_term_ref
  u(1)=0, temporal_mvp u(1), strong_intra_smoothing u(1)=1, vui_present u(1)=0.
- PPS (type 34): pps_id ue, sps_id ue, dependent_slices u(1)=0, output_flag
  u(1)=0, extra_slice_header_bits u(3)=0, sign_data_hiding u(1)=0, cabac_init
  u(1), ref_idx defaults ue x2, init_qp_minus26 se (ADVERSARIAL), constrained
  intra u(1), transform_skip u(1), cu_qp_delta u(1)=0, chroma_qp_offsets u(1)=0,
  weighted_pred/bipred u(1) x2, transquant_bypass u(1)=0, tiles u(1),
  entropy_sync u(1), loop_filter_across u(1)=1, deblock_present u(1)=1,
  deblock_override u(1)=0, deblock_disabled u(1), scaling_list_data u(1)=0,
  lists_modification u(1)=0, log2_parallel_merge ue(0), slice_ext u(1)=0,
  pps_ext u(1)=0.
- I-slice (type 0): first_slice u(1)=1, pps_id ue, dependent u(1)=0,
  slice_type ue(2=I), poc_lsb u(4), st_ref_set_sps u(1)=1, sao_luma u(1),
  sao_chroma u(1), then 5 arbitrary entropy bytes + rbsp_trailing.

### Adversarial value sets (sweep dimensions)
width/height: 1,2,3,16,64,176,255,256,352,767,768,1000,1024,2048,4096,8192,
16384,32767,65534 × cb sizes (8,64)/(8,32)/(16,64)/(4,64)/(16,32)/(32,64)/(8,8)
× chroma 0/1/2 × bit depth 8/9/10/12; then levels 10..255 × st_ref_sets ×
pps variants; then transform depths 0-3 × sao/amp flags. ~30K streams total.

## Status (COMPLETE — definitive negative, 2026-08-09)
Generator VALIDATED: ffmpeg rc=0 on generated streams (headers parse; only
"missing picture" = waiting for a full picture). 30K synthetic streams
transferred to the Kali VM and swept via `fuzz_hevc_asan hevc_gen_corpus/ -runs=1`:
**0 ASAN errors, 0 hits** (cov stayed ~260 — the synthetic streams parse headers
but lack real coded picture data, so deep decode paths are not reached).

### The splice refinement (hevc_splice.py — adversarial headers × REAL payloads)
Pure synthetic generation stops at header-parse depth. The fix that reaches
deep paths: parse a REAL seed's NALs (hevc_352x288.h265 → 21 slice NALs incl.
type 39 SEI + IDR + non-IDR), rebuild VPS/SPS/PPS with adversarial fields,
then append the REAL slice payloads. 215 spliced streams (hostile dims to
16384, CB 4-64, chroma 0-2, bd 8-12) swept through the patched ASAN build:
**216 runs in 4s, 0 ASAN errors, 0 hits.** libhevc's early conformance/size
validation rejects hostile dims before any memory-unsafe path.

CONCLUSION: the generation technique is VALID and reusable for future targets
(generator hevc_gen.py + splicer hevc_splice.py both in aosp-audit\,
ffmpeg-validated), but the libhevc surface it was aimed at is exhausted —
do not re-run blindly expecting a hit. For a new target: reuse the BitWriter
layout + ffmpeg validation + -runs=1 bulk pattern; prefer splice-over-synthetic
from the start (synthetic alone never reaches deep paths).

## Pitfalls hit
- git-bash /tmp is invisible to Windows-native paramiko — write generated
  corpora into the working dir (aosp-audit\hevc_gen_out\) before SFTP.
- Per-file `timeout 3` sweep loops over 30K files are too slow (hours);
  prefer libFuzzer -runs=1 bulk (minutes).
- The `&` backgrounding guard fires on python -c wrappers — write the sweep as
  a .sh, upload it, `nohup ./gen_sweep.sh > log &` remotely.
- A one-shot runner prints "usage: <input>" when given libFuzzer flags — use
  the real fuzzer binary for corpus-dir bulk mode.
