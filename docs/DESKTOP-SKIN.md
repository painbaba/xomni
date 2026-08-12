# XOMNI Desktop Skin — Token Contract & Dark/Light Pairing

> Backlog item **P2-26 — Desktop GUI skin sync**.
> Machine-readable skin tokens for desktop GUI shells (Electron / Tauri / webview),
> synced from the website theme (`website/css/style.css`).
> Source file: `data/skins/xomni-skin.json` · Contract: `xomni-skin/v1`.

---

## 1. Token contract

`data/skins/xomni-skin.json` is the single machine-readable source of the XOMNI look for any
non-web client. Schema:

```jsonc
{
  "name": "xomni",                 // skin identifier
  "version": "1.0.0",              // bump on every token change (see resync, §3)
  "synced_from": "website/css/style.css", // canonical source of the dark tokens
  "synced_at": "2026-08-12",       // ISO date of last sync
  "contract": "xomni-skin/v1",     // schema contract id (breaking changes bump this, not version)
  "variants": {
    "dark":  { "<token>": "<value>", ..., "_notes": "..." },
    "light": { "<token>": "<value>", ..., "_notes": { "<token>": "why this value" } }
  }
}
```

### Key naming

- Key = CSS custom property name from `:root` **minus the leading `--`** (`--accent2` → `"accent2"`).
- Values are verbatim CSS values: hex colors keep the case used in the stylesheet
  (`#0A0C0E`, not `#0a0c0e`); non-color tokens (`mono`, `sans`, `radius`, `maxw`) are
  kept identical across variants.
- `_notes` is reserved: per-variant metadata, never a style token. Consumers MUST ignore it.

### Variants

| Field | Meaning |
|---|---|
| `variants.dark` | **Source of truth.** Must byte-match the `:root` block of `website/css/style.css` at `synced_at`. Never hand-edit — re-extract (§3). |
| `variants.light` | Same key set (including `_notes`), human-curated inversion. Theme-agnostic tokens (`mono`, `sans`, `radius`, `maxw`) are identical to dark; every color is an intentional light-mode counterpart documented in `_notes`. |

### Current token set (16 + `_notes`)

`bg`, `bg-soft`, `panel`, `card`, `border`, `text`, `muted`, `accent`, `accent2`,
`green`, `amber`, `red`, `mono`, `sans`, `radius`, `maxw`.

---

## 2. Dark/light pairing rules

### Flip on theme switch (surface & content luminance)

| Token | Dark | Light | Rule |
|---|---|---|---|
| `bg` | `#050607` | `#F5F6F7` | base surface, flips to near-white |
| `bg-soft` | `#0A0C0E` | `#ECEEF1` | always **slightly lighter than `bg` in dark, slightly darker than `bg` in light** |
| `panel` | `#101316` | `#EFF1F4` | secondary surface |
| `card` | `#171B1F` | `#FFFFFF` | always **lighter than `panel`** in both modes |
| `border` | `#1E2329` | `#D9DEE4` | low-emphasis outline, visible on both surfaces |
| `text` | `#E8EAED` | `#111417` | primary foreground, same hue family as `bg` |
| `muted` | `#A6ADB5` | `#5C6470` | secondary foreground; darkened in light to keep contrast |

### Stay constant (accent palette — brand identity)

`accent` (`#00E5A0`), `accent2` (`#00B87E`), `green` (`#2FD6A1`), `amber` (`#FFB454`),
`red` (`#FF6B6B`) are the **brand hue values in dark mode**. The website uses them only on
dark backgrounds, so desktop light mode **may** use the darkened counterparts
(`#00A87A`, `#008F63`, `#1FA97C`, `#A86400`, `#D64545`) when the token is rendered on a
light surface — but the dark variant values must never change (they are the brand).
Rule: **the hue family never changes; only luminance may be tuned for contrast**, and any
tuning is recorded in the light variant's `_notes`.

### Theme-agnostic (never flip)

`mono`, `sans`, `radius` (`12px`), `maxw` (`1160px`).

### Minimum required set for a desktop GUI

A desktop shell (Electron/Tauri/webview) renders the XOMNI look with these 10 tokens;
the other 6 are optional refinements:

1. `bg` — window background
2. `panel` — sidebars, toolbars, input fields
3. `card` — message bubbles, list items, popovers
4. `border` — all 1px separators / outlines
5. `text` — primary text
6. `muted` — secondary text, timestamps, labels
7. `accent` — interactive elements, links, focus rings, logo gradient start
8. `accent2` — gradient end, secondary interactive states
9. `green` — success/prompt/code-string text
10. `red` — errors, destructive actions

(`bg-soft`, `amber`, `mono`, `sans`, `radius`, `maxw` are optional; default them
from the dark variant if omitted.)

**Pairing invariant:** switching variants must swap *every* token in rows 1–7 of the
flip table together — never a partial flip (e.g. `bg` light with `text` dark breaks
contrast). `mono`/`sans`/`radius`/`maxw` carry over unchanged.

---

## 3. Resync procedure (when `style.css` `:root` changes)

1. Re-extract the dark tokens from `website/css/style.css`.
2. Diff against `variants.dark` — if any value differs, update `variants.dark` and
   `synced_at` to today's date.
3. Bump `version` (patch `1.0.0` → `1.0.1` for value-only changes). If keys were added
   or removed, also update the light variant key set and bump the minor version.
4. If the light variant counterpart needs contrast work, update it and its `_notes`.
5. Run the verification snippet from §4 (both asserts must pass) before committing.

One-line re-extraction sketch (bash, from repo root) — extracts `:root` vars as JSON:

```bash
python -c "import re,json;css=open('website/css/style.css').read();m=re.search(r':root\s*\{(.*?)\}',css,re.S);t={k.strip():v.strip().rstrip(';').strip() for k,v in re.findall(r'--([\w-]+)\s*:\s*([^;]+);',m.group(1))};json.dump(t,open('data/skins/dark-tmp.json','w'),indent=2);print(len(t),'tokens extracted')"
```

Then diff `data/skins/dark-tmp.json` against `variants.dark` (ignoring `_notes`) and fold
in any changes.

---

## 4. How a desktop app consumes it

```js
// Electron/Tauri preload or renderer — load once at startup
const skin = await fetch('data/skins/xomni-skin.json').then(r => r.json());

// pick variant: dark = default (XOMNI brand), light = system preference
const variant = matchMedia('(prefers-color-scheme: light)').matches
  ? skin.variants.light : skin.variants.dark;

// map to CSS variables: token "accent2" -> "--accent2"
const vars = Object.entries(variant)
  .filter(([k]) => !k.startsWith('_'))      // drop _notes
  .map(([k, v]) => `--${k}: ${v};`)
  .join('\n');

const style = document.createElement('style');
style.textContent = `:root { ${vars} }`;
document.head.appendChild(style);

// or, for a native toolkit: build a theme object from the same tokens
// e.g. { background: variant.bg, surface: variant.card, primary: variant.accent, ... }
```

**Rules for consumers:**

- Never hardcode XOMNI colors in the app — always read them from the JSON.
- Cache the parsed skin; listen for app-level "theme changed" events and re-apply the
  mapping (swap `variants.dark` ⇄ `variants.light`) rather than reloading.
- If `contract` is ever bumped to `xomni-skin/v2`, treat the file as a breaking schema
  change and update the mapper accordingly.

### Verification

```bash
python -c "import json;d=json.load(open('data/skins/xomni-skin.json'));assert set(d['variants']['dark'])==set(d['variants']['light']);print(len(d['variants']['dark']),'tokens ok')"
```
