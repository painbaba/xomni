# Scout extraction recipes (verified 2026-08)

Site-specific extraction patterns proven in a research-scout session (hardware/network/volunteer-compute for decentralized LLM inference). Full compiled deliverable of that session: `C:\Users\HP\decentral-ai-research\sources\track3_hardware_network.md`.

## Steam Hardware & Software Survey (store.steampowered.com/hwsurvey/)
- **Fully server-rendered.** Plain curl works; no JSON endpoint exists (`?json=1` / `?format=json` return the same HTML). Guessed subpaths (`/hwsurvey/videocardmemory/`, `/vram/`, `/ram/`) all silently redirect to the main page — only `/videocard/`, `/cpus/`, `/directx/`, `/processormfg/` exist.
- Summary row gives only the most-popular value; **full category distributions are in hidden `<div id="cat<N>_details">` blocks** (toggleRow JS shows them client-side). Extract with:
  ```python
  m = re.search(r'id="cat4_details">(.*?)(<div class="stats_hr_clear|<div class="stats_row row_)', html, re.S)
  rows = re.findall(r'stats_col_mid data_row">(.*?)</div>.*?stats_col_right[^>]*>(.*?)</div>', seg, re.S)
  # label = strip tags of group(1); value = strip tags of group(2)
  ```
  cat indices (July 2026 page): cat0=System RAM, cat1=CPU speeds, cat2=Physical CPUs, cat3=Video Card Description, cat4=VRAM, cat5=Display Resolution, cat6=Free HDD space, cat7=Total HDD space, cat8=Windows version, cat9=Language.
- Snapshot numbers (July 2026): RAM 16GB 40.97% / 32GB 36.93% / 8GB 7.98% → ≥16GB ≈ 88%, ≥32GB ≈ 44%. VRAM 16GB 25.90% / 8GB 25.32% / 12GB 12.88% / 24GB 5.43% / 32GB 1.27% / 64GB 0.50% → ≥8GB ≈ 74%, ≥16GB ≈ 36%. Top card RTX 3060 3.71%; NVIDIA 72.72%. Caveat: gaming-PC-biased; no laptop/desktop split published — get that from PC-shipment analysts (Canalys/IDC; both JS-blocked to plain curl, Jina Reader may render).

## Speedtest Global Index (speedtest.net/global-index)
- Global page shows only top-25 per tab; **country pages are server-rendered**: `https://www.speedtest.net/global-index/<country>#fixed` → a11y snapshot contains Mobile + Fixed blocks with DL / UL / latency / rank ("Median Country Speeds Updated <Month Year>").
- Captured June 2026: global fixed DL 125.59 / UL 63.08; global mobile DL 112.07 / UL 14.68. US fixed 304.83/58.28 (rank 9), mobile 197.34/10.35 (rank 10). India fixed 63.25/59.44 (rank 101), mobile 129.78/11.34 (rank 37). Germany fixed 103.05/37.72 (rank 69), mobile N/A.
- Caveat: medians are self-selected fast tests; real always-on numbers lower.

## Wikipedia extraction
- Isolate the article body FIRST: `re.search(r'mw-parser-output(.*?)<div id="catlinks"', raw, re.S)` — naive full-page tag-strip returns CSS/JS head blobs.
- Non-obvious article titles (all hit this session):
  - Intel TDX → article is **"Trust Domain Extensions"**
  - Golem → **no English Wikipedia article** ("Golem Network", "Golem (software)" both 404); use golem.network + stats.golem.network (both JS-heavy → Jina)
  - AMD SEV / "Secure Encrypted Virtualization" → redirects to "Zen (first generation)"; use https://www.amd.com/en/developer/sev.html (server-rendered, greppable)
  - "SETI@home", "Folding@home", "BOINC", "Data cap", "Software Guard Extensions" → exist under those exact names.
- F@h/SETI numbers captured: F@h peak 2.43 exaFLOPS (2020-04-12) → 12.9 petaFLOPS (2025-10-31); users 30k by Jan 2020. SETI: 5.2M lifetime participants, 91,454 active at Mar-2020 shutdown (~1.8%). BOINC (Nov 2021): 34,236 participants / 136,341 hosts / 20.164 PFLOPS.

## arXiv
- API: `curl "http://export.arxiv.org/api/query?search_query=ti:%22Phrase%22&max_results=5" -o tmp.xml` then parse — **do NOT pipe into a python heredoc** (`curl | python - <<EOF` silently loses the pipe because the heredoc replaces stdin).
- Abstract extraction from `/abs/<id>`: `re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', raw, re.S)`.
- arxiv.org/search UI: returns 50 date-desc hits; ID extraction works but title regex differs — prefer the API for title-author queries.
- Wrong-ID hazard: guessing IDs from memory fails (2407.11018 is NOT Distributed Llama). Verify via title search or GitHub repo README citation first.
- PoL paper IDs (verified): Proof-of-Learning 2103.05633; "Adversarial Examples for Proof-of-Learning" 2108.09454; "Proof-of-Learning with Incentive Security" 2404.09005; watermark 2301.10226; Petals 2209.01188.

## Search fallback (when DDG/Bing direct curl returns nothing)
- `curl -sL "https://r.jina.ai/https://html.duckduckgo.com/html/?q=<query>"` → rendered markdown results with `uddg=` redirect links (URL-decode with `urllib.parse.unquote`). Verified working; Jina needs no key for reader mode (rate-limited, ~20 req/min unauthenticated — batch queries into few calls).
- Jina Reader also renders JS-heavy pages (Canalys newsroom, golem.network) that plain curl gets as marketing-only or 404 HTML.

## Domain notes: decentralized LLM inference feasibility (from track3 session)
- **TP bandwidth math**: all-reduce bytes/token = 2 bytes (fp16) × 2 × hidden × L. 70B (h=8192, L=80): **2.62 MB/token** (5.24 MB with 2 all-reduces/layer). 20 Mbps uplink → 0.95 tok/s; US fixed median 58 Mbps → ~2.8 tok/s.
- **Latency floor (worse)**: tok/s ≤ 1/(L × RTT). 80 layers × 100 ms = 8 s/token (0.125 tok/s); even 20 ms caps at 0.6 tok/s. WAN TP is RTT-bound → only LAN clusters do TP (distributed-llama, exo-with-RDMA).
- **Cross-checks**: Petals BLOOM-176B ≈ 1 step/s on consumer GPUs ≈ formula; exo TP speedups 1.8×/2 devices, 3.2×/4 devices.
- **TEE availability on consumer hardware (as of 2026)**: TDX = Xeon 4th/5th-gen+ server-only; SEV-SNP = EPYC 3rd-gen+ server-only; SGX deprecated from 11th/12th-gen consumer Core (2021). → No consumer-grade TEE for volunteer nodes; verification must be probabilistic (challenge-response + staking), not attestation-based. PoL forgeable (2108.09454).
- **Quantized model sizes** (Distributed Llama repo): 8B Q4 ≈ 6.3-6.7 GB; 14B Q4 ≈ 10.9 GB; 70B Q4 ≈ 40 GB.
