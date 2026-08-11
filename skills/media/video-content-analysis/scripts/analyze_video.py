#!/usr/bin/env python
"""One-shot video content analysis: download -> frames -> audio -> vision -> transcript.

Usage:  python analyze_video.py <URL> [workdir]
        python analyze_video.py https://www.instagram.com/reel/XXXXX/

Deps on this host: yt-dlp, ffmpeg, faster-whisper (all under `python` 3.11).
Vision goes through the opencode-go gateway (minimax-m3) using
OPENCODE_GO_API_KEY from ~/AppData/Local/hermes/.env — a browser User-Agent
header is REQUIRED or the gateway 403s (Cloudflare 1010).

Outputs:
  <workdir>/<slug>/video.mp4, frames/fr_*.jpg, audio.mp3
  prints: caption metadata, vision description, transcript.
"""
import base64, glob, json, os, re, subprocess, sys, urllib.request, urllib.error

def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("CMD FAIL:", " ".join(cmd), "\n", r.stderr[-800:], file=sys.stderr)
        raise SystemExit(1)
    return r

def load_key():
    p = os.path.expanduser("~/AppData/Local/hermes/.env")
    for line in open(p, encoding="utf-8", errors="ignore"):
        m = re.match(r'\s*OPENCODE_GO_API_KEY\s*=\s*"?([^"\s]+)', line)
        if m:
            return m.group(1)
    raise SystemExit("no OPENCODE_GO_API_KEY in " + p)

def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    url = sys.argv[1]
    workdir = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/Downloads"))
    slug = re.sub(r'\W+', '_', url.split('/')[-1].split('?')[0]) or "video"
    out = os.path.join(workdir, slug)
    os.makedirs(os.path.join(out, "frames"), exist_ok=True)

    # 1) metadata
    sh(["yt-dlp", "--skip-download", "--no-warnings",
        "--print", "%(title)s ||| %(uploader)s ||| %(description)s", url])
    # 2) download
    sh(["yt-dlp", "--no-warnings", "-f", "best[ext=mp4]/best",
        "-o", os.path.join(out, "video.%(ext)s"), url])
    video = glob.glob(os.path.join(out, "video.*"))[0]
    # 3) frames (1 per 4s) + 4) audio
    sh(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf", "fps=1/4", "-q:v", "3",
        os.path.join(out, "frames", "fr_%02d.jpg")])
    sh(["ffmpeg", "-y", "-v", "error", "-i", video, "-ar", "16000", "-ac", "1",
        os.path.join(out, "audio.mp3")])

    # 5) vision via gateway
    key = load_key()
    H = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}
    frames = sorted(glob.glob(os.path.join(out, "frames", "fr_*.jpg")))
    step = max(1, len(frames) // 6)
    sel = frames[::step][:6]
    content = [{"type": "text", "text": (
        "Frames from a video. Describe each frame precisely: all visible text/captions "
        "verbatim, action, any code/terminal/website screenshots, and what feat or claim "
        "the video demonstrates.")}]
    for p in sel:
        b64 = base64.b64encode(open(p, "rb").read()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    req = urllib.request.Request(
        "https://opencode.ai/zen/go/v1/chat/completions",
        data=json.dumps({"model": "minimax-m3",
                         "messages": [{"role": "user", "content": content}],
                         "max_tokens": 1500}).encode(), headers=H)
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            vision = json.loads(r.read().decode())["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        vision = f"(vision failed {e.code}: {e.read().decode()[:300]})"
    print("\n=== VISION ===\n" + vision)

    # 6) transcription
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segs, _ = model.transcribe(os.path.join(out, "audio.mp3"),
                                   language="en", vad_filter=True)
        print("\n=== TRANSCRIPT ===")
        for s in segs:
            print(f"[{s.start:6.1f}-{s.end:6.1f}] {s.text.strip()}")
    except ImportError:
        print("\n(no faster-whisper in this python; install via: uv pip install --system faster-whisper)")

    print("\nArtifacts:", out)

if __name__ == "__main__":
    main()
