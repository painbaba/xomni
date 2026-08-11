# local-models

Detect and manage LOCAL OpenAI-compatible model servers — free local
inference with zero API keys. Pure stdlib, no Hermes imports.

## What it does

- Probes Ollama (`http://127.0.0.1:11434/v1`) and LM Studio
  (`http://127.0.0.1:1234/v1`) via `GET {base}/models`, plus any extras in
  the plugin-local `servers.json`.
- Generates per-agent wiring snippets (Hermes `config.yaml` provider block,
  opencode.json `@ai-sdk/openai-compatible` block) so XOMNI can route to
  local models.
- Bundled Ollama runtime manager (`runtime.py`): first-run installer
  downloads the official portable build into `$XOMNI_HOME/ollama/runtime`,
  starts `ollama serve` detached, and pulls the default model
  (`qwen2.5:3b`, ~1.9 GB) so local inference works offline.

## Tools / commands

- Commands: `/localmodels status|scan|config [server]|add <base_url> [id]|remove <id>`
  and `/ollama status|start|install|pull`.
- Model tool: `local_models(action=status|scan|config[, server])` — the agent
  can query local models mid-task.

## Speed posture

Zero hooks — all hooks return `None`; this module never alters agent
behavior. Network probes (3 s timeout) happen only on explicit commands.

## Test

```bash
cd plugins/local-models && python -m unittest tests.test_core -v
cd plugins/local-models && python -m unittest tests.test_runtime -v
```

## Config

- `servers.json` (plugin-local) — extra servers `[{id, name, base_url}]`,
  created by `/localmodels add`, hand-editable.
- `XOMNI_HOME` env var — runtime dir (default `~/.xomni/ollama/runtime`).
- Ports: Ollama 11434, LM Studio 1234 (module constants).
