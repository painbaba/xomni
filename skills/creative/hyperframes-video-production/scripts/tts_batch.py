#!/usr/bin/env python3
"""tts_batch.py — generate edge-tts narration mp3s for documentary scenes.

Usage: python tts_batch.py scenes.json outdir [--voice en-US-ChristopherNeural] [--rate +8%]

scenes.json: [{"id": "a1s1", "text": "...", "rate": "+8%", "pitch": "-2Hz"}]
Output: outdir/<id>.mp3 for each scene + outdir/durations.json {"<id>": seconds}

Pitfalls encoded (all cost debugging time):
- rate/pitch must use the `=` form (--rate=-12%) — argparse eats `-12%` as a flag.
- subprocess must use sys.executable, not "python" (PATH can resolve a
  different interpreter than the one running this script).
- wpm varies 90-170 for the SAME rate depending on text — always derive
  scene durations from the measured ffprobe durations, never from word counts.
"""
import json, subprocess, sys, os

def main():
    manifest_path, outdir = sys.argv[1], sys.argv[2]
    voice = "en-US-ChristopherNeural"
    rate = "+0%"
    if "--voice" in sys.argv:
        voice = sys.argv[sys.argv.index("--voice") + 1]
    if "--rate" in sys.argv:
        rate = sys.argv[sys.argv.index("--rate") + 1]

    os.makedirs(outdir, exist_ok=True)
    scenes = json.load(open(manifest_path, encoding="utf-8"))
    durations = {}
    for i, sc in enumerate(scenes):
        mp3 = os.path.join(outdir, sc["id"] + ".mp3")
        cmd = [sys.executable, "-m", "edge_tts", "--voice", sc.get("voice", voice),
               f"--rate={sc.get('rate', rate)}"]
        if sc.get("pitch"):
            cmd += [f"--pitch={sc['pitch']}"]
        cmd += ["--text", sc["text"], "--write-media", mp3]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"[FAIL] {sc['id']}: {r.stderr[-300:]}", flush=True)
            continue
        dur = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", mp3], capture_output=True, text=True)
        durations[sc["id"]] = round(float(dur.stdout.strip()), 2)
        words = len(sc["text"].split())
        print(f"[{i+1}/{len(scenes)}] {sc['id']}: {durations[sc['id']]}s "
              f"({words/durations[sc['id']]*60:.0f} wpm)", flush=True)
    json.dump(durations, open(os.path.join(outdir, "durations.json"), "w"), indent=1)
    print("TOTAL AUDIO:", round(sum(durations.values())/60, 1), "min")

if __name__ == "__main__":
    main()
