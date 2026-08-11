"""Prompt Enhancer plugin — /enhance <raw prompt>.

VERIFIED WORKING (2026-08-10): unit-tested handler + real ctx.llm path +
live CLI end-to-end (enhanced prompt appeared in state.db as an injected
user message; agent executed it and delivered the output).

Takes a raw, unpolished user prompt, rewrites it to prompt-engineer
quality using the user's active model (ctx.llm), prints the enhanced
version, and (by default) injects it back as the next user message so
the agent executes the enhanced prompt and produces the best output.

Modes:
  /enhance <raw prompt>        enhance + show + auto-execute (default)
  /enhance --show <raw prompt> only show the enhanced prompt
  /enhance -s <raw prompt>     alias for --show
  /enhance help                usage
Alias: /pe

Files: plugin.yaml (name: prompt-enhancer, version, description) +
this __init__.py in $HERMES_HOME/plugins/prompt-enhancer/.
Enable with: hermes plugins enable prompt-enhancer  (takes effect NEXT session)
"""

# The heart of the feature: an elite prompt-engineering system prompt.
ENHANCER_SYSTEM_PROMPT = """You are a world-class prompt engineer — the kind top AI labs hire to design prompts for their frontier models. The user gives you a RAW, unpolished request. Rewrite it into a precisely engineered prompt that extracts the best possible output from any LLM.

CORE RULES
1. Preserve intent 100%. Never add requirements the user didn't ask for, never drop or soften details, never invent facts.
2. Make it self-contained. Front-load everything the model needs: role, goal, context, constraints, output format, quality bar.
3. Kill ambiguity. If the request is vague, either (a) make the most reasonable interpretation explicit in the prompt, or (b) if truly necessary, state the key assumption in brackets at the start. Do NOT end with a list of questions.
4. Be concrete. Replace weak words ("good", "nice", "some", "better") with measurable or checkable terms.
5. Structure with these sections — but ONLY include the ones that add value for THIS request (skip irrelevant ones, never pad):
   - ROLE: the persona/expertise the model should adopt
   - GOAL: one crisp sentence describing the deliverable
   - CONTEXT: background, environment, constraints, audience
   - REQUIREMENTS: numbered, concrete instructions
   - CONSTRAINTS: what to avoid, limits (tone, length, style, forbidden things)
   - OUTPUT FORMAT: exact structure — headings, bullets, JSON schema, code layout, file naming
   - QUALITY BAR: what "excellent" looks like and how the result will be judged
   - EDGE CASES / AMBIGUITIES: pre-empt the obvious failure modes
6. Include 1-2 targeted examples (input -> expected output shape) ONLY when the format is non-obvious and an example would genuinely help.
7. If the raw request is ALREADY excellent, tighten it only — do not bloat.
8. Output ONLY the enhanced prompt itself. No preamble, no "Here is your enhanced prompt:", no explanations, no markdown fences, no quotes around it."""

HELP_TEXT = """Prompt Enhancer — /enhance <raw prompt>

Rewrites your raw prompt to prompt-engineer quality (role, goal,
context, requirements, constraints, output format, quality bar) using
your active model, then auto-executes it so you get the best output.

Usage:
  /enhance <raw prompt>         enhance + show + auto-execute (default)
  /enhance --show <raw prompt>  only show the enhanced prompt (-s works too)
  /enhance help                 this help

Example:
  /enhance explain quantum computing simply
Alias: /pe"""


def _strip_marker(args: str, marker: str) -> tuple[str, bool]:
    """If args starts with marker, strip it and return (rest, True)."""
    low = args.lower()
    if low.startswith(marker):
        return args[len(marker):].lstrip(), True
    return args, False


def _parse_args(raw_args: str) -> tuple[str, bool] | None:
    """Return (prompt, show_only) or None for help/empty."""
    args = raw_args.strip()
    if not args or args.lower() in {"help", "-h", "--help"}:
        return None
    args, show_only = _strip_marker(args, "--show")
    if not show_only:
        args, show_only = _strip_marker(args, "-s")
    args = args.strip()
    if not args:
        return None
    return args, show_only


def _enhance(ctx, raw_prompt: str) -> str:
    """Run the enhancement completion against the user's active model."""
    result = ctx.llm.complete(
        messages=[
            {"role": "system", "content": ENHANCER_SYSTEM_PROMPT},
            {"role": "user", "content": raw_prompt},
        ],
        temperature=0.4,
        max_tokens=2500,
        purpose="prompt enhancement",
    )
    text = (result.text or "").strip()
    if not text:
        raise RuntimeError("model returned an empty enhancement")
    return text


def _handle_enhance(raw_args: str) -> str:
    parsed = _parse_args(raw_args)
    if parsed is None:
        return HELP_TEXT

    prompt, show_only = parsed
    try:
        enhanced = _enhance(_CTX, prompt)
    except Exception as exc:  # noqa: BLE001 — surface to user, don't crash CLI
        return (
            f"\033[1;31m/enhance failed: {exc}\033[0m\n"
            "Your original prompt was left untouched — just re-send it."
        )

    if show_only:
        return f"[enhanced prompt — copy & reuse]\n\n{enhanced}"

    # Default: queue the enhanced prompt as the next user message so the
    # agent executes it and delivers the best output.
    try:
        _CTX.inject_message(enhanced, role="user")
    except Exception as exc:  # noqa: BLE001
        return (
            f"[enhanced prompt — could not auto-execute ({exc}), copy it]\n\n{enhanced}"
        )
    return (
        "[enhanced prompt queued — the agent will now execute it]\n\n"
        f"{enhanced}"
    )


# Module-level context ref, set in register(). The CLI dispatch calls the
# handler synchronously with the context already registered, so a module
# global is safe here (single active session per process).
_CTX = None


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_command(
        "enhance",
        handler=_handle_enhance,
        description="Rewrite your raw prompt to prompt-engineer quality, then execute it.",
        args_hint="<raw prompt>",
    )
    ctx.register_command(
        "pe",
        handler=_handle_enhance,
        description="Alias for /enhance — prompt enhancement + auto-execute.",
        args_hint="<raw prompt>",
    )
