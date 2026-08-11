"""OmniDesign — pure-stdlib core: token presets, 10-tell slop audit, artifact generator.

XOMNI Omni Design feature. Zero hooks, zero host imports — unit-testable standalone.
"""
from __future__ import annotations

import os
import re

# ---------------------------------------------------------------- token presets
TOKEN_PRESETS: dict = {
    "xomni-dark": {
        "bg": "#050607", "surface1": "#0A0C0E", "surface2": "#101316", "elevated": "#171B1F",
        "ink": "#E8EAED", "muted": "#A6ADB5", "faint": "#7B828A", "border": "#1E2329",
        "accent": "#00E5A0", "accent_hover": "#00FFB0", "accent_dim": "#00B87E",
        "success": "#2FD6A1", "danger": "#FF6B6B", "warning": "#FFB454", "syntax": "#5CC8FF",
    },
    "xomni-light": {
        "bg": "#FFFFFF", "surface1": "#F7F8FA", "surface2": "#EFF1F4", "elevated": "#FFFFFF",
        "ink": "#101316", "muted": "#5A626B", "faint": "#8A929B", "border": "#E2E6EA",
        "accent": "#00B87E", "accent_hover": "#009E6D", "accent_dim": "#00E5A0",
        "success": "#1FA97C", "danger": "#D64545", "warning": "#C77E1B", "syntax": "#0B7BB8",
    },
    "terminal-emerald": {
        "bg": "#000000", "surface1": "#050505", "surface2": "#0A0A0A", "elevated": "#111111",
        "ink": "#D4FFE8", "muted": "#7FB89B", "faint": "#4F7A66", "border": "#1A2E24",
        "accent": "#00FF9D", "accent_hover": "#5CFFBE", "accent_dim": "#00CC7D",
        "success": "#00FF9D", "danger": "#FF5555", "warning": "#FFB454", "syntax": "#55FFFF",
    },
    "plasma-cyan": {
        "bg": "#050A14", "surface1": "#0A1120", "surface2": "#101A2E", "elevated": "#16223A",
        "ink": "#E4F2FF", "muted": "#8FA8C4", "faint": "#5E7590", "border": "#1C2A42",
        "accent": "#5CC8FF", "accent_hover": "#8FDBFF", "accent_dim": "#3AA8E8",
        "success": "#5CC8FF", "danger": "#FF6B6B", "warning": "#FFB454", "syntax": "#00E5A0",
    },
}

REQUIRED_TOKEN_KEYS = {"bg", "surface1", "surface2", "elevated", "ink", "muted", "faint",
                       "border", "accent", "accent_hover", "accent_dim", "success", "danger",
                       "warning", "syntax"}

FONT_SANS = "ui-sans-serif, 'Segoe UI', system-ui, -apple-system, sans-serif"
FONT_MONO = "ui-monospace, 'Cascadia Code', Consolas, monospace"

EASE_EXPO = "cubic-bezier(.16,1,.3,1)"

REDUCED_MOTION_CSS = (
    "@media (prefers-reduced-motion: reduce){*,*::before,*::after{"
    "animation-duration:.01ms!important;animation-iteration-count:1!important;"
    "transition-duration:.01ms!important;scroll-behavior:auto!important}}"
)

FOCUS_CSS = ":focus-visible{outline:2px solid var(--accent);outline-offset:2px}"


def css_tokens(preset_name: str = "xomni-dark") -> str:
    """Render the :root CSS custom-property block for a preset."""
    t = TOKEN_PRESETS.get(preset_name, TOKEN_PRESETS["xomni-dark"])
    return (
        ":root{"
        f"--bg:{t['bg']};--surface-1:{t['surface1']};--surface-2:{t['surface2']};"
        f"--elevated:{t['elevated']};--ink:{t['ink']};--muted:{t['muted']};--faint:{t['faint']};"
        f"--border:{t['border']};--accent:{t['accent']};--accent-hover:{t['accent_hover']};"
        f"--accent-dim:{t['accent_dim']};--success:{t['success']};--danger:{t['danger']};"
        f"--warning:{t['warning']};--syntax:{t['syntax']};"
        f"--font-sans:{FONT_SANS};--font-mono:{FONT_MONO};"
        f"--space-1:4px;--space-2:8px;--space-3:16px;--space-4:24px;--space-5:32px;"
        f"--space-6:48px;--space-7:64px;"
        f"--radius-1:6px;--radius-2:10px;--radius-3:16px;"
        f"--shadow-1:0 1px 2px rgba(0,0,0,.4);--shadow-2:0 4px 12px rgba(0,0,0,.4);"
        f"--shadow-3:0 12px 32px rgba(0,0,0,.5);"
        f"--ease-out-expo:{EASE_EXPO};--dur-fast:150ms;--dur-med:300ms;--dur-slow:500ms;"
        f"color-scheme:{'dark' if t['bg'].startswith('#0') or t['bg']=='#000000' else 'light'};"
        "}"
    )


