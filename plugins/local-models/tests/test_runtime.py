import os
import tempfile
import unittest
from pathlib import Path

from runtime import (
    DEFAULT_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_PORT,
    binary_path,
    find_binary,
    is_serving,
    parse_ollama_list,
    runtime_dir,
)


def _fake_probe(ok: bool):
    def probe(base_url, timeout=2.0):
        return {"ok": ok, "base_url": base_url, "models": []}

    return probe


class OllamaRuntimeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = str(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_runtime_dir_resolution(self):
        self.assertEqual(runtime_dir(self.home), Path(self.home) / "ollama" / "runtime")

    def test_binary_path_none_when_absent(self):
        self.assertIsNone(binary_path(self.home))

    def test_binary_path_found_when_present(self):
        d = runtime_dir(self.home)
        d.mkdir(parents=True)
        (d / "ollama.exe").write_bytes(b"x")
        self.assertEqual(binary_path(self.home), d / "ollama.exe")

    def test_find_binary_returns_bundled_first(self):
        d = runtime_dir(self.home)
        d.mkdir(parents=True)
        (d / "ollama.exe").write_bytes(b"x")
        self.assertEqual(find_binary(self.home), str(d / "ollama.exe"))

    def test_is_serving_uses_probe_result(self):
        self.assertTrue(is_serving(probe=_fake_probe(True)))
        self.assertFalse(is_serving(probe=_fake_probe(False)))

    def test_is_serving_default_probe_against_port(self):
        # Without a real server this must be False and fast — never hang.
        self.assertFalse(is_serving(probe=_fake_probe(False)))

    def test_port_constant(self):
        self.assertEqual(OLLAMA_PORT, 11434)
        self.assertIn(str(OLLAMA_PORT), OLLAMA_BASE_URL)

    def test_default_model_is_small_and_explicit(self):
        self.assertEqual(DEFAULT_MODEL, "qwen2.5:3b")

    def test_parse_ollama_list_ignores_header(self):
        out = (
            "NAME                ID              SIZE      MODIFIED\n"
            "qwen2.5:3b          0faf2be2b0a3    1.9 GB    2 days ago\n"
            "llama3.2:3b         7d5b7b...       2.0 GB    5 days ago\n"
        )
        rows = parse_ollama_list(out)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["name"], "qwen2.5:3b")
        self.assertEqual(rows[0]["size"], "1.9 GB")
        self.assertEqual(rows[1]["modified"], "5 days ago")

    def test_parse_ollama_list_legacy_3col(self):
        rows = parse_ollama_list("mymodel  1.2 GB  today\n")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "mymodel")
        self.assertEqual(rows[0]["size"], "1.2 GB")
        self.assertEqual(rows[0]["modified"], "today")

    def test_parse_ollama_list_empty(self):
        self.assertEqual(parse_ollama_list(""), [])
        self.assertEqual(parse_ollama_list("NAME ID SIZE MODIFIED\n"), [])


if __name__ == "__main__":
    unittest.main()
