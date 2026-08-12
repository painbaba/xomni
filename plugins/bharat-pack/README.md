# bharat-pack

Bharat Pack — the India-market layer for XOMNI (feature #1 from
`.tmp/research-next/INDIA-FEATURES.md`): Hindi/regional UI strings, an
Indian model-pool registry, and provider config snippets for the
free/rupee-priced vernacular AI stack — **zero hooks**.

**What it does:** `/bharat` switches UI strings to Hindi (default) or any of
en/hi/ta/te/bn; `/bharat providers` prints config snippets for **Sarvam AI**
(100 free credits, ₹4–16/1M tokens), **Bhashini** (MeitY government
ASR/TTS/MT, 22+ languages, free-to-register) and **Krutrim Cloud** (INR
billing, India data residency); `/bharat models` lists the 6-entry Indian
model pool (`source=spec` — facts from the 2026-08-12 primary-source
research pass; unverified items flagged `[UNVERIFIED]` in place).

**Commands:**
- `/bharat` — Hindi UI strings + help
- `/bharat <lang>` — switch UI strings: `en | hi | ta | te | bn`
- `/bharat providers [name]` — all / one Indian provider snippet
- `/bharat models` — Indian model-pool registry
- `/bharat langs` — supported languages + edge-tts voice fallbacks
- `/bharat tts <lang> <text>` — **Sarvam TTS dry-run** preview: exact
  `POST https://api.sarvam.ai/v1/tts` payload (`model=bulbul/v1`,
  `target_language_code`) + ready curl. **No live call** — `SARVAM_API_KEY`
  is referenced by env-var name only, never read or printed.

**Speed posture:** commands only, no hooks (`register_hook` absent) — never
alters agent behavior. Pure stdlib `core.py`, no network calls, no state on
disk.

**Market brief:** `docs/INDIA.md` — WhatsApp B2B-only constraint (Meta AI
Provider ToS Jan 15, 2026 excludes India for consumer assistants), UPI
rails (zero-MDR UPI, Autopay/Intent not Collect), DPDP Act status, ranked
feature table and risks.

```bash
cd plugins/bharat-pack && python -m unittest tests.test_core -q
```
