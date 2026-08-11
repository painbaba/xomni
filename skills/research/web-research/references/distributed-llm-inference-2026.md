# Distributed / P2P LLM Inference — Verified State of the Art (Aug 2026)

Condensed knowledge bank from the Track-1 research scout. Full dossier with all sources:
`C:\Users\HP\decentral-ai-research\sources\track1_distributed_inference.md`.
All star counts verified via GitHub API/HTML on 2026-08-06; all arXiv IDs verified via `id_list=`.

## Verified repo stats (stars / license / last push)
| Project | Stars | License | Last push | Notes |
|---|---|---|---|---|
| exo-explore/exo | 46,692 | Apache-2.0 | 2026-06 | LAN/Thunderbolt-RDMA cluster tool; $250K funding (Beacon) |
| ggml-org/llama.cpp | 122,877 | MIT | 2026-08 | baseline consumer inference |
| vllm-project/vllm | 88,339 | Apache-2.0 | 2026-08 | industry serving baseline |
| sgl-project/sglang | 31,414 | Apache-2.0 | 2026-08 | serving baseline |
| bigscience-workshop/petals | 10,481 | MIT | **2024-09** | DEAD — the canonical cautionary tale |
| deepseek-ai/DeepEP | 9,957 | MIT | 2026-08 | MoE all-to-all; NVLink/RDMA only, no WAN mode |
| llm-d/llm-d | 3,987 | Apache-2.0 | 2026-08 | CNCF sandbox (Red Hat/Google/IBM/CoreWeave/NVIDIA); k8s, not P2P |
| Mesh-LLM/mesh-llm | 3,057 | Apache-2.0 | 2026-08 | iroh-based (per HN); OpenAI-compatible API :9337; Skippy stage splits |
| learning-at-home/hivemind | 2,509 | MIT | — | P2P framework under Petals |
| hyperspaceai/agi | 2,013 | MIT | — | agent gossip, not inference serving |
| gensyn-ai/rl-swarm | 1,681 | — | — | Gensyn's open-source swarm framework |
| NousResearch/DisTrO | 1,051 | none | 2025-10 | comms -3-4 orders of magnitude; 15B model trained over internet |
| akash-network/node | 1,104 | Apache-2.0 | 2026-07 | Cosmos "Supercloud" |
| PrimeIntellect-ai/prime | 239 | MIT | 2026-08 | CLI/SDK for their GPU marketplace |
| Agent-FM/agentfm-core | 129 | Apache-2.0 | 2026-07 | Go+libp2p agent mesh; honesty-star trust |
| wavefy/decentralized-llm-inference | 46 | — | — | hobby |
| jstdv/imece | 2 | MIT | 2026-05 | **FLOP-denominated inference credits** — exact concept match, hobby scale |

## Funding (verified via press)
- Gensyn: $43M Series A, a16z crypto, Jun 2023 (decrypt.co/144068)
- Prime Intellect: $5.5M seed Apr 2024 → $15M Feb 2025 → **$130M Series A Jul 2026** (Radical Ventures; NVIDIA/Intel/Dell capital), $1B valuation (cryptobriefing.com/prime-intellect-130m-series-a-billion-valuation)
- io.net: $30M Series A Mar 2024, Hack VC, $1B valuation (depinhub.io/projects/ionet)
- Together AI: $305M Series B Feb 2025, General Catalyst+Prosperity7, $3.3B valuation, ~$1.33B total (prnewswire 302380967)
- Ritual (Infernet): $25M Polychain/Hack VC; pivoted to sovereign AI L1 (ritual.net)
- Akash: $1.8M seed 2018 (messari.io report); Mainnet 14 in 2025
- Exo Labs: $250K single round from Beacon (tracxn)
- Vast.ai / Salad: bootstrapped (unverified)

## Key papers (all arXiv-verified)
- Petals 2209.01188; Prime Intellect internet inference 2312.08361; MDI-LLM edge model-distribution 2505.18164
- DiLoCo 2311.08105; DiLoCoX 2506.21263; Streaming DiLoCo 2501.18512; Factored Gossip DiLoCo 2606.22768; MuLoCo 2505.23725; torchft (Meta, FT) github.com/meta-pytorch/torchft
- Mooncake (KV disaggregation) 2407.00079; CacheGen 2310.07240; Prompt Cache 2311.04934; PolyKV 2604.24971
- GoodSpeed (distributed-edge speculative) 2512.09963; ConfigSpec 2604.09722; SLED 2506.09397
- EdgeMoE 2308.14352; DALI (local-PC MoE) 2602.03495; ExpertFlow 2410.17954; PowerInfer 2312.12456 / PowerInfer-2 2406.06282
- Training Transformers Together 2207.03481 (Petals lineage — NOT the Together AI company); BitTensor whitepaper 2003.03917

## The 10 claims a feasibility analysis must know
1. Bandwidth (not compute) is the fundamental blocker for WAN P2P inference — Petals died on it; 2026 retrospective agrees (explainx.ai/blog/petals-distributed-llm-inference-revisited-july-2026).
2. Every successful consumer cluster tool (Exo, Mesh-LLM) is LAN/trust-cluster; nobody has productized open-internet P2P serving.
3. MoE expert routing is the most WAN-friendly parallelism, but DeepEP assumes NVLink/RDMA — no WAN all-to-all exists.
4. KV-cache transfer works only inside datacenters (Mooncake, llm-d); WAN cache shipping is cost/latency-prohibitive; compression/sharing still research.
5. Speculative decoding (draft-on-edge, verify-on-cloud) is the emerging natural P2P division of labor (GoodSpeed, ConfigSpec).
6. DiLoCo family proves WAN *training* viable (~500x less comms); per-token inference latency remains unsolved.
7. Market validated GPU aggregation + OpenAI-compatible APIs but with datacenter GPUs (Prime Intellect $130M, io.net $30M, Together $305M, Gensyn $43M, Ritual $25M); consumer-idle plays (Salad, Vast) serve batch/slack workloads.
8. The inference-credit economy concept is being tried at hobby scale (imece, 2 stars) — concept valid, execution/governance is the hard part.
9. Token-incentivized inference (Bittensor/Targon SN4) works as a marketplace but has a verification/quality crisis; source-trust is the hard oracle problem (ainvest.com Jun 2026).
10. Single consumer devices are surprisingly capable alone (PowerInfer-2 smartphone, llama.cpp) — a 1M-device network's pitch must be "models too big for one device + community ownership," not raw capability.
