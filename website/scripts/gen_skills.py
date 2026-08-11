#!/usr/bin/env python3
"""XOMNI SKILLS site generator (curated pipeline).

Consumes <repo>/data/curated-skills.json (180 ranked records produced by the
curation pipeline: name, category, description, usefulness_score, rank,
source, license, ...) and emits:

  website/data/skills.json   - machine-readable array of all curated skills
  website/skills.html        - self-contained "XOMNI SKILLS" page with
                               vanilla-JS search + category filter and
                               rank badge + score chip per skill card

Usage:  python scripts/gen_skills.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]          # C:\Users\HP\xomni
CURATED_JSON = REPO_ROOT / "data" / "curated-skills.json"  # 180 ranked records
WEBSITE_DIR = REPO_ROOT / "website"
DATA_DIR = WEBSITE_DIR / "data"

# Fields carried over from the curated DB into the site data.
KEEP_FIELDS = (
    "name",        # skill identifier
    "category",    # curated domain (11 top-level categories)
    "description", # purpose / trigger description
    "score",       # usefulness_score (9.1 – 10.2)
    "rank",        # curated rank 1..180
    "source",      # provenance repo, e.g. microsoft/skills
    "license",     # license string from the source skill
)


def load_curated() -> list[dict]:
    """Load the curated skills DB and project it onto site fields."""
    if not CURATED_JSON.is_file():
        print(f"error: curated skills db not found: {CURATED_JSON}", file=sys.stderr)
        sys.exit(1)

    with CURATED_JSON.open(encoding="utf-8") as fh:
        records = json.load(fh)

    skills = []
    for rec in records:
        name = str(rec.get("name") or "").strip()
        if not name:
            print(f"  [warn] record without name skipped: {rec}", file=sys.stderr)
            continue
        skills.append(
            {
                "name": name,
                "category": str(rec.get("category") or "misc").strip(),
                "description": str(rec.get("description") or "").strip(),
                "score": rec.get("usefulness_score"),
                "rank": rec.get("rank"),
                "source": str(rec.get("source") or "").strip(),
                "license": str(rec.get("license") or "").strip(),
            }
        )

    # Curated order is authoritative: rank ascending, ties by name.
    skills.sort(key=lambda s: (s["rank"] is None, s["rank"] or 0, s["name"].lower()))
    return skills


def build_html(skills: list[dict]) -> str:
    categories = sorted({s["category"] for s in skills})
    count = len(skills)
    score_lo = min((s["score"] for s in skills if s["score"] is not None), default=0)
    score_hi = max((s["score"] for s in skills if s["score"] is not None), default=0)

    stylesheet = (
        "<style>\n"
        ":root{--bg:#0b0f1a;--panel:#121826;--card:#161e30;--border:#26304a;"
        "--text:#e6ebf5;--muted:#8b96b0;--accent:#6ea8fe;--accent2:#c084fc;}\n"
        "*{box-sizing:border-box;margin:0;padding:0;}\n"
        "body{background:var(--bg);color:var(--text);"
        "font-family:'Segoe UI',system-ui,-apple-system,sans-serif;line-height:1.55;}\n"
        ".wrap{max-width:1200px;margin:0 auto;padding:48px 24px 80px;}\n"
        "header h1{font-size:2.2rem;letter-spacing:.5px;}\n"
        "header h1 .x{background:linear-gradient(90deg,var(--accent),var(--accent2));"
        "-webkit-background-clip:text;background-clip:text;color:transparent;}\n"
        "header p{color:var(--muted);margin:10px 0 28px;}\n"
        ".controls{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:28px;}\n"
        "input,select{background:var(--panel);color:var(--text);border:1px solid var(--border);"
        "border-radius:10px;padding:12px 16px;font-size:1rem;outline:none;}\n"
        "input{flex:1;min-width:240px;}\n"
        "input:focus,select:focus{border-color:var(--accent);}\n"
        "#count{color:var(--muted);margin-bottom:20px;font-size:.95rem;}\n"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px;}\n"
        ".card{background:var(--card);border:1px solid var(--border);border-radius:14px;"
        "padding:18px 20px;display:flex;flex-direction:column;gap:8px;"
        "transition:transform .12s ease,border-color .12s ease;}\n"
        ".card:hover{transform:translateY(-2px);border-color:var(--accent);}\n"
        ".card .meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}\n"
        ".card h3{font-size:1.05rem;word-break:break-word;}\n"
        ".card .desc{color:var(--muted);font-size:.92rem;flex:1;}\n"
        ".chip{font-size:.72rem;border-radius:999px;padding:3px 10px;border:1px solid var(--border);}\n"
        ".chip.rank{color:var(--accent);font-weight:600;}\n"
        ".chip.score{color:var(--accent2);font-weight:600;}\n"
        ".chip.tag{align-self:flex-start;text-transform:uppercase;"
        "letter-spacing:.8px;color:var(--muted);}\n"
        ".chip.source{color:var(--muted);text-transform:none;letter-spacing:0;}\n"
        ".empty{color:var(--muted);padding:40px;text-align:center;}\n"
        "footer{margin-top:48px;color:var(--muted);font-size:.85rem;text-align:center;}\n"
        "</style>"
    )

    # Embed the data inline so the page works on any static host (file://, GH Pages, CF Pages).
    data_json = json.dumps(skills, ensure_ascii=False, indent=1)
    data_json = data_json.replace("<", "\\u003c").replace(">", "\\u003e")

    options = "".join(
        f'<option value="{c}">{c}</option>' for c in categories
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>XOMNI SKILLS — {count} Curated Capabilities</title>
<meta name="description" content="The curated XOMNI skills catalog: {count} ranked skills across {len(categories)} domains (scores {score_lo}–{score_hi}).">
{stylesheet}
</head>
<body>
<div class="wrap">
  <header>
    <h1><span class="x">XOMNI</span> SKILLS</h1>
    <p>The curated XOMNI capability catalog — {count} ranked skills across {len(categories)} domains (usefulness score {score_lo}–{score_hi}), generated from <code>data/curated-skills.json</code> by <code>scripts/gen_skills.py</code>.</p>
  </header>

  <div class="controls">
    <input id="search" type="search" placeholder="Search skills by name, description, source, or tag…" autocomplete="off">
    <select id="domain">
      <option value="">All domains</option>
      {options}
    </select>
  </div>

  <div id="count"></div>
  <div id="grid" class="grid"></div>
  <footer>XOMNI · data also available at <a href="data/skills.json">data/skills.json</a> · ranked by the curation pipeline</footer>
</div>

<script>
const SKILLS = {data_json};

const searchEl = document.getElementById('search');
const domainEl = document.getElementById('domain');
const gridEl = document.getElementById('grid');
const countEl = document.getElementById('count');

function chip(cls, text) {{
  return `<span class="chip ${{cls}}">${{text}}</span>`;
}}

function render() {{
  const q = searchEl.value.trim().toLowerCase();
  const d = domainEl.value;
  const items = SKILLS.filter(s => {{
    if (d && s.category !== d) return false;
    if (!q) return true;
    return (s.name + ' ' + s.description + ' ' + s.category + ' ' + (s.source || '')).toLowerCase().includes(q);
  }});
  countEl.textContent = items.length === SKILLS.length
    ? `Showing all ${{SKILLS.length}} curated skills`
    : `${{items.length}} of ${{SKILLS.length}} skills`;
  gridEl.innerHTML = items.map(s =>
    `<div class="card">`
    + `<div class="meta">`
    + (s.rank ? chip('rank', '#' + s.rank) : '')
    + (s.score != null ? chip('score', 'score ' + s.score) : '')
    + chip('tag', s.category)
    + (s.source ? chip('source', s.source) : '')
    + `</div>`
    + `<h3>${{s.name}}</h3>`
    + `<div class="desc">${{s.description || '—'}}</div>`
    + `</div>`
  ).join('') || '<div class="empty">No skills match your filters.</div>';
}}

searchEl.addEventListener('input', render);
domainEl.addEventListener('change', render);
render();
</script>
</body>
</html>
"""


def main() -> int:
    print(f"Loading {CURATED_JSON} …")
    skills = load_curated()
    print(f"Loaded {len(skills)} curated skills.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "skills.json").write_text(
        json.dumps(skills, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    html = build_html(skills)
    (WEBSITE_DIR / "skills.html").write_text(html, encoding="utf-8")

    cats = len({s["category"] for s in skills})
    print(f"Wrote {DATA_DIR / 'skills.json'} ({len(skills)} skills, {cats} categories)")
    print(f"Wrote {WEBSITE_DIR / 'skills.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
