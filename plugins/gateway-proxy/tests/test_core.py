"""Tests for the gateway-proxy plugin (bare `from core import ...`).

Run from the plugin dir:
    cd plugins/gateway-proxy
    python -m unittest tests.test_core -q
"""

import json
import threading
import unittest
import urllib.error
import urllib.request

from core import (
    FALLBACK_MODELS,
    GatewayError,
    RouterBackend,
    build_handler,
    route_openai,
    start_server,
)


class FakeBackend:
    """Deterministic in-memory backend used across the HTTP tests."""

    def __init__(self):
        self.last_prompt = None
        self.calls = 0

    def route(self, prompt):
        self.last_prompt = prompt
        self.calls += 1
        return {"model": "fake", "provider": "fake", "reply": "hi"}

    def model_list(self):
        return ["xomni-quick", "xomni-reasoning", "xomni-vision"]


class RaisingBackend(FakeBackend):
    def route(self, prompt):
        raise RuntimeError("boom: upstream provider exploded")


class CustomListBackend(FakeBackend):
    def model_list(self):
        return ["custom-a", "custom-b"]


class GatewayServerTest(unittest.TestCase):
    def setUp(self):
        self.backend = FakeBackend()
        self.server, self.thread = start_server(0, self.backend)
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    # -- helpers ---------------------------------------------------------

    def _request(self, method, path, body=None, raw=None):
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        data = raw
        if data is None and body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            resp = urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))
        return resp.status, json.loads(resp.read().decode("utf-8"))

    def _chat(self, **overrides):
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hello gateway"}],
        }
        payload.update(overrides)
        return self._request("POST", "/v1/chat/completions", body=payload)

    # -- endpoints -------------------------------------------------------

    def test_models_endpoint_shape(self):
        status, body = self._request("GET", "/v1/models")
        self.assertEqual(status, 200)
        self.assertEqual(body["object"], "list")
        self.assertIsInstance(body["data"], list)
        for entry in body["data"]:
            self.assertIsInstance(entry["id"], str)

    def test_models_endpoint_lists_backend_ids(self):
        status, body = self._request("GET", "/v1/models")
        ids = [entry["id"] for entry in body["data"]]
        self.assertEqual(ids, self.backend.model_list())

    def test_chat_happy_path_openai_fields(self):
        status, body = self._chat()
        self.assertEqual(status, 200)
        self.assertTrue(body["id"].startswith("chatcmpl-"))
        self.assertEqual(body["object"], "chat.completion")
        self.assertIsInstance(body["created"], int)
        self.assertEqual(body["model"], "gpt-4o-mini")
        choice = body["choices"][0]
        self.assertEqual(choice["index"], 0)
        self.assertEqual(choice["message"]["role"], "assistant")
        self.assertEqual(choice["message"]["content"], "hi")
        self.assertEqual(choice["finish_reason"], "stop")

    def test_chat_usage_counts(self):
        _, body = self._chat()
        usage = body["usage"]
        self.assertIn("prompt_tokens", usage)
        self.assertIn("completion_tokens", usage)
        self.assertIn("total_tokens", usage)
        self.assertEqual(
            usage["total_tokens"],
            usage["prompt_tokens"] + usage["completion_tokens"],
        )

    def test_chat_echoes_requested_model(self):
        _, body = self._chat(model="gpt-4o")
        self.assertEqual(body["model"], "gpt-4o")

    def test_chat_joins_messages_into_one_prompt(self):
        self._chat(
            messages=[
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "summarize x"},
                {"role": "assistant", "content": "sure"},
                {"role": "user", "content": "now do y"},
            ]
        )
        self.assertEqual(
            self.backend.last_prompt, "be brief\nsummarize x\nsure\nnow do y"
        )
        self.assertEqual(self.backend.calls, 1)

    def test_stream_true_rejected_400(self):
        status, body = self._chat(stream=True)
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["type"], "invalid_request_error")
        self.assertIn("stream", body["error"]["message"])

    def test_malformed_json_400_envelope(self):
        status, body = self._request(
            "POST", "/v1/chat/completions", raw=b"{not json!!"
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["type"], "invalid_request_error")
        self.assertTrue(body["error"]["message"])

    def test_empty_body_400(self):
        status, body = self._request("POST", "/v1/chat/completions", raw=b"")
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["type"], "invalid_request_error")

    def test_missing_messages_400(self):
        status, body = self._chat(messages=[])
        self.assertEqual(status, 400)
        self.assertEqual(body["error"]["type"], "invalid_request_error")

    def test_unknown_path_404(self):
        status, body = self._request("GET", "/v1/does-not-exist")
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["type"], "invalid_request_error")

    def test_get_on_chat_path_404(self):
        status, _ = self._request("GET", "/v1/chat/completions")
        self.assertEqual(status, 404)

    def test_backend_failure_502(self):
        server, thread = start_server(0, RaisingBackend())
        try:
            port = server.server_address[1]
            url = "http://127.0.0.1:%d/v1/chat/completions" % port
            req = urllib.request.Request(
                url,
                data=json.dumps(
                    {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "x"}]}
                ).encode(),
                method="POST",
            )
            req.add_header("Content-Type", "application/json")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(ctx.exception.code, 502)
            body = json.loads(ctx.exception.read().decode("utf-8"))
            self.assertEqual(body["error"]["type"], "server_error")
            self.assertIn("boom", body["error"]["message"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_model_list_passthrough(self):
        server, thread = start_server(0, CustomListBackend())
        try:
            port = server.server_address[1]
            url = "http://127.0.0.1:%d/v1/models" % port
            resp = urllib.request.urlopen(url, timeout=10)
            body = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(resp.status, 200)
            self.assertEqual(
                [entry["id"] for entry in body["data"]], ["custom-a", "custom-b"]
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


class PureFunctionTest(unittest.TestCase):
    def test_route_openai_pure_function(self):
        backend = FakeBackend()
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "pure fn"}],
        }
        response = route_openai(payload, backend)
        self.assertEqual(response["object"], "chat.completion")
        self.assertTrue(response["id"].startswith("chatcmpl-"))
        self.assertEqual(response["choices"][0]["message"]["content"], "hi")
        self.assertEqual(backend.last_prompt, "pure fn")

    def test_route_openai_raises_gateway_error_on_stream(self):
        backend = FakeBackend()
        payload = {
            "model": "gpt-4o",
            "stream": True,
            "messages": [{"role": "user", "content": "x"}],
        }
        with self.assertRaises(GatewayError) as ctx:
            route_openai(payload, backend)
        self.assertEqual(ctx.exception.status, 400)

    def test_route_openai_wraps_backend_failure(self):
        with self.assertRaises(GatewayError) as ctx:
            route_openai(
                {"model": "gpt-4o", "messages": [{"role": "user", "content": "x"}]},
                RaisingBackend(),
            )
        self.assertEqual(ctx.exception.status, 502)
        self.assertEqual(ctx.exception.error_type, "server_error")

    def test_build_handler_returns_class(self):
        handler = build_handler(FakeBackend())
        self.assertTrue(issubclass(handler, object))
        self.assertTrue(hasattr(handler, "do_GET"))
        self.assertTrue(hasattr(handler, "do_POST"))
        self.assertIsInstance(handler.backend, FakeBackend)


class RouterBackendTest(unittest.TestCase):
    def test_fallback_models_static_table(self):
        tiers = [entry["tier"] for entry in FALLBACK_MODELS]
        self.assertIn("quick", tiers)
        self.assertIn("reasoning", tiers)

    def test_router_backend_route_returns_contract(self):
        result = RouterBackend().route("summarize this quickly")
        self.assertIn("model", result)
        self.assertIn("provider", result)
        self.assertIn("reply", result)
        self.assertIsInstance(result["reply"], str)
        self.assertTrue(result["reply"])

    def test_router_backend_model_list(self):
        model_ids = RouterBackend().model_list()
        self.assertIsInstance(model_ids, list)
        self.assertTrue(all(isinstance(mid, str) and mid for mid in model_ids))
        self.assertEqual(len(model_ids), 3)

    def test_start_server_refuses_non_localhost(self):
        with self.assertRaises(GatewayError):
            start_server(0, FakeBackend(), host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()
