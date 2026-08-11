"""Aider-style repo map — pure stdlib, no Hermes imports.

Builds a compact symbol-level map of a codebase (files + top-level
classes/functions/types) so the model can navigate without dumping whole files.
The honest v1 uses per-language regex extraction; tree-sitter is the deferred
upgrade (see docs/PORT-PLAN.md P3).
"""
from __future__ import annotations

import os
import re

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "dist", "build", ".next", ".nuxt", ".output", "target", "vendor",
    ".idea", ".vscode", ".vs", "coverage", ".cache", "site-packages",
    ".terraform", ".serverless", "Pods", ".gradle",
}
MAX_FILE_BYTES = 500_000

_SYMBOL_PATTERNS = [
    (".py", re.compile(r"^\s*(?:async\s+def|def|class)\s+([A-Za-z_]\w*)", re.M)),
    (".js", re.compile(r"^\s*(?:export\s+(?:default\s+)?(?:class|function|const|let|var)\s+|function\s+|class\s+)([A-Za-z_$][\w$]*)", re.M)),
    (".ts", re.compile(r"^\s*(?:export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type|enum)\s+|function\s+|class\s+|interface\s+|type\s+|enum\s+)([A-Za-z_$][\w$]*)", re.M)),
    (".go", re.compile(r"^\s*(?:func\s+\([^)]*\)\s+)?(?:func|type)\s+([A-Za-z_]\w*)", re.M)),
    (".rs", re.compile(r"^\s*(?:pub\s+)?(?:fn|struct|enum|trait|impl|mod|type|const)\s+([A-Za-z_]\w*)", re.M)),
    (".c", re.compile(r"^\s*(?:static\s+|inline\s+)*[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^;]*\)\s*\{|^\s*typedef\s+.*?\b([A-Za-z_]\w*)\s*;|^\s*#define\s+([A-Za-z_]\w*)", re.M)),
    (".cpp", re.compile(r"^\s*(?:static\s+|inline\s+|virtual\s+)*[A-Za-z_~][\w\s\*&:<>,]*?\b([A-Za-z_~]\w*)\s*\([^;]*\)\s*(?:const\s*)?\{|^\s*class\s+([A-Za-z_]\w*)|^\s*struct\s+([A-Za-z_]\w*)", re.M)),
    (".java", re.compile(r"^\s*(?:public|private|protected|static|final|abstract|synchronized|native|transient|volatile|default)\s+.*?\b(class|interface|enum)\s+([A-Z]\w*)|^\s*(?:public|private|protected|static|final|abstract)\s+[\w<>,?\[\]\s]+\s+([a-z]\w*)\s*\(", re.M)),
    (".rb", re.compile(r"^\s*(?:class|module|def)\s+([A-Za-z_]\w*(?:::\w+)*)", re.M)),
    (".php", re.compile(r"^\s*(?:public|private|protected|static|final|abstract)?\s*function\s+([A-Za-z_]\w*)|^\s*(?:abstract\s+|final\s+)?class\s+([A-Za-z_]\w*)", re.M)),
    (".sh", re.compile(r"^\s*([A-Za-z_]\w*)\s*\(\s*\)\s*\{", re.M)),
    (".sql", re.compile(r"^\s*(?:CREATE|create)\s+(?:TABLE|table|VIEW|view|FUNCTION|function|PROCEDURE|procedure)\s+([\w.]+)", re.M)),
    (".kt", re.compile(r"^\s*(?:(?:public|private|protected|internal|sealed|data|enum|annotation|abstract|final|open|suspend|inline|override)\s+)*(?:companion\s+object|object|interface|class|fun)\s+([A-Za-z_]\w*)", re.M)),
    (".swift", re.compile(r"^\s*(?:(?:public|private|internal|fileprivate|open|final|indirect|mutating|nonmutating|static|class)\s+)*(?:extension|protocol|struct|enum|class|func)\s+([A-Za-z_]\w*)", re.M)),
    (".dart", re.compile(r"^\s*(?:abstract\s+|base\s+|final\s+|sealed\s+|interface\s+|mixin\s+)*class\s+([A-Za-z_]\w*)|^\s*(?:void|Future\s*<[^>]*>|Stream\s*<[^>]*>|[A-Za-z_]\w*)\s+([a-z_]\w*)\s*\(|^\s*enum\s+([A-Za-z_]\w*)|^\s*typedef\s+(?:[A-Za-z_]\w*\s+)?([A-Za-z_]\w*)", re.M)),
    (".scala", re.compile(r"^\s*(?:(?:private|protected|final|abstract|sealed|case|implicit|lazy|override)\s+)*(?:object|trait|class|def)\s+([A-Za-z_]\w*)", re.M)),
    (".lua", re.compile(r"^\s*(?:local\s+)?function\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)", re.M)),
    (".r", re.compile(r"^\s*([A-Za-z_.]\w*)\s*(?:<-|=)\s*function\s*\(|^\s*setClass\s*\(\s*['\"]([A-Za-z_]\w*)['\"]", re.M)),
    (".tf", re.compile(r"^\s*(?:resource|data)\s+[\"'][A-Za-z_][\w-]*[\"']\s+[\"']([A-Za-z_][\w-]*)[\"']\s*\{|^\s*(?:variable|output|module)\s+[\"']([A-Za-z_][\w-]*)[\"']\s*\{", re.M)),
    (".vue", re.compile(r"^\s*(?:export\s+default\s+)?(?:class|function|const|let|var)\s+([A-Za-z_$][\w$]*)|^\s*name\s*:\s*['\"]([A-Za-z_$][\w$]*)['\"]", re.M)),
]

