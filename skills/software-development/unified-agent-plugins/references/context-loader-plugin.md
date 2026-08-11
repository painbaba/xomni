# context-loader plugin — verified build notes

Aider-style context injection (web pages + images) built 2026-08-10 at
`C:\Users\HP\unified-agent\plugins\context-loader\` (34/34 unit tests green;
live smoke-tested against real example.com AND the real opencode Zen vision
gateway). Use as the worked example for network-tool + vision-gateway plugins
in this collection.

## Anatomy (follows the collection layout)

```
plugins/context-loader/
├── plugin.yaml                # name/version/description only
├── core.py                    # PURE stdlib: html_to_text, fetch_page,
│                              #   image_to_data_url, vision_describe, load_key
├── __init__.py                # register(ctx): 2 model tools + 2 commands
└── tests/test_core.py         # `import core` + sys.path preamble
```

- Toolset labels are free-form: `fetch_page` registered under `"web"`,
  `describe_image` under `"file"` — no validation against a fixed set.
- Slash commands `/fetch <url>` and `/describe <path>` share the same core
  functions as the tools (handler = thin arg extraction + try/except).

## html_to_text — pipeline ORDER matters (regex-based, no parser)

1. extract `<title>` (first match, strip inner tags, unescape)
2. drop `<script|style|noscript|template>` blocks + `<!-- comments -->`
3. convert links FIRST (they carry hrefs): `<a ...href="..">text</a>` →
   `[text](href)`; drop `javascript:/data:/vbscript:` hrefs, keep anchor text
4. convert `<h1-h3>` → `#/##/### ` lines
5. strip remaining tags (replace with `" "` NOT `""`, or words fuse)
6. `html.unescape`, collapse `\s+` per line, drop blank lines
7. punctuation pass `re.sub(r"\s+([,.;:!?%])", r"\1", line)` — tag-stripping
   otherwise leaves `"world ,"` artifacts (found via a failing exact-phrase
   assertion; this is a real output-quality fix, keep it)

## fetch_page — urllib patterns

- Validate scheme via `urlparse(url).scheme` BEFORE any request; return
  `"fetch_page: unsupported URL scheme 'ftp' ... (only http/https allowed)"`.
- `Request(url, headers={"User-Agent": BROWSER_UA})`; `urlopen(req, timeout=20)`.
- Size cap: `raw = resp.read(max_bytes + 1)`; `truncated = len(raw) > max_bytes`;
  slice and append `" [truncated at N bytes]"` to the `URL:` header line.
- Charset: `resp.headers.get_content_charset()` wrapped in try/except
  AttributeError (a plain dict in mocks raises it) → utf-8 fallback, decode
  with `errors="replace"`.
- Error ladder: HTTPError (→ `HTTP error {code}`) → URLError (→ network error)
  → OSError (catches socket timeouts). Also a defensive `resp.status != 200`
  check after read.

## Vision gateway — VERIFIED recipe (opencode Zen, minimax-m3)

Live-verified this session (real key, real image, real description returned):

- Endpoint: `https://opencode.ai/zen/go/v1/chat/completions` (POST, `urllib`)
- Model: `minimax-m3`; `max_tokens: 900`; timeout 90s
- **Browser User-Agent is MANDATORY** — without it the gateway answers
  **403 with `{"error":{"code":1010}}`**. Surface it: on HTTPError read
  `exc.read().decode(...)[:200]` into the error message (the code number is
  the diagnostic).
- Auth: `Authorization: Bearer <key>`; key = `OPENCODE_GO_API_KEY` in
  `~/AppData/Local/hermes/.env` (present on this box, 67 chars; load_key()
  parses `KEY=value`, strips quotes, ignores comments/`#`, returns None if
  missing — never log/print the value).
- Body shape: `{"model", "messages":[{"role":"user","content":[
  {"type":"text","text":...}, {"type":"image_url","image_url":{"url": <data_url>}}]}],
  "max_tokens"}`.
- Response: `data["choices"][0]["message"]["content"]` — may be empty
  (explicit "empty description" error) or include the model's own
  `<think>...</think>` block (pass through verbatim — that is the model's
  honest output).
- Failure fallbacks: URLError/OSError → `"vision: gateway unreachable (...)"`;
  JSON/KeyError → `"vision: unexpected gateway response: ..."`.

## Testing gotchas (both bit/verified this session)

1. **Hyphenated-dir harness double-module trap**: loading `__init__.py` by
   file (`spec_from_file_location` + `mod.__path__ = [dir]` +
   `sys.modules["plug"] = mod`) makes `from . import core` import core.py as a
   SECOND module instance under the package name (`plug.core`) — distinct from
   the test's `import core`. `mock.patch.object(core, ...)` then silently
   patches the wrong object. Fix: pre-seed
   `sys.modules["plug.core"] = core` BEFORE `exec_module` → `mod.core is core`
   and patches land.
2. **urllib Request header capitalization**: `Request` stores headers via
   `key.capitalize()`, so `"User-Agent"` becomes `"User-agent"` internally.
   Assert with `req.get_header("User-agent")` or
   `dict(req.header_items())["User-agent"]`; timeout is
   `urlopen.call_args[1]["timeout"]`. Same for `Content-Type` → `Content-type`.
3. **MagicMock urlopen pattern**: set `uo.return_value.__enter__.return_value`
   = resp mock (or just `uo.return_value` — MagicMock's `__enter__` returns
   itself); MUST set `resp.status = 200` explicitly (auto-attributes are
   truthy MagicMocks and fail `status != 200`); `resp.headers = {}` triggers
   the charset fallback; `resp.read.return_value = bytes`.
4. **image_to_data_url**: extension whitelist `.jpg/.jpeg/.png` → mime map;
   `os.path.getsize` check against `max_bytes` param (tests pass tiny caps,
   no 4MB fixtures needed); raise ValueError with clear messages, handlers
   convert to `"describe_image: ..."` strings.
