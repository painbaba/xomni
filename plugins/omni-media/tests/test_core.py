import base64
import json
import os
import tempfile
import unittest
from pathlib import Path

from core import (
    MAX_IMAGE_BYTES,
    _MIME_BY_EXT,
    caption_image,
    image_to_data_url,
    ocr_image,
    scan_dir,
)


def _write_png(path: str, size: int = 64):
    """A minimal (invalid-to-decoders but structurally fine) PNG header blob.

    The gateway is never hit in unit tests — these files only exercise the
    local data-URL and scan paths.
    """
    header = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
    with open(path, "wb") as f:
        f.write(header + bytes(size))


class OmniMediaCoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_image_to_data_url_roundtrip(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        url = image_to_data_url(str(p))
        self.assertTrue(url.startswith("data:image/png;base64,"))
        raw = base64.b64decode(url.split(",", 1)[1])
        self.assertTrue(raw.startswith(b"\x89PNG"))

    def test_image_to_data_url_rejects_missing(self):
        with self.assertRaises(ValueError):
            image_to_data_url(str(self.root / "nope.png"))

    def test_image_to_data_url_rejects_unsupported_ext(self):
        p = self.root / "doc.pdf"
        p.write_bytes(b"%PDF")
        with self.assertRaises(ValueError):
            image_to_data_url(str(p))

    def test_ocr_without_key_returns_error_string(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        result = ocr_image(str(p), "")
        self.assertTrue(result.startswith("media:"))

    def test_caption_with_bad_key_fails_open(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        result = caption_image(str(p), "not-a-key")
        self.assertTrue(result.startswith("media:") or "media:" in result)

    def test_scan_dir_never_aborts_on_bad_file(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        bad = self.root / "broken.png"
        bad.write_bytes(b"")
        result = scan_dir(str(self.root), "", kind="ocr", limit=10)
        self.assertEqual(result["scanned"], 2)
        self.assertEqual(len(result["items"]), 2)
        oks = [i["ok"] for i in result["items"]]
        self.assertFalse(any(oks))  # no key -> all fail open with media: strings

    def test_scan_dir_skips_non_images(self):
        (self.root / "notes.txt").write_text("hi")
        (self.root / "a.jpg").write_bytes(b"x")
        result = scan_dir(str(self.root), "", kind="ocr")
        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["items"][0]["path"].endswith("a.jpg"), True)

    def test_scan_dir_missing_dir(self):
        with self.assertRaises(ValueError):
            scan_dir(str(self.root / "ghost"), "", kind="ocr")

    def test_mime_map_covers_common_exts(self):
        self.assertIn(".jpg", _MIME_BY_EXT)
        self.assertIn(".jpeg", _MIME_BY_EXT)
        self.assertIn(".png", _MIME_BY_EXT)


if __name__ == "__main__":
    unittest.main()
