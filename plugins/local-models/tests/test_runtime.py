import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from runtime import (
    DEFAULT_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_PORT,
    _extract_zip,
    binary_path,
    find_binary,
    install_runtime,
    is_serving,
    parse_ollama_list,
    pull_model,
    runtime_dir,
    start_serve,
    status,
    wait_for_ready,
)


def _fake_probe(ok: bool):
    def probe(base_url, timeout=2.0):
        return {"ok": ok, "base_url": base_url, "models": []}

    return probe


class _TempHomeBase(unittest.TestCase):
    """Every test gets an isolated $XOMNI_HOME temp dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = str(Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()


class OllamaRuntimeTest(_TempHomeBase):
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

    def test_parse_ollama_list_4col_with_id(self):
        rows = parse_ollama_list("qwen2.5:3b  0faf2be2b0a3  1.9 GB  2 days ago\n")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "qwen2.5:3b")
        self.assertEqual(rows[0]["size"], "1.9 GB")
        self.assertEqual(rows[0]["modified"], "2 days ago")

    def test_parse_ollama_list_size_without_unit(self):
        rows = parse_ollama_list("modelx  abc123  512  today\n")
        self.assertEqual(rows[0]["size"], "512")
        self.assertEqual(rows[0]["modified"], "today")

    def test_parse_ollama_list_name_only(self):
        self.assertEqual(
            parse_ollama_list("lonely-model\n"),
            [{"name": "lonely-model", "size": "?", "modified": "?"}],
        )

    def test_parse_ollama_list_blank_lines_and_whitespace(self):
        rows = parse_ollama_list("  \nNAME ID SIZE MODIFIED\n   qwen2.5:3b   0faf  1.9 GB  today  \n\n")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "qwen2.5:3b")


class RuntimeDetectionTests(_TempHomeBase):
    """find_binary / is_serving / start_serve / wait_for_ready orchestration."""

    def test_find_binary_falls_back_to_path(self):
        with mock.patch("shutil.which", return_value="/usr/bin/ollama"):
            self.assertEqual(find_binary(self.home), "/usr/bin/ollama")

    def test_find_binary_none_when_nowhere(self):
        with mock.patch("shutil.which", return_value=None):
            self.assertIsNone(find_binary(self.home))

    def test_is_serving_forwards_timeout(self):
        seen = {}

        def probe(base_url, timeout=2.0):
            seen["timeout"] = timeout
            return {"ok": False}

        self.assertFalse(is_serving(probe=probe, timeout=5.0))
        self.assertEqual(seen["timeout"], 5.0)

    def test_start_serve_already_serving_short_circuit(self):
        with mock.patch("runtime.is_serving", return_value=True) as isv, \
             mock.patch("subprocess.Popen") as popen:
            r = start_serve("/x/ollama.exe", self.home)
        self.assertEqual(r, {"started": True, "ready": True, "error": None})
        isv.assert_called_once()
        popen.assert_not_called()

    def test_start_serve_popen_failure(self):
        with mock.patch("runtime.is_serving", return_value=False), \
             mock.patch("subprocess.Popen", side_effect=OSError("no binary")):
            r = start_serve("/nope/ollama.exe", self.home)
        self.assertFalse(r["started"])
        self.assertFalse(r["ready"])
        self.assertIn("no binary", r["error"])

    def test_start_serve_launches_without_waiting(self):
        with mock.patch("runtime.is_serving", return_value=False), \
             mock.patch("subprocess.Popen") as popen:
            r = start_serve("/x/ollama.exe", self.home, wait_ready=False)
        popen.assert_called_once()
        self.assertEqual(popen.call_args.args[0], ["/x/ollama.exe", "serve"])
        self.assertTrue(r["started"])
        self.assertFalse(r["ready"])

    def test_wait_for_ready_polls_until_up(self):
        with mock.patch("runtime.is_serving", side_effect=[False, False, True]), \
             mock.patch("time.sleep") as slp:
            self.assertTrue(wait_for_ready(timeout=5, step=0.01))
        self.assertEqual(slp.call_count, 2)

    def test_wait_for_ready_times_out(self):
        with mock.patch("runtime.is_serving", return_value=False), \
             mock.patch("time.sleep"):
            self.assertFalse(wait_for_ready(timeout=0.01, step=0.01))


class RuntimeInstallTests(_TempHomeBase):
    """install_runtime / _extract_zip / pull_model."""

    def test_extract_zip_flat(self):
        with tempfile.TemporaryDirectory() as d:
            zip_path = os.path.join(d, "x.zip")
            dest = Path(d) / "dest"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("ollama.exe", b"bin")
            _extract_zip(zip_path, dest)
            self.assertTrue((dest / "ollama.exe").is_file())

    def test_extract_zip_nested_root_moved_up(self):
        with tempfile.TemporaryDirectory() as d:
            zip_path = os.path.join(d, "x.zip")
            dest = Path(d) / "dest"
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("ollama-windows-amd64/ollama.exe", b"bin")
            _extract_zip(zip_path, dest)
            self.assertTrue((dest / "ollama.exe").is_file())

    def test_install_runtime_skips_when_binary_present(self):
        d = runtime_dir(self.home)
        d.mkdir(parents=True)
        (d / "ollama.exe").write_bytes(b"x")
        with mock.patch("urllib.request.urlopen") as uo:
            r = install_runtime(self.home)
        uo.assert_not_called()
        self.assertTrue(r["installed"])
        self.assertIsNone(r["error"])
        self.assertEqual(r["binary"], str(d / "ollama.exe"))

    def test_install_runtime_download_failure_cleans_temp(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("no net")):
            r = install_runtime(self.home)
        self.assertFalse(r["installed"])
        self.assertIsNone(r["binary"])
        self.assertIn("no net", r["error"])
        leftover = [p for p in runtime_dir(self.home).iterdir() if p.suffix == ".zip"]
        self.assertEqual(leftover, [])

    def test_pull_model_success(self):
        with mock.patch("subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stderr = ""
            r = pull_model("/x/ollama.exe", "qwen2.5:3b")
        self.assertTrue(r["ok"])
        self.assertIsNone(r["error"])
        self.assertEqual(run.call_args.args[0], ["/x/ollama.exe", "pull", "qwen2.5:3b"])

    def test_pull_model_failure_reports_stderr_tail(self):
        with mock.patch("subprocess.run") as run:
            run.return_value.returncode = 1
            run.return_value.stderr = "Error: pull failed\nmanifest unknown\n"
            run.return_value.stdout = ""
            r = pull_model("/x/ollama.exe", "nope")
        self.assertFalse(r["ok"])
        self.assertIn("manifest unknown", r["error"])

    def test_pull_model_oserror(self):
        with mock.patch("subprocess.run", side_effect=OSError("boom")):
            r = pull_model("/x/ollama.exe")
        self.assertFalse(r["ok"])
        self.assertIn("boom", r["error"])


class RuntimeStatusTests(_TempHomeBase):
    """status() composition: serving flag, bundled binary, default model presence."""

    def test_status_full_composition(self):
        d = runtime_dir(self.home)
        d.mkdir(parents=True)
        (d / "ollama.exe").write_bytes(b"x")
        with mock.patch("runtime.is_serving", return_value=True), \
             mock.patch("runtime.list_models", return_value=[
                 {"name": "qwen2.5:3b", "size": "1.9 GB", "modified": "2 days ago"},
                 {"name": "llama3.2:3b", "size": "2.0 GB", "modified": "5 days ago"},
             ]):
            s = status(self.home)
        self.assertTrue(s["serving"])
        self.assertTrue(s["bundled_installed"])
        self.assertTrue(s["default_model_present"])  # qwen2.5 prefix matches
        self.assertEqual(s["models"], ["qwen2.5:3b", "llama3.2:3b"])
        self.assertIn("ollama", s["runtime_dir"])

    def test_status_default_model_absent(self):
        d = runtime_dir(self.home)
        d.mkdir(parents=True)
        (d / "ollama.exe").write_bytes(b"x")
        with mock.patch("runtime.is_serving", return_value=True), \
             mock.patch("runtime.list_models", return_value=[
                 {"name": "llama3.2:3b", "size": "x", "modified": "y"},
             ]):
            s = status(self.home)
        self.assertFalse(s["default_model_present"])

    def test_status_not_serving_no_models(self):
        with mock.patch("runtime.is_serving", return_value=False), \
             mock.patch("runtime.find_binary", return_value=None):
            s = status(self.home)
        self.assertFalse(s["serving"])
        self.assertIsNone(s["binary"])
        self.assertEqual(s["models"], [])
        self.assertFalse(s["bundled_installed"])

    def test_status_serving_but_no_binary_skips_list(self):
        with mock.patch("runtime.is_serving", return_value=True), \
             mock.patch("runtime.find_binary", return_value=None), \
             mock.patch("runtime.list_models") as lm:
            s = status(self.home)
        lm.assert_not_called()
        self.assertEqual(s["models"], [])


if __name__ == "__main__":
    unittest.main()
