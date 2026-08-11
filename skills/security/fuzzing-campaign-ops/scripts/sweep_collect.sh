#!/bin/bash
# Full-campaign enumeration for a sweep/status report (validated Aug 2026).
# Upload to Kali (kali_xfer.py put sweep_collect.sh /tmp/) then: bash /tmp/sweep_collect.sh
# Capture with: python kali_ssh.py "bash /tmp/sweep_collect.sh" 400 > sweep_collect_out.txt 2>&1
# NOTE: never pipe the SSH call through head/tee|head -- SIGPIPE truncates the capture.
# Adjust FUZZ_GREP / REF_BASE / LOG_GLOB for the target names. Kali shell is zsh,
# so ALWAYS run via `bash /tmp/...`, never bare.
FUZZ_GREP='fuzz_.*asan'
REF_BASE=~/fuzz/hevc_bundle.tgz        # find -newer base for "recent files"
LOG_GLOB=~/fuzz/*.log
ART_PATTERNS=( -iname '*artifact*' -o -iname 'vpx_*' -o -iname 'xml_*' -o -iname 'jpeg_*' \
  -o -iname 'yuv_*' -o -iname 'avc2_*' -o -iname 'hevc_*' -o -iname 'avc_*' \
  -o -iname 'timeout-*' -o -iname 'crash-*' -o -iname 'slow-unit-*' -o -iname 'leak-*' )
SEED_DIRS=( ~/fuzz/corpus* ~/fuzz/seeds* )

echo "=====PS====="
ps aux | grep -E "$FUZZ_GREP" | grep -v grep || echo "(no $FUZZ_GREP processes running)"
echo "=====LOGS====="
ls -la $LOG_GLOB 2>/dev/null || echo "(no *.log)"
echo "=====RECENT====="
if [ -f "$REF_BASE" ]; then
  echo "(base: $(basename "$REF_BASE") exists)"
  find ~/fuzz -maxdepth 1 -type f -newer "$REF_BASE" -printf '%TY-%Tm-%Td %TH:%TM %10s %f\n' 2>/dev/null | sort -k1,2
else
  echo "($(basename "$REF_BASE") MISSING - listing all ~/fuzz files by mtime)"
  find ~/fuzz -maxdepth 1 -type f -printf '%TY-%Tm-%Td %TH:%TM %10s %f\n' 2>/dev/null | sort -k1,2
fi
echo "=====ARTSCAN====="
find ~/fuzz -maxdepth 1 -type f \( "${ART_PATTERNS[@]}" \) -printf '%TY-%Tm-%Td %TH:%TM %10s %f\n' 2>/dev/null | sort -k1,2
echo "=====CORPUS====="
for d in "${SEED_DIRS[@]}"; do
  [ -d "$d" ] && printf '%s: %s files\n' "$d" "$(ls "$d" | wc -l)"
done
echo "=====MEM====="
free -h | head -2
echo "=====LOGTAIL====="
for f in $LOG_GLOB; do
  [ -f "$f" ] || continue
  echo "-----LOG $(basename "$f")"
  echo "--tail--"
  tail -3 "$f"
  echo "--asan_count--"
  grep -c 'ERROR: AddressSanitizer' "$f" || true
  echo "--last_run--"
  grep -oE '^#[0-9]+' "$f" | tail -1 || true
  echo "--last_stats--"
  grep -oE 'cov: [0-9]+ ft: [0-9]+ corp: [0-9]+/[0-9]+' "$f" | tail -1 || true
  echo "--real_exec--"   # NB: '[0-9]+ exec/s' would match max_len; this one is correct
  grep -oE 'exec/s: [0-9]+' "$f" | tail -1 || true
  echo "--seeds--"
  grep -oE '[0-9]+ files found in [^ ]+' "$f" | tail -1 || true
  echo "--artifact_writes--"
  grep 'Test unit written to' "$f" | tail -5 || true
  echo "--running_line--"
  grep -m1 'Running: ' "$f" || true
done
echo "=====END====="
