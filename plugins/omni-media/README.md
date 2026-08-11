# omni-media

OpenClaw-style media understanding: `/ocr` `/caption` `/mediascan` via the
verified vision model (`minimax-m3`) on the opencode gateway. Zero hooks.

**What it does:** `/ocr` extracts all text verbatim (line order preserved)
from a jpg/jpeg/png; `/caption` describes an image in 2-3 factual sentences;
`/mediascan` batch-processes a folder (default `ocr`, max 10 files, sorted,
≤8 MB each) — a failed file never aborts the batch, its result carries a
`media:` error string. Same base64-frame wire pattern as the context-loader
vision helper, kept independent (no cross-plugin import).

**Commands:** `/ocr <image>` · `/caption <image>` · `/mediascan <dir>
[ocr|caption]`

**Speed posture:** no hooks — zero per-turn cost; vision calls are on-demand
only, and only when the user invokes a command. No subprocess; failures
report per-file and never crash a turn.

**Config:** needs `OPENCODE_GO_API_KEY` in the hermes `.env` (read on demand,
never logged); gateway `https://opencode.ai/zen/go/v1/chat/completions`.

```bash
cd plugins/omni-media && python -m unittest tests.test_core -v
```
