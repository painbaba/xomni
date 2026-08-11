# Lab-Agent Swarm — tool-using agents doing hands-on experiments

Third swarm mode (after fast-knowledge and deep-browsing). Agents get a REAL
experiment surface: a localhost simulator (the "lab") that behaves like a target
parser/WAF, and the agent iterates: hypothesize → run python against the lab →
read verdicts → refine → emit a discovery report. Built and verified 2026-08-08
on this host, 3 campaigns run (WAF bypass 10 agents, zero-touch 50 agents,
Android zero-click 50 agents).

## Location
All under `C:\Users\HP\ai-workforce\swarm\`:
- `lab\lab.py` — WAF-sim + origin-sim + rate-limiter (port 8899). /probe
  (WAF decode-count norm=0/1/2 vs origin always-double-decode + HPP first-vs-last),
  /probe-json, /probe-multipart, /rate (XFF-trust misconfig), /path-check,
  /te (CL/TE), /echo.
- `lab\lab3.py` — zero-touch parser sims (port 8898): /img /font /doc /xml-auto
  /archive /email /deeplink /media /vcard /qr. Each = filter sim + execution sim;
  `filter=PASSED + executed=true` = confirmed finding.
- `lab\lab4.py` — Android zero-click parser sims (port 8897): /parcel (Binder
  length-prefix), /ims (SIP), /nfc (NDEF), /bt (L2CAP), /sms (PDU UDH), /media
  (MP4/FLAC boxes), /quic (H3 varints), /bundle, /audio (ADTS/FLAC), /rcs.
- `lab_agent.py` / `lab_agent_zt.py` / `lab_agent_android.py` — the runner
  (channels, socket guard, mission dict, agent loop).
- `rerun_agents.py` — re-run selected agent ids with hardened missions.
- `synth_lab.py` / `synth_zt.py` / `synth_android.py` — report synthesis.

## How the agent loop works
- Model: OpenCode Go deepseek-v4-flash, `reasoning_effort: "high"`,
  `max_tokens: 3000-3500` (small budgets get eaten by reasoning → empty content),
  temperature 0.5, 300s timeout, browser UA mandatory.
- Protocol: agent responds ONLY with JSON actions:
  `{"tool":"python","code":"..."}` (executed in a subprocess) or
  `{"tool":"final","report":"markdown"}`. Loop up to 16-20 steps.
- Every step's reasoning + action + lab output appended to a transcript; final
  report + transcript written to `results_*/agent_XX_<title>.md`.
- SOCKET GUARD: run_python monkeypatches `socket.getaddrinfo` and
  `socket.socket.connect` to raise for any host other than 127.0.0.1/localhost/::1.
  Agents CANNOT touch anything external — mandatory for exploit-development work.
- run_python MUST `textwrap.dedent` the agent code before wrapping in `try:` —
  otherwise IndentationError burns 3+ turns (hit repeatedly in the first run).

## Mission design (the key lever)
10 vulnerability classes × 5 specializations = 50 agents. Classes = one per
parser surface. Specializations (SPECS dict):
- A baseline-zoo: map filter surface, 30+ payloads, build the zoo table
- B length-bypass / filter-bypass: defeat validation (overflow, truncation,
  inconsistent sizes, huge counts, negative arithmetic)
- C polyglot: input valid for TWO parsers at once (cross-surface confusion)
- D escalation: chain parser primitive → RCE/SSRF/file-read class sink
- E novel-hunt: INVENT payload families beyond documented CVEs; classify
  KNOWN (name the CVE/technique) vs NOVEL (your discovery)
Missions embed: class description, lab endpoint, response format, protocol
(≥10-12 payloads, zoo table, classifications), zero-click/zero-touch severity
framing. Never theorize without testing is in the system prompt.

## Verified campaign numbers (2026-08-08)
- WAF-bypass lab: 10 agents on 2 OpenCode keys, ~12.8 min, ~113 confirmed
  findings. Best: encoding-depth rule (payload encoded norm+2 times, every byte
  percent-encoded incl. dashes → WAF single-decode still sees encoded text,
  origin double-decode recovers attack; over-encoding fails), HPP clean-first/
  evil-last, JSON-body confusion, XFF-rotation rate-limit bypass (20-request proof).
- Zero-touch: 50 agents, 12.8 min, ~243 NOVEL mentions, 34/50 full reports.
  Best: namespace-less SVG bypass, entity-encoded schemes (&#104;ttp://),
  zero-length/impossible-geometry font table records dispatched, PDF magic at
  arbitrary offset, data:// vs data: scheme split, UTF-16 DOCTYPE.
- Android zero-click: 50 agents, 12.7 min, ~119 distinct NOVEL-with-evidence
  lines. Best: LF-only SIP line-ending bypass, MP4 size=0/largesize=0 box family
  + cross-surface type confusion (t=mp3 routes to MP4 parser), SMS UDL=0 overflow
  + SMS-NDEF polyglot, RCS file: URI canonicalization + schema-confusion
  (file.url bypass), ADTS sample-rate-index 15 bypass.

## Extraction gotcha
Agents print verdicts in THEIR format (`finding: True`, `PASSED SQLI finding=True`)
not raw JSON — grep regex must be `finding.?[=:] ?True|PASSED \w+ True` etc.
The raw lab JSON `"finding": true` returns 0 hits in transcripts and makes a
successful campaign look empty.

## Reuse recipe for a new surface
1. Write a new lab module (copy lab4.py shape): endpoint per parser, filter sim
   (hardened validation) + execution sim (vulnerable parser trusts fields),
   return `{filter, rule, executed, result}`. Start on a NEW port.
2. New runner file (copy lab_agent_android.py): CLASSES dict (surface name →
   desc + endpoint), SPECS dict, LAB url, OUT dir, guarded __main__ block.
3. `python lab_agent_new.py` in background with notify_on_complete; ~13 min/50.
4. synth script → report_*.md. Always end with honest caveats: lab sims model
   validation-gap MECHANISMS, not real target code — leads to validate per-target.
