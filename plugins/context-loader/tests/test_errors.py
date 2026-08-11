"""Error paths, caps and arg handling for the context-loader plugin (core.py + handlers)."""
import base64
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_DIR = os.path.dirname(_HERE)
sys.path.insert(0, os.path.dirname(_PLUGIN_DIR))  # plugins/ (for sibling imports)
sys.path.insert(0, _PLUGIN_DIR)                   # context-loader/ -> import core

import core  # noqa: E402
import urllib.error  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class FetchPageErrorPathTests(unittest.TestCase):
    def _mock_resp(self, body: bytes, status: int = 200, charset=None):
        resp = mock.MagicMock()
        resp.status = status
        resp.read.return_value = body
        if charset is None:
            resp.headers = {}  # no get_content_charset -> utf-8 fallback
        else:
            resp.headers = mock.MagicMock()
            resp.headers.get_content_charset.return_value = charset
        return resp

    def test_empty_url_rejected(self):
        with mock.patch("urllib.request.urlopen") as uo:
            self.assertIn("no URL given", core.fetch_page(""))
            self.assertIn("no URL given", core.fetch_page("   "))
        uo.assert_not_called()

    def test_uppercase_scheme_accepted(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(b"<p>hi</p>")
            out = core.fetch_page("HTTPS://example.com/page")
        self.assertIn("URL: HTTPS://example.com/page", out)
        self.assertIn("hi", out)

    def test_mailto_and_file_schemes_rejected(self):
        with mock.patch("urllib.request.urlopen") as uo:
            self.assertIn("only http/https", core.fetch_page("mailto:a@b.com"))
            self.assertIn("only http/https", core.fetch_page("file:///etc/passwd"))
        uo.assert_not_called()

    def test_oserror_fallback(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = OSError("connection reset by peer")
            out = core.fetch_page("https://example.com/")
        self.assertIn("request failed", out)
        self.assertIn("connection reset", out)

    def test_http_error_without_body(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = urllib.error.HTTPError("https://example.com/", 500, "Err", {}, None)
            out = core.fetch_page("https://example.com/")
        self.assertIn("HTTP error 500", out)

    def test_custom_max_bytes_cap(self):
        body = b"<p>" + b"a" * 150 + b"</p>"
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(body)
            out = core.fetch_page("https://example.com/big", max_bytes=100)
        self.assertIn("truncated at 100 bytes", out)
        self.assertLessEqual(len(out), 500)

    def test_exact_cap_not_truncated(self):
        body = b"<p>ok</p>"
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(body)
            out = core.fetch_page("https://example.com/", max_bytes=len(body))
        self.assertNotIn("truncated", out)

    def test_response_charset_honored(self):
        body = "<p>caf\u00e9</p>".encode("latin-1")
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(body, charset="latin-1")
            out = core.fetch_page("https://example.com/")
        self.assertIn("caf\u00e9", out)


class HtmlToTextExtraTests(unittest.TestCase):
    def test_strips_noscript_and_template(self):
        html = "<noscript>enable js</noscript><template><p>tpl</p></template><p>real</p>"
        out = core.html_to_text(html)
        self.assertNotIn("enable js", out)
        self.assertNotIn("tpl", out)
        self.assertIn("real", out)

    def test_strips_comments(self):
        out = core.html_to_text("<p>a</p><!-- secret --><p>b</p>")
        self.assertNotIn("secret", out)
        self.assertIn("a", out)
        self.assertIn("b", out)

    def test_unsafe_link_variants_dropped(self):
        for href in ("data:text/html,x", "vbscript:msgbox(1)", ""):
            out = core.html_to_text(f'<a href="{href}">keep me</a>')
            self.assertIn("keep me", out)
            self.assertNotIn("](", out)  # no link syntax, plain text only

    def test_punctuation_spacing_fixed(self):
        out = core.html_to_text("<p>Hello , world ! What ?</p>")
        self.assertIn("Hello, world! What?", out)
        self.assertNotIn(" ,", out)

    def test_title_only_page(self):
        out = core.html_to_text("<html><head><title>Only</title></head></html>")
        self.assertTrue(out.startswith("Title: Only"), out)


class ImageDataUrlErrorPathTests(unittest.TestCase):
    def test_empty_path_raises(self):
        with self.assertRaises(ValueError) as ctx:
            core.image_to_data_url("")
        self.assertIn("no image path given", str(ctx.exception))

    def test_directory_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError) as ctx:
                core.image_to_data_url(d)
            self.assertIn("no such file", str(ctx.exception))

    def test_uppercase_extension_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "IMG.PNG")
            with open(p, "wb") as f:
                f.write(PNG)
            out = core.image_to_data_url(p)
        self.assertTrue(out.startswith("data:image/png;base64,"))

    def test_exact_size_boundary_ok(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "edge.png")
            with open(p, "wb") as f:
                f.write(b"x" * 50)
            out = core.image_to_data_url(p, max_bytes=50)
        self.assertTrue(out.startswith("data:image/png;base64,"))

    def test_one_byte_over_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "big.png")
            with open(p, "wb") as f:
                f.write(b"x" * 51)
            with self.assertRaises(ValueError) as ctx:
                core.image_to_data_url(p, max_bytes=50)
            self.assertIn("too large", str(ctx.exception))


