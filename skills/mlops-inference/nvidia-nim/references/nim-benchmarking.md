# NIM Benchmarking Recipe (capability mapping)

Verified 2026-08-06: 10 models x 4 tasks, 6 keys, 40/40 calls done.

## Why benchmark at all

The /v1/models catalog lists ~102 models but per-account provisioning
means many 404 on your keys. Benchmarking answers two questions per
model: (a) is it CALLABLE on my keys? (b) what is it good at?
Results go into a capability matrix that drives workforce role
assignment (synthesis lead vs drafter vs structured-data).

## Model shortlist

Pick candidates across classes, don't just take the biggest:
- Flagship reasoning: nemotron ultra 550b/253b, deepseek-v4-pro
- Workhorses: gpt-oss-120b, nemotron-3-super-120b, llama-3.3-
  nemotron-super-49b, glm-5.2, kimi-k2.6, mistral-large-2
- Small/fast: deepseek-v4-flash, llama-3.3-70b

## The 4-task battery

1. **reasoning** — hard math with exact answer (e.g. expected tosses
   for 3 consecutive heads = 14). max_tokens 1200.
2. **coding** — real algorithm with test asserts (e.g. Manacher
   longest-palindromic-substring, O(n)). max_tokens 1200.
3. **domain** — task-specific depth question (for distributed-
   inference research: quantify the bandwidth bottleneck with numbers).
   max_tokens 1500.
4. **structured** — strict JSON output, no commentary. max_tokens 800.

temperature 0.3, save EVERY raw output to disk:
`bench/<model_sanitized>/<task>.txt` with STATUS line first.

## Parallelism: thread-per-key, pin key to model

- One thread per KEY (6 keys = 6 threads). Each thread pops tasks
  from a shared queue.
- Per user directive: pin ONE key per model for reruns instead of
  round-robin. Round-robin caused 503 ResourceExhausted storms when
  6 threads hit the same model's shared workers simultaneously.
- 404 = dead model (per-account), break to next model.
- 503 = worker limit, retry with 5s*attempt backoff, up to 4 tries.
- Timeout: reasoning models (deepseek-v4) exceed 240s — that is NOT
  a failure. Use 600s+ or accept "slow" as a capability finding.

## Filter before the full run

Do a cheap probe first: one "hi" call per model per key (max_tokens 5,
25s timeout). Models that 404/timeout on the probe are dead — drop
them from the 4-task battery and save the API budget.

## Capability matrix format

| Model | Reasoning | Coding | Domain | Structured | Verdict |
|---|---|---|---|---|---|
| openai/gpt-oss-120b | OK | OK | OK | OK | WORKHORSE 4/4 |

Known results (free accounts, Aug 2026): workhorses = gpt-oss-120b,
nemotron-3-super-120b, llama-3.3-nemotron-super-49b, glm-5.2 (all 4/4).
Dead = nemotron-ultra-253b (404 all), kimi-k2.6, mistral-large-2.
550b ultra = partial (2/4, 503s retryable). deepseek-v4 = slow (timeout,
alive). See the project's bench/capability_matrix.md for full table.

## Lessons

- The benchmark doubles as an availability audit — record WHICH models
  404 per account; it changes over time and per key.
- Batch probe + benchmark scripts belong in the project's mvp/ dir
  (probe_nim.py, nim_health.py, nvidia_bench.py patterns).
