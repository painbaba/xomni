#!/usr/bin/env python3
"""Benchmark LLM API models for workforce role assignment.

CORRECTED PATTERN (user-verified): pin ONE key per model — never round-robin
keys across calls to the same model. One thread per model, each with its own
key. This avoids 503 ResourceExhausted on shared workers.

Usage:
  1. Put keys in a file, one per line: PROVIDER_KEY_N=<value>
  2. Edit MODELS + TASKS below (or import and override).
  3. python benchmark_models.py

Outputs: <OUTDIR>/<model-safe>/<task>.txt  (STATUS header + raw completion)
"""
import json
import os
import queue
import re
import threading
import time
import urllib.error
import urllib.request

# --- CONFIG ---
KEY_FILE = r"C:\Users\HP\AppData\Local\hermes\tmp_nvidia_keys.txt"
BASE = "https://integrate.api.nvidia.com/v1"
OUTDIR = r"C:\Users\HP\decentral-ai-research\bench"

# Model IDs to test. Probe each with a tiny completion first — catalog
# availability != account provisioning (404 "Function not found for account"
# = permanent for that account, drop the model).
MODELS = [
    "deepseek-ai/deepseek-v4-pro",
    "deepseek-ai/deepseek-v4-flash",
    "z-ai/glm-5.2",
    "moonshotai/kimi-k2.6",
    "openai/gpt-oss-120b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "mistralai/mistral-large-2-instruct",
]

# Proven task set: reasoning (checkable math), coding (runnable asserts),
# domain (real project question), structured (JSON-only).
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
            {"role": "user", "content": "Implement a Python function longest_palindromic_substring(s: str) -> str that returns the longest palindromic substring using Manacher's algorithm in O(n) time. Include a small test block at the end that asserts: longest_palindromic_substring('babad') in ('bab','aba'), longest_palindromic_substring('cbbd') == 'bb', longest_palindromic_substring('a') == 'a', longest_palindromic_substring('racecar') == 'racecar'."},
        ],
    },
    "domain": {
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": "You are a distributed systems researcher. Be technically precise, quantify everything, and state assumptions. No fluff."},
            {"role": "user", "content": "Evaluate the technical feasibility of running tensor-parallel inference of a 70B-parameter MoE LLM across volunteer consumer desktops connected over residential internet (typical home upload ~10-20 Mbps, RTT 10-50ms). Identify the single hardest bottleneck and quantify it with numbers: activation sizes per token, per-layer communication, and achievable tokens/sec. What would a practical upper bound on throughput be?"},
        ],
    },
    "structured": {
        "max_tokens": 800,
        "messages": [
            {"role": "system", "content": "You output ONLY valid JSON. No markdown, no commentary."},
            {"role": "user", "content": "Return JSON: {\"name\": \"distributed_inference_system\", \"ranked_risks\": [3 items, each {\"risk\": str, \"probability\": 0-1, \"impact\": \"low|medium|high\"}], \"verdict\": str} for a volunteer-compute LLM inference network."},
        ],
    },
}

HTTP_RETRYABLE = {429, 500, 502, 503, 504}


def load_keys(path):
    keys = []
    for line in open(path):
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
    with urllib.request.urlopen(req, timeout=240) as r:
        data = json.loads(r.read().decode())
    return data["choices"][0]["message"]["content"]


def worker(model, key, tasks, results):
    """One thread per model; key pinned per model."""
    for tname in tasks:
        status = "FAIL"
        out = ""
        for attempt in range(4):
            try:
                out = call_chat(model, TASKS[tname], key)
                status = "OK"
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # "Function not found for account" — permanent, skip model
                    out = f"HTTP 404 (not provisioned for this account): {e.read().decode()[:200]}"
                    break
                if e.code in HTTP_RETRYABLE:
                    time.sleep(5 * (attempt + 1))
                    continue
                out = f"HTTP {e.code}: {e.read().decode()[:200]}"
                break
            except Exception as e:
                out = f"ERR: {e}"
                if attempt < 3:
                    time.sleep(3 * (attempt + 1))
                    continue
                break
        results[model][tname] = status
        safe = model.replace("/", "__")
        d = os.path.join(OUTDIR, safe)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{tname}.txt"), "w", encoding="utf-8") as f:
            f.write(f"STATUS: {status}\nMODEL: {model}\nTASK: {tname}\n\n{out}")
        print(f"[{status}] {model} / {tname}", flush=True)


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    keys = load_keys(KEY_FILE)
    print(f"Keys: {len(keys)}, Models: {len(MODELS)}, Tasks: {len(TASKS)}")
    if not keys:
        raise SystemExit("No keys loaded — check KEY_FILE")
    results = {m: {} for m in MODELS}
    # Pin: key i -> model i (cycle if more models than keys).
    threads = [
        threading.Thread(target=worker, args=(m, keys[i % len(keys)], list(TASKS), results))
        for i, m in enumerate(MODELS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    print("\n=== SUMMARY ===")
    for m in MODELS:
        print(f"{m}: {results[m]}")


if __name__ == "__main__":
    main()
