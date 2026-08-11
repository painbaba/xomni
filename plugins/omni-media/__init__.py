"""OmniMedia — XOMNI media-understanding plugin (OpenClaw-style).

Commands: /ocr <image>, /caption <image>, /mediascan <dir> [ocr|caption].
All calls go through the verified vision model (minimax-m3) on the
opencode gateway; failures are reported per-file and never crash a turn.
"""
from __future__ import annotations

from . import core

_CTX = None

HELP = (
    "/ocr <image>            extract all text verbatim from an image\n"
    "/caption <image>        describe an image in 2-3 sentences\n"
    "/mediascan <dir> [ocr|caption]  batch-process a folder (default ocr, max 10 files)\n"
)


def _key() -> str | None:
    return core.load_key()


def _handle_ocr(raw: str) -> str:
    path = (raw or "").strip()
    if not path:
        return "usage: /ocr <image path>"
    result = core.ocr_image(path, _key() or "")
    return result


def _handle_caption(raw: str) -> str:
    path = (raw or "").strip()
    if not path:
        return "usage: /caption <image path>"
    result = core.caption_image(path, _key() or "")
    return result


def _handle_scan(raw: str) -> str:
    parts = (raw or "").split(None, 1)
    directory = parts[0] if parts else ""
    kind = (parts[1] if len(parts) > 1 else "ocr").strip().lower()
    if not directory:
        return "usage: /mediascan <dir> [ocr|caption]"
    if kind not in ("ocr", "caption"):
        return "kind must be 'ocr' or 'caption'"
    try:
        result = core.scan_dir(directory, _key() or "", kind=kind)
    except ValueError as exc:
        return f"scan failed: {exc}"
    lines = [f"scanned {result['scanned']} file(s):"]
    for item in result["items"]:
        mark = "OK " if item["ok"] else "ERR"
        preview = item["result"].replace("\n", " ")[:160]
        lines.append(f"  [{mark}] {item['path']}: {preview}")
    return "\n".join(lines)


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command("ocr", handler=_handle_ocr,
                         description="Extract all text verbatim from an image",
                         args_hint="<image path>")
    ctx.register_command("caption", handler=_handle_caption,
                         description="Describe an image in 2-3 sentences",
                         args_hint="<image path>")
    ctx.register_command("mediascan", handler=_handle_scan,
                         description="Batch OCR/caption a folder of images",
                         args_hint="<dir> [ocr|caption]")
