# context-loader

Aider-style context injection: pulls web pages and local images into the
conversation as clean, readable context. Pure stdlib, no Hermes imports.

## What it does

- `fetch_page(url)` — fetch any http/https page as clean text: title, `h1`-`h3`
  headings, and `[text](href)` links kept; script/style stripped; 512 KB cap;
  20 s timeout; browser User-Agent.
- `describe_image(path)` — send a local jpg/jpeg/png (≤ 4 MB) to the opencode
  Zen vision gateway (model `minimax-m3`) and return the model's description.
- `image_to_data_url(path)` / `html_to_text(html)` / `load_key()` — building
  blocks (base64 data URL, HTML→text converter, `.env` key reader).

## Tools / commands

- Model tools: `fetch_page(url)` (toolset `web`), `describe_image(path)`
  (toolset `file`).
- Slash commands: `/fetch <url>`, `/describe <image path>`.

## Speed posture

Zero hooks registered. Vision calls hit the gateway only when a
tool/command is explicitly invoked — never on agent startup or mid-turn.

## Test

```bash
cd plugins/context-loader && python -m unittest tests.test_core -v
```

## Config

- `OPENCODE_GO_API_KEY` in `~/AppData/Local/hermes/.env` — required for
  `describe_image` (the gateway answers 403/1010 without it). The key is
  never logged or printed.
- Module constants: `DEFAULT_TIMEOUT = 20`, `MAX_PAGE_BYTES = 512 KB`,
  `DEFAULT_MAX_IMAGE_BYTES = 4 MB`, `VISION_MODEL = minimax-m3`.
