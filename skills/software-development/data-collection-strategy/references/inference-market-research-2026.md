# LLM inference market research — worked example (fetched 2026-08-06)

Point-in-time snapshot from a research-scout run on the industrial LLM serving stack + commercial inference landscape. Re-verify before reuse; prices change fast (DeepSeek official API moved V3→V4 models by mid-2026).

## Canonical API sources (no auth needed)
- OpenRouter models: `https://openrouter.ai/api/v1/models` (340 models) — prices in $/token (×1e6 = $/M), fields: pricing.prompt/completion, context_length, supported_parameters, benchmarks.artificial_analysis
- Per-provider prices: `https://openrouter.ai/api/v1/models/<id>/endpoints` — every upstream provider's price for one model
- GitHub stars/license: `https://api.github.com/repos/<owner>/<repo>` (60 req/hr unauthenticated)
- arXiv full text: `https://arxiv.org/html/<id>` (redirects to latest version)

## Serving engines (stars/license/latest, 2026-08-06, GitHub API)
| Engine | Stars | License | Latest release | Notes |
|---|---|---|---|---|
| vLLM | 88,339 | Apache-2.0 | v0.26.0 (2026-07-27) | PagedAttention arXiv:2309.06180; industry default |
| llama.cpp | 122,878 | MIT | — | repo moved to ggml-org; GGUF quant |
| SGLang | 31,414 | Apache-2.0 | v0.5.16 (2026-07-25) | RadixAttention arXiv:2403.03852 |
| Ray | 43,457 | Apache-2.0 | — | Ray Serve = orchestration, not a kernel engine |
| TensorRT-LLM | 14,316 | NOASSERTION (NVIDIA) | — | powers NVIDIA NIM |
| TGI | 10,888 | Apache-2.0 | — | HF Inference Endpoints |
| Mosec | 903 | Apache-2.0 | — | niche dynamic batching |

## Price anchors (OpenRouter endpoints, USD/1M tokens in/out)
- Llama-3.3-70B-Instruct: DeepInfra $0.10/$0.32 · Nebius $0.13/$0.40 · AkashML (decentralized) $0.13/$0.40 · Novita $0.135/$0.40 · Cloudflare $0.293/$2.25 · SambaNova $0.45/$0.90 · Groq $0.59/$0.79 · CoreWeave $0.71/$0.71 · Together $1.04/$1.04
- Qwen-2.5-72B: DeepInfra $0.36/$0.40 · Novita $0.38/$0.40
- DeepSeek-R1: Novita $0.70/$2.50 · Azure $1.49/$5.94
- DeepSeek-V3.2 (Dec-2025): Baidu $0.207/$0.31 · SiliconFlow $0.259/$0.42 · DeepInfra $0.26/$0.38 · DigitalOcean $0.25/$0.80 · Phala (decentralized/TEE) $1.00/$1.00 · SambaNova $3.00/$4.50

## GPU $/hr (Modal per-second ×3600; Fireworks on-demand)
- Modal: H100 $3.95 · H200 $4.54 · B200 $6.25 · B300 $7.10 · RTX PRO 6000 $3.03 · A100-80G $2.50 · A100-40G $2.10 · L40S $1.95 · L4 $0.80 · T4 $0.59
- Fireworks: H100/H200 $7.00 · B200 $10.00 · B300 $12.00

## DeepInfra page (server-rendered, text-extracts cleanly)
- DeepSeek-V4-Pro 1024k $1.30 / $0.10 cached / $2.60 · V4-Flash $0.09 / $0.018 / $0.18 · V3.2 $0.26/$0.13/$0.38 · V3.1-Terminus $0.27/$0.13/$0.95 · V3-0324 $0.24/$0.135/$0.90 · R1-0528 $0.50/$0.35/$2.15 · Llama-3.3-70B-Turbo $0.10/$0.32 · Llama-4-Maverick $0.20/$0.80 · Qwen2.5-72B $0.36/$0.40 · Nemotron-3-Super-120B-A12B $0.085/$0.40
- DeepSeek official (api-docs.deepseek.com): v4-flash $0.14 (cache miss) / $0.028 hit / $0.28 out; v4-pro $0.435/$0.87; concurrency 2500/500; OpenAI-format base_url https://api.deepseek.com

## DeepSeek-V3 MoE deployment facts (arXiv:2412.19437 §3.4, full HTML)
- 671B total / 37B active; 1 shared + 256 routed experts (hidden dim 2048); top-8 routed; token routed to ≤4 nodes
- Prefill deployment: min 4 nodes / 32 GPUs; TP4+SP+DP8; MoE EP32; 32 redundant experts; dual micro-batch overlap
- Decode deployment: min 40 nodes / 320 GPUs; TP4+SP+DP80; MoE EP320 = 1 expert/GPU (64 GPUs for redundant+shared); IBGDA P2P all-to-all; per-expert batch ≤256 tokens → memory-bound
- Bandwidth: NVLink 160 GB/s vs InfiniBand 50 GB/s (3.2×); 20 of 132 SMs dedicated to all-to-all comms
- Key implication: distributed 671B-MoE inference across consumer nodes is bandwidth-bound, not compute-bound (consumer NIC ~1–10 Gbit/s vs datacenter 400G IB)

## OpenAI-compat surface (proxy must implement)
/v1/models · /v1/chat/completions (+ SSE streaming, stream_options.include_usage) · /v1/completions · /v1/embeddings · tools + tool_choice · response_format (json_object / json_schema = structured outputs) · logprobs/top_logprobs · seed · stop · temperature/top_p/top_k/min_p · frequency/presence/repetition penalties · logit_bias · prefix-cache accounting (cache-hit vs cache-miss billing)

## Vendor page extraction quirks (tested 2026-08-06)
- deepinfra.com/pricing — SSR, clean text extraction
- together.ai/pricing — partial SSR (minimum-charge numbers visible; per-token table JS-rendered)
- cerebras.ai/pricing — Sanity CMS escaped JSON: `raw.replace('\\"','"')` then regex `"cells":\[(.*?)\]\}` (rows: model | ~N tokens/s | $in/M | $out/M)
- groq.com/pricing — marketing-only (LPU→LPX, "$650M fundraise" banner); real prices via OpenRouter endpoints
- fireworks.ai/pricing — SSR (GPU $/hr + fine-tune tiers per 1M tokens)
- modal.com/pricing — SSR per-second GPU rates
- build.nvidia.com — HTTP 202 deferred → browser only; NIM per-token prices unverified
- mlcommons.org — 403 to curl → browser only
- lmsys.org/blog — slugs embedded as `"YYYY-MM-DD-slug\"` in index HTML; URL = /blog/<slug>/; the Jan-2025 SGLang-R1 post (2025-01-23-sglang-deepseek) is 404'd with no Wayback snapshot — use newer posts (2025-09-29-deepseek-V32, 2026-04-25-deepseek-v4)
