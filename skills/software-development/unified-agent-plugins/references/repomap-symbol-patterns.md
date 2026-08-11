# Repomap: symbol-extraction regex craft + relevance scoring (validated by 15 green tests)

All patterns live in `_SYMBOL_PATTERNS` as `(ext, re.compile(rx, re.M))` — `^`-anchored,
line-based, one regex per extension. `_symbols_for(path, ext)` applies the matching
regex, takes the **first non-empty group per match** (multi-group patterns are in
existing style: java/c/cpp/php already use them), dedupes preserving order.

## Modifier-list + keyword-alternation pattern shape
```
^\s*(?:(?:public|private|protected|...)\s+)*(?:kw1|kw2|class|fun)\s+([A-Za-z_]\w*)
```
- **Alternation order matters**: put multi-word keywords before their prefixes
  (`companion\s+object` before `object`). `case\s+class` handled by `case` in the
  modifier list + `class` keyword (same capture either way).
- **A keyword can be both modifier and declaration** (swift `class func foo()` vs
  `class User {}`): put `class` in the modifier list AND the alternation — regex
  backtracking resolves it correctly (verified).
- Kotlin modifiers: public/private/protected/internal/sealed/data/enum/annotation/
  abstract/final/open/suspend/inline/override. Swift: public/private/internal/
  fileprivate/open/final/indirect/mutating/nonmutating/static/class. Scala:
  private/protected/final/abstract/sealed/case/implicit/lazy/override.

## Per-language specifics
- **kotlin** `.kt`: `(?:companion\s+object|object|interface|class|fun)\s+([A-Za-z_]\w*)`.
  Captures the companion's NAME; the enclosing class is also a symbol (test expected
  `[Server, main, Handler, Registry, Wrapper, Factory]`).
- **swift** `.swift`: `(?:extension|protocol|struct|enum|class|func)\s+([A-Za-z_]\w*)`.
- **dart** `.dart` (4 alternatives, order = class | func | enum | typedef):
  - class: `(?:abstract\s+|base\s+|final\s+|sealed\s+|interface\s+|mixin\s+)*class\s+([A-Za-z_]\w*)`
  - func: `^\s*(?:void|Future\s*<[^>]*>|Stream\s*<[^>]*>|[A-Za-z_]\w*)\s+([a-z_]\w*)\s*\(`
    — **lowercase-first capture `[a-z_]\w*` prevents class names being caught by the
    func alternative**; `Future\s*<[^>]*>` matches `Future<void>` without `\s+` issues.
  - typedef: `^\s*typedef\s+(?:[A-Za-z_]\w*\s+)?([A-Za-z_]\w*)` — optional leading
    return type consumed so `typedef int Compare(...)` and `typedef Compare = ...`
    both yield the name (backtracking makes the optional group skip when needed).
- **scala** `.scala`: `(?:object|trait|class|def)\s+([A-Za-z_]\w*)`.
- **lua** `.lua`: `^\s*(?:local\s+)?function\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)` —
  dotted names (`M.run`) kept, mirroring the ruby `Foo::Bar` style.
- **r** `.r`: `^\s*([A-Za-z_.]\w*)\s*(?:<-|=)\s*function\s*\(` OR `^\s*setClass\s*\(\s*['"]([A-Za-z_]\w*)['"]`.
- **terraform** `.tf`: `^\s*(?:resource|data)\s+["'][A-Za-z_][\w-]*["']\s+["']([A-Za-z_][\w-]*)["']\s*\{`
  OR `^\s*(?:variable|output|module)\s+["']([A-Za-z_][\w-]*)["']\s*\{` — capture the
  **instance name** (2nd identifier) for resource/data: the first-non-empty-group
  mechanic drops the 2nd group, so the type alone would be all that survived.
- **vue** `.vue`: extract `<script>` body first, then apply a JS-ish pattern on it:
  - `_vue_script_section`: `re.search(r"<script[^>]*>(.*?)</script>", text, re.S | re.I)`
  - pattern: `^\s*(?:export\s+default\s+)?(?:class|function|const|let|var)\s+([A-Za-z_$][\w$]*)`
    OR `^\s*name\s*:\s*['"]([A-Za-z_$][\w$]*)['"]` (Options-API `name:`).
  - **Fallback**: no `<script>` or zero matches → file-level component name
    (`os.path.splitext(os.path.basename(path))[0]`). Template HTML can't pollute
    because extraction runs on the script section only.
- **shell** `.sh` already existed (`^\s*([A-Za-z_]\w*)\s*\(\s*\)\s*\{`) — leave as-is.

## rank_files relevance scoring (aider 'relevant files')
`rank_files(root, query, top_n=10) -> str`; terms = lowercased whitespace split.
Per term, one tier via elif chain (NOT additive per term):

| tier | trigger | pts |
|---|---|---|
| exact word in symbol | `re.search(rf"\b{re.escape(t)}\b", s, re.I)` on any symbol | +3 |
| filename substring | `t in rel.lower()` | +2 |
| symbol substring | `t in s.lower()` on any symbol | +1 |

- Scores from all terms SUM per file; zero-score files omitted; sort `(-score, depth, rel)`;
  render like `build_map` (indent by depth, `[sym, ...]` cap 12, `(+N more)`, max-chars cap),
  each line prefixed `f"{score}  "` — so `line.split()[1]` is the path, token 0 the score.
- Blank/whitespace query → `""`. Case-insensitive by construction (terms lowercased,
  rel lowercased, symbol search re.I).
- Exact-vs-substring trap: `tokenize` is NOT an exact word match for term `token`
  (`\btoken\b` fails — no boundary before the trailing `e`) → scores +1, proving the
  tier ordering in tests.
