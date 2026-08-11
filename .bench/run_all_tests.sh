#!/bin/bash
# XOMNI plugin test matrix — runs every plugin suite, appends per-plugin results.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
OUT="$ROOT/docs/TEST-MATRIX.md"
echo "# Plugin Test Matrix (auto-generated $(date '+%Y-%m-%d %H:%M'))" > "$OUT"
echo "" >> "$OUT"
TOTAL=0; PASSED=0; FAILED_SUITES=""
for p in "$ROOT"/plugins/*/; do
  name=$(basename "$p")
  LOG=/tmp/xomni_tests_$name.log
  cd "$p" || continue
  mods=$(ls tests/test_*.py 2>/dev/null | sed 's|/|.|g; s|\.py$||')
  if [ -z "$mods" ]; then
    echo "| $name | N/A | test_methods: 0 (no tests dir) |" >> "$OUT"
    cd "$ROOT" || exit 1
    continue
  fi
  if python -m unittest $mods -v > "$LOG" 2>&1; then
    cnt=$(grep -c "^test" "$LOG" || true)
    nf=$(grep -cE "FAIL:|ERROR:" "$LOG" || true)
    res="PASS"
    TOTAL=$((TOTAL + cnt)); PASSED=$((PASSED + cnt))
  else
    cnt=$(grep -c "^test" "$LOG" || true)
    nf=$(grep -cE "FAIL:|ERROR:" "$LOG" || true)
    res="FAIL(err=$nf)"
    FAILED_SUITES="$FAILED_SUITES $name"
  fi
  echo "| $name | $res | test_methods: $cnt |" >> "$OUT"
  cd "$ROOT" || exit 1
done
echo "" >> "$OUT"
echo "TOTAL test methods: $TOTAL | passed: $PASSED | failed suites:$FAILED_SUITES" >> "$OUT"
echo "WROTE $OUT"
tail -6 "$OUT"
[ -n "$FAILED_SUITES" ] && { echo "FAILED SUITES:$FAILED_SUITES" >&2; exit 1; }
exit 0
