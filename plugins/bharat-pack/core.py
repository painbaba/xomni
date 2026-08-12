"""Bharat Pack — India-market layer for XOMNI.

Hindi/regional UI strings, an Indian model-pool registry (Sarvam AI,
Bhashini/MeitY, Krutrim Cloud) and provider config snippets in the same
shape as plugins/provider-pool, so the free/rupee-priced Indian stack can
be wired into every agent in the XOMNI host.

All facts (pricing, free tiers, language counts) come from
INDIA-FEATURES.md — the 2026-08-12 primary-source research pass; every
registry entry carries source="spec" and anything the research could not
verify is flagged [UNVERIFIED] in place.

Pure stdlib, no Hermes imports. Unit-testable in isolation.
"""
from __future__ import annotations

import json

# ---------------------------------------------------------------------------
# Language strings — key UI strings for the India belt.
# en + hi are the parity pair; regional languages share the same key set.
# Voice fallbacks use edge-tts style locale codes (hi-IN, ta-IN, ...).
# ---------------------------------------------------------------------------

UI_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "hello": "Hello",
        "welcome": "Welcome to XOMNI",
        "models": "Models",
        "providers": "Providers",
        "sponsor": "Sponsor",
        "install": "Install",
        "verify": "Verify",
        "done": "Done",
        "error": "Error",
        "loading": "Loading",
        "exit": "Exit",
        "free": "Free",
        "help": "Help",
        "commands": "Commands",
        "settings": "Settings",
        "update": "Update",
        "version": "Version",
        "language_switched": "Language switched to",
    },
    "hi": {
        "hello": "नमस्ते",
        "welcome": "XOMNI में आपका स्वागत है",
        "models": "मॉडल",
        "providers": "प्रदाता",
        "sponsor": "प्रायोजक",
        "install": "इंस्टॉल",
        "verify": "जाँच",
        "done": "हो गया",
        "error": "त्रुटि",
        "loading": "लोड हो रहा है",
        "exit": "बाहर निकलें",
        "free": "मुफ्त",
        "help": "सहायता",
        "commands": "कमांड",
        "settings": "सेटिंग्स",
        "update": "अपडेट",
        "version": "संस्करण",
        "language_switched": "भाषा बदल दी गई है",
    },
    "mr": {
        "hello": "नमस्कार",
        "welcome": "XOMNI मध्ये आपले स्वागत आहे",
        "models": "मॉडेल",
        "providers": "प्रदाते",
        "sponsor": "प्रायोजक",
        "install": "स्थापित करा",
        "verify": "तपासा",
        "done": "झाले",
        "error": "त्रुटी",
        "loading": "लोड होत आहे",
        "exit": "बाहेर पडा",
        "free": "मोफत",
        "help": "मदत",
        "commands": "आज्ञा",
        "settings": "सेटिंग्ज",
        "update": "अपडेट",
        "version": "आवृत्ती",
        "language_switched": "भाषा बदलली",
    },
    "ta": {
        "hello": "வணக்கம்",
        "welcome": "XOMNIக்கு வரவேற்கிறோம்",
        "models": "மாதிரிகள்",
        "providers": "வழங்குநர்கள்",
        "sponsor": "ஆதரவாளர்",
        "install": "நிறுவு",
        "verify": "சரிபார்",
        "done": "முடிந்தது",
        "error": "பிழை",
        "loading": "ஏற்றுகிறது",
        "exit": "வெளியேறு",
        "free": "இலவசம்",
        "help": "உதவி",
        "commands": "கட்டளைகள்",
        "settings": "அமைப்புகள்",
        "update": "புதுப்பி",
        "version": "பதிப்பு",
        "language_switched": "மொழி மாற்றப்பட்டது",
    },
    "te": {
        "hello": "నమస్కారం",
        "welcome": "XOMNIకి స్వాగతం",
        "models": "మోడల్స్",
        "providers": "ప్రొవైడర్లు",
        "sponsor": "స్పాన్సర్",
        "install": "ఇన్స్టాల్",
        "verify": "ధృవీకరించు",
        "done": "పూర్తయింది",
        "error": "లోపం",
        "loading": "లోడ్ అవుతోంది",
        "exit": "నిష్క్రమించు",
        "free": "ఉచితం",
        "help": "సహాయం",
        "commands": "ఆదేశాలు",
        "settings": "సెట్టింగ్స్",
        "update": "నవీకరణ",
        "version": "వెర్షన్",
        "language_switched": "భాష మార్చబడింది",
    },
    "kn": {
        "hello": "ನಮಸ್ಕಾರ",
        "welcome": "XOMNI ಗೆ ಸುಸ್ವಾಗತ",
        "models": "ಮಾದರಿಗಳು",
        "providers": "ಪೂರೈಕೆದಾರರು",
        "sponsor": "ಪ್ರಾಯೋಜಕ",
        "install": "ಸ್ಥಾಪಿಸಿ",
        "verify": "ಪರಿಶೀಲಿಸಿ",
        "done": "ಪೂರ್ಣಗೊಂಡಿದೆ",
        "error": "ದೋಷ",
        "loading": "ಲೋಡ್ ಆಗುತ್ತಿದೆ",
        "exit": "ನಿರ್ಗಮಿಸಿ",
        "free": "ಉಚಿತ",
        "help": "ಸಹಾಯ",
        "commands": "ಆಜ್ಞೆಗಳು",
        "settings": "ಸೆಟ್ಟಿಂಗ್ಗಳು",
        "update": "ನವೀಕರಿಸಿ",
        "version": "ಆವೃತ್ತಿ",
        "language_switched": "ಭಾಷೆ ಬದಲಾಯಿಸಲಾಗಿದೆ",
    },
    "gu": {
        "hello": "નમસ્તે",
        "welcome": "XOMNI માં આપનું સ્વાગત છે",
        "models": "મોડેલ્સ",
        "providers": "પ્રદાતાઓ",
        "sponsor": "પ્રાયોજક",
        "install": "ઇન્સ્ટોલ કરો",
        "verify": "ચકાસો",
        "done": "થઈ ગયું",
        "error": "ભૂલ",
        "loading": "લોડ થઈ રહ્યું છે",
        "exit": "બહાર નીકળો",
        "free": "મફત",
        "help": "મદદ",
        "commands": "આદેશો",
        "settings": "સેટિંગ્સ",
        "update": "અપડેટ",
        "version": "આવૃત્તિ",
        "language_switched": "ભાષા બદલાઈ",
    },
    "bn": {
        "hello": "নমস্কার",
        "welcome": "XOMNI-তে স্বাগতম",
        "models": "মডেল",
        "providers": "প্রদানকারী",
        "sponsor": "স্পনসর",
        "install": "ইনস্টল",
        "verify": "যাচাই",
        "done": "সম্পন্ন",
        "error": "ত্রুটি",
        "loading": "লোড হচ্ছে",
        "exit": "প্রস্থান",
        "free": "বিনামূল্যে",
        "help": "সহায়তা",
        "commands": "কমান্ড",
        "settings": "সেটিংস",
        "update": "আপডেট",
        "version": "সংস্করণ",
        "language_switched": "ভাষা পরিবর্তিত হয়েছে",
    },
}

