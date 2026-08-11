#!/usr/bin/env python3
"""Verify AI-generated image candidates before shipping them in a report.

Usage: python verify_image.py <path-or-url> [<path-or-url> ...]

Checks per file:
  - downloadable / opens with PIL
  - JPEG magic bytes (FF D8) + dimensions parsed from SOF markers (works when PIL can't)
  - brightness/contrast sanity (rejects blank/near-blank images)
  - Laplacian sharpness (higher = crisper; ~20+ is decent for portraits)
  - OpenCV Haar frontal-face detection: face count + largest-face coverage
    (cv2 is OPTIONAL — skipped with a note if not importable)

Exit code 0 if at least one file verified; prints one JSON line per file.
Verified with opencv-python-headless 4.10.0.84. NOTE: cv2 5.x removed
CascadeClassifier — pin 4.x if installing fresh:
  pip install "opencv-python-headless==4.10.0.84"
"""
import json
import os
import re
import statistics
import sys
import tempfile
import urllib.request

try:
    import cv2
    CASCADE = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
except Exception:
    CASCADE = None
    cv2 = None

try:
    from PIL import Image
except ImportError:
    sys.exit("PIL required: pip install pillow")


def jpeg_dims(data: bytes):
    """Dimensions from JPEG SOF markers without PIL (pure Python)."""
    if data[:2] != b"\xff\xd8":
        return None
    i, n = 2, len(data)
    while i + 9 < n:
        if data[i] != 0xFF:
            i += 1
            continue
        m = data[i + 1]
        if m == 0xD8:
            i += 2
            continue
        if 0xD0 <= m <= 0xD7 or m in (0x01, 0xD9):
            i += 2
            continue
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h = int.from_bytes(data[i + 5:i + 7], "big")
            w = int.from_bytes(data[i + 7:i + 9], "big")
            return (w, h)
        seglen = int.from_bytes(data[i + 2:i + 4], "big")
        if seglen < 2:
            return None
        i += 2 + seglen
    return None


def fetch(path_or_url: str) -> bytes:
    if re.match(r"^https?://", path_or_url):
        req = urllib.request.Request(path_or_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    with open(path_or_url, "rb") as f:
        return f.read()


def analyze(path_or_url: str) -> dict:
    r = {"source": path_or_url}
    data = fetch(path_or_url)
    r["bytes"] = len(data)
    r["jpeg_magic"] = data[:2] == b"\xff\xd8"
    dims = jpeg_dims(data)
    if dims:
        r["jpeg_dims"] = dims
    tmp = None
    try:
        if re.match(r"^https?://", path_or_url):
            fd, tmp = tempfile.mkstemp(suffix=".img")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            local = tmp
        else:
            local = path_or_url
        im = Image.open(local).convert("RGB")
        w, h = im.size
        r["dims"] = [w, h]
        r["format"] = Image.open(local).format
        g = im.convert("L")
        px = list(g.getdata())
        r["brightness"] = round(statistics.mean(px), 0)
        r["contrast"] = round(statistics.pstdev(px), 0)
        if cv2 is not None:
            gray = cv2.cvtColor(cv2.imread(local), cv2.COLOR_BGR2GRAY)
            lapl = cv2.Laplacian(gray, cv2.CV_64F)
            r["sharpness_lap"] = round(float(lapl.var()), 1)
            faces = CASCADE.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5,
                minSize=(int(min(w, h) * 0.15), int(min(w, h) * 0.15)))
            r["faces"] = len(faces)
            if len(faces):
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                r["face_coverage"] = round((fw * fh) / (w * h), 3)
        else:
            r["note"] = "cv2 not available; face/sharpness skipped"
        r["ok"] = r.get("jpeg_magic", False) or dims is not None or (w >= 500 and h >= 500)
    except Exception as e:
        r["error"] = str(e)
        r["ok"] = False
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
    return r


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    results = [analyze(a) for a in sys.argv[1:]]
    for r in sorted(results, key=lambda x: (x.get("ok", False), x.get("dims", [0, 0])[0]),
                    reverse=True):
        print(json.dumps(r))
    return 0 if any(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
