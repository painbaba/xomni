"""check_models.py — standalone gateway health check for the XOMNI provider pool.

Pings the opencode Zen gateway (https://opencode.ai/zen/go/v1) for EVERY model
in plugins/provider-pool/core.py's GATEWAY_MODELS list via a minimal
chat/completions call (max_tokens=1), prints a table (model | status |
latency ms), and exits 0 if all models are OK or 1 if any are down.

Pure stdlib. Reads the key via core.load_key() (from ~/AppData/Local/hermes/.env,
env var OPENCODE_GO_API_KEY) — the key is never printed.

Usage:
    python scripts/check_models.py                 # check all 25 models
    python scripts/check_models.py --limit 3       # first 3 only (smoke test)
    python scripts/check_models.py --json          # machine-readable output
    python scripts/check_models.py --limit 5 --json

Exit codes:
    0  all checked models reachable (HTTP 2xx)
    1  at least one model down / error
    2  usage or internal error (bad args, import failure)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

TIMEOUT = 30  # seconds per model
CORE_REL = Path("plugins") / "provider-pool" / "core.py"


def load_core() -> "module":
    """Import plugins/provider-pool/core.py robustly, wherever we're run from.

    Tries a plain import first (works if provider-pool is on sys.path), then
    falls back to loading the file directly by path relative to this script.
    """
    try:  # pragma: no cover - simple path
        import core  # type: ignore

        return core
    except ImportError:
        pass

    here = Path(__file__).resolve().parent
    core_path = here.parent / CORE_REL
    if not core_path.is_file():
        # also try cwd-relative (running from repo root as `python scripts/...`)
        core_path = Path.cwd() / CORE_REL
    if not core_path.is_file():
        print(f"error: cannot find provider-pool core at {core_path}", file=sys.stderr)
        sys.exit(2)

    spec = importlib.util.spec_from_file_location("xomni_core", core_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def check_model(base_url: str, key: str, model_id: str, timeout: int) -> dict:
    """One minimal chat/completions call against the model. Returns result dict."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0",
        "Content-Type": "application/json",
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = json.dumps(
        {
            "model": model_id,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 1,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(base_url + "/chat/completions", data=body, headers=headers)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return {
                "model": model_id,
                "ok": True,
                "status": "OK",
                "http": resp.status,
                "latency_ms": round((time.monotonic() - start) * 1000),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        return {
            "model": model_id,
            "ok": False,
            "status": "DOWN",
            "http": e.code,
            "latency_ms": round((time.monotonic() - start) * 1000),
            "error": f"HTTP {e.code}",
        }
    except Exception as exc:  # timeout, connection refused, etc.
        return {
            "model": model_id,
            "ok": False,
            "status": "DOWN",
            "http": None,
            "latency_ms": round((time.monotonic() - start) * 1000),
            "error": str(exc)[:120],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Health-check every model on the opencode Zen gateway.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--limit", type=int, default=None,
                        help="check only the first N models in GATEWAY_MODELS")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON instead of the table")
    parser.add_argument("--timeout", type=int, default=TIMEOUT,
                        help="per-model timeout in seconds")
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be >= 1")

    core = load_core()
    models = core.GATEWAY_MODELS
    if args.limit is not None:
        models = models[: args.limit]

    key = core.load_key()
    base_url = core.GATEWAY_URL

    results = [check_model(base_url, key, m["id"], args.timeout) for m in models]
    ok_count = sum(1 for r in results if r["ok"])
    any_down = ok_count != len(results)

    if args.json:
        print(json.dumps({
            "gateway": base_url,
            "checked": len(results),
            "ok": ok_count,
            "all_ok": not any_down,
            "results": results,
        }, indent=2))
    else:
        print(f"gateway: {base_url}  |  checked: {len(results)}  |  "
              f"OK: {ok_count}  |  DOWN: {len(results) - ok_count}")
        print(f"{'model':<24} {'status':<6} {'latency ms':>10}")
        print("-" * 44)
        for r in results:
            detail = r["error"] or ""
            print(f"{r['model']:<24} {r['status']:<6} {r['latency_ms']:>10}  {detail}")

    return 1 if any_down else 0


if __name__ == "__main__":
    sys.exit(main())
