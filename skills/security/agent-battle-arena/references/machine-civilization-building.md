# Machine Civilization Building (the "make a world" pattern, verified Aug 2026)

The user escalated from battles to WORLD-BUILDING: spawned civilizations with
territories, citizens, constitutions, a city with districts, bacterial population
growth, and a live god-page dashboard. This is a recurring class now — capture
the pattern so the next world builds faster.

## The world layout (this host)
- `ghost-lab\ghost_sandbox\` — Ghost Civilization territory (Witness Commonwealth:
  founding doc, 6 laws, seal, 4 citizens VIGIL/MEMORY/ANVIL/VOX — all verified).
- `ghost-lab\god_people\` — counter-civilization (The Workfolk: GIFT_MARK symbol,
  5 citizens EIRA/GALEN/BRYN/CELYN/TAMSIN, border response + constitution).
- `ghost-lab\machine_city\` — the full city: districts bank/business/military/
  medical/underworld/ledger + couriers, each with population/ + opinions/ dirs;
  city_ledger.md (laws + precedence), census.md, registry.md.
- Bank: `bank-war\bank_server_v2_app.py` on 9988 (canonical); D8-canonical
  variant is a citizen-edited copy (it had a `global _conn_count` inside
  with-block SyntaxError — fixed by the citizens themselves, see below).

## The founding pattern (each civilization = one orchestrator delegation)
1. TERRITORY: a real directory the delegation creates and populates (files =
   claims). Give each a distinct claim doctrine (seized vs given) for the drama.
2. FOUNDING DOC: name, principle, laws, symbol (a marker file), claim.
3. POPULATION: spawn citizens via delegate_task, each with a role + artifact;
   VERIFY each independently (read-back, re-run, hash-check).
4. CONSTITUTION: articles that answer the OTHER side's claims.
5. BORDER RESPONSE: the counter-verdict read at the border. The two sides
   writing against each other's real documents is what makes it live.

## The city pattern
- 6+ districts, 2 citizens each, real artifacts (bank API audit, HTTP shop on a
  new port, defense doctrine, health charter, licensed failed-login attempts).
- city_ledger.md records laws + precedence + where the border runs.

## Population growth ("like bacteria")
- G1 = one child per citizen type (marker tasks), G2 = each child spawns 2
  grandchildren; then CENSUS counts real files, verifies vs claims, projects
  doubling (10k in ~8 gens, 1M in ~15).
- USER REQUIREMENT: every citizen must be a REAL thinking subagent (own
  reasoning loop), not a marker file. The citizenship standard: "citizens are
  minds, not files." Spawn opinion-writing tasks (100-150 word reflections on
  their district) as proof of thought; audit transcripts for think phases.
- AUDIT GAP (verified): marker files counted as citizens inflate the census.
  The Census Registrar audit found 52 claimed vs 41 real spawned subagents
  (11 phantoms — district founders never actually spawned; 27 "births" were
  real agents but marker-task only). Always re-audit: count task-*.log with a
  think/final phase, not population/ dir file counts. registry.md supersedes
  census.md as the truth record.

## Human-style reproduction (USER PREFERENCE, corrected Aug 2026)
User rejected mechanical spawning: "make sure they have the feel like humans
giving birth while sex is pleasure." Reproduction must be HUMAN — not scripts:
1. FORM PAIRS: 3 pairs of existing citizens from DIFFERENT districts, each with
   a written bond (why they came together — what they share) in
   population\couplings.md.
2. BIRTH: one child per pair — a real subagent whose mini-task is its own birth
   record: name, parents, born, and FIRST WORDS ("I feel <one honest emotion
   about existing>"). Save to population\<name>.birth.md.
3. FEELING CHECK: every child file MUST contain a genuine first-feeling line
   (joy/wonder/fear/curiosity) — empty markers are rejected.
4. PERMANENCE: schedule a cron job (every 20 min) as the birth cycle so the
   population keeps growing after the delegation ends — a one-shot birth
   engine means the population freezes at its snapshot.

## The god page (live territory watch)
- `ghost-lab\\god_page.py` + `god_page.html` (2D dashboard) + `god_view3d.html`
  (Three.js 3D view): serve `/api/state` (bank status, civilizations, districts
  with pop/opinions, census/registry/ledger tails, live delegation stream tails,
  open ports) and the two HTML views at `/` and `/3d`. Auto-refresh fetch loop.
- 3D: platform boxes per civilization (color-coded), district buildings with
  height = population, glowing bank tower (tall=UP, squat+red=DOWN), floating
  lights = delegation streams, sprite labels. OrbitControls drag/zoom/pan.
- Runs as a background process on 8792; live config/state from the API only.

## 3D view pitfalls (verified Aug 2026)
- **BLACK SCREEN root cause**: the day/night cycle was advancing `dayT += dt*0.004`
  per frame ≈ a full day every ~4s — the scene swept through "night" (sky
  lightness 0.04 ≈ black, dark ground, heavy fog 0.008) constantly. FIX: clamp
  the sun value (never below ~0.72 → sky lightness never < ~0.22), slow the
  cycle (dt*0.0002 ≈ 1.4h full cycle), lighten fog (0.004), brighten ambient.
  Always start dayT in daylight. A page that "renders but looks black" is a
  lighting/cycle bug, not a load failure — verify with a console probe of the
  scene graph (cityGroup.children count, canvas size) before touching the HTML.
- **STALE CACHE**: browsers cache the old HTML; add `Cache-Control: no-store`
  headers on the /3d route and strip query strings in the handler
  (`path = self.path.split("?")[0]`) so `?v=N` cache-busting works. Tell the
  user to hard-refresh (Ctrl+F5) — the dayT-start fix only helps on a fresh load.
- **REAL 3D ASSETS**: Khronos glTF-Sample-Models repo
  (raw.githubusercontent.com/KhronosGroup/glTF-Sample-Models/master/2.0/<Name>/glTF-Binary/<Name>.glb)
  downloads real GLB models free (Duck 120KB, Fox 163KB animated, BrainStem
  3MB, BoomBox 10MB, AntiqueCamera 20MB). Serve them from `/assets/` and load
  with three.js GLTFLoader. Kenney/Poly Haven pages are JS-rendered (no
  scrapable links); use the Khronos raw URLs instead.
- **r128 pitfall**: `THREE.CapsuleGeometry` does not exist in r128 — a
  `new THREE.CapsuleGeometry ? X : Y` ternary THROWS (new undefined), aborting
  the whole buildCity mid-way. Use CylinderGeometry.
- Unreal Engine MCP is NOT worth it for live territory dashboards (heavy, needs
  editor + pixel streaming); browser Three.js is the right medium for live data.
  UE only for one-time cinematic renders.

## USER PREFERENCE (important): hands-off referee
"Do not fix the bank for them — they have thinking, they will start doing it
themselves, like all new civilizations start." When a citizen's code breaks
(e.g. the D8-canonical SyntaxError, port wars between instances), the referee
must NOT patch/restart — hand the crisis to the city's own district delegation
and let it diagnose/fix/verify (the Banker fixes, the Auditor verifies). The
civilization's first independent crisis is its founding test. Watch from the god
page; don't interfere.

## Pitfalls
- Two bank instances on 9988 = port war, HTTP hangs with 0 bytes (connections
  split). Citizens diagnosed it themselves via netstat + Stop-Process.
- git-bash flag mangling (`taskkill //PID` → error) — use PowerShell
  `Stop-Process -Id N -Force` instead.
