#!/usr/bin/env bash
# Verify the Camofox anti-detection browser server is up and usable.
# Usage: ./verify-camofox.sh [CAMOFOX_URL]   (default http://localhost:9377)
set -u
BASE="${1:-http://localhost:9377}"

echo "== health =="
HEALTH=$(curl -s --max-time 10 "$BASE/health")
echo "$HEALTH" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print('ok:', d.get('ok'), '| engine:', d.get('engine'), '| browserRunning:', d.get('browserRunning'))
    if d.get('engine') != 'camoufox':
        print('WARNING: engine is not camoufox — plain browser may be in use')
except Exception as e:
    print('FAILED to parse health (server up?):', e)
" || echo "FAILED: server not reachable at $BASE"

echo "== open test tab (bot.sannysoft.com) =="
TAB=$(curl -s --max-time 60 -X POST "$BASE/tabs" -H "Content-Type: application/json" \
  -d '{"url":"https://bot.sannysoft.com/","userId":"verify-script","listItemId":"verify"}')
echo "$TAB"
echo "$TAB" | python -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tab = d.get('tabId')
    if tab:
        print('OK tabId:', tab)
    else:
        print('WARNING: no tabId — response:', d)
except Exception as e:
    print('FAILED to parse tab response:', e)
" || echo "FAILED: tab open call errored"

# NOTE: GET /tabs/{tabId}/snapshot needs params (see browser_camofox.py camofox_snapshot()).
# Fingerprint deep-check (expect Firefox UA, no HeadlessChrome, no webdriver flags)
# can be done by opening https://bot.sannysoft.com/ in the Hermes browser once
# CAMOFOX_URL is set and reading the result table.
echo "== done =="
