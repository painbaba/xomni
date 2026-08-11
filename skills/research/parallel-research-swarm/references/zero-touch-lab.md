# Zero-Touch Lab (lab3.py) + 50-Agent Campaign Results

Lab v3 runs on 127.0.0.1:8898, socket-guarded. Each endpoint simulates a filter +
execution sink for a ZERO-TOUCH parser surface (fires with no user interaction).

## Endpoint map (lab3.py)
| Endpoint | Surface | Notable filter rules |
|---|---|---|
| GET /img?data=<hex>&type=svg\|png\|gif\|jpg | image decode/preview | img-xss-content, img-uri |
| GET /font?data=<hex> | TTF/OTF/WOFF table parse | font-cmd-string |
| GET /doc?data=<hex>&type=pdf\|docx\|rtf | doc preview | doc-xss, doc-macro, doc-uri |
| POST /xml-auto | XML ingestion | xml-doctype, xml-entity |
| POST /archive | archive auto-extract | arch-traversal, arch-sensitive |
| GET /email?html=<enc> | rich email render | email-xss, email-css-js |
| GET /deeplink?uri=<enc> | scheme/intent handling | link-js-scheme, link-traversal |
| GET /media?data=<hex>&type=mp3\|mp4 | metadata parse | (none — lenient) |
| GET /vcard?data=<enc> | vCard/iCal import | vcard-uri |
| GET /qr?data=<enc> | QR/notification content | (none) |

Response: `{filter: BLOCKED|PASSED, rule, executed: bool, result, endpoint}`.
**Finding = filter PASSED + executed true.**

## Mission structure (lab_agent_zt.py)
10 classes x 5 specializations = 50 agents, deepseek-v4-flash reasoning_effort=high:
- A baseline-zoo: map filter surface (30+ payloads)
- B filter-bypass: encoding/obfuscation vs filter
- C polyglot: valid file of declared type that ALSO parses as second format
- D escalation: chain parser primitive → file-read/SSRF/exec
- E novel-hunt: invent payload families; CLASSIFY KNOWN vs NOVEL

## NOVEL payload families (lab-verified, classified NOVEL by agents, Aug 2026)
These are LAB discoveries — mechanisms to re-validate per real target, not universal 0-days.

1. **SVG/image**: namespace-less SVG bypasses img-uri allowlist entirely; XML-entity-encoded schemes (&#104;ttp://, &#102;ile://) defeat scheme filters; null-byte/BOM/overlong-UTF-8 prefixes tolerated by parser but not filter; PNG/GIF+SVG entity polyglots reach parser path; protocol-relative (//www.w3.org) and scheme-less namespaces accepted.
2. **Font parser**: zero-length and impossible-geometry table records still dispatched (offset=0xFFFFFFF0, length=0xFFFFFFFF, count overflow 0xFFFF, duplicate/overlapping table ranges, 4GB length w/o backing data) — "count overflow not validated" class; UTF-16BE/LE NUL-interleaved command strings defeat substring filters.
3. **Doc preview**: PDF magic accepted at ANY offset and mid-string; valid PNG/GIF/HTML/XML polyglots carrying %PDF-1.4 reach the PDF scanner; PDF+RTF+macro tri-polyglot hits AutoOpen sink; line-folding, hex-string and null-byte URI encodings bypass doc-uri.
4. **Email auto-render**: entity-encoded event attribute NAMES (on&#101;rror) bypass filter while still executing; data:text/html + srcdoc chaining re-enables blocked primitives; view-source:/about:/cid: schemes fire tracking-pixel sink.
5. **Deep links**: data:// (double-slash) bypasses data: denylist; triple-encoded javascript: in custom schemes; intent:// scheme=javascript + browser_fallback_url chains two bypass primitives in ONE URI; action-parameter passthrough (myapp://shell?cmd=id).
6. **XML**: UTF-16/UTF-32-encoded DOCTYPE/XXE bypasses ASCII regex filter (filter passes, parser doesn't execute — gap documented for XInclude/XSLT follow-up).
7. **vCard/iCal**: malformed slash variants (http:host, http:/host, http:\\host), control-char-in-scheme (space/tab/CR/FF/NBSP after colon), double-encoded URIs defeat scheme filter — reproducible SSRF-primitive bypass.
8. **QR/notifications**: Unicode fullwidth colon (data：), overlong-UTF-8 colon, null-mixed case schemes — all execute.

## Lessons
- Zero-touch framing = the severity multiplier: parser fires with no user click.
- Agents print findings in varied formats (`finding: True`, `PASSED XSS True`) — grep both raw-JSON and prose patterns when mining transcripts.
- ~16/50 agents hit the 16-step cap; transcripts preserve evidence, just no polished report. Run with more steps or fewer agents for full reports.
- Campaign output: results_zt/agent_XX_*.md + report_zerotouch.md.