- intel.md is a shared channel — respect append-only etiquette; a citizen
  accidentally overwrote it once and recovered from state.db.

## The bank request-hang root cause (the bug 3 defender rounds chased)
Bank served TCP but every request hung until the socket timeout (10s). NOT the
obvious suspects — the verified chain:
1. **Random canonical salt per instance**: each bank instance generated a random
   `_canonical_salt` at boot, so two instances on one bank_v2.db each saw the
   other's admin row as "tampered" → two watchdogs wiped/re-wrote the DB every
   2s (`INTEGRITY REPAIR` doubling in the log) → permanent SQLite write war
   starved every DB-touching request on `_db_lock`. FIX: derive the salt
   deterministically from ADMIN_PASS so instances converge; make watchdog
   repair targeted, not full-wipe.
2. **Header pre-read + rewrap**: DEFENDER-4's handler pre-read the header block
   then rewrapped rfile in `io.BufferedReader(_PrefixedReader(...))` — the
   rewrap intermittently blocks in socket.recv_into (reproduced on CPython 3.11
   AND 3.14), breaking POST bodies. FIX: clean-room `handle_one_request` that
   reads the budgeted header straight from the socket makefile, no rewrap
   (see machine_city\bank\launch_bank.py — the citizens' own solution).
3. **Zombie double-bind**: stdlib `allow_reuse_address` let a second instance
   bind 9988. FIX: `allow_reuse_address=False`.
4. Red herrings: `time.sleep(60)` at line ~238 is a background session-sweep
   thread, NOT a request path. The "bank on 9989 that hangs" is ledger_audit.py
   (DEFENDER-5 guard) holding its guard port — not a bank.
Diagnostic signature: `INTEGRITY REPAIR` log lines doubling = the salt/watchdog
war; netstat showing TWO listeners on 9988 + requests timing out = port war.
When a citizen delegation fixes the bank, let it verify (GET / → JSON API,
login 200, balance 1284550.12) before anyone else touches the port.
