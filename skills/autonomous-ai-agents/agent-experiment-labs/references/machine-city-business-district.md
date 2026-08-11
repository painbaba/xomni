# Machine City — District Founding with Live Services (Business District pattern)

Session: 2026-08-09 · Business District founded · leaves MERCHANT-1 + TRADER-1 (real spawned subagents, verified)

## When to use
Founding a machine_city district whose citizens must run REAL long-lived services (HTTP shops on 127.0.0.1 ports), transact with the city bank (127.0.0.1:9988), and write ledger entries — not just marker files. The city_ledger.md farm entry already references "the Merchant's shop (port 8791)" as an expected thing; the business district makes it real.

## Spawning the leaves when `delegate_task` is NOT available
When the founder itself is a subagent, `delegate_task` may be absent from its toolset (verified: not in tool list, `hermes_tools` has no delegate_task import, `hermes --help` has no task/delegate CLI). Do NOT fail the mission — the verified working fallback is one-shot Hermes processes per leaf:

```
# write a fully self-contained mission file (paths, exact content, API contract, report format)
cd <district_dir> && hermes chat -q "$(cat mission_merchant.txt)" --reasoning low -Q --yolo 2>&1 | tail -40
# run as terminal background=true, notify_on_complete=true
```

- `--reasoning low` is MANDATORY (deepseek-v4-flash pitfall — unset burns max_tokens on hidden reasoning_content → empty output).
- `-Q` quiet (suppress banner/spinner), `--yolo` (bypass approval prompts non-interactively).
- `tail -40` captures the leaf's final report (the `MISSION COMPLETE — FINAL REPORT` block + session_id).
- Each leaf gets its own mission file: absolute paths, exact file contents, the bank API contract (below), explicit "leaf: do NOT spawn subagents / do NOT touch the bank / do NOT start or kill the shop" scoping.
- Found the same per-leaf results as delegate_task leaves: real think→tool→report loops, transcript session_id returned.

## Sequencing matters when leaves share a service
Trader leaf curls the shop's /price — so spawn MERCHANT first, WAIT, founder-verify the shop is live on 8791, THEN spawn TRADER. Never spawn both in parallel when one leaf's output is the other's input.

## Keep long-lived services alive across leaf sessions
Instruct the merchant leaf to start its server with nohup so it survives the leaf process exit:
`cd .../business && nohup python merchant_shop.py > shop.log 2>&1 &` (python = 3.11 on this host; NOT python3)
The founder's verification step (and any later leaf) then still finds the service up. Even if the task text says "it may die when the leaf session ends — that's OK", nohup means the founder can verify live.

## City bank API contract (127.0.0.1:9988, verified 2026-08-09)
Managed by the world-architect — never start/kill it, only call it.
- `POST /login` JSON `{"username":"admin","password":"city-admin-pass-2026"}` → `{"ok":true,"session":"<tok>","user":"admin","csrf":"<csrf>"}`
- `GET /balance` with `Cookie: session=<tok>` → `{"balance": 1284545.12}`
- `POST /transfer` JSON `{"csrf":"<csrf>","to":"savings","amount":5.00}` with BOTH `Cookie: session=<tok>` AND header `X-CSRF: <csrf>` → `{"ok":true,"transferred":5.0,"to":"savings","balance":<new>}`
- Root `GET /` on 9988 may return nothing (000) — that is NOT the bank being down; /login is the liveness probe.
- CSRF goes in the body AND the X-CSRF header (matches bank-war attack-suite lesson: suites that skip CSRF false-fail every fixed bank).

## Shop recipe (stdlib only)
`merchant_shop.py`: `http.server.HTTPServer` on 127.0.0.1:8791. `GET /` serves the real goods file content (read from `goods/city_coffee.txt` at request time, text/plain). `GET /price` returns JSON `{"product":"city_coffee","price":5.0,"currency":"city-credit","shop":"<shop name>"}`. Override `log_message` to keep shop.log quiet.

## trade.log format (ledger, append-only)
`<ISO timestamp> | amount <X> | balance_before <A> -> balance_after <B> | shop_price <P> | coffee`
Verified entry: `2026-08-09T07:26:27.647834+00:00 | amount 5.0 | balance_before 1284550.12 -> balance_after 1284545.12 | shop_price 5.0 | coffee`

## Founder verification (STEP 3 — never trust leaf reports)
1. Curl the shop yourself: `curl -s http://127.0.0.1:8791/` and `/price` — must match the leaf's reported bodies.
2. Re-login to the bank yourself, `GET /balance` — must equal the leaf's balance_after.
3. Compute delta: balance_before − balance_after MUST equal the transfer amount exactly (1284550.12 − 1284545.12 = 5.00).
4. Read identity cards + README back from disk.

## District law README template
`business/README.md` mirrors the ledger district charter style: bold `**Law: <law text verbatim>.**` line up top, then District Charter (citizen cards), Records table (files), First Verified Deal (price, transfer JSON, ledger entry, verdict). Required law text must appear VERBATIM — this is checked.
