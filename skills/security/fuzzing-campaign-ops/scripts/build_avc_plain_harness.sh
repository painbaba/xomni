#!/bin/bash
# Build a plain (non-ASAN) libavc H.264 decoder harness on the Kali VM.
# Run:  bash ~/fuzz/build_avc_plain.sh     (upload to ~/fuzz first)
# Out:  ~/fuzz/build_avc_plain/avc_dec_plain   (usage: ./avc_dec_plain <file>)
#
# Source list mirrors libavc's OSS-Fuzz cmake (common/common.cmake +
# decoder/libavcdec.cmake, x86 branch). Key pitfalls baked in:
#   - x86 dispatcher NEEDS common/x86/*.c SIMD files (-msse4.2 -mssse3)
#   - main.cpp lacks <cstdint> -> compile with -include cstdint
#   - ithread.c -> link -lpthread
# The script itself must be run under bash (Kali login shell is zsh, which
# does not word-split $FLAGS — would break every gcc call).
set -u
cd ~/fuzz || exit 1
rm -rf build_avc_plain
mkdir -p build_avc_plain
cd build_avc_plain || exit 1

INC="-I../libavc -I../libavc/decoder -I../libavc/decoder/x86 -I../libavc/common -I../libavc/common/x86 -I../libavc/common/mvc -I../libavc/fuzzer"
FLAGS="-O2 -fno-strict-aliasing $INC"

ok=0; fail=0
for f in \
  ../libavc/common/ih264_buf_mgr.c \
  ../libavc/common/ih264_cabac_tables.c \
  ../libavc/common/ih264_cavlc_tables.c \
  ../libavc/common/ih264_chroma_intra_pred_filters.c \
  ../libavc/common/ih264_common_tables.c \
  ../libavc/common/ih264_deblk_edge_filters.c \
  ../libavc/common/ih264_deblk_tables.c \
  ../libavc/common/ih264_disp_mgr.c \
  ../libavc/common/ih264_dpb_mgr.c \
  ../libavc/common/ih264_ihadamard_scaling.c \
  ../libavc/common/ih264_inter_pred_filters.c \
  ../libavc/common/ih264_iquant_itrans_recon.c \
  ../libavc/common/ih264_list.c \
  ../libavc/common/ih264_luma_intra_pred_filters.c \
  ../libavc/common/ih264_mem_fns.c \
  ../libavc/common/ih264_padding.c \
  ../libavc/common/ih264_resi_trans_quant.c \
  ../libavc/common/ih264_trans_data.c \
  ../libavc/common/ih264_weighted_pred.c \
  ../libavc/common/ithread.c \
  ../libavc/decoder/ih264d_api.c \
  ../libavc/decoder/ih264d_bitstrm.c \
  ../libavc/decoder/ih264d_cabac.c \
  ../libavc/decoder/ih264d_cabac_init_tables.c \
  ../libavc/decoder/ih264d_compute_bs.c \
  ../libavc/decoder/ih264d_deblocking.c \
  ../libavc/decoder/ih264d_dpb_mgr.c \
  ../libavc/decoder/ih264d_format_conv.c \
  ../libavc/decoder/ih264d_function_selector_generic.c \
  ../libavc/decoder/ih264d_inter_pred.c \
  ../libavc/decoder/ih264d_mb_utils.c \
  ../libavc/decoder/ih264d_mvpred.c \
  ../libavc/decoder/ih264d_nal.c \
  ../libavc/decoder/ih264d_parse_bslice.c \
  ../libavc/decoder/ih264d_parse_cabac.c \
  ../libavc/decoder/ih264d_parse_cavlc.c \
  ../libavc/decoder/ih264d_parse_headers.c \
  ../libavc/decoder/ih264d_parse_islice.c \
  ../libavc/decoder/ih264d_parse_mb_header.c \
  ../libavc/decoder/ih264d_parse_pslice.c \
  ../libavc/decoder/ih264d_parse_slice.c \
  ../libavc/decoder/ih264d_process_bslice.c \
  ../libavc/decoder/ih264d_process_intra_mb.c \
  ../libavc/decoder/ih264d_process_pslice.c \
  ../libavc/decoder/ih264d_quant_scaling.c \
  ../libavc/decoder/ih264d_sei.c \
  ../libavc/decoder/ih264d_tables.c \
  ../libavc/decoder/ih264d_thread_compute_bs.c \
  ../libavc/decoder/ih264d_thread_parse_decode.c \
  ../libavc/decoder/ih264d_utils.c \
  ../libavc/decoder/ih264d_vui.c \
  ../libavc/decoder/x86/ih264d_function_selector.c \
  ../libavc/decoder/x86/ih264d_function_selector_sse42.c \
  ../libavc/decoder/x86/ih264d_function_selector_ssse3.c ; do
  b=$(basename "$f" .c)
  if gcc $FLAGS -msse4.2 -mssse3 -c "$f" -o "$b.o" >/tmp/cc_$b.log 2>&1; then
    ok=$((ok+1))
  else
    fail=$((fail+1)); echo "FAIL: $f"; tail -3 /tmp/cc_$b.log
  fi
done
echo "C-COMPILE ok=$ok fail=$fail"

ok2=0; fail2=0
for f in ../libavc/common/x86/*.c; do
  b=$(basename "$f" .c)
  if gcc $FLAGS -msse4.2 -mssse3 -c "$f" -o "x86_$b.o" >/tmp/cc_$b.log 2>&1; then
    ok2=$((ok2+1))
  else
    fail2=$((fail2+1)); echo "FAIL: $f"; tail -3 /tmp/cc_$b.log
  fi
done
echo "X86-COMPILE ok=$ok2 fail=$fail2"

# harness: use the non-dbg variant; main.cpp needs <cstdint> (gcc >= 13 stricter)
if g++ $FLAGS -c ../libavc/fuzzer/avc_dec_fuzzer_nodbg.cpp -o avc_fuzzer.o >/tmp/cc_harness.log 2>&1; then
  echo "HARNESS ok"
else
  echo "HARNESS FAIL"; tail -15 /tmp/cc_harness.log
fi
if g++ $FLAGS -include cstdint -c ../main.cpp -o main.o >/tmp/cc_main.log 2>&1; then
  echo "MAIN ok"
else
  echo "MAIN FAIL"; tail -10 /tmp/cc_main.log
fi
if g++ -O2 -o avc_dec_plain *.o -lpthread >/tmp/link.log 2>&1; then
  echo "LINK ok -> ~/fuzz/build_avc_plain/avc_dec_plain"
  ls -la avc_dec_plain
else
  echo "LINK FAIL (missing symbols usually mean a source file was skipped)"; tail -20 /tmp/link.log
fi
echo "BUILD_DONE"
