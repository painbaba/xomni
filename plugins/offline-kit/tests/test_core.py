"""offline-kit core tests — pure stdlib, no network (stubbed urlopen)."""
from __future__ import annotations

import json
import socket
import unittest
import urllib.error

from core import (
    BASE_URL,
    build_offline_stack,
    offline_prompt_for,
    probe,
    render_markdown,
    smoke_prompt,
)

TAGS_3 = {
    "models": [
        {"name": "qwen2.5:7b"},
        {"name": "nomic-embed-text:latest"},
        {"name": "llama3.2:3b"},
    ]
}


class FakeResponse:
    """Minimal stand-in for a urllib response: only read() is needed."""

    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body


def _stub(body: bytes):
    return lambda url, **kwargs: FakeResponse(body)


class ProbeTest(unittest.TestCase):
    def test_probe_ok(self):
        report = probe(urlopen=_stub(json.dumps(TAGS_3).encode()))
        self.assertTrue(report["ollama"]["reachable"])
        self.assertIsNone(report["ollama"]["error"])
        self.assertEqual(
            report["ollama"]["models"],
            ["qwen2.5:7b", "nomic-embed-text:latest", "llama3.2:3b"],
        )
        self.assertTrue(report["embeddings"]["available"])
        self.assertEqual(report["embeddings"]["model"], "nomic-embed-text:latest")
        self.assertTrue(report["search"]["available"])
        self.assertEqual(report["search"]["backend"], "fts5-local")
        self.assertTrue(report["offline_ready"])
        self.assertEqual(len(report["checks"]), 4)

    def test_probe_network_errors(self):
        cases = [
            ("URLError", urllib.error.URLError("boom")),
            ("OSError", OSError("connection refused")),
            ("socket.timeout", socket.timeout("timed out")),
        ]
        for name, exc in cases:
            with self.subTest(name=name):

                def raiser(url, **kwargs):
                    raise exc

                report = probe(urlopen=raiser)
                self.assertFalse(report["ollama"]["reachable"])
                self.assertIsNotNone(report["ollama"]["error"])
                self.assertEqual(report["ollama"]["models"], [])
                self.assertFalse(report["offline_ready"])

    def test_probe_malformed_payload(self):
        report = probe(urlopen=_stub(b"not json"))
        self.assertFalse(report["ollama"]["reachable"])
        self.assertIsNotNone(report["ollama"]["error"])
        self.assertFalse(report["offline_ready"])

    def test_probe_payload_without_models_key(self):
        report = probe(urlopen=_stub(b"{}"))
        self.assertFalse(report["ollama"]["reachable"])
        self.assertIn("models", report["ollama"]["error"])

    def test_probe_empty_models_reachable(self):
        report = probe(urlopen=_stub(b'{"models": []}'))
        self.assertTrue(report["ollama"]["reachable"])
        self.assertEqual(report["ollama"]["models"], [])
        self.assertFalse(report["embeddings"]["available"])
        self.assertIsNone(report["embeddings"]["model"])
        self.assertFalse(report["offline_ready"])

    def test_probe_custom_host_port(self):
        seen = {}

        def spy(url, **kwargs):
            seen["url"] = url
            return FakeResponse(json.dumps(TAGS_3).encode())

        report = probe(host="localhost", port=9999, urlopen=spy)
        self.assertIn("localhost:9999/api/tags", seen["url"])
        self.assertTrue(report["ollama"]["reachable"])

    def test_timeout_arg_passed_through(self):
        def spy(url, **kwargs):
            self.assertIsNotNone(kwargs.get("timeout"))
            self.assertEqual(kwargs.get("timeout"), 1.5)
            return FakeResponse(json.dumps(TAGS_3).encode())

        report = probe(timeout=1.5, urlopen=spy)
        self.assertTrue(report["ollama"]["reachable"])


class StackTest(unittest.TestCase):
    def _report(self, names):
        payload = json.dumps({"models": [{"name": n} for n in names]}).encode()
        return probe(urlopen=_stub(payload))

    def test_build_stack_preferred(self):
        plan = build_offline_stack(
            self._report(["qwen2.5:7b", "nomic-embed-text:latest", "llama3.2:3b"])
        )
        self.assertEqual(plan["provider"], "ollama")
        self.assertEqual(plan["base_url"], BASE_URL)
        self.assertEqual(plan["chat_model"], "qwen2.5:7b")
        self.assertEqual(plan["embeddings_model"], "nomic-embed-text:latest")
        self.assertEqual(plan["search"], "codebase-index (fts5)")
        self.assertTrue(plan["offline_ready"])
        self.assertEqual(plan["model_count"], 3)

    def test_build_stack_empty_models(self):
        plan = build_offline_stack(self._report([]))
        self.assertIsNone(plan["chat_model"])
        self.assertIsNone(plan["embeddings_model"])
        self.assertFalse(plan["offline_ready"])

    def test_build_stack_prefer_override(self):
        plan = build_offline_stack(
            self._report(["qwen2.5:7b", "llama3.2:3b"]), prefer="llama3.2"
        )
        self.assertEqual(plan["chat_model"], "llama3.2:3b")

    def test_build_stack_prefer_unknown_falls_back(self):
        plan = build_offline_stack(
            self._report(["qwen2.5:7b", "llama3.2:3b"]), prefer="falcon3"
        )
        self.assertEqual(plan["chat_model"], "qwen2.5:7b")


class PromptTest(unittest.TestCase):
    def _plan(self):
        return build_offline_stack(
            probe(urlopen=_stub(json.dumps(TAGS_3).encode()))
        )

    def test_offline_prompt_deterministic_contains_models(self):
        plan = self._plan()
        p1 = offline_prompt_for("summarize the changelog", plan)
        p2 = offline_prompt_for("summarize the changelog", plan)
        self.assertEqual(p1, p2)
        self.assertIn("qwen2.5:7b", p1)
        self.assertIn("nomic-embed-text:latest", p1)
        self.assertIn("summarize the changelog", p1)

    def test_smoke_prompt_one_line(self):
        line = smoke_prompt(self._plan())
        self.assertEqual(line.count("\n"), 0)
        self.assertIn("offline-kit:", line)
        self.assertIn("3 models", line)
        self.assertIn("chat=qwen2.5:7b", line)
        self.assertIn("embeddings=nomic-embed-text:latest", line)
        self.assertIn("search=fts5-local", line)

    def test_render_markdown_all_checks(self):
        md = render_markdown(probe(urlopen=_stub(json.dumps(TAGS_3).encode())))
        for name in ("ollama-reachable", "embeddings-model", "local-search", "offline-ready"):
            self.assertIn(name, md)
        self.assertIn("|", md)
        self.assertIn("qwen2.5:7b", md)
        self.assertIn("offline_ready", md)


if __name__ == "__main__":
    unittest.main()
