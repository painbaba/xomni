#!/usr/bin/env python3
"""XOMNI SKILLS site generator.

Scans <repo>/skills for SKILL.md files, parses their YAML frontmatter
(name, description; fallback: directory name), derives the category from
the path (e.g. skills/creative/ascii-art -> "creative"), and emits:

  website/data/skills.json   - machine-readable array of all skills
  website/skills.html        - self-contained "XOMNI SKILLS" page with
                               vanilla-JS search + category filter

Usage:  python scripts/gen_skills.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]          # C:\Users\HP\xomni
SKILLS_DIR = REPO_ROOT / "skills"                        # 170 SKILL.md files
WEBSITE_DIR = REPO_ROOT / "website"
DATA_DIR = WEBSITE_DIR / "data"
CSS_CANDIDATES = [WEBSITE_DIR / "css" / "style.css"]     # optional site-wide css

FRONTMATTER_DELIM = "---"


def parse_skill_md(path: Path) -> dict:
    """Return {name, description} from a SKILL.md's YAML frontmatter."""
    text = path.read_text(encoding="utf-8", errors="replace")
    # Normalise CRLF so the frontmatter delimiters always match.
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    fm: dict = {}
    if lines and lines[0].strip() == FRONTMATTER_DELIM:
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == FRONTMATTER_DELIM:
                end = i
                break
        if end:
            try:
                fm = yaml.safe_load("\n".join(lines[1:end])) or {}
            except yaml.YAMLError as exc:
                print(f"  [warn] bad YAML in {path}: {exc}", file=sys.stderr)
                fm = {}
    if not isinstance(fm, dict):
        fm = {}
    name = str(fm.get("name") or path.parent.name).strip()
    description = str(fm.get("description") or "").strip()
    return {"name": name, "description": description}


def collect_skills() -> list[dict]:
    skills = []
    for md in sorted(SKILLS_DIR.rglob("SKILL.md")):
        rel_dir = md.parent.relative_to(SKILLS_DIR)      # e.g. creative/ascii-art
        parts = rel_dir.parts
        category = parts[0]                              # top-level domain dir
        parsed = parse_skill_md(md)
        skills.append(
            {
                "name": parsed["name"],
                "category": category,
                "description": parsed["description"],
                "dir": str(rel_dir).replace("\\", "/"),  # nested path (info only)
            }
        )
    # Stable ordering: category, then name.
    skills.sort(key=lambda s: (s["category"].lower(), s["name"].lower()))
    return skills


def build_html(skills: list[dict]) -> str:
    categories = sorted({s["category"] for s in skills})
    count = len(skills)

    # Use the site-wide stylesheet when present, otherwise inline dark styles.
    css = next((c for c in CSS_CANDIDATES if c.exists()), None)
    if css:
        stylesheet = '<link rel="stylesheet" href="css/style.css">'
    else:
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
            ".card h3{font-size:1.05rem;word-break:break-word;}\n"
            ".card .desc{color:var(--muted);font-size:.92rem;flex:1;}\n"
            ".card .tag{align-self:flex-start;font-size:.72rem;text-transform:uppercase;"
            "letter-spacing:.8px;color:var(--accent2);border:1px solid var(--border);"
            "border-radius:999px;padding:3px 10px;}\n"
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
<title>XOMNI SKILLS — {count} Capabilities</title>
<meta name="description" content="The full XOMNI skills catalog: {count} skills across {len(categories)} domains.">
{stylesheet}
</head>
<body>
<div class="wrap">
  <header>
    <h1><span class="x">XOMNI</span> SKILLS</h1>
    <p>The complete XOMNI capability catalog — {count} skills across {len(categories)} domains, generated from <code>skills/</code> by <code>scripts/gen_skills.py</code>.</p>
  </header>

  <div class="controls">
    <input id="search" type="search" placeholder="Search skills by name, description, or tag…" autocomplete="off">
    <select id="domain">
      <option value="">All domains</option>
      {options}
    </select>
  </div>

  <div id="count"></div>
  <div id="grid" class="grid"></div>
  <footer>XOMNI · data also available at <a href="data/skills.json">data/skills.json</a></footer>
</div>

<script>
const SKILLS = {data_json};

const searchEl = document.getElementById('search');
const domainEl = document.getElementById('domain');
const gridEl = document.getElementById('grid');
const countEl = document.getElementById('count');

function render() {{
  const q = searchEl.value.trim().toLowerCase();
  const d = domainEl.value;
  const items = SKILLS.filter(s => {{
    if (d && s.category !== d) return false;
    if (!q) return true;
    return (s.name + ' ' + s.description + ' ' + s.category).toLowerCase().includes(q);
  }});
  countEl.textContent = items.length === SKILLS.length
    ? `Showing all ${{SKILLS.length}} skills`
    : `${{items.length}} of ${{SKILLS.length}} skills`;
  gridEl.innerHTML = items.map(s =>
    `<div class="card"><span class="tag">${{s.category}}</span><h3>${{s.name}}</h3><div class="desc">${{s.description || '—'}}</div></div>`
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
    if not SKILLS_DIR.is_dir():
        print(f"error: skills dir not found: {SKILLS_DIR}", file=sys.stderr)
        return 1

    print(f"Scanning {SKILLS_DIR} …")
    skills = collect_skills()
    print(f"Found {len(skills)} SKILL.md files.")

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
