#!/usr/bin/env python3
"""XOMNI external-skills database builder + security report.

Reads data/raw/scrape*.json (produced by the scraping pipeline), dedupes by
sha256, loads into data/skills.db, and regenerates docs/SKILLS-SECURITY.md.

Integration (additive):
  - If data/curated-skills.json exists (curator output: ranked top-useful list,
    entries keyed by sha256), the skills table additionally gets
    `rank INTEGER` and `usefulness REAL` columns populated by sha256 match.

Usage: python data/build_db.py   (run from repo root or anywhere — paths are absolute)
"""
import json, os, re, sqlite3, datetime

ROOT = r"C:\Users\HP\xomni"
RAW = os.path.join(ROOT, "data", "raw")
DB = os.path.join(ROOT, "data", "skills.db")
REPORT = os.path.join(ROOT, "docs", "SKILLS-SECURITY.md")
CURATED = os.path.join(ROOT, "data", "curated-skills.json")
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def load_curated(path):
    """Return dict {sha256: (rank, usefulness)} plus {name: (rank, usefulness)}
    fallback map and entry count. Tolerant of list or {'skills': [...]} shapes."""
    by_sha, by_name, n = {}, {}, 0
    if not os.path.exists(path):
        return by_sha, by_name, n
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print(f"!! curated-skills.json unreadable ({e}) — proceeding without rank columns")
        return by_sha, by_name, n
    if isinstance(data, dict):
        # allow {"skills": [...]} wrapper
        data = data.get("skills") or data.get("entries") or []
    if not isinstance(data, list):
        print("!! curated-skills.json: expected list — proceeding without rank columns")
        return by_sha, by_name, n
    for it in data:
        if not isinstance(it, dict):
            continue
        n += 1
        try:
            rank = int(it.get("rank"))
        except (TypeError, ValueError):
            rank = None
        use = it.get("usefulness")
        if use is None:
            use = it.get("usefulness_score") or it.get("score")
        try:
            use = float(use) if use is not None else None
        except (TypeError, ValueError):
            use = None
        sha = it.get("sha256") or it.get("hash")
        name = it.get("name")
        if sha and rank is not None:
            by_sha[sha] = (rank, use)
        elif name and rank is not None:
            by_name[str(name).lower()] = (rank, use)
    print(f"curated-skills.json: {n} entries loaded ({len(by_sha)} by sha256, "
          f"{len(by_name)} by name)")
    return by_sha, by_name, n


