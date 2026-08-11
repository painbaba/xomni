#!/usr/bin/env python3
"""probe_models.py -- fast parallel health probe for free-tier model pools.

Reads API keys from a .env file (NEVER prints them), pings N models with a
tiny max_tokens=8 call, classifies each:
  ALIVE               -> 200 OK
  DEAD                -> 404 "not found for account" (per-account gap, permanent)
  HTTP <code> <msg>   -> other HTTP error (read the body)
  CONGESTED/timeout   -> shared worker saturated at peak (retry off-peak, NOT dead)

Use BEFORE benchmarking or wiring roles. Works for any OpenAI-compatible
chat/completions base (NVIDIA NIM, OpenRouter, z.ai, groq, ...) and for
Gemini's REST endpoint (--gemini, key passed as query param).

Usage:
  # OpenAI-compatible (NIM example):
  python probe_models.py --env C:/Users/HP/AppData/Local/hermes/.env \
      --key NVIDIA_NIM_API_KEY_1 \
      --base https://integrate.api.nvidia.com/v1 \
      nvidia/nemotron-3-ultra-550b-a55b nvidia/nemotron-3-super-120b-a12b \
      openai/gpt-oss-120b z-ai/glm-5.2

  # Gemini (REST, key in query param):
  python probe_models.py --env C:/Users/HP/AppData/Local/hermes/.env \
      --key GOOGLE_AI_STUDIO_API_KEY_1 \
      --base https://generativelanguage.googleapis.com/v1beta --gemini \
      gemini-3.1-flash-lite gemini-3-flash-preview

  # Secret guard note: the KEY never appears on the command line -- it is
  # read from the .env file inside the script.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def load_env(path):
    vals = {}
    for line in open(path, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            vals[k] = v
    return vals


def classify(model, err):
    if err is None:
        return f"{model}: ALIVE"
    if isinstance(err, urllib.error.HTTPError):
        body = err.read().decode(errors="ignore")[:100]
        if err.code == 404 and "account" in body.lower():
            return f"{model}: DEAD (404 per-account -- permanent, drop it)"
        return f"{model}: HTTP {err.code} {body}"
    return f"{model}: CONGESTED/timeout (retry off-peak, NOT dead)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--env", required=True, help="path to .env file")
    ap.add_argument("--key", required=True, help="env var name holding the key")
    ap.add_argument("--base", required=True, help="API base URL")
    ap.add_argument("--gemini", action="store_true",
                    help="use ?key= query param + :generateContent (Gemini REST)")
    ap.add_argument("--timeout", type=int, default=90)
    ap.add_argument("--threads", type=int, default=8)
    a = ap.parse_args()

    env = load_env(a.env)
    key = env.get(a.key)
    if not key:
        print(f"key {a.key} not found or empty in {a.env}")
        sys.exit(1)

    def probe(model):
        if a.gemini:
            url = f"{a.base}/models/{model}:generateContent?key={key}"
            body = json.dumps({
                "contents": [{"parts": [{"text": "reply with exactly: ok"}]}],
                "generationConfig": {"maxOutputTokens": 8},
            }).encode()
            headers = {"Content-Type": "application/json"}
        else:
            url = f"{a.base}/chat/completions"
            body = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "reply with exactly: ok"}],
                "max_tokens": 8,
            }).encode()
            headers = {"Authorization": "Bearer " + key,
                       "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            urllib.request.urlopen(req, timeout=a.timeout)
            return classify(model, None)
        except urllib.error.HTTPError as e:
            return classify(model, e)
        except Exception as e:  # TimeoutError, ConnectionError, ...
            return classify(model, e)

    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        for line in ex.map(probe, a.models):
            print(line)


if __name__ == "__main__":
    main()
