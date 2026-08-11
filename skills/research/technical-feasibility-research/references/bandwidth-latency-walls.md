# The Two Walls — bandwidth and latency math for distributed inference

The reusable templates behind the decentralized-inference verdict
(2026-08-06 session). Apply to ANY distributed-compute feasibility
question: substitute the model's numbers, keep the formulas.

## Wall 1 — Bandwidth (bytes/token × tok/s vs upload)

Dense tensor-parallel transformer, per generated token:

    bytes/token = hidden_size × bytes_per_value × 2 (all-reduce) × L (layers)

Example, 70B dense (Llama-3-70B class): hidden 8192, fp16 (2 bytes), L=80
    8192 × 2 × 2 × 80 = 2.56 MB per token

    tokens/sec ≤ upload_bps ÷ bytes/token

Real residential uploads (Speedtest Global Index, June 2026):
- India fixed 59.44 Mbps → 2.9 tok/s
- India mobile 11.34 Mbps → 0.55 tok/s
- US mobile 10.35 Mbps → 0.51 tok/s
- Usable chat UX = 20-50 tok/s → 10-50x gap. Dead on arrival.

## Wall 2 — Latency (worse: independent of bandwidth)

Tensor parallelism is RTT-bound: each of L layers needs a full all-reduce
round-trip per token, tokens serialized per layer:

    tokens/sec ≤ 1 / (L × RTT)

70B (L=80): 1ms→12.5, 10ms→1.25, 20ms→0.6, 100ms→0.125 tok/s.
Even at INFINITE bandwidth, cross-country peers (20-100ms) cap at
0.1-0.6 tok/s. The latency wall is usually LOWER than the bandwidth wall.

Ceiling = min(bandwidth wall, latency wall).

## MoE variant (expert parallelism)

DeepSeek-V3 primary-source numbers (arXiv 2412.19437):
- 671B total / 37B active, 61 layers, hidden 7168, 1 shared + 256 routed
  experts, top-8 routed per token
- Node-limited routing: "each token will be ensured to be sent to at most
  4 nodes" — designed to CAP cross-node traffic
- Decode deployment: min 40 nodes/320 GPUs, EP320 (one expert per GPU),
  IBGDA point-to-point all-to-all
- Their own comm section: custom kernels for IB/NVLink, 20/132 SMs for
  comms, FP8 low-precision communication
- Lesson: even with datacenter InfiniBand (400 Gbps), cross-node all-to-all
  is THE bottleneck they engineered around. Residential upload is
  10,000-40,000x weaker. No software fixes that.

## Escape hatches that do NOT work
- Speculative decoding: reduces forwards, not all-reduce bytes
- INT4 quantization: halves bytes (1.28 MB/token → ~2 tok/s on 20 Mbps)
- Latency hiding/pipelining: reduces stall, not total bytes
- More devices: "more devices = faster" is false at network layer —
  per-request throughput bounded by slowest link in the pipeline path

## Empirical confirmation (real projects, 2026)
- Petals: BLOOM-176B ~1 step/s over residential internet; per-token
  all-reduce 2.62-5.2 MB → needs 21-42 Mbps for 1 tok/s. Matches formula.
  De facto abandoned (last push 2024-09); 2026 retrospective: bandwidth
  still unsolved.
- Distributed Llama (b4rtaz): LAN-only, "high-speed synchronization over
  Ethernet"; 70B Q40 on 4× Mac Mini M4 Pro 24GB.
- exo (46.7k stars): TP speedups 1.8×/3.2× on 2/4 devices via
  RDMA-over-Thunderbolt 5 ("99% latency reduction") — wired cluster tool,
  NOT internet P2P. 30-32 tok/s on 4× M3 Ultra ($40k, same room).
- Mesh-LLM (3k stars): pipeline stage splits gated on "low-latency
  network" (LAN); llama.cpp RPC layer-spread "performance DECREASES as
  you add more nodes" (Geerling benchmark).
- Sanity: 20 Mbps × 1s = 2.5 MB cannot move 2.62 MB/token faster than
  ~0.95 tok/s. Number conservation — no system beats the byte count.

## What survives (the mutations)
1. Local-first mesh: each node serves models that FIT its hardware
   (7-34B quantized); mesh is router/reputation/credits, not tensor math
2. Speculative hybrid: local draft + remote verify (~50-200 bytes/token)
3. Memory-pooling for big models: LAN only, honest low tok/s
4. Embeddings/rerank: tiny bytes/token, the only volunteer-positive
   economics — but not "frontier LLM serving"

## Data sources that verified these numbers
- DeepSeek-V3 Technical Report — arxiv.org/abs/2412.19437 (full text)
- Steam Hardware Survey July 2026 (VRAM distribution: 8GB=25.3% largest
  tier; only ~7% at 24GB+; ~40% at ≤6GB = can't participate)
- Speedtest Global Index June 2026 (country medians, live browser)
- OpenRouter /api/v1/models + /endpoints (real per-1M-token prices)
- Jeff Geerling Mac Studio cluster benchmark blog (2025)
- exo README (46.7k stars, RDMA-over-Thunderbolt), Mesh-LLM docs
  (meshllm.cloud/docs/pages/architecture/), GitHub API metadata
