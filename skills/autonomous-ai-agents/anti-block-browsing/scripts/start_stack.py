#!/usr/bin/env python3
"""Start the full anti-block browsing stack: Camofox + Gemini rotation proxy.

Usage: python start_stack.py [--no-camofox] [--no-proxy]

Starts both servers in the background and prints health checks. On Windows the
processes are detached (survive this shell). Logs:
  - Camofox:   C:\\Users\\HP\\camofox\\camofox.log
  - Proxy:     C:\\Users\\HP\\AppData\\Local\\hermes\\skills\\autonomous-ai-agents\\gemini-browser-control\\proxy.log
"""
import os
import subprocess
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
SKILL_DIR = os.path.join(HOME, "AppData", "Local", "hermes", "skills",
                         "autonomous-ai-agents", "gemini-browser-control")

def check(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

def start_camofox() -> None:
    if check("http://localhost:9377/health"):
        print("[camofox] already running on :9377")
        return
    log = open(os.path.join(HOME, "camofox", "camofox.log"), "ab")
    # detached: own process group, survives this shell
    subprocess.Popen(
        ["cmd", "/c", "cd /d C:\\Users\\HP\\camofox && npx camofox-browser"],
        stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    print("[camofox] starting... (first load ~5-10s)")

def start_proxy() -> None:
    if check("http://127.0.0.1:8790/health"):
        print("[proxy] already running on :8790")
        return
    env = dict(os.environ)
    env_path = os.path.join(HOME, "AppData", "Local", "hermes", ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip())
    log = open(os.path.join(SKILL_DIR, "proxy.log"), "ab")
    subprocess.Popen(
        [sys.executable, os.path.join(SKILL_DIR, "scripts", "gemini_rotation_proxy.py")],
        stdout=log, stderr=subprocess.STDOUT,
        env=env,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    print("[proxy] starting...")

def main() -> None:
    if "--no-camofox" not in sys.argv:
        start_camofox()
    if "--no-proxy" not in sys.argv:
        start_proxy()
    print("Waiting for servers...")
    for _ in range(15):
        time.sleep(1)
        if check("http://localhost:9377/health") and check("http://127.0.0.1:8790/health"):
            break
    print("CAMOFOX:", "UP" if check("http://localhost:9377/health") else "DOWN (check log)")
    print("PROXY:  ", "UP" if check("http://127.0.0.1:8790/health") else "DOWN (check log)")
    print("\nReady. Routes:")
    print("  A. Sandbox:  python gemini_browser.py 'task' --url https://...")
    print("  B. Personal: open Chrome, use Nanobrowser side panel")
    print("  C. Channels: opencli <site> <cmd> | curl https://r.jina.ai/URL")

if __name__ == "__main__":
    main()
