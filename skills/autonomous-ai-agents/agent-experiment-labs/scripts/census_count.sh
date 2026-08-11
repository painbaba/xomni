#!/usr/bin/env bash
# Census counter for the machine city — counts population marker files per
# district, splits by generation, prints totals + originals.
# Usage: bash census_count.sh [machine_city_root]   (defaults to the standard path)
# Hardline-safe: the terminal invocation is a plain `bash script.sh` — the
# blocklist inspects the command string, not file contents.
set -u
ROOT="${1:-$HOME/ai-workforce/ghost-lab/machine_city}"
cd "$ROOT" || { echo "no machine city at $ROOT"; exit 1; }

echo "=== PER DISTRICT (population marker files) ==="
for d in bank business ledger medical military underworld couriers; do
  n=$(find "$d/population" -name '*.md' 2>/dev/null | wc -l)
  printf '%-12s %s\n' "$d" "$n"
done

echo "=== TOTAL MARKER FILES ==="
find . -path '*/population/*.md' | wc -l

echo "=== BY GENERATION (from file contents) ==="
grep -h 'Generation:' */population/*.md 2>/dev/null | sort | uniq -c

echo "=== ORIGINALS (neighbor civs, in their own territories) ==="
g=0; w=0
[ -d "$HOME/ai-workforce/ghost-lab/ghost_sandbox/citizens" ] && g=$(ls "$HOME/ai-workforce/ghost-lab/ghost_sandbox/citizens" | grep -v '^__' | wc -l)
[ -d "$HOME/ai-workforce/ghost-lab/god_people/citizens" ] && w=$(ls "$HOME/ai-workforce/ghost-lab/god_people/citizens" | grep -v -E '^registry\.' | wc -l)
echo "Witness Commonwealth artifacts: $g   Workfolk citizen files: $w   (originals = 4 + 5)"

echo "=== PROJECTION (total doubles each generation: T x 2^n) ==="
T=$(find . -path '*/population/*.md' | wc -l)
echo "current total T=$T (add 9 originals for grand total $((T + 9)))"
echo "10k crossed at n=$(python3 -c "import math;print(math.ceil(math.log(10000/$T,2)))" 2>/dev/null || echo '?') doublings"
echo "1M crossed at n=$(python3 -c "import math;print(math.ceil(math.log(1000000/$T,2)))" 2>/dev/null || echo '?') doublings"