def main():
    raws = sorted(f for f in os.listdir(RAW) if f.startswith("scrape") and f.endswith(".json"))
    curated_sha, curated_name, n_curated = load_curated(CURATED)
    rows, sources = [], {}
    for f in raws:
        path = os.path.join(RAW, f)
        try:
            items = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print(f"!! {f}: unreadable ({e}) — skipped")
            continue
        if not isinstance(items, list):
            print(f"!! {f}: not a list ({type(items).__name__}) — skipped")
            continue
        seen = set()
        for it in items:
            if not isinstance(it, dict) or "sha256" not in it:
                continue
            if it["sha256"] in seen:
                continue
            seen.add(it["sha256"])
            sha = str(it.get("sha256", ""))
            rank, use = curated_sha.get(sha, (None, None))
            if rank is None and sha:
                rank, use = curated_name.get(str(it.get("name", "")).lower(), (None, None))
            rows.append((
                str(it.get("name", ""))[:200], str(it.get("source", ""))[:200],
                str(it.get("source_url", ""))[:500], str(it.get("category", ""))[:100],
                str(it.get("description", ""))[:500], str(it.get("content", "")),
                sha, str(it.get("license", ""))[:100],
                str(it.get("scan_verdict", "REVIEW")), str(it.get("scan_notes", ""))[:2000],
                rank, use, NOW,
            ))
        sources[f] = {"items": len(items), "unique": len(seen), "file": path,
                      "url": f"data/raw/{f}"}

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS skills")
    cur.execute("DROP TABLE IF EXISTS sources")
    cur.execute("""CREATE TABLE sources(
        source TEXT PRIMARY KEY, url TEXT, items_found INTEGER, scraped_at TEXT)""")
    cur.execute("""CREATE TABLE skills(
        id INTEGER PRIMARY KEY, name TEXT, source TEXT, source_url TEXT, category TEXT,
        description TEXT, content TEXT, sha256 TEXT, license TEXT,
        scan_verdict TEXT CHECK(scan_verdict IN ('PASS','REVIEW','REJECT')),
        scan_notes TEXT, rank INTEGER, usefulness REAL, scraped_at TEXT)""")
    for f, info in sources.items():
        cur.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?)",
                    (f, info["url"], info["unique"], NOW))
    cur.executemany("INSERT INTO skills(name,source,source_url,category,description,"
                    "content,sha256,license,scan_verdict,scan_notes,rank,usefulness,scraped_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()

    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    by_src = cur.execute("SELECT source, COUNT(*) FROM skills GROUP BY source ORDER BY 2 DESC").fetchall()
    by_verdict = cur.execute("SELECT scan_verdict, COUNT(*) FROM skills GROUP BY scan_verdict").fetchall()
    ranked = cur.execute("SELECT COUNT(*) FROM skills WHERE rank IS NOT NULL").fetchone()[0]
    ranked_by_verdict = cur.execute(
        "SELECT scan_verdict, COUNT(*) FROM skills WHERE rank IS NOT NULL "
        "GROUP BY scan_verdict").fetchall()
    top_ranked = cur.execute(
        "SELECT name, source, rank, usefulness FROM skills WHERE rank IS NOT NULL "
        "ORDER BY rank LIMIT 20").fetchall()
    rejected = cur.execute("SELECT name, source, scan_notes FROM skills WHERE scan_verdict='REJECT' "
                           "ORDER BY source LIMIT 30").fetchall()
    reviewed = cur.execute("SELECT name, source, scan_notes FROM skills WHERE scan_verdict='REVIEW' "
                           "ORDER BY source LIMIT 30").fetchall()
    con.close()

    # ---- write the security report ----
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(f"# XOMNI External Skills — Security Scan Report ({NOW})\n\n")
        f.write(f"Database: `data/skills.db` — integrity_check: **{integrity}**\n\n")
        f.write("## Methodology\n\n"
                "Every SKILL.md harvested from external sources is scanned statically "
                "(never executed) for: prompt-injection instructions (\"ignore previous "
                "instructions\", exfiltration), credential theft (env/API-key reads "
                "combined with network sends), eval/exec/subprocess of remote or dynamic "
                "content, network calls to unknown hosts, and obfuscation (large "
                "base64/hex blobs). Verdicts: **PASS** (clean), **REVIEW** (warning-level "
                "findings), **REJECT** (dangerous — kept in DB only for the audit trail, "
                "never suggested for import).\n\n")
        f.write("## Totals\n\n")
        f.write(f"- Total skills in DB: **{total}**\n")
        f.write(f"- Sources merged: {len(sources)} (`{', '.join(raws)}`)\n")
        for v, c in by_verdict:
            f.write(f"- {v}: **{c}**\n")
        f.write(f"- Ranked (from curated-skills.json): **{ranked}** / {total} "
                f"({100.0 * ranked / total:.1f}% coverage)\n")
        if n_curated:
            f.write(f"- Curated entries: {n_curated} loaded from `data/curated-skills.json`"
                    f" (matched by sha256)\n")
        else:
            f.write("- curated-skills.json not present at build time — rank/usefulness columns empty\n")
        if ranked_by_verdict:
            f.write("- Ranked by verdict: "
                    + ", ".join(f"{v} {c}" for v, c in ranked_by_verdict) + "\n")
        f.write("\n## Per-source counts\n\n| Source | Skills |\n|---|---|\n")
        for s, c in by_src:
            f.write(f"| {s} | {c} |\n")
        f.write("\n## Top-20 curated skills (by rank)\n\n| Rank | Name | Source | Usefulness |\n|---|---|---|---|\n")
        for name, src, rank, use in top_ranked:
            f.write(f"| {rank} | {name} | {src} | {use if use is not None else '-'} |\n")
        f.write("\n## REJECTED skills (audit trail — do not import)\n\n")
        if rejected:
            for name, src, notes in rejected:
                f.write(f"- **{name}** ({src}): {notes[:200]}\n")
        else:
            f.write("None.\n")
        f.write("\n## REVIEW findings (warning-level)\n\n")
        if reviewed:
            for name, src, notes in reviewed:
                f.write(f"- **{name}** ({src}): {notes[:200]}\n")
        else:
            f.write("None.\n")
        f.write("\n## Raw source files\n\n")
        for fname, info in sources.items():
            f.write(f"- `{fname}`: {info['items']} items, {info['unique']} unique "
                    f"(sha256) -> {info['file']}\n")

    print(f"DB: {DB}")
    print(f"integrity_check: {integrity}")
    print(f"total skills: {total}")
    print("by source:", by_src)
    print("by verdict:", by_verdict)
    print(f"ranked: {ranked}/{total} ({100.0 * ranked / total:.1f}%)")
    print("ranked by verdict:", ranked_by_verdict)
    print(f"REJECTED: {len(rejected)} shown, REVIEW: {len(reviewed)} shown")
    print(f"report: {REPORT}")

if __name__ == "__main__":
    main()
