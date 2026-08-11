#!/usr/bin/env python3
"""
Manus-style vision-driven browser control for Hermes.
Loop: screenshot -> gemini-3.6-flash sees + decides -> execute action -> repeat.

Stack:
  - Camofox server (anti-detection Camoufox) at CAMOFOX_URL (default http://localhost:9377)
  - Gemini 3.6 flash as the vision/decision model
  - N Gemini API keys with automatic rotation on 429 (free tier: ~10 RPM each)

Usage:
  python gemini_browser.py "<task>" [--url https://...] [--max-steps 15] [--model gemini-3.6-flash]

Env:
  CAMOFOX_URL          default http://localhost:9377
  GOOGLE_AI_STUDIO_API_KEY_1..N   (or GOOGLE_API_KEY / GEMINI_API_KEY)
  GEMINI_BROWSER_MODEL default gemini-3.6-flash

The model is prompted to return strict JSON:
  {"action":"click|type|press|scroll|navigate|extract|done",
   "ref":"<element ref from snapshot>", "value":"...", "reasoning":"..."}
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

CAMOFOX_URL = os.environ.get("CAMOFOX_URL", "http://localhost:9377").rstrip("/")
MODEL = os.environ.get("GEMINI_BROWSER_MODEL", "gemini-3.6-flash")
MAX_STEPS = int(os.environ.get("GEMINI_BROWSER_MAX_STEPS", "15"))


# ---------------------------------------------------------------- keys/rotation
def _all_keys() -> list[str]:
    keys: list[str] = []
    i = 1
    while True:
        k = os.environ.get(f"GOOGLE_AI_STUDIO_API_KEY_{i}") or os.environ.get(f"GEMINI_API_KEY_{i}")
        if not k:
            break
        keys.append(k)
        i += 1
    if not keys:
        for env in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY"):
            if os.environ.get(env):
                keys.append(os.environ[env])
    if not keys:
        sys.exit("No Gemini keys found. Set GOOGLE_AI_STUDIO_API_KEY_1..N (or GOOGLE_API_KEY).")
    return keys


_KEYS = _all_keys()
_key_idx = 0
_key_until = 0  # epoch seconds; rotate before this if 429


def _next_key() -> str:
    global _key_idx, _key_until
    if time.time() < _key_until:
        pass  # keep current key
    else:
        _key_idx = (_key_idx + 1) % len(_KEYS)
        _key_until = 0
    return _KEYS[_key_idx]


def _rotate() -> None:
    global _key_idx, _key_until
    _key_idx = (_key_idx + 1) % len(_KEYS)
    _key_until = time.time() + 55  # give the exhausted key a breather
    print(f"  [keys] rotated to key #{_key_idx + 1}/{len(_KEYS)}", file=sys.stderr)


def gemini_ask(parts: list[dict]) -> str:
    """parts: [{'text': ...}, {'inline_data': {'mime_type': 'image/png', 'data': b64}}]"""
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "action": {"type": "STRING",
                               "enum": ["click", "type", "press", "scroll", "navigate", "back",
                                        "forward", "refresh", "wait", "new_tab", "extract", "done"]},
                    "ref": {"type": "STRING"},
                    "value": {"type": "STRING"},
                    "reasoning": {"type": "STRING"},
                },
                "required": ["action", "reasoning"],
            },
        },
    }).encode()
    last_err = None
    for _ in range(len(_KEYS) * 2):
        key = _next_key()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}"
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                d = json.loads(resp.read())
            try:
                return d["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return json.dumps(d)[:500]
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 429:
                print(f"  [keys] 429 on key #{_key_idx + 1}, rotating", file=sys.stderr)
                _rotate()
                continue
            if e.code == 400:
                err_body = e.read().decode(errors="replace")[:300]
                raise RuntimeError(f"Gemini 400: {err_body}")
            raise
        except Exception as e:  # network blip -> try next key
            last_err = str(e)
            _rotate()
            continue
    raise RuntimeError(f"All keys failed: {last_err}")


# ---------------------------------------------------------------- camofox client
def _req(method: str, path: str, body: dict | None = None, timeout: int = 90) -> dict:
    url = f"{CAMOFOX_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def camofox_open_tab(user_id: str, url: str) -> str:
    d = _req("POST", "/tabs", {"url": url, "userId": user_id, "listItemId": "gemini_browser"})
    return d["tabId"]


def camofox_snapshot(tab_id: str, user_id: str) -> dict:
    return _req("GET", f"/tabs/{tab_id}/snapshot?userId={user_id}", timeout=120)


def camofox_act(tab_id: str, user_id: str, action: str, **kw) -> dict:
    body = {"userId": user_id, **kw}
    return _req("POST", f"/tabs/{tab_id}/{action}", body)


def camofox_close_session(user_id: str) -> None:
    """Close the session so the server drops all tabs + session state.

    Prevents orphaned-session log noise ('Cannot read properties of
    undefined (reading url)') from the server's tab reaper when tabs are
    deleted while the session object still references them.
    """
    try:
        _req("DELETE", f"/sessions/{user_id}", timeout=15)
        print(f"  [camofox] session {user_id} closed", file=sys.stderr)
    except Exception as e:
        print(f"  [camofox] session close failed (harmless): {e}", file=sys.stderr)


# ---------------------------------------------------------------- the loop
def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    # Try the whole thing first (Gemini with responseMimeType=json returns pure JSON)
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {"action": "retry", "reasoning": text[:300]}
    try:
        return json.loads(text[start:end + 1])
    except Exception as e:
        print(f"  [parse] JSON error: {e} | raw={text[:150]!r}", file=sys.stderr)
        return {"action": "retry", "reasoning": text[:300]}


def run_loop(task: str, start_url: str | None) -> None:
    user_id = os.environ.get("GEMINI_BROWSER_USER", "hermes_gemini_browser")
    # NOTE: same userId across runs = persistent cookies/logins (Camofox saves
    # storageState on session close, restores it on next open). Use a distinct
    # GEMINI_BROWSER_USER per task-domain to keep login contexts separate.
    tab_id = camofox_open_tab(user_id, start_url or "about:blank")
    tabs: dict[str, str] = {"current": tab_id}  # name -> tabId
    print(f"[camofox] tab {tab_id} (user {user_id})", file=sys.stderr)

    try:
        for step in range(1, MAX_STEPS + 1):
            print(f"\n=== step {step}/{MAX_STEPS} ===", file=sys.stderr)
            snap = camofox_snapshot(tab_id, user_id)
            snapshot_txt = snap.get("snapshot") or json.dumps(snap)[:4000]
            screenshot_b64 = (snap.get("screenshot") or {}).get("data", "")

            parts: list[dict] = []
            if screenshot_b64:
                parts.append({"inline_data": {"mime_type": "image/png", "data": screenshot_b64}})
            parts.append({"text": (
                "You are a Manus-class browser agent. You see the page (screenshot + accessibility snapshot).\n"
                f"TASK: {task}\n\n"
                "Page snapshot (element refs like [e1] are clickable/typeable targets):\n"
                f"{snapshot_txt[:12000]}\n\n"
                "Respond with ONLY strict JSON, one of:\n"
                '{"action":"click","ref":"e12","reasoning":"..."}\n'
                '{"action":"type","ref":"e5","value":"text to type","reasoning":"..."}\n'
                '{"action":"press","value":"Enter","reasoning":"..."}\n'
                '{"action":"scroll","value":"down","reasoning":"..."}\n'
                '{"action":"navigate","value":"https://...","reasoning":"..."}\n'
                '{"action":"back","reasoning":"..."}\n'
                '{"action":"forward","reasoning":"..."}\n'
                '{"action":"refresh","reasoning":"..."}\n'
                '{"action":"wait","value":"2","reasoning":"..."}\n'
                '{"action":"new_tab","value":"https://...","reasoning":"open secondary site"}\n'
                '{"action":"extract","reasoning":"final answer to the task"}\n'
                '{"action":"done","reasoning":"task complete"}\n'
                "Rules: click/type/scroll/press/back/forward/refresh/wait/new_tab for UI moves; "
                "extract = answer the task from what you see; "
                "done only when the task is truly finished. If a ref is stale, pick the closest current ref. "
                "For comparison tasks use new_tab to open the second site.\n"
                f"Steps remaining: {MAX_STEPS - step + 1}. If the task is answerable NOW, use extract — "
                "do not re-do work already done."
            )})

            reply = gemini_ask(parts)
            print(f"  [gemini] {reply[:200]}", file=sys.stderr)
            decision = extract_json(reply)
            action = decision.get("action", "extract")

            if action == "done":
                print(f"TASK COMPLETE: {decision.get('reasoning','')}")
                return
            if action == "extract":
                print(f"ANSWER: {decision.get('reasoning','')}")
                # one more look to confirm, then stop
                return
            if action == "retry":
                print("  [parse] retrying with fresh snapshot...", file=sys.stderr)
                time.sleep(1)
                continue
            try:
                if action == "new_tab":
                    new_id = camofox_open_tab(user_id, decision.get("value", "about:blank"))
                    tabs["current"] = new_id
                    print(f"  [exec] new_tab -> {new_id}", file=sys.stderr)
                elif action == "switch_tab":
                    # value = url fragment or '1'/'2'... or index; Camofox keeps
                    # tabs per session — simplest: navigate current tab, or open
                    # fresh if it's an index beyond known set
                    target = decision.get("value", "")
                    if target.isdigit() and int(target) > 0:
                        idx = int(target) - 1
                        if idx < len(tabs) - 1:
                            # switch among named tabs we opened
                            pass
                    # fall back: treat as URL to open in a new tab
                    new_id = camofox_open_tab(user_id, target if "://" in target else "about:blank")
                    tabs["current"] = new_id
                    print(f"  [exec] switch_tab -> {new_id}", file=sys.stderr)
                else:
                    cur = tabs["current"]
                    if action == "click":
                        r = camofox_act(cur, user_id, "click", ref=decision.get("ref", ""))
                    elif action == "type":
                        r = camofox_act(cur, user_id, "type",
                                        ref=decision.get("ref", ""), text=decision.get("value", ""))
                    elif action == "press":
                        r = camofox_act(cur, user_id, "press", key=decision.get("value", "Enter"))
                    elif action == "scroll":
                        r = camofox_act(cur, user_id, "scroll", direction=decision.get("value", "down"))
                    elif action == "navigate":
                        r = camofox_act(cur, user_id, "navigate", url=decision.get("value", ""))
                    elif action == "back":
                        r = camofox_act(cur, user_id, "back")
                    elif action == "forward":
                        r = camofox_act(cur, user_id, "forward")
                    elif action == "refresh":
                        r = camofox_act(cur, user_id, "refresh")
                    elif action == "wait":
                        time.sleep(min(int(decision.get("value") or 2), 15))
                        r = {"ok": True}
                    else:
                        print(f"UNKNOWN ACTION {action}, treating as done")
                        return
                ok = r.get("ok", True)
                print(f"  [exec] {action} -> {'ok' if ok else r}", file=sys.stderr)
                if not ok:
                    time.sleep(1)
            except Exception as e:
                print(f"  [exec] FAILED {action}: {e}", file=sys.stderr)
                time.sleep(1)

        print(f"STEP LIMIT ({MAX_STEPS}) REACHED. Last snapshot below (final answer if visible):")
        snap = camofox_snapshot(tab_id, user_id)
        print(snap.get("snapshot", "")[:3000])
    finally:
        camofox_close_session(user_id)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    task = sys.argv[1]
    start_url = None
    if "--url" in sys.argv:
        start_url = sys.argv[sys.argv.index("--url") + 1]
    run_loop(task, start_url)


if __name__ == "__main__":
    main()
