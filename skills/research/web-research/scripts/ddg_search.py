#!/usr/bin/env python3
"""DuckDuckGo HTML search. Works for the first ~2-4 queries, then gets
rate-limited (connection reset / empty results) — wrap in a retry loop and
fall back to Bing/Google News RSS or direct URL guesses after repeated empties.
Usage: python3 ddg_search.py <query words...>
"""
import sys, re, html as h, urllib.request, urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}

def main():
    q = " ".join(sys.argv[1:])
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read().decode("utf-8", "ignore")
    except Exception as ex:
        print("DDG ERROR:", ex); return
    links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', raw, flags=re.S)
    snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', raw, flags=re.S)
    for i, (u, title) in enumerate(links[:12]):
        if "uddg=" in u:  # DDG redirect wrapper -> real URL
            m = re.search(r"uddg=([^&]+)", u)
            u = urllib.parse.unquote(m.group(1)) if m else u
        tt = re.sub(r"<[^>]+>", "", title)
        sn = re.sub(r"<[^>]+>", "", snips[i]) if i < len(snips) else ""
        print(f"{i+1}. {h.unescape(tt)}\n   {h.unescape(u)}\n   {h.unescape(sn)[:220]}")

main()
