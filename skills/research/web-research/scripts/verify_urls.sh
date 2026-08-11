#!/usr/bin/env bash
# verify_urls.sh — batch live-verifier for URL lists.
# Prints one line per URL: "HTTP_CODE | url | <title>"
# Usage:
#   ./verify_urls.sh https://a.example https://b.example ...
#   cat urls.txt | ./verify_urls.sh
#
# Design notes (learned the hard way, Aug 2026):
#   - Writes scratch to a LOCAL dir, never /tmp (on this Windows/MSYS host /tmp can be
#     missing or 100% full -> curl -o writes fail SILENTLY while status codes still print).
#   - A fake/bot-blocked page is still a 2xx/3xx: follow up with title extraction; an
#     empty title on a 200 often means client-rendered (Observable, Remotion, Motion Canvas)
#     — in that case the HTTP status IS the verification signal.
#   - A 404 on a known-good site may be a wrong URL pattern, not a dead page: retry
#     plural/singular, trailing-slash, and "Plugin"-suffix variants before declaring it dead.
#   - --retry handles transient 429s/5xx (Observable rate-limits aggressively).

set -u
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
SCRATCH="${VERIFY_SCRATCH:-$HOME/.verify_scratch}"
mkdir -p "$SCRATCH"

urls=("$@")
if [ ${#urls[@]} -eq 0 ]; then
  while IFS= read -r u; do
    [ -n "$u" ] && urls+=("$u")
  done
fi

for u in "${urls[@]}"; do
  f="$SCRATCH/pg.html"
  code=$(curl -sL --max-time 20 --retry 2 --retry-delay 2 -A "$UA" -o "$f" -w "%{http_code}" "$u" 2>/dev/null)
  title=$(grep -oiP '(?<=<title>).*?(?=</title>)' "$f" 2>/dev/null | head -1 | tr -d '\r\n' | cut -c1-100)
  echo "$code | $u | $title"
  sleep 0.3   # be polite; also dodges aggressive rate-limiters
done

rm -f "$SCRATCH/pg.html"
