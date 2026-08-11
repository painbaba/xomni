"""Tests for the context-loader plugin (core.py + register() wiring).

Covers: html_to_text (strip script/style/tags, keep title/headings/links,
collapse whitespace), fetch_page (success w/ browser UA + timeout, HTTP error,
bad scheme, network error, 512KB cap), image_to_data_url (size cap, missing
file, unsupported type), vision_describe (request build asserts browser UA +
model minimax-m3 + image_url content, gateway-unreachable fallback, empty
assistant content), load_key (found/missing), and the register() wiring
(toolsets "web"/"file" + /fetch and /describe commands).
"""
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

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Example — Test Page</title>
<style>body { color: red; }</style>
<script>alert('nope');</script></head>
<body>
<h1>Big Heading</h1>
<p>Hello <b>world</b>, this is a paragraph with  lots   of   space.</p>
<h2>Sub Heading</h2>
<a href="https://example.com/docs">Read the docs</a>
<script>var x = 1;</script>
</body></html>"""


class HtmlToTextTests(unittest.TestCase):
    def test_strips_scripts_styles_and_tags(self):
        out = core.html_to_text(SAMPLE_HTML)
        self.assertNotIn("alert", out)
        self.assertNotIn("color: red", out)
        self.assertNotIn("var x", out)
        self.assertNotIn("<b>", out)
        self.assertNotIn("<p>", out)

    def test_keeps_title(self):
        self.assertIn("Title: Example — Test Page", core.html_to_text(SAMPLE_HTML))

    def test_keeps_headings_as_markdown(self):
        out = core.html_to_text(SAMPLE_HTML)
        self.assertIn("# Big Heading", out)
        self.assertIn("## Sub Heading", out)
        self.assertIn("### Third", core.html_to_text("<h3>Third</h3>"))

    def test_keeps_links_as_markdown(self):
        out = core.html_to_text(SAMPLE_HTML)
        self.assertIn("[Read the docs](https://example.com/docs)", out)

    def test_drops_unsafe_links_keeps_text(self):
        out = core.html_to_text('<a href="javascript:alert(1)">click</a>')
        self.assertNotIn("javascript:", out)
        self.assertIn("click", out)

    def test_collapses_whitespace(self):
        out = core.html_to_text(SAMPLE_HTML)
        self.assertNotIn("  ", out)
        self.assertIn("Hello world, this is a paragraph with lots of space.", out)

    def test_empty_input(self):
        self.assertEqual(core.html_to_text(""), "")
        self.assertEqual(core.html_to_text(None), "")


class FetchPageTests(unittest.TestCase):
    def _mock_resp(self, body: bytes, status: int = 200):
        resp = mock.MagicMock()
        resp.status = status
        resp.read.return_value = body
        resp.headers = {}  # no get_content_charset -> utf-8 fallback
        return resp

    def test_success_returns_clean_text(self):
        html = "<html><head><title>Docs</title></head><body><h1>Hello</h1><p>World</p></body></html>"
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(html.encode("utf-8"))
            out = core.fetch_page("https://example.com/doc")
        self.assertIn("URL: https://example.com/doc", out)
        self.assertIn("Title: Docs", out)
        self.assertIn("# Hello", out)
        self.assertIn("World", out)

    def test_sends_browser_ua_and_timeout(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(b"<p>hi</p>")
            core.fetch_page("https://example.com/", timeout=7)
        req = uo.call_args[0][0]
        self.assertEqual(req.get_header("User-agent"), core.BROWSER_UA)
        self.assertEqual(uo.call_args[1]["timeout"], 7)

    def test_http_error(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = urllib.error.HTTPError("https://example.com/", 404, "Not Found", {}, None)
            out = core.fetch_page("https://example.com/")
        self.assertIn("HTTP error 404", out)

    def test_non_200_status_defensive(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(b"<p>x</p>", status=503)
            out = core.fetch_page("https://example.com/")
        self.assertIn("HTTP 503", out)

    def test_bad_scheme(self):
        with mock.patch("urllib.request.urlopen") as uo:
            out = core.fetch_page("ftp://example.com/file")
        self.assertIn("only http/https", out)
        uo.assert_not_called()

    def test_missing_scheme(self):
        out = core.fetch_page("example.com/no-scheme")
        self.assertIn("only http/https", out)

    def test_network_error(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = urllib.error.URLError("connection refused")
            out = core.fetch_page("https://example.com/")
        self.assertIn("network error", out)

    def test_response_capped_at_512kb(self):
        big = b"<p>" + b"a" * (core.MAX_PAGE_BYTES + 10) + b"</p>"
        with mock.patch("urllib.request.urlopen") as uo:
            uo.return_value.__enter__.return_value = self._mock_resp(big)
            out = core.fetch_page("https://example.com/big")
        self.assertIn("truncated", out)
        self.assertLessEqual(len(out), core.MAX_PAGE_BYTES + 200)


class ImageToDataUrlTests(unittest.TestCase):
    PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64

    def test_ok_png(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "img.png")
            with open(p, "wb") as f:
                f.write(self.PNG)
            out = core.image_to_data_url(p)
        self.assertTrue(out.startswith("data:image/png;base64,"))
        self.assertEqual(base64.b64decode(out.split(",", 1)[1]), self.PNG)

    def test_ok_jpg_and_jpeg(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ("a.jpg", "b.jpeg"):
                p = os.path.join(d, name)
                with open(p, "wb") as f:
                    f.write(b"\xff\xd8\xff" + b"1" * 32)
                out = core.image_to_data_url(p)
        self.assertTrue(out.startswith("data:image/jpeg;base64,"))

    def test_missing_file_rejected(self):
        with self.assertRaises(ValueError):
            core.image_to_data_url(os.path.join(tempfile.gettempdir(), "does-not-exist-xyz.png"))

    def test_oversize_capped(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "big.png")
            with open(p, "wb") as f:
                f.write(b"x" * 100)
            with self.assertRaises(ValueError) as ctx:
                core.image_to_data_url(p, max_bytes=50)
            self.assertIn("too large", str(ctx.exception))

    def test_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "img.gif")
            with open(p, "wb") as f:
                f.write(b"GIF89a")
            with self.assertRaises(ValueError):
                core.image_to_data_url(p)


class VisionDescribeTests(unittest.TestCase):
    DATA_URL = "data:image/png;base64,AAAA"

    def _ok_response(self, text="A cat on a mat."):
        return json.dumps({"choices": [{"message": {"content": text}}]}).encode("utf-8")

    def test_builds_correct_request(self):
        with mock.patch("urllib.request.urlopen") as uo:
            resp = mock.MagicMock()
            resp.read.return_value = self._ok_response()
            uo.return_value.__enter__.return_value = resp
            out = core.vision_describe(self.DATA_URL, "sekret")
        req = uo.call_args[0][0]
        self.assertEqual(req.full_url, core.VISION_URL)
        self.assertEqual(req.get_method(), "POST")
        headers = dict(req.header_items())
        self.assertEqual(headers["User-agent"], core.BROWSER_UA)
        self.assertEqual(headers["Authorization"], "Bearer sekret")
        self.assertEqual(headers["Content-type"], "application/json")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["model"], "minimax-m3")
        self.assertEqual(body["max_tokens"], 900)
        content = body["messages"][0]["content"]
        self.assertEqual([c["type"] for c in content], ["text", "image_url"])
        img = content[1]
        self.assertEqual(img["image_url"]["url"], self.DATA_URL)
        self.assertEqual(out, "A cat on a mat.")

    def test_missing_key_short_circuits(self):
        with mock.patch("urllib.request.urlopen") as uo:
            out = core.vision_describe(self.DATA_URL, "")
        self.assertIn("no API key", out)
        uo.assert_not_called()

    def test_gateway_unreachable(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = urllib.error.URLError("timed out")
            out = core.vision_describe(self.DATA_URL, "k")
        self.assertIn("unreachable", out)

    def test_http_error_surfaces_code_and_body(self):
        with mock.patch("urllib.request.urlopen") as uo:
            uo.side_effect = urllib.error.HTTPError(
                core.VISION_URL, 403, "Forbidden", {}, io.BytesIO(b'{"error":{"code":1010}}')
            )
            out = core.vision_describe(self.DATA_URL, "k")
        self.assertIn("403", out)
        self.assertIn("1010", out)

    def test_empty_assistant_content(self):
        with mock.patch("urllib.request.urlopen") as uo:
            resp = mock.MagicMock()
            resp.read.return_value = self._ok_response("")
            uo.return_value.__enter__.return_value = resp
            out = core.vision_describe(self.DATA_URL, "k")
        self.assertIn("empty description", out)


class LoadKeyTests(unittest.TestCase):
    def test_found(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("# comment\nOTHER=1\nOPENCODE_GO_API_KEY=sk-test-123\n")
            self.assertEqual(core.load_key(env), "sk-test-123")

    def test_found_with_quotes(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write('OPENCODE_GO_API_KEY="sk-quoted"\n')
            self.assertEqual(core.load_key(env), "sk-quoted")

    def test_missing_file(self):
        self.assertIsNone(core.load_key(os.path.join(tempfile.gettempdir(), "no-such-env-xyz")))

    def test_missing_key(self):
        with tempfile.TemporaryDirectory() as d:
            env = os.path.join(d, ".env")
            with open(env, "w", encoding="utf-8") as f:
                f.write("OTHER_KEY=1\n")
            self.assertIsNone(core.load_key(env))


# ---------------------------------------------------------------------------
# register() wiring — hyphenated dir name, so load __init__.py by file with an
# importlib harness and pre-seed the submodule so `mod.core is core`.
# ---------------------------------------------------------------------------

def _load_plugin_module():
    spec = importlib.util.spec_from_file_location(
        "context_loader_plug", os.path.join(_PLUGIN_DIR, "__init__.py")
    )
    mod = importlib.util.module_from_spec(spec)
    mod.__path__ = [_PLUGIN_DIR]
    sys.modules["context_loader_plug"] = mod
    sys.modules["context_loader_plug.core"] = core  # reuse the same core module
    spec.loader.exec_module(mod)
    return mod


class RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_plugin_module()
        cls.addClassCleanup(sys.modules.pop, "context_loader_plug", None)
        cls.addClassCleanup(sys.modules.pop, "context_loader_plug.core", None)

    class FakeCtx:
        def __init__(self):
            self.tools = []
            self.commands = []

        def register_tool(self, name, toolset, schema, handler, **kw):
            self.tools.append((name, toolset, schema, handler, kw))

        def register_command(self, name, handler, description="", args_hint=""):
            self.commands.append((name, handler, description, args_hint))

    def test_register_wires_tools_and_commands(self):
        ctx = self.FakeCtx()
        self.mod.register(ctx)
        tools = {t[0]: t for t in ctx.tools}
        self.assertIn("fetch_page", tools)
        self.assertEqual(tools["fetch_page"][1], "web")
        self.assertIn("url", tools["fetch_page"][2].get("required", []))
        self.assertIn("describe_image", tools)
        self.assertEqual(tools["describe_image"][1], "file")
        self.assertIn("path", tools["describe_image"][2].get("required", []))
        commands = {c[0]: c for c in ctx.commands}
        self.assertIn("fetch", commands)
        self.assertIn("describe", commands)
        self.assertEqual(commands["fetch"][3], "<url>")
        self.assertEqual(commands["describe"][3], "<image path>")

    def test_fetch_tool_handler_errors(self):
        out = self.mod._fetch_page_tool({})
        self.assertIn("missing required", out)
        out = self.mod._fetch_page_tool({"url": "ftp://x"})
        self.assertIn("only http/https", out)

    def test_describe_tool_handler_missing_file(self):
        out = self.mod._describe_image_tool({"path": "C:/nope-not-there.png"})
        self.assertIn("no such file", out)

    def test_describe_tool_handler_missing_key(self):
        with mock.patch.object(core, "load_key", return_value=None):
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "x.png")
                with open(p, "wb") as f:
                    f.write(ImageToDataUrlTests.PNG)
                out = self.mod._describe_image_tool({"path": p})
        self.assertIn("OPENCODE_GO_API_KEY", out)

    def test_describe_tool_handler_full_flow(self):
        with mock.patch.object(core, "load_key", return_value="k") as lk, \
             mock.patch.object(core, "vision_describe", return_value="A red panda.") as vd:
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "x.png")
                with open(p, "wb") as f:
                    f.write(ImageToDataUrlTests.PNG)
                out = self.mod._describe_image_tool({"path": p})
        self.assertEqual(out, "A red panda.")
        self.assertTrue(vd.call_args[0][0].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
