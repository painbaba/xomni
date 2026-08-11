#!/usr/bin/env python3
"""Window-grep a dumped single-line text file (see fetch_page.py dump mode).
grep -C is useless on single-line dumps; this prints +/-500-char windows
around up to 4 matches per name.
Usage: python3 grep_windows.py <file.txt> Name1 "Name Two" ...
"""
import sys, re

def main():
    path, names = sys.argv[1], sys.argv[2:]
    t = open(path, encoding="utf-8").read()
    for n in names:
        ms = list(re.finditer(re.escape(n), t, flags=re.I))
        print(f"\n########## [{n}] -> {len(ms)} matches")
        for i, m in enumerate(ms[:4]):
            s = max(0, m.start() - 500); e = min(len(t), m.end() + 500)
            print(f"--- match {i+1} ---\n{t[s:e]}")

main()
