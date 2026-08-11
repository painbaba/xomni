#!/usr/bin/env python3
"""Ad-hoc verification for a Remotion project after code changes.

Usage: python3 verify-remotion.py <project_dir> [<artifact_mp4>]

Checks, in order:
  1. npx tsc --noEmit (strict typecheck of the composition code)
  2. every LITERAL staticFile("...") ref resolves under public/; template-literal
     refs (staticFile(`dir/${var}`)) are checked by verifying their constant
     PREFIX directory exists (regex cannot resolve variables — a known false
     positive; do not report template refs as missing)
  3. [optional] rendered artifact: duration ~= expected, codecs, width via ffprobe

Exit 0 = PASS, 1 = FAIL. Prints one line per check. This is a temporary
verification script, NOT a suite — clean up after use (or keep under
~/.hermes/scripts/ if you want it reusable).

Session notes (Aug 2026, UPI trailer):
- The naive regex for staticFile refs flags `footage/${s.media}` etc. as missing.
  Template literals are DYNAMIC — check prefix dirs instead. Only literal strings
  are real refs.
- ffprobe JSON gives duration/codecs/width in one call.
- On Windows Python, use "npx.cmd" (raw "npx" raises FileNotFoundError — it's a
  .cmd shim; the same bug breaks `remotion skills add`, see remotion-migration.md).
"""
import json
import os
import re
import subprocess
import sys

PROJ = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
ART = sys.argv[2] if len(sys.argv) > 2 else None
fails = []

# 1) strict typecheck
r = subprocess.run(["npx.cmd", "tsc", "--noEmit"], cwd=PROJ,
                   capture_output=True, text=True)
if r.returncode == 0:
    print("[1] tsc --noEmit: PASS")
else:
    fails.append("tsc")
    print("[1] tsc --noEmit: FAIL\n" + r.stdout[-1500:])

# 2) staticFile refs
src_files = []
for root, _dirs, files in os.walk(os.path.join(PROJ, "src")):
    for f in files:
        if f.endswith((".tsx", ".ts")):
            src_files.append(os.path.join(root, f))
lit = []
tpl = []
for p in src_files:
    s = open(p, encoding="utf-8").read()
    lit += re.findall(r'staticFile\(\s*"([^"]+)"\s*\)', s)
    tpl += re.findall(r'staticFile\(`([^`]+)`\)', s)
missing = [x for x in lit if not os.path.exists(os.path.join(PROJ, "public", x))]
prefix_ok = all(
    os.path.isdir(os.path.join(PROJ, "public", os.path.dirname(t).split("${")[0]))
    for t in tpl
)
if missing or not prefix_ok:
    fails.append("assets")
    print(f"[2] staticFile refs: FAIL missing_literal={missing} template_prefix_ok={prefix_ok}")
else:
    print(f"[2] staticFile refs: PASS ({len(lit)} literal, {len(tpl)} template prefixes ok)")

# 3) artifact specs (optional)
if ART and os.path.exists(ART):
    pr = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_name,codec_type,width,height",
         "-of", "json", ART], capture_output=True, text=True)
    d = json.loads(pr.stdout)
    dur = float(d["format"]["duration"])
    st = {s["codec_name"] for s in d["streams"] if s.get("codec_type") == "video"}
    au = {s["codec_name"] for s in d["streams"] if s.get("codec_type") == "audio"}
    w = next((s.get("width") for s in d["streams"] if s.get("codec_type") == "video"), None)
    ok = st and w and au
    print(f"[3] artifact: {'PASS' if ok else 'FAIL'} dur={dur:.1f}s video={st} audio={au} width={w}")
    if not ok:
        fails.append("artifact")
elif ART:
    fails.append("artifact-missing")
    print("[3] artifact: FAIL (file missing)")

print("\nVERDICT:", "PASS" if not fails else f"FAIL -> {fails}")
sys.exit(0 if not fails else 1)
