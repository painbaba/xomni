#!/usr/bin/env python3
"""Benchmark LLM API models across a pool of API keys.

Pattern proven on NVIDIA NIM free tier (6 keys, 2026-08):
- ONE KEY PER MODEL (pin keys to models) — round-robin hammers shared
  workers and triggers 503 ResourceExhausted.
- Save EVERY output to disk as it completes so partial results survive.
- 404 "Function not found for account" = per-account provisioning gap:
  mark DEAD, do not retry.
- 503 ResourceExhausted = transient shared-worker limit: retry w/ backoff.
- Reasoning models (DeepSeek V4 class) need >=600s timeout; a timeout
  means SLOW, not dead.

Usage:
  python bench_models.py
  # edit MODELS / TASKS / KEYS_FILE / OUTDIR below, or pass as args

Output: OUTDIR/<model-sanitized>/<task>.txt with STATUS line + raw output.
"""
import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.request

# ---- CONFIG (edit these) ----
BASE = "https://integrate.api.nvidia.com/v1"
KEYS_FILE = r"C:\Users\HP\AppData\Local\hermes\tmp_nvidia_keys.txt"
OUTDIR = r"C:\Users\HP\decentral-ai-research\bench"
TIMEOUT = 600  # reasoning models are slow; 240s was too short
RETRIES = 4

MODELS = [
    "openai/gpt-oss-120b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "z-ai/glm-5.2",
    "deepseek-ai/deepseek-v4-flash",
]

TASKS = {
    "reasoning": {
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": "You are a rigorous mathematician. Solve the problem and give the final answer clearly."},
            {"role": "user", "content": "A fair coin is tossed repeatedly. What is the expected number of tosses needed to get 3 consecutive heads? Show your work and give the exact expected value."},
        ],
    },
    "coding": {
        "max_tokens": 1200,
        "messages": [
            {"role": "system", "content": "You are a senior software engineer. Write correct, complete Python code. Output only the code in a single python code block."},
            {"role": "user", "content": "Implement a Python function longest_palindromic_substring(s: str) -> str using Manacher's algorithm in O(n) time. Include asserts: longest_palindromic_substring('babad') in ('bab','aba'), longest_palindromic_substring('cbbd') == 'bb', longest_palindromic_substring('a') == 'a', longest_palindromic_substring('racecar') == 'racecar'."},
        ],
    },
    "structured": {
        "max_tokens": 800,
        "messages": [
            {"role": "system", "content": "You output ONLY valid JSON. No markdown, no commentary."},
            {"role": "user", "content": 'Return JSON: {"name": str, "items": [3 dicts with {"id": int, "label": str}], "ok": true}.'},
        ],
    },
}
# ---- END CONFIG ----


def load_keys(path):
    """Read KEY_NAME=key lines from a file (keys never touch the shell)."""
    keys = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^[A-Z0-9_]+=(.+)$", line.strip())
        if m:
            keys.append(m.group(1).strip())
    return keys


def call_chat(model, task, key):
    payload = json.dumps({
        "model": model,
        "messages": task["messages"],
        "max_tokens": task["max_tokens"],
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=payload, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"]


def worker(keys, q, results, lock):
    """One worker thread = one key at a time (key-per-model discipline)."""
    ki = 0
    while True:
        try:
            model, tname = q.get_nowait()
        except queue.Empty:
            return
        status, out = "FAIL", ""
        for attempt in range(RETRIES):
            key = keys[ki % len(keys)]
            ki += 1
            try:
                out = call_chat(model, TASKS[tname], key)
                status = "OK"
                break
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:300]
                if e.code == 404:  # per-account provisioning gap: DEAD
                    out = f"HTTP 404 {body}"
                    break
                if e.code in (429, 503):  # transient rate limits
                    out = f"HTTP {e.code} {body}"
                    time.sleep(5 * (attempt + 1))
                    continue
                out = f"HTTP {e.code} {body}"
                break
            except Exception as e:
                out = f"ERR: {e}"
                if attempt < RETRIES - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
                break
        with lock:
            results.setdefault(model, {})[tname] = status
        d = os.path.join(OUTDIR, model.replace("/", "__"))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{tname}.txt"), "w", encoding="utf-8") as f:
            f.write(f"STATUS: {status}\nMODEL: {model}\nTASK: {tname}\n\n{out}")
        print(f"[{status}] {model} / {tname}", flush=True)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    keys = load_keys(KEYS_FILE)
    print(f"Keys: {len(keys)}, Models: {len(MODELS)}, Tasks: {len(TASKS)}")
    q = queue.Queue()
    for m in MODELS:
        for t in TASKS:
            q.put((m, t))
    results, lock = {}, threading.Lock()
    threads = [threading.Thread(target=worker, args=(keys, q, results, lock))
               for _ in keys]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("\n=== SUMMARY ===")
    for m in MODELS:
        print(f"{m}: {results.get(m, {})}")


if __name__ == "__main__":
    main()
