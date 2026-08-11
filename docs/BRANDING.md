# XOMNI Brand Rules

This document is the single source of truth for how the product is named,
written, and referenced anywhere in this repository — docs, plugin strings,
launchers, README copy, and future marketing. If a string is user-visible, it
follows these rules.

## 1. The product name

- The product is **XOMNI** — always ALL-CAPS, five letters, no punctuation.
  Correct: `XOMNI`, `[XOMNI]`, `$XOMNI_HOME`, `XOMNI_HOME`.
  Wrong: `Xomni`, `xomni`, `XOMNI™`, `xOmni`, `Omni`.
- The tagline, used verbatim in launchers, READMEs, and demos:
  **"one agent. every feature. every free model."** (lowercase by design —
  do not title-case it, do not add a period after the last word).
- XOMNI is a separate, sellable product. It is not "the unified agent", not
  "the omni agent", not "Omni", and not a Hermes skin.

## 2. Architecture wording

- When describing the *architecture* (host core + edge modules), say
  **"the unified host"** — never "the unified agent".
- When naming the *product* in prose, say **XOMNI** — e.g. "XOMNI's contract",
  "every agent in the XOMNI stack", "the free-model layer of XOMNI".
- `$XOMNI_HOME` is the canonical env var for the install root. Launchers
  (`run.cmd`, `run.sh`) set it; code reads it. Never introduce a parallel
  `OMNI_HOME` / `UNIFIED_HOME`.

## 3. Agent names are attribution, never co-branding

- The six agent names (Hermes, OpenCode, jcode, Codex, Aider, Goose) — plus
  OpenClaw as a feature source — appear **only** as:
  - attribution in license/attribution docs,
  - strength/feature source tables (e.g. the FEATURES.md matrix),
  - technical descriptions of where a capability came from.
- Never write "Hermes-XOMNI", "XOMNI by Hermes", "powered by OpenCode", or
  any fused/co-branded form. XOMNI is the brand; the agents are ingredients.
- In prose about the product, list them as plain nouns: "XOMNI ships 6 merged
  agents (Hermes, OpenCode, jcode, Codex, Aider, Goose)."

## 4. What never to write

| Never | Because |
|---|---|
| `unified agent` (as a product name) | Old working title; it is not the brand |
| `OmniFlash`, `Omni Flash`, `omni-flash` | Another product's model name; never ours |
| Standalone `omni` / `Omni` as a brand | XOMNI is the brand; bare "omni" is a generic prefix |
| `[xomni]` lowercase console prefix | Brand must be ALL-CAPS even in log lines |
| `Xomni` / `XOMNI™` / `xOmni` | Wrong casing / trademark styling |
| `unified stack` / `unified host core` as product | "the unified host" is architecture-only wording |
| Co-branded forms (`Hermes-XOMNI`, `XOMNI x Aider`) | Agents are sources, not partners |

Third-party "omni" words are fine and must NOT be renamed: `Gemini Omni
Flash`, `Kling 3.0 Omni`, `Qwen-Omni`, `mimo-v2-omni`, `omni-moderation`,
`omnibus`, `omnidirectional`, `omniscient`, `OmniDocBench`. These are other
products' names or plain English — they are not our brand and changing them
would corrupt model IDs and research notes.

## 5. Plugin and path naming

- Existing plugin identifiers (`omni-media`, `omni-memory`) and their state
  paths (`~/.omni-memory`, `OMNIMEM_STATE`) are **stable identifiers** — do
  not rename; renaming breaks installs, tests, and stored state. When their
  docstrings are product-facing, say "XOMNI … plugin" so the plugin reads as
  part of XOMNI, not as a separate "omni" brand.
- New plugins: prefer names that do not start with a bare `omni` prefix.
  If a name must contain it, keep the identifier lowercase and clarify the
  XOMNI relationship in the docstring.
- Console/log prefixes in launchers and scripts: `[XOMNI]` (ALL-CAPS), never
  `[xomni]` or `[omni]`.

## 6. Do / Don't checklist (run before any commit touching user-visible text)

Do:
- [ ] Product referred to as `XOMNI` (ALL-CAPS) in every user-visible string.
- [ ] Tagline spelled exactly: `one agent. every feature. every free model.`
- [ ] `XOMNI_HOME` used for the install root env var.
- [ ] Agent names appear only in attribution / strength tables or provenance notes.
- [ ] `[XOMNI]` prefix on launcher/log output.

Don't:
- [ ] `unified agent`, `the unified stack`, `OmniFlash`, or bare `omni`/`Omni` as a brand.
- [ ] Lowercase `xomni` in any user-visible string.
- [ ] Co-branded or hyphenated product names.
- [ ] Renaming existing plugin identifiers or state paths.

## 7. Verification

Run from the repo root after any text change:

```bash
grep -rn -i "unified agent" --include="*.md" --include="*.py" --include="*.cmd" --include="*.sh" --include="*.ps1" . | grep -v "\.tmp/"   # expect 0
grep -rn -i "omniflash" . | grep -v "\.tmp/"                                   # expect 0
grep -rn "\[xomni\]" .                                                          # expect 0
grep -rn -i "omni" . | grep -v -i "xomni" \
  | grep -v -iE "omnibus|omnidirectional|omniscient|omniflash|omni[ -]flash|kling|gemini|omnidoc|mimo|hypersomnia|omnia|vendor/|\.tmp/"  # expect only plugin identifiers omni-media/omni-memory + third-party model names
```

Note: the parent repo `unified-agent` still contains pre-rebrand wording
(`unified agent` ×11 text files, lowercase `[xomni]` in `ollama/start-ollama.ps1`)
and is tracked separately — do not edit it from this repo.
