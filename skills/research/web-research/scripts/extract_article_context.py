#!/usr/bin/env python3
"""Extract keyword-anchored context windows from messy HTML article files.

Why: full-page news HTML collapses to one giant text line after tag
stripping, so line-length filters and naive truncation miss the exact
quotes you need to verify. This script strips tags, then prints a
+/-CHARS window around each keyword/phrase occurrence (deduped), so you
can verify quotes fast without dumping megabytes of boilerplate.

Usage:
  python extract_article_context.py article.html "keyword1|keyword2|phrase three"

Notes:
  - Phrases are matched case-insensitively as literal substrings.
  - On Windows git-bash, set PYTHONIOENCODING=utf-8 if output garbles
    non-ASCII quotes.
  - For many distinct terms, run once with '|'-joined terms; hits are
    capped per term (default 8) and de-duplicated.
"""
import re
import sys
import html


def extract(fn, phrases, chars=500, max_hits=8):
    raw = open(fn, encoding="utf-8", errors="ignore").read()
    raw = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    seen = set()
    for p in phrases:
        hits = 0
        for m in re.finditer(re.escape(p), text, re.IGNORECASE):
            s = max(0, m.start() - chars)
            e = min(len(text), m.end() + chars)
            chunk = text[s:e]
            key = chunk[:80]
            if key in seen:
                continue
            seen.add(key)
            print(f"[{p}] ...{chunk}...")
            print("---")
            hits += 1
            if hits >= max_hits:
                break


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2].split("|"))
