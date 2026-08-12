"""Bharat Pack — Hermes plugin wiring.

Commands: /bharat [lang] (switch Hindi/regional UI strings), /bharat
providers [name] (Indian provider snippets: Sarvam/Bhashini/Krutrim),
/bharat models, /bharat langs.

No hooks — this module registers commands only and never alters agent
behavior (zero-hooks rule for new plugins).
"""
from __future__ import annotations

from . import core

_CTX = None
_current = "hi"  # in-memory UI-language state; not persisted, not hooked

HELP = (
    "/bharat                 switch to Hindi UI strings (default)\n"
    "/bharat <lang>          switch UI strings: en | hi | ta | te | bn\n"
    "/bharat providers       all Indian provider snippets (Sarvam/Bhashini/Krutrim)\n"
    "/bharat providers <p>   one provider's snippet\n"
    "/bharat models          Indian model-pool registry (source=spec)\n"
    "/bharat langs           supported languages + voice fallbacks\n"
)


def _handle_bharat(raw: str) -> str:
    global _current
    args = (raw or "").strip().split()
    if not args:
        return core.greet(_current) + "\n\n" + HELP
    cmd = args[0].lower()
    if cmd == "providers":
        if len(args) > 1:
            snip = core.provider_snippet(args[1])
            if snip is None:
                return f"unknown provider '{args[1]}'. Known: {', '.join(core.PROVIDER_SNIPPETS)}"
            return snip
        return core.providers_text()
    if cmd == "models":
        return core.models_text()
    if cmd == "langs":
        return core.langs_text()
    if cmd in core.UI_STRINGS:
        _current = cmd
        s = core.ui_strings(cmd)
        return f"{s['language_switched']}: {cmd} — {s['hello']}"
    return f"unknown language '{cmd}'. Known: {', '.join(core.UI_STRINGS)}"


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "bharat",
        handler=_handle_bharat,
        description="Bharat Pack: switch Hindi/regional UI strings, list Indian providers/models",
        args_hint="[lang|providers [name]|models|langs]",
    )
