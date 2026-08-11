#!/usr/bin/env python3
"""Fetch a URL and either dump stripped text to a file or print windows around names.
Usage:
  python3 fetch_page.py <URL> dump <outfile>          # save full stripped text
  python3 fetch_page.py <URL> Name1 "Name Two" ...    # print ~900-char window around first match of each name
Works with urllib + browser UA on Wikipedia and most mainstream news sites.
"""
import sys, re, html as h, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "ignore")

def to_text(htm):
    t = re.sub(r"<(script|style|head|nav|footer)[^>]*>.*?</\1>", " ", htm, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = h.unescape(t)
    return re.sub(r"\s+", " ", t)

def main():
    url, args = sys.argv[1], sys.argv[2:]
    t = to_text(get(url))
    print("URL:", url, "| textlen:", len(t))
    if args and args[0] == "dump":
        with open(args[1], "w", encoding="utf-8") as f:
            f.write(t)
        print("saved to", args[1])
        return
    for n in (args or [None]):
        if n is None:
            print(t[:6000]); continue
        m = re.search(re.escape(n), t, flags=re.I)
        if m:
            s = max(0, m.start() - 450); e = min(len(t), m.end() + 450)
            print(f"\n--- [{n}] ---\n{t[s:e]}")
        else:
            print(f"\n--- [{n}] --- NO MATCH")

main()
