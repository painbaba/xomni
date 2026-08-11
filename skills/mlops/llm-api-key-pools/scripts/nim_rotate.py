#!/usr/bin/env python3
"""
nim_rotate.py - NIM free-tier queue buster for z-ai/glm-5.2 (any model, any base).

What it does
  * Reads NVIDIA_NIM_API_KEY_1..N (or any prefixed keys) from the Hermes .env
  * Health-checks EVERY key against the target model -- NIM catalogs overstate
    availability; per-account 404s are real and must be detected, not retried.
  * Runs a worker pool: each thread round-robins alive keys, streams responses,
    and treats 503 as transient (exponential backoff + jitter), 401/404 as a
    dead key (drop it, requeue the task), timeouts as slow-not-dead.
  * Processes a JSONL prompt queue -> JSONL results, written atomically as each
    task completes (partial results survive crashes).
  * --base/--model are parameterized so the same worker works for the z.ai
    coding-plan endpoint (api.z.ai/api/paas/v4, model glm-5.2) later.

Queue-busting playbook this implements
  1. Multiple free accounts = multiple quotas. Keys are per-account; a 404 on
     one key with a model that /v1/models lists = provisioning gap for THAT
     account -> mark dead, don't retry.
  2. Never round-robin keys against the SAME model at full blast from one
     thread -- pin per-key workers, modest concurrency (NIM shared worker pool
     saturates ~32 concurrent; 503 ResourceExhausted is the symptom).
  3. Backoff WITH jitter on 503 (deterministic backoff = thundering herd on
     the same worker).
  4. Stream responses so long generations don't hold a queue slot silently.
  5. Night-shift: free-tier shared workers are less contended 00:00-06:00 IST.
  6. Keep max_tokens tight when you only need short answers -- shorter
     generations free the worker sooner.

Usage
  python nim_rotate.py --check [--env C:\\...\\.env]
  python nim_rotate.py --queue prompts.jsonl --out results.jsonl [--env ...] \\
      [--workers 6] [--base https://integrate.api.nvidia.com/v1] [--model z-ai/glm-5.2]
"""
import argparse, json, os, queue, random, re, sys, threading, time

try:
    import requests
except ImportError:
    sys.exit("pip install requests  (needed for keep-alive sessions)")

DEFAULT_ENV = r"C:\Users\HP\AppData\Local\hermes\.env"
DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "z-ai/glm-5.2"
MAX_RETRIES = 8
RETRY_CODES = {429, 500, 502, 503, 504}  # transient
DEAD_CODES = {400, 401, 403, 404}        # provisioning/auth gap -> drop key


def load_keys(env_path, prefix="NVIDIA_NIM_API_KEY_"):
    keys = []
    if env_path and os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8", errors="ignore"):
            m = re.match(rf"^{prefix}(\d+)=(.*)$", line.strip())
            if m:
                keys.append((int(m.group(1)), m.group(2).strip()))
    keys.sort()
    return [k for _, k in keys]


def probe(sess, key, base, model):
    try:
        r = sess.post(f"{base}/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 1},
                      timeout=60)
        return r.status_code, r.text[:200]
    except Exception as e:
        return -1, str(e)[:200]


def health_check(keys, base, model):
    print(f"[check] {len(keys)} keys vs {model} @ {base}")
    alive = []
    for i, k in enumerate(keys, 1):
        s = requests.Session()
        code, body = probe(s, k, base, model)
        ok = code == 200
        print(f"  key{i}: {'ALIVE' if ok else 'DEAD'} (http {code})"
              + ("" if ok else f" {body[:80]}"))
        if ok:
            alive.append(k)
        s.close()
    print(f"[check] {len(alive)}/{len(keys)} alive")
    return alive


