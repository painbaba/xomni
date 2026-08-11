"""OmniMedia core — media understanding pipeline (OpenClaw-style, via the verified vision model).

Pure stdlib: OCR, captioning and directory scans against the opencode
vision gateway (minimax-m3, verified with base64 frames). Same wire
pattern as the context-loader vision helper, kept independent so the
plugin has no cross-plugin import.

No Hermes imports; unit-testable in isolation.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

VISION_URL = "https://opencode.ai/zen/go/v1/chat/completions"
VISION_MODEL = "minimax-m3"
VISION_MAX_TOKENS = 1200
VISION_TIMEOUT = 120
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"

OCR_PROMPT = (
    "Extract and return ALL text visible in this image, verbatim, preserving "
    "line order. Return only the extracted text and nothing else."
)
CAPTION_PROMPT = "Describe this image in 2-3 concise sentences, factual only."

_MIME_BY_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def image_to_data_url(path: str, max_bytes: int = MAX_IMAGE_BYTES) -> str:
    """Read jpg/jpeg/png as a base64 data URL; ValueError on any problem."""
    path = (path or "").strip()
    if not path:
        raise ValueError("no image path given")
    if not os.path.isfile(path):
        raise ValueError(f"no such file: {path}")
    ext = os.path.splitext(path)[1].lower()
    mime = _MIME_BY_EXT.get(ext)
    if mime is None:
        raise ValueError(f"unsupported image type {ext!r} (use .jpg, .jpeg or .png): {path}")
    size = os.path.getsize(path)
    if size > max_bytes:
        raise ValueError(f"image too large: {size} bytes exceeds the {max_bytes}-byte limit: {path}")
    with open(path, "rb") as f:
        raw = f.read()
    return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"


def _vision(data_url: str, key: str, prompt: str, timeout: int = VISION_TIMEOUT) -> str:
    """One vision completion against the gateway. Error strings start with 'media:'."""
    if not key:
        return "media: no API key provided (OPENCODE_GO_API_KEY missing)"
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": VISION_MAX_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": BROWSER_UA,
    }
    req = urllib.request.Request(
        VISION_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        return f"media: gateway HTTP error {exc.code}"
    except (urllib.error.URLError, OSError) as exc:
        return f"media: gateway unreachable ({exc})"
    try:
        data = json.loads(raw.decode("utf-8", errors="replace"))
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        return f"media: unexpected gateway response: {exc}"
    if not content or not str(content).strip():
        return "media: the model returned an empty result."
    return str(content).strip()


def ocr_image(path: str, key: str) -> str:
    """Extract verbatim text from an image."""
    return _vision(image_to_data_url(path), key, OCR_PROMPT)


def caption_image(path: str, key: str) -> str:
    """Describe an image in 2-3 factual sentences."""
    return _vision(image_to_data_url(path), key, CAPTION_PROMPT)


def scan_dir(directory: str, key: str, kind: str = "ocr", limit: int = 10) -> dict:
    """OCR/caption every jpg/jpeg/png in a directory.

    Returns {'scanned': n, 'items': [{path, ok, result}]} — a failed file
    never aborts the batch; its result carries the 'media:' error string.
    """
    directory = (directory or "").strip()
    if not directory or not os.path.isdir(directory):
        raise ValueError(f"no such directory: {directory}")
    items = []
    for name in sorted(os.listdir(directory)):
        if len(items) >= limit:
            break
        ext = os.path.splitext(name)[1].lower()
        if ext not in _MIME_BY_EXT:
            continue
        full = str(Path(directory) / name)
        try:
            if kind == "caption":
                result = caption_image(full, key)
            else:
                result = ocr_image(full, key)
            ok = not result.startswith("media:")
        except ValueError as exc:
            result = f"media: {exc}"
            ok = False
        items.append({"path": full, "ok": ok, "result": result})
    return {"scanned": len(items), "items": items}


def load_key(env_path: str = r"C:\Users\HP\AppData\Local\hermes\.env") -> str | None:
    """Read OPENCODE_GO_API_KEY from the hermes .env file (never logged)."""
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                if name.strip() == "OPENCODE_GO_API_KEY":
                    return value.strip().strip('"').strip("'")
    except OSError:
        return None
    return None