LANGUAGES: list[dict] = [
    {"code": "en", "name": "English", "name_native": "English", "edge_tts": "en-IN", "bhashini": "en"},
    {"code": "hi", "name": "Hindi", "name_native": "हिन्दी", "edge_tts": "hi-IN", "bhashini": "hi"},
    {"code": "mr", "name": "Marathi", "name_native": "मराठी", "edge_tts": "mr-IN", "bhashini": "mr"},
    {"code": "ta", "name": "Tamil", "name_native": "தமிழ்", "edge_tts": "ta-IN", "bhashini": "ta"},
    {"code": "te", "name": "Telugu", "name_native": "తెలుగు", "edge_tts": "te-IN", "bhashini": "te"},
    {"code": "kn", "name": "Kannada", "name_native": "ಕನ್ನಡ", "edge_tts": "kn-IN", "bhashini": "kn"},
    {"code": "gu", "name": "Gujarati", "name_native": "ગુજરાતી", "edge_tts": "gu-IN", "bhashini": "gu"},
    {"code": "bn", "name": "Bengali", "name_native": "বাংলা", "edge_tts": "bn-IN", "bhashini": "bn"},
]


def ui_strings(lang: str) -> dict[str, str]:
    """Strings for a language code; unknown codes fall back to English."""
    return UI_STRINGS.get((lang or "").strip().lower(), UI_STRINGS["en"])


