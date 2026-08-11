import base64
import os
import tempfile
import unittest
from pathlib import Path

from core import (
    MAX_IMAGE_BYTES,
    _MIME_BY_EXT,
    caption_image,
    image_to_data_url,
    load_key,
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

    # --------------------------------------------------------- data-url roundtrip
    def test_image_to_data_url_roundtrip(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        url = image_to_data_url(str(p))
        self.assertTrue(url.startswith("data:image/png;base64,"))
        raw = base64.b64decode(url.split(",", 1)[1])
        self.assertTrue(raw.startswith(b"\x89PNG"))

    def test_image_to_data_url_jpg_and_jpeg_mime(self):
        for name, mime in (("a.jpg", "image/jpeg"), ("b.jpeg", "image/jpeg")):
            p = self.root / name
            p.write_bytes(b"x")
            self.assertTrue(image_to_data_url(str(p)).startswith(f"data:{mime};base64,"))

    def test_image_to_data_url_rejects_missing(self):
        with self.assertRaises(ValueError):
            image_to_data_url(str(self.root / "nope.png"))

    def test_image_to_data_url_empty_and_none_raise(self):
        with self.assertRaises(ValueError):
            image_to_data_url("")
        with self.assertRaises(ValueError):
            image_to_data_url(None)

    def test_image_to_data_url_rejects_unsupported_ext(self):
        p = self.root / "doc.pdf"
        p.write_bytes(b"%PDF")
        with self.assertRaises(ValueError):
            image_to_data_url(str(p))

    def test_image_to_data_url_custom_max_bytes_raises(self):
        p = self.root / "shot.png"
        _write_png(str(p))  # 72 bytes
        with self.assertRaises(ValueError):
            image_to_data_url(str(p), max_bytes=16)

    def test_image_to_data_url_default_max_bytes_raises(self):
        p = self.root / "huge.png"
        with open(p, "wb") as f:
            f.truncate(MAX_IMAGE_BYTES + 1)
        with self.assertRaises(ValueError):
            image_to_data_url(str(p))

    # ------------------------------------------------------------ ocr/caption args
    def test_ocr_image_missing_file_raises(self):
        with self.assertRaises(ValueError):
            ocr_image(str(self.root / "ghost.png"), "key")

    def test_caption_image_missing_file_raises(self):
        with self.assertRaises(ValueError):
            caption_image(str(self.root / "ghost.png"), "key")

    def test_ocr_image_unsupported_ext_raises(self):
        p = self.root / "notes.txt"
        p.write_text("hi")
        with self.assertRaises(ValueError):
            ocr_image(str(p), "key")

    def test_ocr_without_key_returns_error_string(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        result = ocr_image(str(p), "")
        self.assertTrue(result.startswith("media:"))

    def test_caption_without_key_returns_media_error(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        result = caption_image(str(p), "")
        self.assertTrue(result.startswith("media: no API key provided"))

    def test_caption_with_bad_key_fails_open(self):
        p = self.root / "shot.png"
        _write_png(str(p))
        result = caption_image(str(p), "not-a-key")
        self.assertTrue(result.startswith("media:") or "media:" in result)

    def test_ocr_zero_byte_image_fails_open(self):
        p = self.root / "empty.png"
        p.write_bytes(b"")
        result = ocr_image(str(p), "")
        self.assertTrue(result.startswith("media:"))

    # ------------------------------------------------------------------ scan_dir
    def test_scan_dir_output_shape_empty_dir(self):
        result = scan_dir(str(self.root), "", kind="ocr")
        self.assertEqual(result, {"scanned": 0, "items": []})
        self.assertEqual(set(result.keys()), {"scanned", "items"})

    def test_scan_dir_item_shape(self):
        _write_png(str(self.root / "a.png"))
        result = scan_dir(str(self.root), "", kind="ocr")
        self.assertEqual(result["scanned"], 1)
        item = result["items"][0]
        self.assertEqual(set(item.keys()), {"path", "ok", "result"})
        self.assertIsInstance(item["path"], str)
        self.assertIsInstance(item["result"], str)
        self.assertFalse(item["ok"])

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

    def test_scan_dir_corrupt_image_fails_open(self):
        p = self.root / "corrupt.png"
        p.write_bytes(b"\x89PNG garbage that is not really an image" * 4)
        result = scan_dir(str(self.root), "", kind="ocr")
        self.assertEqual(result["scanned"], 1)
        item = result["items"][0]
        self.assertFalse(item["ok"])
        self.assertTrue(item["result"].startswith("media:"))

    def test_scan_dir_caption_kind_fails_open_without_key(self):
        _write_png(str(self.root / "a.png"))
        result = scan_dir(str(self.root), "", kind="caption")
        self.assertEqual(result["scanned"], 1)
        item = result["items"][0]
        self.assertFalse(item["ok"])
        self.assertTrue(item["result"].startswith("media:"))

    def test_scan_dir_unknown_kind_defaults_to_ocr(self):
        _write_png(str(self.root / "a.png"))
        result = scan_dir(str(self.root), "", kind="bogus-kind")
        self.assertEqual(result["scanned"], 1)
        self.assertFalse(result["items"][0]["ok"])
        self.assertTrue(result["items"][0]["result"].startswith("media:"))

    def test_scan_dir_respects_limit(self):
        for i in range(5):
            _write_png(str(self.root / f"img{i}.png"))
        result = scan_dir(str(self.root), "", kind="ocr", limit=3)
        self.assertEqual(result["scanned"], 3)
        self.assertEqual(len(result["items"]), 3)

    def test_scan_dir_skips_non_images(self):
        (self.root / "notes.txt").write_text("hi")
        (self.root / "a.jpg").write_bytes(b"x")
        result = scan_dir(str(self.root), "", kind="ocr")
        self.assertEqual(result["scanned"], 1)
        self.assertEqual(result["items"][0]["path"].endswith("a.jpg"), True)

    def test_scan_dir_missing_dir(self):
        with self.assertRaises(ValueError):
            scan_dir(str(self.root / "ghost"), "", kind="ocr")

    def test_scan_dir_none_and_empty_directory_raise(self):
        with self.assertRaises(ValueError):
            scan_dir(None, "", kind="ocr")
        with self.assertRaises(ValueError):
            scan_dir("   ", "", kind="ocr")

    def test_mime_map_covers_common_exts(self):
        self.assertIn(".jpg", _MIME_BY_EXT)
        self.assertIn(".jpeg", _MIME_BY_EXT)
        self.assertIn(".png", _MIME_BY_EXT)

    # ---------------------------------------------------------------- load_key
    def test_load_key_missing_env_returns_none(self):
        self.assertIsNone(load_key(str(self.root / "nope.env")))

    def test_load_key_parses_value_and_strips_quotes(self):
        env = self.root / ".env"
        env.write_text('OPENCODE_GO_API_KEY = "my-media-key"\n', encoding="utf-8")
        self.assertEqual(load_key(str(env)), "my-media-key")


if __name__ == "__main__":
    unittest.main()
