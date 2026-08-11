# Omni Design Doctrine (condensed)

XOMNI's design doctrine for agent-generated UI, distilled from Claude Design,
Google Stitch (DESIGN.md), Linear/Vercel/Stripe, DTCG tokens, and WCAG 2.2.
Full research: `.tmp/omni-design/research/{SYNTHESIS,CLAUDE-DESIGN,STITCH,OTHER-SOURCES}.md`

## Principles (ranked)

1. Surface first — commit to ONE of 7 archetypes before any tokens:
   Monitor / Operate / Compare / Configure / Decide-Learn / Explore / Command-Inspect.
   A hero is correct ONLY on Decide/Learn.
2. Achromatic base + one functional accent — never a decorative palette.
3. Type is hierarchy before boxes — <=3 weights, negative tracking at display,
   mono for code/numerals (tabular-nums).
4. Whisper-level chrome — 0.05-0.08 alpha borders, layered shadows,
   luminance-stepped dark elevation. No unearned blur.
5. Every element earns its place — no filler, fake metrics, placeholder
   testimonials, or decorative stats.
6. Motion is discipline, not theater — state-clarifying, subtle, respects
   prefers-reduced-motion.
7. Tokens are the contract; verification is the ship gate.

## The 10-tell slop diagnostic

Score 0-10; ship threshold <= 2. Repair in the register the complaint calls for:

| # | Tell | Repair |
|---|------|--------|
| 1 | Tech gradient (blue/violet 3+ colors) | recolor/re-typeset |
| 2 | Generic indigo/violet accent | recolor/re-typeset |
| 3 | Feature-tile grid (3+ equal cards) | re-layout |
| 4 | Accent rail (colored left strip) | remove decoration |
| 5 | Unearned blur / glassmorphism | remove decoration |
| 6 | Monument stat numbers | remove decoration |
| 7 | Icon topper above headings | remove decoration |
| 8 | Centered stack | re-layout |
| 9 | Default type (Inter/system-ui only) | recolor/re-typeset |
| 10 | Wrong surface (hero on Monitor) | re-layout |

Diagnose first, then repair — never recolor a layout problem.

## Token blueprint (DTCG-style)

base -> semantic -> component aliasing. Required groups: color (bg/surface/elevated/
ink/muted/faint/border/accent/accent-hover/accent-dim/success/danger/warning/syntax),
type (system sans + mono, clamp() scale), space (4-64px), radius (6/10/16),
shadow (1-3), motion (--ease-out-expo cubic-bezier(.16,1,.3,1); 150/300/500ms),
reduced-motion block. Presets: xomni-dark, xomni-light, terminal-emerald, plasma-cyan.

## Composition playbook (non-hero alternatives)

Asymmetric hero with code-window anchor · editorial alternating sections ·
stat band · logo/model marquee · full-bleed CTA band · command-palette anchor.

## Verification gate (before shipping any artifact)

1. HTML parses; no placeholders left. 2. Zero external network refs.
3. prefers-reduced-motion block present. 4. focus-visible styles present.
5. Contrast >= 4.5:1 for text. 6. 44px touch targets. 7. 320px no overflow.
8. JS syntax checks. 9. Slop score <= 2. 10. Real numbers only (no fake stats).