# ---------------------------------------------------------------- slop audit (10 tells)
def _pat(p: str) -> re.Pattern:
    return re.compile(p, re.IGNORECASE | re.DOTALL)


def _is_neutral(hex6: str) -> bool:
    """True if the hex is a neutral gray (R~G~B) — not a hue the audit should flag."""
    try:
        r, g, b = int(hex6[1:3], 16), int(hex6[3:5], 16), int(hex6[5:7], 16)
    except ValueError:
        return True
    return abs(r - g) <= 18 and abs(g - b) <= 18 and abs(r - b) <= 18


def _generic_indigo(html: str) -> bool:
    """Tell 2: a generic indigo/violet/blue accent — but NOT neutral grays."""
    for m in re.finditer(r"#(?:[6-9][0-9a-f]{2})[0-9a-f]{3}", html):
        h = m.group(0)
        if h.lower() in ("#7b828a", "#8b96b0", "#a6adb5", "#565e66", "#5e7590", "#8fa8c4"):
            continue  # known token grays
        if _is_neutral(h):
            continue
        # indigo/violet family: B clearly above R (blue-dominant, not cyan-green)
        r = int(h[1:3], 16); b = int(h[5:7], 16)
        if b - r >= 24:
            return True
    return False


def _tile_grid(html: str) -> bool:
    """Tell 3: three-plus equal icon/heading/sentence blocks (card tiles)."""
    return html.lower().count("<article") >= 3 or len(re.findall(r"<h[23]>", html)) >= 6


def _wrong_surface(html: str) -> bool:
    """Tell 10: a data-table presence inside a hero/landing/marketing section."""
    m = re.search(r"<section[^>]*class=\"[^\"]*hero[^\"]*\"[^>]*>(.*?)</section>",
                  html, re.I | re.S)
    if m and re.search(r"<table", m.group(1)):
        return True
    return bool(re.search(r"<table[\s\S]{0,200}?class=\"[^\"]*(hero|marketing)", html, re.I))


SLOP_CHECKS = [
    ("tech-gradient", _pat(r"linear-gradient\([^)]*#[0-9a-f]{6}[^)]*"),
     "recolor/re-typeset"),
    ("generic-indigo", _generic_indigo, "recolor/re-typeset"),
    ("feature-tile-grid", _tile_grid, "re-layout"),
    ("accent-rail", _pat(r"border-left:\s*(?:4|5|6)px\s+solid\s+(?:var\(--accent\)|#[0-9a-f]{3,6})"),
     "remove decoration"),
    ("unearned-blur", _pat(r"backdrop-filter:\s*blur|glass"),
     "remove decoration"),
    ("monument-stat", _pat(r"font-size:\s*(?:8[0-9]|[0-9]{3})px"),
     "remove decoration"),
    ("icon-topper", _pat(r"<svg[^>]*>\s*</svg>\s*</?[^>]*>\s*<h[23]"),
     "remove decoration"),
    ("center-stack", _pat(r"text-align:\s*center"),
     "re-layout"),
    ("default-type", _pat(r"font-family:\s*(?:Inter|system-ui)(?:,|;|\))"),
     "recolor/re-typeset"),
    ("wrong-surface", _wrong_surface, "re-layout"),
]

TELL_LABELS = {
    "tech-gradient": "Tech gradient",
    "generic-indigo": "Generic indigo/violet hue",
    "feature-tile-grid": "Feature-tile grid (3+ equal cards)",
    "accent-rail": "Accent rail (colored left strip)",
    "unearned-blur": "Unearned blur / glassmorphism",
    "monument-stat": "Monument stat numbers",
    "icon-topper": "Icon topper above headings",
    "center-stack": "Centered stack",
    "default-type": "Default type (Inter/system-ui only)",
    "wrong-surface": "Wrong surface (hero on monitor)",
}


def slop_score(html: str) -> dict:
    """Run the 10-tell diagnostic. Returns {score 0-10, tells, repair}."""
    fired = []
    for tell, check, _repair in SLOP_CHECKS:
        if callable(check):
            hit = bool(check(html))
        else:
            hit = bool(check.search(html))
        if hit:
            fired.append(tell)
    repairs = sorted({r for _, _, r in SLOP_CHECKS if r in _repair_of(fired)})
    return {
        "score": min(10, len(fired)),
        "tells": [TELL_LABELS.get(t, t) for t in fired],
        "tell_keys": fired,
        "repair": repairs,
    }


def _repair_of(fired):
    repair_map = {
        "feature-tile-grid": "re-layout", "center-stack": "re-layout", "wrong-surface": "re-layout",
        "tech-gradient": "recolor/re-typeset", "generic-indigo": "recolor/re-typeset",
        "default-type": "recolor/re-typeset",
        "accent-rail": "remove decoration", "unearned-blur": "remove decoration",
        "monument-stat": "remove decoration", "icon-topper": "remove decoration",
    }
    return {repair_map[t] for t in fired if t in repair_map}


