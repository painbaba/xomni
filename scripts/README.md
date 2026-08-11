# scripts/check_models.py — gateway health check

Standalone health check for the **opencode Zen gateway** (`https://opencode.ai/zen/go/v1`),
the free-model channel wired in `plugins/provider-pool/core.py` (25 verified models).

## What it does

1. Imports `GATEWAY_MODELS` from `plugins/provider-pool/core.py`.
2. For each model, makes one minimal `POST /chat/completions` call
   (`max_tokens=1`, prompt `"ping"`) with a 30s per-model timeout
   (override with `--timeout N`).
3. Prints a table: `model | status | latency ms`.
4. Exits `0` if every checked model answered HTTP 2xx, `1` if any are down.

The API key (`OPENCODE_GO_API_KEY`) is read from
`~/AppData/Local/hermes/.env` via `core.load_key()` and is **never printed**.

## Requirements

- Python 3.9+ (pure stdlib — no pip installs).
- `OPENCODE_GO_API_KEY` present in `~/AppData/Local/hermes/.env`.
- A browser-style `User-Agent` header is sent automatically (the gateway
  blocks plain `urllib` UAs via Cloudflare 1010).

## Usage

```bash
# from the repo root:
python scripts/check_models.py            # all 25 models (takes a while)
python scripts/check_models.py --limit 3  # first 3 only (quick smoke test)
python scripts/check_models.py --json     # machine-readable JSON
python scripts/check_models.py --limit 5 --json --timeout 60
```

## Exit codes

| Code | Meaning                                          |
|------|--------------------------------------------------|
| 0    | all checked models OK (HTTP 2xx)                 |
| 1    | ≥1 model down / errored                          |
| 2    | usage error or provider-pool core not found      |

## Output

```
gateway: https://opencode.ai/zen/go/v1  |  checked: 3  |  OK: 3  |  DOWN: 0
model                    status   latency ms
--------------------------------------------
deepseek-v4-flash        OK             812
deepseek-v4-pro          OK            1043
kimi-k3                  OK             977
```

With `--json`, the same data is emitted as a single JSON object
(`{gateway, checked, ok, all_ok, results: [...]}`) — useful for cron/CI.
