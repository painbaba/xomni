#!/usr/bin/env python
"""One-shot analysis of an Instagram reel (or any yt-dlp-supported video URL).

Usage:  python analyze_reel.py "<video-url>"
Run with `python` (3.11) — faster-whisper is installed only there, not python3/uv 3.14.

Pipeline: yt-dlp metadata -> download -> ffmpeg keyframes -> vision (minimax-m3 via
opencode-go gateway) -> faster-whisper transcript. Prints META, FRAMES, VISION, TRANSCRIPT.
Requires: yt-dlp + ffmpeg on PATH; OPENCODE_GO_API_KEY in ~/AppData/Local/hermes/.env.
"""
import base64, glob, json, os, re, subprocess, sys, urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: python analyze_reel.py <url>")
WORK = os.path.expanduser("~/Downloads/reel_analysis")
os.makedirs(WORK, exist_ok=True)

def sh(*cmd):
    return subprocess.run(list(cmd), capture_output=True, text=True)

# 1) metadata + caption
r = sh("yt-dlp", "--skip-download", "--no-warnings",
       "--print", "%(title)s ||| %(uploader)s ||| %(description)s", URL)
print("=== META ===")
print((r.stdout or r.stderr)[:1500])

# 2) download
r = sh("yt-dlp", "--no-warnings", "-f", "best[ext=mp4]/best",
       "-o", os.path.join(WORK, "reel.%(ext)s"), URL)
video = None
for c in glob.glob(os.path.join(WORK, "reel.*")):
    if c.lower().endswith((".mp4", ".mov", ".webm", ".mkv")):
        video = c
if not video:
    sys.exit("DOWNLOAD FAILED: " + (r.stderr or r.stdout)[-500:])
print("=== DOWNLOAD OK:", video, "===")

# 3) keyframes (explicit real path — never /tmp with native ffmpeg)
sh("ffmpeg", "-y", "-v", "error", "-i", video, "-vf", "fps=1/4",
   "-q:v", "3", os.path.join(WORK, "fr_%02d.jpg"))
frames = sorted(glob.glob(os.path.join(WORK, "fr_*.jpg")))
print(f"=== FRAMES: {len(frames)} ===")

# 4) vision via opencode-go gateway (browser UA required, see skill pitfalls)
def load_key():
    with open(os.path.expanduser("~/AppData/Local/hermes/.env")) as f:
        for line in f:
            m = re.match(r'\s*OPENCODE_GO_API_KEY\s*=\s*"?([^"\s]+)', line)
            if m:
                return m.group(1)
    raise SystemExit("OPENCODE_GO_API_KEY not found in .env")

KEY = load_key()
BASE = "https://opencode.ai/zen/go/v1"
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}

def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=H)
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode())

step = max(1, len(frames) // 8)
sel = frames[::step][:8]
content = [{"type": "text", "text": (
    "Frames from a social-media video. For each frame, describe exactly what is on "
    "screen: all visible text/captions verbatim, action, any UI/code/screenshots, and "
    "what claim or stunt the video demonstrates.")}]
for p in sel:
    b64 = base64.b64encode(open(p, "rb").read()).decode()
    content.append({"type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
resp = post(BASE + "/chat/completions", {"model": "minimax-m3",
    "messages": [{"role": "user", "content": content}], "max_tokens": 1600})
print("=== VISION ===")
print(resp["choices"][0]["message"]["content"])

# 5) transcript via faster-whisper
sh("ffmpeg", "-y", "-v", "error", "-i", video, "-ar", "16000", "-ac", "1",
   os.path.join(WORK, "reel_audio.mp3"))
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, info = model.transcribe(os.path.join(WORK, "reel_audio.mp3"),
                                  language="en", vad_filter=True)
print("=== TRANSCRIPT ===")
for s in segments:
    print(f"[{s.start:6.1f}-{s.end:6.1f}] {s.text.strip()}")