# ---------------------------------------------------------------- artifact generator
SURFACE_KEYWORDS = {
    "Monitor": ["dashboard", "status", "monitor", "metrics", "observability", "analytics"],
    "Configure": ["settings", "configure", "setup", "onboarding", "wizard", "admin"],
    "Compare": ["pricing", "plans", "compare", "table", "spec"],
    "Explore": ["gallery", "search", "catalog", "browse", "discover", "marketplace"],
    "Operate": ["console", "queue", "inbox", "triage", "control"],
}
DECIDE_LEARN = "Decide/Learn"


def pick_surface(brief: str) -> str:
    b = brief.lower()
    for surface, kws in SURFACE_KEYWORDS.items():
        if any(k in b for k in kws):
            return surface
    return DECIDE_LEARN


def pick_template(brief: str) -> str:
    b = brief.lower()
    if any(k in b for k in ("deck", "presentation", "slides", "talk")):
        return "deck.html"
    if any(k in b for k in ("components", "lab", "component", "ui kit", "design system")):
        return "component-lab.html"
    return "landing.html"


def _body_for_surface(surface: str, title: str) -> str:
    h = f"<h1>{title}</h1>"
    if surface == "Monitor":
        return (
            "<section class=\"band\">" + h +
            "<p class=\"sub\">Live status at a glance.</p>"
            "<div class=\"stat-strip\"><div class=\"stat\"><strong>0</strong><span>metric</span></div>"
            "<div class=\"stat\"><strong>0</strong><span>metric</span></div>"
            "<div class=\"stat\"><strong>0</strong><span>metric</span></div></div>"
            "<table role=\"grid\"><tr><th>Item</th><th>Status</th></tr>"
            "<tr><td>—</td><td>ok</td></tr></table></section>"
        )
    if surface == "Configure":
        return (
            "<section class=\"band\">" + h +
            "<p class=\"sub\">Configure in minutes.</p>"
            "<div class=\"panel\"><label>Setting</label><input placeholder=\"value\">"
            "<button class=\"primary\">Save</button></div></section>"
        )
    if surface == "Compare":
        return (
            "<section class=\"band\">" + h +
            "<p class=\"sub\">Compare the options.</p>"
            "<table role=\"grid\"><tr><th></th><th>Option A</th><th>Option B</th></tr>"
            "<tr><td>Feature</td><td>✓</td><td>—</td></tr></table></section>"
        )
    if surface == "Explore":
        return (
            "<section class=\"band\">" + h +
            "<p class=\"sub\">Browse everything.</p>"
            "<div class=\"card-grid\"><article class=\"card\"><h3>Item</h3><p>Description.</p></article>"
            "<article class=\"card\"><h3>Item</h3><p>Description.</p></article>"
            "<article class=\"card\"><h3>Item</h3><p>Description.</p></article></div></section>"
        )
    if surface == "Operate":
        return (
            "<section class=\"band\">" + h +
            "<p class=\"sub\">Act on the queue.</p>"
            "<div class=\"queue\"><div class=\"row\"><span>task</span><button>Run</button></div></div></section>"
        )
    # Decide/Learn default: asymmetric hero + stats + features + cta
    return (
        "<section class=\"hero\">" + h +
        "<p class=\"sub\">A clear line about what this is and why it matters.</p>"
        "<div class=\"cta-row\"><button class=\"primary\">Get started</button>"
        "<button class=\"ghost\">Learn more</button></div></section>"
        "<section class=\"band stats\"><div class=\"stat\"><strong>1</strong><span>metric</span></div>"
        "<div class=\"stat\"><strong>2</strong><span>metric</span></div>"
        "<div class=\"stat\"><strong>3</strong><span>metric</span></div></section>"
        "<section class=\"band\"><div class=\"card-grid\">"
        "<article class=\"card\"><h3>Feature one</h3><p>What it does, briefly.</p></article>"
        "<article class=\"card\"><h3>Feature two</h3><p>What it does, briefly.</p></article>"
        "<article class=\"card\"><h3>Feature three</h3><p>What it does, briefly.</p></article>"
        "</div></section><section class=\"band cta\"><h2>Ready?</h2>"
        "<button class=\"primary\">Start now</button></section>"
    )


def _load_template(name: str) -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    with open(os.path.join(d, name), encoding="utf-8") as f:
        return f.read()


def generate_artifact(brief: str, preset: str = "xomni-dark", out_dir: str = ".") -> str:
    """Generate a self-contained single-file HTML artifact from a brief."""
    brief = (brief or "").strip() or "A clean landing page"
    surface = pick_surface(brief)
    template_name = pick_template(brief)
    title = brief.splitlines()[0][:80] if brief else "XOMNI artifact"
    html = _load_template(template_name)
    html = html.replace("{TOKENS}", css_tokens(preset))
    html = html.replace("{TITLE}", title)
    html = html.replace("{SURFACE}", surface)
    html = html.replace("{BODY}", _body_for_surface(surface, title))
    if "{TOKENS}" in html or "{BODY}" in html:
        raise ValueError("template placeholders not fully substituted")
    os.makedirs(out_dir, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:48] or "artifact"
    path = os.path.join(out_dir, f"{slug}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path
