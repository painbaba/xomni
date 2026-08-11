# Global auto-enhance via pre_llm_call — complete verified implementation

Extracted from the prompt-enhancer plugin auto mode (session 2026-08-10, verified
end-to-end against state.db). This is the full working pattern for silently
upgrading every user message before the agent's first model call of a turn.

## Architecture

- `register(ctx)` wires the hook: `ctx.register_hook("pre_llm_call", _on_pre_llm_call)`
- Hook returns `{"context": "..."}` -> appended into the turn's user message as
  `api_content` (ephemeral, cache-safe, never persisted). `content` stays clean.
- Toggle lives in `state.json` next to `__init__.py` (NOT config.yaml).
- Same handler serves manual mode + toggle: `/enhance <raw>`, `/enhance --show <raw>`,
  `/enhance auto [on|off]`, alias `/pe`.

## State toggle (survives restarts, no config.yaml edits)

```python
STATE_FILE = Path(__file__).resolve().parent / "state.json"

def _load_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}

def _save_state(state: dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except Exception:
        pass

def _auto_enabled() -> bool:
    return bool(_load_state().get("auto", False))
```

`/enhance auto on|off` -> `_save_state({"auto": True/False})`; `/enhance auto` -> query.

## Skip gate — never burn an LLM call on trivial messages

```python
TRIVIAL_RE = re.compile(r"^\s*(?:\W|\d)*\s*$")          # punct/digit/emoji only
TRIVIAL_WORDS = {"ok","okay","k","yes","yeah","yep","no","nope","thanks","thank you",
    "thx","done","got it","cool","nice","great","perfect","good","fine","sure",
    "continue","go on","next","again","more","👍","✅","🙏","❤️","😂"}
MIN_AUTO_LEN = 8

def _should_skip(raw: str) -> bool:
    text = (raw or "").strip()
    if not text or text.startswith("/"):   # slash commands never reach the loop anyway
        return True
    if len(text) < MIN_AUTO_LEN or TRIVIAL_RE.match(text):
        return True
    return text.lower().rstrip(".!?") in TRIVIAL_WORDS
```

## The hook

```python
def _on_pre_llm_call(**kwargs):
    if not _auto_enabled():
        return None
    raw = kwargs.get("user_message")
    if not isinstance(raw, str) or _should_skip(raw):
        return None
    try:
        # optional: pass a trimmed history tail so follow-ups disambiguate
        history = kwargs.get("conversation_history") or []
        tail = ""
        recent = []
        for msg in history[-4:]:
            if isinstance(msg, dict) and msg.get("role") in ("user","assistant") \
               and isinstance(msg.get("content"), str):
                s = msg["content"].strip().replace("\n", " ")[:400]
                if s:
                    recent.append(f"[{msg['role']}] {s}")
        if recent:
            tail = "\n\nPRIOR CONVERSATION (recent tail, for disambiguation only):\n" \
                   + "\n".join(recent[-3:])

        result = _CTX.llm.complete(
            messages=[
                {"role": "system", "content": AUTO_SYSTEM_PROMPT},
                {"role": "user", "content": f"USER MESSAGE TO ENHANCE:\n{raw}{tail}"},
            ],
            temperature=0.3, max_tokens=1200, purpose="auto prompt enhancement",
        )
        enhanced = (result.text or "").strip()
        if not enhanced or enhanced == raw.strip():
            return None
        return {"context": "[The request above was auto-enhanced for best output — "
                           "follow the refined prompt below, which fully captures the "
                           "user's intent.]\n\n" + enhanced}
    except Exception:
        return None   # silent fallback — message passes through untouched
```

## Auto-mode system prompt (DIFFERENT from manual mode)

Must handle conversational follow-ups without bloating short asks and without
altering code/paths/numbers:

```
You are a world-class prompt engineer embedded in an AI assistant. A user message
is about to be sent to the agent. Rewrite it into a precisely engineered prompt
that extracts the best possible output — but stay invisible and surgical.
1. Preserve intent 100%: never add requirements the user didn't ask for, never drop
   or soften details, never invent facts.
2. The user message may be a CONVERSATIONAL FOLLOW-UP ("make it faster", "now do
   part 2"). If prior context is provided, use it to disambiguate — but do NOT
   restate the whole history; keep the enhancement tight.
3. If the message is already clear and well-formed, tighten it only. If it is
   trivial (a bare instruction, a short command), DO NOT bloat it — a one-line
   message stays one line.
4. Ambiguity: make the most reasonable interpretation explicit in the prompt, or
   state the key assumption in brackets at the start. Never end with a list of
   questions.
5. Never alter code blocks, exact strings, file paths, commands, or numbers —
   preserve them verbatim.
6. Add structure ONLY where it helps: role, goal, context, requirements,
   constraints, output format, quality bar — whichever sections add value for THIS
   message, never pad.
7. Output ONLY the rewritten prompt. No preamble, no explanations, no markdown
   fences, no quotes.
```

## Verification (the authoritative proof)

`hermes chat -q "raw prompt"` runs the same loop + hooks; then:

```sql
SELECT substr(content,1,150), substr(api_content,1,700) FROM messages
WHERE session_id='<id>' AND role='user' ORDER BY timestamp ASC;
```

- `content` = what the user typed (stays clean) — proves silent
- `api_content` = what the model received (contains the enhanced prompt) — proves the hook fired

Observed live: raw 10-word ask became a structured ROLE/GOAL/CONTEXT prompt in
api_content; agent output matched the enhanced bar (caught a real bug in testing).

## Tradeoff to disclose to the user

Every non-trivial message costs one extra small LLM call before the real one
(~10-20s per turn). Provide `/cmd auto off` as the escape hatch and mention the
cost when enabling.