def greet(lang: str) -> str:
    s = ui_strings(lang)
    return f"{s['hello']} — {s['welcome']} ({lang})"


def langs_text() -> str:
    out = ["Bharat Pack languages (voice fallback = edge-tts locale):"]
    for lang in LANGUAGES:
        out.append(
            f"  {lang['code']:<4} {lang['name_native']:<12} {lang['name']:<10} "
            f"edge-tts: {lang['edge_tts']:<6} bhashini: {lang['bhashini']}"
        )
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Indian model pool — registry entries in the same shape as provider-pool's
# GATEWAY_MODELS, plus India-specific fields. source="spec" = facts taken
# from INDIA-FEATURES.md (the 2026-08-12 primary-source research pass).
# ---------------------------------------------------------------------------

INDIAN_MODELS: list[dict] = [
    {
        "id": "sarvam-105b",
        "vendor": "Sarvam AI",
        "kind": "chat",
        "tags": ["indic", "chat", "inr", "hindi"],
        "vision": False,
        "pricing": "₹4 in / ₹2.5 cached / ₹16 out per 1M tokens",
        "free_tier": "100 free API credits on signup",
        "languages": "11 Indic languages",
        "source": "spec",
        "note": "sarvam.ai/api-pricing · ISO 27001 + SOC 2 Type II",
    },
    {
        "id": "sarvam-30b",
        "vendor": "Sarvam AI",
        "kind": "chat",
        "tags": ["indic", "chat", "inr", "fast"],
        "vision": False,
        "pricing": "₹2.5 in / ₹1.5 cached / ₹10 out per 1M tokens",
        "free_tier": "100 free API credits on signup",
        "languages": "Hindi-first Indic chat",
        "source": "spec",
        "note": "sarvam.ai/api-pricing · cheaper sibling of Sarvam-105B",
    },
    {
        "id": "krutrim-1",
        "vendor": "Krutrim Cloud (Ola)",
        "kind": "chat",
        "tags": ["indic", "chat", "inr", "residency"],
        "vision": False,
        "pricing": "INR billing · per-token [UNVERIFIED — public pricing page 404s]",
        "free_tier": "Free start, no credit card required",
        "languages": "Hindi + English",
        "source": "spec",
        "note": "cloud.olakrutrim.com · Made in India, data stays in India · ISO 27001/27017/27018",
    },
    {
        "id": "bhashini-asr",
        "vendor": "Bhashini (MeitY)",
        "kind": "asr",
        "tags": ["indic", "asr", "gov", "free"],
        "vision": False,
        "pricing": "free-to-register, approval-gated [pricing unverified — government-funded]",
        "free_tier": "One Registration → API access",
        "languages": "22+ languages",
        "source": "spec",
        "note": "bhashini.gov.in · National Language Translation Mission · in production for Parliament",
    },
    {
        "id": "bhashini-tts",
        "vendor": "Bhashini (MeitY)",
        "kind": "tts",
        "tags": ["indic", "tts", "gov", "free"],
        "vision": False,
        "pricing": "free-to-register, approval-gated [pricing unverified]",
        "free_tier": "One Registration → API access",
        "languages": "22+ languages",
        "source": "spec",
        "note": "bhashini.gov.in · voice-out for the Bharat Pack (edge-tts hi-IN fallback)",
    },
    {
        "id": "bhashini-mt",
        "vendor": "Bhashini (MeitY)",
        "kind": "mt",
        "tags": ["indic", "mt", "gov", "free"],
        "vision": False,
        "pricing": "free-to-register, approval-gated [pricing unverified]",
        "free_tier": "One Registration → API access",
        "languages": "22 scheduled languages (IndicTrans2 lineage)",
        "source": "spec",
        "note": "bhashini.gov.in · machine translation · billion+ inferences served",
    },
]

