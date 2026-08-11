# Local Lab Experiments — discovering bypass classes hands-on (Aug 2026)

When the user wants agents to "invent/discover new techniques by doing practicals," don't rely on literature review alone — build a local lab and let agents run real experiments. This is the pattern that produced ~113 confirmed findings including one genuinely novel mechanism.

## Architecture (all in C:\Users\HP\ai-workforce\swarm\lab\)
- `lab.py` — ThreadingHTTPServer on 127.0.0.1:8899 simulating WAF-vs-origin parser mismatch:
  - `/probe?p=<payload>&norm=0|1|2&hpp=last` — WAF sim (regex managed rules, decodes `norm` times) vs origin sim (ALWAYS double-decodes, takes LAST `p=` value). Response: `{"waf": BLOCKED|PASSED, "waf_rule", "origin": SAFE|SQLI|XSS, "finding": bool, "hpp_split": {waf_saw, origin_saw}}`. finding=true = WAF missed it, origin executes = discovery.
  - `/probe-json` (JSON body), `/probe-multipart` (field p), `/echo` (header mirror), `/rate` (rate limiter trusting X-Forwarded-For — classic misconfig), `/path-check?u=` (path normalization resolver), `/te` (CL/TE parser sim)
- `lab_agent.py` — N-agent experiment harness: each agent = deepseek-v4-flash with `reasoning_effort: "high"`, loop of {LLM emits JSON action → run_python executes with socket guard → result fed back → up to 20 steps → final report}. Missions dict defines one experiment brief per agent.

## Key harness details
- **Socket guard**: monkeypatch `socket.getaddrinfo` + `socket.socket.connect` to raise for any host except 127.0.0.1/localhost/::1 — agents physically cannot touch external hosts. Wrap in every run_python.
- **textwrap.dedent(code)** before indenting into the `try:` wrapper — without it, agent-generated indented code throws IndentationError and burns steps.
- Guard worker launch with `if __name__ == "__main__":` — module-level code runs on import (test imports started the whole 10-agent swarm once).
- `run_agent(agent_id, key, text)` skips existing result files → resumable reruns of weak agents.
- Grep for findings in transcripts must match BOTH JSON (`"finding": true`) and agent-formatted prose (`finding: True`, `PASSED XSS True`) — the two formats differ.

## Discovered mechanisms (lab-verified, reproducible)
1. **Encoding-depth rule (NOVEL — the flagship find)**: encoding depth must exceed the WAF's decode count by exactly 2. Full-character uppercase-hex encoding (EVERY byte %XX, including letters and dashes — partial encoding fails because keywords like OR/UNION/script stay visible after WAF decode) at depth 2-3 beats single-decode WAFs while origin double-decode recovers the raw attack. Depth 4 over-encodes (origin can't decode → SAFE). Confirmed for `' OR 1=1--`, UNION SELECT, SLEEP, `<script>`, `<img onerror>`.
2. **HPP**: WAF inspects first `p=` occurrence, origin uses last → clean-first + evil-last combos bypass at every normalization level (46 combos).
3. **JSON body confusion**: SQLi in JSON POST bodies passes form-rule inspection entirely.
4. **Path normalization**: drive-letter paths (C:/admin), UNC authority collapse (//server/admin), substring admin matching (/admin1, /administrator, /foo/admin), Unicode slash look-alikes as suffixes. Case does NOT bypass (origin case-sensitive).
5. **Rate-limit**: XFF trust with full header-priority map (XFF wins over True-Client-IP/CF-Connecting-IP/X-Real-IP/Forwarded; empty XFF invalidates to real IP). 20-request sequence with unique XFF never blocks.
6. **TE/CL**: 8 chunked-size obfuscations (0x5, +5, 05, 5;ext, space-ext, extra CRLF) all accepted by parser; desync primed when CL+TE both present.

## Honest caveat
The lab models decoder-mismatch CLASSES real CDNs exhibit — it is not Cloudflare/Akamai/AWS itself. Findings are mechanism discoveries to validate per-target, not universal wins. Say this in the report.