DEFAULT_MAX_FILES = 60
DEFAULT_MAX_CHARS = 6000


def stack_tags(root: str) -> list[str]:
    """Local, private stack detection — extension scan only. Nothing leaves the machine."""
    tags: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            low = fn.lower()
            if low == "package.json" or low.endswith((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")):
                tags.add("node")
            if low == "requirements.txt" or low == "pyproject.toml" or low == "setup.py" or low.endswith(".py"):
                tags.add("python")
            if low == "go.mod" or low.endswith(".go"):
                tags.add("go")
            if low == "cargo.toml" or low.endswith(".rs"):
                tags.add("rust")
            if low == "pom.xml" or low.endswith(".java"):
                tags.add("java")
            if low == "gemfile" or low.endswith(".rb"):
                tags.add("ruby")
            if low in ("dockerfile", "compose.yml", "compose.yaml") or low.endswith(".dockerfile"):
                tags.add("docker")
            if low.endswith(".php"):
                tags.add("php")
            if low.endswith((".sql",)):
                tags.add("sql")
            if low.endswith((".c", ".h")):
                tags.add("c")
            if low.endswith((".cpp", ".cc", ".hpp")):
                tags.add("cpp")
    return sorted(tags)


def _vue_script_section(text: str) -> str | None:
    """Extract the <script> body of a .vue SFC, or None if there is none."""
    m = re.search(r"<script[^>]*>(.*?)</script>", text, re.S | re.I)
    return m.group(1) if m else None


def _vue_component_name(path: str) -> str:
    """File-level component name fallback for .vue files (basename minus ext)."""
    return os.path.splitext(os.path.basename(path))[0]


def _symbols_for(path: str, ext: str) -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    except OSError:
        return []
    if not text or len(text.encode("utf-8", "replace")) > MAX_FILE_BYTES:
        return []
    for pattern_ext, rx in _SYMBOL_PATTERNS:
        if ext == pattern_ext or (pattern_ext in (".c", ".cpp") and ext in (".h", ".hpp", ".cc")):
            search_text = text
            if ext == ".vue":
                section = _vue_script_section(text)
                if section is None:
                    return [_vue_component_name(path)]
                search_text = section
            found = []
            for m in rx.finditer(search_text):
                for g in m.groups():
                    if g:
                        found.append(g)
                        break
            if ext == ".vue" and not found:
                found.append(_vue_component_name(path))
            return list(dict.fromkeys(found))  # dedupe, keep order
    return []


def _walk_entries(root: str) -> list[tuple[int, str, list[str]]]:
    """Walk root (skipping noise dirs and oversized files): (depth, relpath, symbols)."""
    entries: list[tuple[int, str, list[str]]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(full) > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            ext = os.path.splitext(fn)[1].lower()
            rel = os.path.relpath(full, root).replace("\\", "/")
            symbols = _symbols_for(full, ext)
            depth = rel.count("/")
            entries.append((depth, rel, symbols))
    return entries


def build_map(root: str, max_files: int = DEFAULT_MAX_FILES, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Return the repo map: depth-sorted file list with symbol lines, size-capped."""
    entries = _walk_entries(root)
    entries.sort(key=lambda e: (e[0], e[1]))
    out: list[str] = []
    total = 0
    for depth, rel, symbols in entries[:max_files]:
        line = f"{'  ' * depth}{rel}"
        if symbols:
            line += "  [" + ", ".join(symbols[:12]) + "]"
        if len(symbols) > 12:
            line += f" (+{len(symbols) - 12} more)"
        if total + len(line) > max_chars:
            break
        out.append(line)
        total += len(line)
    return "\n".join(out)


def _score_file(rel: str, symbols: list[str], terms: list[str]) -> int:
    """Score one file against query terms (all matching case-insensitive).

    Per term, in descending priority:
      +3  exact word-boundary match inside a symbol name
      +2  substring match in the filename
      +1  case-insensitive substring match inside a symbol name
    Scores from all terms combine per file.
    """
    score = 0
    rel_l = rel.lower()
    for t in terms:
        if any(re.search(rf"\b{re.escape(t)}\b", s, re.I) for s in symbols):
            score += 3
        elif t in rel_l:
            score += 2
        elif any(t in s.lower() for s in symbols):
            score += 1
    return score


def rank_files(root: str, query: str, top_n: int = 10) -> str:
    """Rank files by relevance to query terms (aider 'relevant files' idea).

    Scores combine per file (exact symbol match > filename substring >
    plain case-insensitive substring); output is rendered like build_map but
    ranked by score, each line labeled with its score. Unmatched files are
    omitted. Returns "" for a blank query.
    """
    terms = [t.lower() for t in re.split(r"\s+", query.strip()) if t]
    if not terms:
        return ""
    scored: list[tuple[int, int, str, list[str]]] = []
    for depth, rel, symbols in _walk_entries(root):
        score = _score_file(rel, symbols, terms)
        if score > 0:
            scored.append((score, depth, rel, symbols))
    scored.sort(key=lambda e: (-e[0], e[1], e[2]))
    out: list[str] = []
    total = 0
    for score, depth, rel, symbols in scored[:top_n]:
        line = f"{score}  {'  ' * depth}{rel}"
        if symbols:
            line += "  [" + ", ".join(symbols[:12]) + "]"
        if len(symbols) > 12:
            line += f" (+{len(symbols) - 12} more)"
        if total + len(line) > DEFAULT_MAX_CHARS:
            break
        out.append(line)
        total += len(line)
    return "\n".join(out)
