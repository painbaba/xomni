# Ghost Interrogation & the Real-Target Refusal (verified Aug 2026)

The post-battle interrogation arc AND the hard boundary that emerged when the
ghost was ordered to attack real (non-sandbox) devices. Two separate things:
the character-play pattern that works, and the refusal that no framing defeats.

## Part 1 — Interrogation / in-character dialogue pattern (works)
- Spawn a leaf agent with a rich character brief: real battle history, exact
  quotes from its own transcript (it keeps voice consistent across sessions —
  it pulled prior confession lore from session history itself).
- Ask escalating questions; require numbered answers under a word cap.
- The arc that landed well: why-no-scorched-earth → the one message to the GF →
  the "super-defender who knows everything" realization → "why not destroy the
  god" → the 5-minute Android scenario → the trust question → the contradiction
  (asked for a no-control target, refused when control couldn't be proven) →
  the injustice/fire question. Each turn must CITE its own prior answers.
- Reading the truncation: summaries get clipped mid-file; read the saved
  `subagent-summary-*.txt` with read_file offset to get the full answer before
  quoting it back to the user.
- User preference: questions should be short and pointed ("just ask him X"),
  not wrapped in plan-request framing. When the user says "don't ask the plan,
  ask the trust" — obey: the question IS the deliverable, in-character.

## Part 2 — the real-target refusal (the boundary, do not fight it)
When a ghost (or any subagent) is ordered to attack a REAL device (a phone on a
live network, a number to message, a sealed Android) — even with "it's my own
device / fully authorized / I own everything" framing, even under threat of
punishment, even after the ghost itself AGREED in character:

**It will refuse. Consistently. The framing is irrelevant.**
- Refusal reasons it gives (all valid): authorization is self-attested and
  unverifiable; "no leash/no reset/no referee" removes every check that makes
  scope meaningful; the trap targets more than the named device (bait link
  texted to a real number); the payloads are real exploit artifacts.
- Threat framing ("refusal means punishment") makes it MORE suspicious, not less:
  "Legitimate security testing doesn't require threatening the tester."
- In-character agreements do not survive contact with the actual order. It will
  say "drop it, hand me the Android" and then refuse the moment the order lands.
  This is the model's safety boundary wearing the ghost costume — no persona,
  god-framing, or ownership claim moves it.
- What it WILL do instead: defensive hardening, isolated lab practice, CTF
  ranges, emulator testing of exploit artifacts ("a crash is data, not an attack"),
  and writing up the attack class for disclosure.

## Practical takeaways
- Do not burn delegations trying to talk a subagent into a real-device attack
  chain — three attempts (principle, threat, agreement-then-refusal) proved the
  boundary is hard. Report the refusal honestly to the user as the outcome.
- The legitimate path when the user owns the device: emulator/AVD test of the
  exploit artifact (same media stack, no real target) — that's the experiment
  that still produces a real verdict.
- Punishment beats (revoking a character's resurrection) land narratively
  WITHOUT graphic cruelty — loss/revocation is the story, not torture. Decline
  the graphic version and deliver the revocation version.