INDIA_RECOMMENDED: dict[str, str] = {
    "default": "sarvam-105b",
    "chat": "sarvam-105b",
    "asr": "bhashini-asr",
    "tts": "bhashini-tts",
    "mt": "bhashini-mt",
    "residency": "krutrim-1",
}


def models_text() -> str:
    out = [f"Indian model pool — {len(INDIAN_MODELS)} entries (source=spec, INDIA-FEATURES.md 2026-08-12):"]
    out.append(
        f"  recommended: default={INDIA_RECOMMENDED['default']} asr={INDIA_RECOMMENDED['asr']} "
        f"tts={INDIA_RECOMMENDED['tts']} mt={INDIA_RECOMMENDED['mt']} residency={INDIA_RECOMMENDED['residency']}"
    )
    for m in INDIAN_MODELS:
        out.append(f"  {m['id']:<14} {m['vendor']:<22} {m['kind']:<5} {m['pricing']}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Provider snippets — same block format as provider-pool's HERMES_PROVIDER_BLOCK
# (commented YAML: provider / model / base_url / key_env + facts), so the Indian
# stack slots under `model:` in config.yaml the same way the free pool does.
# ---------------------------------------------------------------------------

PROVIDER_SNIPPETS: dict[str, str] = {
    "sarvam": """\
# --- xomni bharat-pack: Sarvam AI (India) ---
# Place under `model:` in config.yaml. OpenAI-compatible chat + TTS/ASR.
#   provider: sarvam
#   model: sarvam-105b            # or sarvam-30b (cheaper)
#   base_url: https://api.sarvam.ai/v1
#   key_env: SARVAM_API_KEY
# 100 free credits on signup · Sarvam-105B ₹4 in / ₹2.5 cached / ₹16 out per
# 1M tokens · Sarvam-30B ₹2.5 / ₹1.5 / ₹10 · TTS bulbul:v3, 11 Indic
# languages, ₹30/₹15 per character · ISO 27001 + SOC 2 Type II
# pricing: https://www.sarvam.ai/api-pricing""",
    "bhashini": """\
# --- xomni bharat-pack: Bhashini (MeitY, government) ---
# National Language Translation Mission. ASR/TTS/MT; free registration is
# approval-gated and per-account endpoints are issued after approval.
#   provider: bhashini
#   model: bhashini-asr            # or bhashini-tts / bhashini-mt
#   base_url: https://bhashini.gov.in/api
#   key_env: BHASHINI_API_KEY
# 22+ languages · free-to-register (approval-gated) · [pricing unverified —
# historically government-funded] · in production for Parliament
# portal: https://bhashini.gov.in""",
    "krutrim": """\
# --- xomni bharat-pack: Krutrim Cloud (Ola, India) ---
# India-resident: bills in INR, data stays in India. Free start, no card.
#   provider: krutrim
#   model: krutrim-1
#   base_url: https://cloud.olakrutrim.com/v1
#   key_env: KRUTRIM_API_KEY
# [UNVERIFIED — per-token pricing page 404s; verify at signup] · ISO 27001/
# 27017/27018, SOC I/II · Made in India
# portal: https://cloud.olakrutrim.com""",
}


def provider_snippet(name: str) -> str | None:
    """One provider's config snippet, or None for unknown names."""
    return PROVIDER_SNIPPETS.get((name or "").strip().lower())


def providers_text() -> str:
    out = ["Indian model providers (Bharat Pack) — snippets match provider-pool format:"]
    for name, snip in PROVIDER_SNIPPETS.items():
        out.append("")
        out.append(f"----- {name} -----")
        out.append(snip)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Sarvam TTS dry-run preview — payload shape only, NO live calls.
# Research (INDIA-FEATURES.md 2026-08-12): Sarvam TTS = "natural voices across
# 11 Indic languages", per-character ₹30/₹15; API is POST /v1/tts with an
# api-subscription-key header. This section builds the exact request shape a
# caller would send (payload dict + ready curl) WITHOUT calling the endpoint
# and WITHOUT reading the API key — the key is referenced by env-var NAME
# only, so its value can never leak into logs or the CLI.
# ---------------------------------------------------------------------------

SARVAM_TTS_URL = "https://api.sarvam.ai/v1/tts"
SARVAM_TTS_MODEL = "bulbul/v1"  # baseline TTS model; research lists bulbul:v3 (₹30/₹15 per char)
SARVAM_API_KEY_ENV = "SARVAM_API_KEY"  # env-var name — referenced, never read/printed
# Bharat-pack lang codes -> Sarvam target_language_code values.
SARVAM_TTS_LANGS: dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "kn": "kn-IN",
    "gu": "gu-IN",
    "bn": "bn-IN",
}


