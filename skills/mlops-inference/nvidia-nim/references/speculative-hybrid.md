# Speculative Hybrid — the bandwidth/latency bypass

Why distributed tensor-parallel inference over residential WAN is dead,
and the architecture that survives. Derived and verified 2026-08-06
(full math in the project: decentral-ai-research/notes/bandwidth_physics.md).

## The two walls (both physical, both fatal to naive distribution)

### Wall 1: bandwidth
Dense 70B tensor-parallel: activation = hidden 8192 x 2 bytes (fp16) =
16 KB/layer/token; all-reduce x2 = 32 KB; x 80 layers = **2.56 MB per
token** crossing the network. Real residential uploads (Speedtest Jun
2026): India fixed 59.4 Mbps, US fixed 58.3, India mobile 11.3.
=> 0.5-2.9 tok/s ceiling. Usable UX is 20-50 tok/s.

### Wall 2: latency (worse)
Tensor parallelism needs a full all-reduce round-trip PER LAYER per
token: **tok/s <= 1 / (L x RTT)**. Even at INFINITE bandwidth, 70B
(L=80) across peers 100 ms apart = 0.125 tok/s. Two independent walls;
no software touches either.

Primary-source confirmation: DeepSeek-V3 (arXiv 2412.19437) — 671B MoE,
1 shared + 256 routed experts, top-8, "each token sent to at most 4
nodes" (node-limited routing), decode deployment = min 40 nodes/320
GPUs with EP320 + IBGDA. They built custom all-to-all kernels for
InfiniBand/NVLink — even in a datacenter, cross-node comm is THE
bottleneck. Residential links are 10,000-40,000x weaker.

Every live project confirms it: Petals (10.5k stars) died on it (last
push 2024-09); exo (46.7k stars) only works via Thunderbolt 5 RDMA
wired clusters (30-32 tok/s on 4x M3 Ultra, $40k); Mesh-LLM (3.1k,
active) gates stage splits on "low-latency network" (LAN).

## The bypass: local draft + remote verifier

- Local llama.cpp 1-3B Q4 draft on user hardware: 60-100+ tok/s (GPU)
- Remote frontier verifier (e.g. NIM gpt-oss-120b): checks drafts
- Per round: draft proposes K=8-16 tokens locally, sends token IDs to
  verifier (~200 bytes), verifier returns accept/reject + next-token
  distribution. ~100-200 bytes/token over the wire = 99.99% less than
  2.56 MB/token. Latency: one RTT per K tokens (amortized) — 100 ms
  RTT / K=16 = ~160 tok/s effective.
- W1 SOLVED (bandwidth trivial), W2 SOLVED (amortized).

The honest trade: the verifier does the real work. Quality = verifier
quality. This inverts the "decentralized supercomputer" framing into
"community-owned frontier weights + smart local clients" — local
devices contribute drafts/storage/routing/credits, not tensor math.
Papers: GoodSpeed (arXiv 2512.09963), ConfigSpec (arXiv 2604.09722),
SLED (arXiv 2506.09397).

## Client pattern (project mvp/speculative_hybrid.py)

- llama-server on :8080 with draft GGUF, --n-gpu-layers 99
- chat_draft() to localhost /v1/chat/completions — model field MUST
  be the real GGUF filename, and the base_url must not double /v1
- chat_nim() to integrate.api.nvidia.com/v1 with nvapi key from .env
- 3 phases: draft baseline, verifier baseline, hybrid loop measuring
  words/s, wire bytes/word, acceptance rate
- Compare: spec-hybrid ~200 B/word vs TP ~640 KB/word (70B 4-way)

## Hardware note

A 1.5B Q4 draft on RTX 3050 4GB: 4-14 tok/s on CPU (fallback) vs
60-100+ tok/s on GPU. GPU engagement is NOT automatic — see
references/windows-cuda-setup.md. Verify with nvidia-smi memory.used
before trusting speed numbers.
