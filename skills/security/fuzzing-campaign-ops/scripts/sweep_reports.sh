#!/bin/bash
# Per-artifact triage for a sweep: sha1 + seed-match + stack extraction +
# single-input repros + real exec/s. Validated Aug 2026.
# Usage:
#   python kali_xfer.py put artifact_list.txt /tmp/artifact_list.txt   # one artifact name per line
#   python kali_xfer.py put sweep_reports.sh /tmp/sweep_reports.sh
#   python kali_ssh.py "bash /tmp/sweep_reports.sh" 550 > sweep_reports_out.txt 2>&1
# Adjust SEED_DIRS / BINARIES / REPRO_FILES for the campaign.
LIST=${1:-/tmp/artifact_list.txt}
cd ~/fuzz || exit 1
SEED_DIRS=( seeds_hevc seeds_hevc2 seeds_avc corpus_avc corpus_avc2 corpus_avc3 xml_seeds yuv_seeds seeds_vpx )

# Build the seed/corpus sha1 index ONCE, then grep per artifact (never re-hash all seeds per artifact)
: > /tmp/seed_hashes.txt
for d in "${SEED_DIRS[@]}"; do
  [ -d "$d" ] && find "$d" -maxdepth 1 -type f -exec sha1sum {} + 2>/dev/null >> /tmp/seed_hashes.txt
done
echo "seed_index_lines=$(wc -l < /tmp/seed_hashes.txt)"

while IFS= read -r b; do
  [ -z "$b" ] && continue
  echo "=====ART $b"
  if [ ! -f "$b" ]; then echo "MISSING_ON_REMOTE"; echo "=====ENDART"; continue; fi
  stat -c 'size=%s mtime=%y' "$b"
  s=$(sha1sum "$b" | awk '{print $1}')
  echo "sha1=$s"
  echo "seedmatch:"
  m=$(grep -m1 "^$s " /tmp/seed_hashes.txt)
  if [ -n "$m" ]; then echo "  MATCH $(echo "$m" | awk '{print $2}')"; else echo "  (no seed/corpus match)"; fi
  log=""
  for f in ~/fuzz/*.log; do
    if grep -q "Test unit written to.*${b}" "$f" 2>/dev/null; then log="$f"; break; fi
  done
  echo "log=${log:-NONE}"
  if [ -n "$log" ]; then
    echo "---report---"
    grep -B45 "Test unit written to.*${b}" "$log" | tail -50   # ASAN/timeout report precedes the write line
  fi
  echo "=====ENDART"
done < "$LIST"

echo "=====CRASHREPRO====="
# Single-input repro: rc=0 + "Executed in N ms" = no ASAN crash, whatever the filename says.
for f in avc_crash_verified.bin avc_crash_last.bin avc_crash_snapshot.bin avc_crash_x50.bin avc_crash_sps9.bin; do
  echo "--- $f with fuzz_avc_asan"
  out=$(timeout 30 ./fuzz_avc_asan "$f" -runs=1 -timeout=25 2>&1)
  rc=$?
  echo "$out" | tail -40
  echo "rc=$rc"
done

echo "=====EXECFIX====="
for f in ~/fuzz/fuzz_hevc_asan.log ~/fuzz/fuzz_hevc_asan2.log ~/fuzz/fuzz_avc_asan.log ~/fuzz/fuzz_avc_asan2.log ~/fuzz/fuzz_avc_asan3.log ~/fuzz/fuzz_expat.log ~/fuzz/fuzz_yuv.log; do
  [ -f "$f" ] || continue
  echo "$(basename "$f"): $(grep -E 'exec/s:' "$f" | tail -1)"
done
echo "=====END====="