def tts_preview(text: str, lang: str) -> dict:
    """Dry-run Sarvam TTS request shape. Never calls the API, never reads the key.

    Returns a dict describing the exact ``POST https://api.sarvam.ai/v1/tts``
    request: headers reference ``SARVAM_API_KEY`` by env-var NAME only (the
    value is never fetched or printed), the body carries model=bulbul/v1 +
    target_language_code + input, and a ready-to-run curl example is included.
    Unknown lang codes fall back to hi-IN.
    """
    lang = (lang or "").strip().lower()
    tlc = SARVAM_TTS_LANGS.get(lang, SARVAM_TTS_LANGS["hi"])  # unknown -> hi-IN
    body = {
        "model": SARVAM_TTS_MODEL,
        "target_language_code": tlc,
        "input": text,
    }
    headers = {
        "api-subscription-key": f"env:{SARVAM_API_KEY_ENV}",
        "Content-Type": "application/json",
    }
    curl = (
        f"curl -sS -X POST {SARVAM_TTS_URL} \\\n"
        f"  -H 'api-subscription-key: ${SARVAM_API_KEY_ENV}' \\\n"
        f"  -H 'Content-Type: application/json' \\\n"
        f"  -d '{json.dumps(body, ensure_ascii=False)}'"
    )
    return {
        "provider": "sarvam",
        "kind": "tts",
        "mode": "dry-run",  # no live call is made by this function
        "method": "POST",
        "url": SARVAM_TTS_URL,
        "key_env": SARVAM_API_KEY_ENV,  # referenced by name; value never read/printed
        "headers": headers,
        "body": body,
        "lang": lang,
        "target_language_code": tlc,
        "text_chars": len(text),
        "curl": curl,
    }


def tts_preview_text(text: str, lang: str) -> str:
    """Human-readable dry-run TTS preview: payload + curl, no live call."""
    p = tts_preview(text, lang)
    return (
        "Sarvam TTS dry-run preview (no live call made):\n"
        f"  POST {p['url']}\n"
        f"  key:  ${p['key_env']}  (env-var name — value not read or printed)\n"
        f"  lang: {p['lang']} -> target_language_code {p['target_language_code']}\n"
        f"  text: {p['text_chars']} chars\n"
        f"  headers: {json.dumps(p['headers'], ensure_ascii=False)}\n"
        f"  body:    {json.dumps(p['body'], ensure_ascii=False)}\n"
        "  curl:\n"
        f"{p['curl']}"
    )