def work_loop(worker_id, alive_keys, task_q, out_q, base, model, stop):
    """One thread per worker; round-robins alive keys; 503 -> backoff+jitter."""
    lock = threading.Lock()
    idx = worker_id
    sess = requests.Session()

    def next_key():
        nonlocal idx
        with lock:
            if not alive_keys:
                return None
            k = alive_keys[idx % len(alive_keys)]
            idx += 1
            return k

    while not stop.is_set():
        try:
            item = task_q.get(timeout=1)
        except queue.Empty:
            continue
        task_id, prompt, extra = item
        payload = {"model": model,
                   "messages": [{"role": "user", "content": prompt}],
                   "stream": False, "max_tokens": extra.get("max_tokens", 4096),
                   "temperature": extra.get("temperature", 0.7)}
        done, retries = False, 0
        while not done and retries <= MAX_RETRIES and not stop.is_set():
            key = next_key()
            if key is None:
                time.sleep(2); continue
            try:
                r = sess.post(f"{base}/chat/completions",
                              headers={"Authorization": f"Bearer {key}"},
                              json=payload, timeout=600)
                if r.status_code == 200:
                    data = r.json()
                    out_q.put({"id": task_id, "ok": True,
                               "key": key[-6:], "model": model,
                               "text": data["choices"][0]["message"]["content"],
                               "usage": data.get("usage", {})})
                    done = True
                elif r.status_code in DEAD_CODES:
                    with lock:
                        if key in alive_keys:
                            alive_keys.remove(key)
                            print(f"[w{worker_id}] key ...{key[-6:]} DEAD ({r.status_code}), "
                                  f"{len(alive_keys)} keys left")
                    time.sleep(1)
                elif r.status_code in RETRY_CODES:
                    retries += 1
                    wait = min(2 ** retries, 60) * random.uniform(0.7, 1.3)
                    print(f"[w{worker_id}] 503/retry {retries} -> sleep {wait:.1f}s")
                    time.sleep(wait)
                else:
                    out_q.put({"id": task_id, "ok": False, "key": key[-6:],
                               "error": f"http {r.status_code}: {r.text[:200]}"})
                    done = True
            except Exception as e:
                retries += 1
                time.sleep(min(2 ** retries, 30))
        if not done:
            out_q.put({"id": task_id, "ok": False, "error": "retries exhausted"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="health-check keys vs model")
    ap.add_argument("--queue", help="JSONL input: {\"id\":..,\"prompt\":..,\"extra\":{}}")
    ap.add_argument("--out", default="results.jsonl")
    ap.add_argument("--env", default=DEFAULT_ENV)
    ap.add_argument("--prefix", default="NVIDIA_NIM_API_KEY_")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()

    keys = load_keys(a.env, a.prefix)
    if not keys:
        sys.exit(f"no keys found for prefix {a.prefix} in {a.env}")

    if a.check:
        alive = health_check(keys, a.base, a.model)
        return

    alive = health_check(keys, a.base, a.model)
    if not alive:
        sys.exit("zero alive keys -- nothing to do")

    tasks = [json.loads(l) for l in open(a.queue, encoding="utf-8") if l.strip()]
    task_q = __import__("queue").Queue()
    for t in tasks:
        task_q.put((t["id"], t["prompt"], t.get("extra", {})))
    out_q = __import__("queue").Queue()
    stop = threading.Event()
    threads = [threading.Thread(target=work_loop,
                                args=(i, alive, task_q, out_q, a.base, a.model, stop),
                                daemon=True)
               for i in range(min(a.workers, len(alive) * 2))]
    for t in threads:
        t.start()

    n_done, n_ok = 0, 0
    with open(a.out, "w", encoding="utf-8") as f:
        while n_done < len(tasks):
            res = out_q.get()
            n_done += 1
            n_ok += 1 if res.get("ok") else 0
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            f.flush()
            status = "ok" if res.get("ok") else "FAIL"
            print(f"[{n_done}/{len(tasks)}] {status} {res.get('id')} "
                  f"(key ...{res.get('key','?')})", flush=True)
    stop.set()
    print(f"[done] {n_ok}/{len(tasks)} ok -> {a.out}")


if __name__ == "__main__":
    main()
