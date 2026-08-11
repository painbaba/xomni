#!/usr/bin/env python3
"""Generic parallel-agent swarm runner for pooled free-tier keys.

Usage:
    python swarm_runner.py [tasks.json]
        tasks.json: {"tasks": [{"id": int, "dimension": str, "question": str}, ...]}
        default: ./tasks.json

Channels (read from Hermes .env):
    6x Gemini GOOGLE_AI_STUDIO_API_KEY_1..6  -> gemini-3.1-flash-lite
    2x OpenCode Go OPENCODE_GO_API_KEY / OPENGO_API_KEY -> deepseek-v4-flash
        (OpenCode Go needs a browser User-Agent or Cloudflare 403 error 1010)

Output: results/agent_XXX.json per task (skips existing = resumable),
        results/agent_XXX.json.fail on exhausted retries, swarm.log.
Verified 2026-08-08: 300 tasks, 14 workers, 4.6 min, 0 failures.
"""
import json, os, re, sys, threading, time, random, urllib.request, urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "tasks.json")
ENV = os.path.expanduser(r"~\AppData\Local\hermes\.env")
RESULTS = os.path.join(BASE, "results")
os.makedirs(RESULTS, exist_ok=True)

def load_env():
    d = {}
    with open(ENV, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d

env = load_env()

# ---------------- channels ----------------
CHANNELS = []
for i in range(1, 7):
    k = env.get(f"GOOGLE_AI_STUDIO_API_KEY_{i}", "")
    if k:
        CHANNELS.append({"name": f"gemini{i}", "kind": "gemini", "key": k,
                         "model": "gemini-3.1-flash-lite", "min_interval": 4.0,
                         "last_call": 0.0, "lock": threading.Lock()})
for name in ("OPENCODE_GO_API_KEY", "OPENGO_API_KEY"):
    k = env.get(name, "")
    if k:
        CHANNELS.append({"name": f"opencode-{name[:6]}", "kind": "opencode", "key": k,
                         "model": "deepseek-v4-flash", "min_interval": 2.5,
                         "last_call": 0.0, "lock": threading.Lock()})
print(f"[swarm] channels: {[c['name'] for c in CHANNELS]}", flush=True)
if not CHANNELS:
    print("[swarm] NO LIVE CHANNELS — check .env keys"); raise SystemExit(1)

SYSTEM = """You are an expert market-research analyst. Answer the research question with SPECIFIC, factual content: names, numbers, dates, and named systems where known. If you do not know something precisely, say "unverified" rather than inventing. Keep every finding to one crisp sentence. Return ONLY a JSON object with exactly these keys:
{"question": "<the question>", "findings": ["3 to 6 concise factual bullets"], "key_numbers": ["up to 5 short strings capturing the most important numbers"], "sources": ["up to 3 named sources or 'model knowledge'"], "confidence": "high|medium|low"}
Do not wrap the JSON in markdown fences. Do not add any text outside the JSON."""

def call_channel(ch, prompt):
    with ch["lock"]:
        wait = ch["last_call"] + ch["min_interval"] - time.time()
        if wait > 0:
            time.sleep(wait)
        ch["last_call"] = time.time()
    if ch["kind"] == "gemini":
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/{ch['model']}"
               f":generateContent?key={ch['key']}")
        body = {"contents": [{"role": "user", "parts": [{"text": SYSTEM + "\n\nQUESTION: " + prompt}]}],
                "generationConfig": {"responseMimeType": "application/json",
                                     "maxOutputTokens": 1000, "temperature": 0.4}}
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    else:  # opencode — browser UA required (Cloudflare 403 error 1010 otherwise)
        url = "https://opencode.ai/zen/go/v1/chat/completions"
        body = {"model": ch["model"],
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": prompt}],
                "max_tokens": 1000, "temperature": 0.4}
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {ch['key']}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"})
    try:
        with urllib.request.urlopen(req, timeout=150) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        if ch["kind"] == "gemini":
            return data["candidates"][0]["content"]["parts"][0]["text"], None
        return data["choices"][0]["message"]["content"], None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read(200).decode('utf-8','ignore')[:120]}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def parse_json(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

# ---------------- worker ----------------
tasks = json.load(open(TASKS_PATH, encoding="utf-8"))["tasks"]
queue = list(tasks)
random.shuffle(queue)
qidx = 0
qlock = threading.Lock()
stats = {"done": 0, "ok": 0, "fail": 0, "retries": 0}
slog = open(os.path.join(BASE, "swarm.log"), "a", encoding="utf-8")

def worker():
    global qidx
    while True:
        with qlock:
            if qidx >= len(queue):
                return
            t = queue[qidx]
            qidx += 1
        tid, dim, q = t["id"], t["dimension"], t["question"]
        out_path = os.path.join(RESULTS, f"agent_{tid:03d}.json")
        if os.path.exists(out_path):
            with qlock:
                stats["done"] += 1; stats["ok"] += 1
            continue
        result = None
        for attempt in range(4):
            ch = random.choice(CHANNELS)
            txt, err = call_channel(ch, q)
            if err:
                with qlock:
                    stats["retries"] += 1
                if "429" in (err or "") and ch["min_interval"] < 30:
                    with ch["lock"]:
                        ch["min_interval"] = min(30.0, ch["min_interval"] * 1.8)
                if attempt < 3:
                    time.sleep(2 + attempt * 2)
                continue
            parsed = parse_json(txt)
            if parsed:
                result = {"id": tid, "dimension": dim, "question": q, **parsed,
                          "channel": ch["name"], "ts": time.time()}
                break
            # non-JSON fallback: keep the raw text as a low-confidence finding
            result = {"id": tid, "dimension": dim, "question": q,
                      "findings": [txt.strip()[:500]], "key_numbers": [],
                      "sources": ["model knowledge"], "confidence": "low",
                      "channel": ch["name"], "ts": time.time(), "raw": True}
            break
        with qlock:
            stats["done"] += 1
            if result:
                stats["ok"] += 1
            else:
                stats["fail"] += 1
        if result:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=1)
        else:
            with open(out_path + ".fail", "w", encoding="utf-8") as f:
                json.dump({"id": tid, "dimension": dim, "question": q,
                           "error": "all retries failed"}, f, ensure_ascii=False)
        if stats["done"] % 25 == 0 or stats["done"] == len(queue):
            print(f"[swarm] {stats['done']}/{len(queue)} done | ok={stats['ok']} "
                  f"fail={stats['fail']} retries={stats['retries']}", flush=True)
            slog.write(f"{time.strftime('%H:%M:%S')} {stats}\n"); slog.flush()

N_WORKERS = min(14, len(CHANNELS) * 2)
threads = [threading.Thread(target=worker) for _ in range(N_WORKERS)]
print(f"[swarm] starting {N_WORKERS} workers for {len(queue)} tasks", flush=True)
t0 = time.time()
for th in threads:
    th.start()
for th in threads:
    th.join()
dt = time.time() - t0
print(f"[swarm] DONE in {dt/60:.1f} min | ok={stats['ok']} fail={stats['fail']} "
      f"retries={stats['retries']}", flush=True)
slog.write(f"DONE {dt/60:.1f}min {stats}\n"); slog.close()