class VisionErrorPathTests(unittest.TestCase):
    DATA_URL = "data:image/png;base64,AAAA"

    def test_unexpected_response_shape(self):
        with mock.patch("urllib.request.urlopen") as uo:
            resp = mock.MagicMock()
            resp.read.return_value = json.dumps({"foo": 1}).encode("utf-8")
            uo.return_value.__enter__.return_value = resp
            out = core.vision_describe(self.DATA_URL, "k")
        self.assertIn("unexpected gateway response", out)

    def test_whitespace_content_treated_as_empty(self):
        with mock.patch("urllib.request.urlopen") as uo:
            resp = mock.MagicMock()
            resp.read.return_value = json.dumps({"choices": [{"message": {"content": "   "}}]}).encode("utf-8")
            uo.return_value.__enter__.return_value = resp
            out = core.vision_describe(self.DATA_URL, "k")
        self.assertIn("empty description", out)

    def test_oserror_unreachable(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = OSError("timeout")
            out = core.vision_describe(self.DATA_URL, "k")
        self.assertIn("gateway unreachable", out)

    def test_http_error_with_unreadable_body(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = urllib.error.HTTPError(core.VISION_URL, 403, "Forbidden", {}, None)
            out = core.vision_describe(self.DATA_URL, "k")
        self.assertIn("403", out)


class LoadKeyExtraTests(unittest.TestCase):
    def test_whitespace_value_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("OPENCODE_GO_API_KEY=   \n")
            self.assertIsNone(core.load_key(env))

    def test_single_quoted_value(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("OPENCODE_GO_API_KEY='sk-single'\n")
            self.assertEqual(core.load_key(env), "sk-single")

    def test_padded_key_and_value(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("OPENCODE_GO_API_KEY = sk-padded\n")
            self.assertEqual(core.load_key(env), "sk-padded")

    def test_comment_only_file_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("# nothing here\n")
            self.assertIsNone(core.load_key(env))


# ---------------------------------------------------------------------------
# describe_image / fetch handlers — hyphenated dir name, so load __init__.py by
# file with an importlib harness and pre-seed the submodule.
# ---------------------------------------------------------------------------

def _load_plugin_module():
    spec = importlib.util.spec_from_file_location(
        "context_loader_plug2", os.path.join(_PLUGIN_DIR, "__init__.py")
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__path__ = [_PLUGIN_DIR]
    sys.modules["context_loader_plug2"] = mod
    sys.modules["context_loader_plug2.core"] = core
    spec.loader.exec_module(mod)
    return mod


class DescribeArgHandlingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_plugin_module()
        cls.addClassCleanup(sys.modules.pop, "context_loader_plug2", None)
        cls.addClassCleanup(sys.modules.pop, "context_loader_plug2.core", None)

    def test_describe_missing_path(self):
        out = self.mod._describe_image_tool({})
        self.assertIn("missing required argument 'path'", out)
        out = self.mod._describe_image_tool({"path": "   "})
        self.assertIn("missing required argument 'path'", out)

    def test_describe_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "img.gif")
            with open(p, "wb") as f:
                f.write(b"GIF89a")
            out = self.mod._describe_image_tool({"path": p})
        self.assertIn("unsupported image type", out)

    def test_describe_oversize_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "huge.png")
            with open(p, "wb") as f:
                f.write(b"x" * (core.DEFAULT_MAX_IMAGE_BYTES + 1))
            out = self.mod._describe_image_tool({"path": p})
        self.assertIn("image too large", out)

    def test_describe_vision_error_propagated(self):
        with mock.patch.object(core, "load_key", return_value="k") as lk, \
             mock.patch.object(core, "vision_describe", return_value="vision: gateway HTTP error 403") as vd:
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "x.png")
                with open(p, "wb") as f:
                    f.write(PNG)
                out = self.mod._describe_image_tool({"path": p})
        self.assertEqual(out, "vision: gateway HTTP error 403")
        self.assertTrue(lk.called)
        self.assertTrue(vd.called)

    def test_describe_tilde_expansion(self):
        out = self.mod._describe_image_tool({"path": "~/definitely-not-here-xyz.png"})
        self.assertNotIn("missing required", out)
        self.assertIn("no such file", out)

    def test_fetch_command_no_args_shows_help(self):
        self.assertEqual(self.mod._handle_fetch(""), self.mod.HELP_FETCH)
        self.assertEqual(self.mod._handle_fetch("   "), self.mod.HELP_FETCH)

    def test_describe_command_no_args_shows_help(self):
        self.assertEqual(self.mod._handle_describe(""), self.mod.HELP_DESCRIBE)

    def test_fetch_command_bad_scheme(self):
        self.assertIn("only http/https", self.mod._handle_fetch("ftp://x"))

    def test_describe_command_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "img.gif")
            with open(p, "wb") as f:
                f.write(b"GIF89a")
            out = self.mod._handle_describe(p)
        self.assertIn("/describe: unsupported image type", out)


if __name__ == "__main__":
    unittest.main()
