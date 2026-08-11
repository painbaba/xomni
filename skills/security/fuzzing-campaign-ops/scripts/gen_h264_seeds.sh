#!/bin/bash
# Generate diverse H.264 seeds for libavc corpus expansion.
# Upload to Kali (kali_xfer.py put) then run: bash gen_h264_seeds.sh
# Requirements: ffmpeg with libx264 (check: ffmpeg -encoders | grep libx264)
#
# Key invariants (validated on Kali, Aug 2026):
#  - Every seed must stay UNDER the fuzzer's -max_len (200000 default) or
#    libFuzzer truncates it. Check sizes, re-encode oversize at lower bitrate.
#  - -profile:v main + -preset ultrafast silently downgrades to Baseline
#    (profile_idc=66) unless main-only features are forced via -x264-params.
#  - Verify profile by SPS byte sniff (find 0x67 NAL, next byte = profile_idc:
#    66=Baseline, 77=Main, 100=High). ffprobe strings are misleading.
set -u
OUT=~/fuzz/corpus_avc2
MAXLEN=200000
mkdir -p "$OUT"
cd "$OUT"
rm -f seed_*.h264

# baseline seeds: plain -profile:v baseline is correct as-is
gen_base() {
  n=$1; res=$2; rate=$3; g=$4; br=$5
  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "testsrc2=size=${res}:rate=${rate}:duration=2" \
    -c:v libx264 -preset ultrafast -profile:v baseline -g "$g" \
    -b:v "${br}k" -maxrate "$((br*2))k" -bufsize "$((br*4))k" \
    -pix_fmt yuv420p -f h264 "seed_${n}.h264"
}

# main seeds: MUST force cabac+bframes or x264 downgrades to baseline
gen_main() {
  n=$1; res=$2; rate=$3; g=$4; br=$5
  ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "testsrc2=size=${res}:rate=${rate}:duration=2" \
    -c:v libx264 -preset ultrafast -profile:v main \
    -x264-params "cabac=1:bframes=3:ref=2" -g "$g" \
    -b:v "${br}k" -maxrate "$((br*2))k" -bufsize "$((br*4))k" \
    -pix_fmt yuv420p -f h264 "seed_${n}.h264"
}

# resolution / framerate / GOP / profile / bitrate variety
gen_base 01 96x96   15 12   baseline 100
gen_main 02 96x96   30 48   main     300
gen_base 03 256x144 25 10   baseline 200
gen_main 04 256x144 12 60   main     500
gen_base 05 320x240 30 24   baseline 400
gen_main 06 320x240 15 90   main     500
gen_base 07 480x270 25 15   baseline 400
gen_main 08 480x270 30 120  main     600
gen_base 09 320x240 50 5    baseline 150
gen_main 10 256x144 60 250  main     350

echo "=== FINAL CHECK (size vs maxlen, SPS profile_idc) ==="
for f in seed_*.h264; do
  sz=$(stat -c%s "$f")
  pid=$(python3 -c "import sys; d=open('$f','rb').read(); i=d.find(b'\x67'); print(d[i+1] if i>=0 else -1)")
  flag=""
  [ "$sz" -gt "$MAXLEN" ] && flag="TOO_BIG (>max_len, re-encode lower bitrate)"
  echo "$f size=$sz profile_idc=$pid $flag"
done
