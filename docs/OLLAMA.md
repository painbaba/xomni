# OLLAMA — Zero-Install Local Models

XOMNI bundles a portable Ollama runtime so LOCAL models work with **zero extra
installs** — no Ollama installer, no Docker. Just run `run.cmd` (or `run.sh`).

## How the zero-install flow works

`ollama/start-ollama.ps1` is invoked automatically by `run.cmd` (best-effort,
non-blocking). It is idempotent — safe to run any time:

1. **Already serving?** If `http://127.0.0.1:11434/v1/models` answers HTTP 200,
   exit immediately.
2. **Download once** — if `ollama/runtime/ollama.exe` is missing, download the
   official portable build (`ollama-windows-amd64.zip`, ~130 MB) and expand it
   into `ollama/runtime/`. The zip is deleted afterwards; a failed download
   leaves no partial file, so the next run retries cleanly.
3. **Serve** — launch `ollama serve` detached (hidden window) bound to
   `127.0.0.1:11434`.
4. **Wait for ready** — poll the OpenAI-compatible `/v1/models` endpoint for up
   to 90 s; warn and continue if it never answers.
5. **Pull once** — if `ollama list` has no `qwen2.5:3b`, pull it (~1.9 GB) so
   local inference works offline afterwards.

**Runtime dir:** `ollama/runtime/` next to the script. The Python runtime
manager (`plugins/local-models/runtime.py`) resolves the same location as
`$XOMNI_HOME/ollama/runtime` (fallback `~/.xomni/ollama/runtime`); `run.cmd`
sets `XOMNI_HOME` to the repo root, so both agree.

## Using local models with XOMNI (`/localmodels`)

The `local-models` plugin probes local OpenAI-compatible servers (no API key
needed) and wires them into Hermes/opencode:

| Command | What it does |
|---|---|
| `/localmodels status` | List configured servers (Ollama :11434/v1, LM Studio :1234/v1, plus extras) |
| `/localmodels scan` | Live-probe every server and list the models it reports |
| `/localmodels config [server]` | Print wiring snippets (Hermes `config.yaml` + `opencode.json`); default: `ollama` |
| `/localmodels add <base_url> [id]` | Remember an extra server, e.g. `/localmodels add http://127.0.0.1:8000/v1 vllm` (saved to `plugins/local-models/servers.json`) |
| `/localmodels remove <id>` | Forget an extra server |

Related runtime commands: `/ollama status | start | install | pull [model]`.
After a pull, `/localmodels scan` shows the model live. Generated configs use a
placeholder `key_env: local` — local endpoints need no real key.

## Troubleshooting

- **Port 11434 in use** — another Ollama answers → script exits 0 (already
  serving). A *non-Ollama* app holding the port blocks bind: check
  `netstat -ano | findstr 11434`, free the port, or set `OLLAMA_HOST`
  (note: the plugin probes `127.0.0.1:11434/v1` by default).
- **Firewall** — first `serve` may trigger a Windows Firewall prompt; allow it
  (localhost traffic is usually exempt).
- **Slow pull** — `qwen2.5:3b` is ~1.9 GB; registry throttling can slow it.
  Re-run `/ollama pull qwen2.5:3b` to resume. Pulls happen only on first run.
- **"did not answer in 90 s" warning** — serve may still come up late; check
  with `/ollama status`.
- **Editing start-ollama.ps1** — keep the UTF-8 BOM: Windows PowerShell 5.1
  reads BOM-less files as ANSI, which mangles non-ASCII chars and breaks
  parsing (fixed in the shipped script).
- **Download fails** — partial zip is discarded automatically; just re-run
  `run.cmd`.

## GPU notes

- **Works on any machine** — no GPU → CPU fallback; `qwen2.5:3b` is small
  enough to run comfortably either way.
- **~4 GB VRAM is enough** for GPU-accelerated `qwen2.5:3b`; Ollama
  auto-detects NVIDIA/AMD (and Apple Metal) with no setup.
- A GPU makes generation several times faster than CPU-only, but is not
  required.

## Config options

| Option | Default | Notes |
|---|---|---|
| `XOMNI_HOME` | repo root (set by `run.cmd`) | Bundled runtime lives at `<XOMNI_HOME>/ollama/runtime` |
| `OLLAMA_HOST` | `127.0.0.1:11434` | Serve bind address/port |
| `OLLAMA_MODELS` | `~/.ollama/models` | Where pulled models are stored |
| Default model | `qwen2.5:3b` | Change in `start-ollama.ps1`/`runtime.py`, or `/ollama pull <model>` |
