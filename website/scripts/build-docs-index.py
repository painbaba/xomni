#!/usr/bin/env python3
"""Build website/docs-index.json from the docs pages (h1/h2 + intro summary).

Zero-network client-side search manifest: one entry per docs page with the
page title, its section headings, and a short intro summary (~150 chars).
"""
import datetime
import html
import json
import re
from pathlib import Path

WEBSITE = Path(__file__).resolve().parent.parent  # website/
DOCS = WEBSITE / "docs"
OUT = WEBSITE / "docs-index.json"

TAG_RE = re.compile(r"<[^>]+>")
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
H2_RE = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
LEAD_RE = re.compile(r'<p[^>]*class="lead"[^>]*>(.*?)</p>', re.S)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)

SUMMARY_LEN = 150


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s)


def text_of(inner: str) -> str:
    return html.unescape(strip_tags(inner)).strip()


def main() -> None:
    pages = []
    for f in sorted(DOCS.glob("*.html")):
        raw = f.read_text(encoding="utf-8")
        m1 = H1_RE.search(raw)
        title = text_of(m1.group(1)) if m1 else f.stem

        headings = [t for t in (text_of(m.group(1)) for m in H2_RE.finditer(raw)) if t]

        lm = LEAD_RE.search(raw)
        intro = text_of(lm.group(1)) if lm else ""
        if not intro:
            pm = P_RE.search(raw)
            if pm:
                intro = text_of(pm.group(1))
        if len(intro) > SUMMARY_LEN:
            intro = intro[: SUMMARY_LEN - 3].rstrip() + "..."

        pages.append(
            {"path": f.name, "title": title, "headings": headings, "summary": intro}
        )

    data = {
        "generated": datetime.date.today().isoformat(),
        "count": len(pages),
        "pages": pages,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} — {len(pages)} pages indexed")


if __name__ == "__main__":
    main()
