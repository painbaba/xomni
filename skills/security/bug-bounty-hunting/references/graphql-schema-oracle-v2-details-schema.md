# GraphQL schema oracle v2 — operation-param schemas & identity wall (2026-08-07, same day as v1)

Supersedes the v1 "decoy, CLOSED" verdict: the availability schema was a
decoy, but a SIBLING OPERATION serves a REAL schema that validates AND
executes — it just needs an identity context. Full map below.

## Operation enum discovery
The act bundle references operations via a minified enum: grep
`[a-zA-Z_$]{1,3}\.Ni\.[a-zA-Z]+` in the activities chunk →
`A.Ni.{availability, calendar, details, review, search}`. Each
`?operation=<value>` serves its OWN GraphQL schema on the SAME endpoint
`POST /api/activities/graphql?operation=<op>`:
- `operation=details` → root field `details: DetailsResponse!`
  (`{ details }` validates ONLY here; on other operations it's
  "Cannot query field 'details'" — the SAME query text is the probe)
- `operation=availability` → root `availability: AvailabilityResponse!`
  (the v1 decoy)
- Unknown/any other value still runs the query pipeline (introspection
  error) — the param is a backend selector, not a strict router.

## operation=details schema (fully mapped, verified live)
```
details(DetailsRequest!): DetailsResponse!
DetailsRequest = {
  context: InternalContext!,
  contentRequest: ContentRequest!,
  detailsRequest: DetailsRequestParameters!
}
InternalContext = {                        # EXACTLY these — verified via
  currency: String!,                       # "not defined by type" oracle:
  memberId: Int,                           # languageId/platformId/pageTypeId/
  experimentInfo: {                        # cid/priceStrategy/origin/locale/
    forcedExperiments: [...],              # appVersion/isWebview/apiBaseUrl/
    forceUserVariant: String               # userAgent/deviceId/sessionId/
  }                                        # customerHash ALL flagged invalid
}
ContentRequest = { imageRequest: ImageRequest! }
ImageRequest = { count: Int!, width: Int, height: Int }
DetailsRequestParameters = { activityId: Int! }   # supplierId NOT valid
DetailsResponse.result: DetailsActivityResult
DetailsActivityResult.activity.activityRepresentativeInfo.
  { activityToken, activityId }              # ALL VALID — query validates
```
Type-error leak on the way: `Expected type 'Int', found "1563604"` —
activityId is a NUMBER, not string.

## "not defined by type" oracle (input-type enumeration)
Feed a batch of guessed fields into a required input object; every
invalid one is flagged `Field 'X' is not defined by type 'Foo'`; fields
ABSENT from the list are real. This pinned InternalContext to exactly 3
fields. IMPORTANT consequence: input types are strict — adding extra
fields to the context flips responses from validation errors to
`"Unable to deserialize request"` on the backend parser. Keep inputs to
the oracle-verified shape.

## Execution probe (validation passed ≠ data available)
After validation passes, `{"data":null,"errors":[{"message":"Internal
server error","path":["details"]}]}` means the query EXECUTED and reached
a real backend. Then sweep:
- activityId 1, 100, 99999999, real IDs (1563604, 1628416) → SAME 500
- extra headers (AG-ACTIVITIES-CLIENT-ID, AG-CORRELATION-ID) → SAME 500
- CONCLUSION: backend 500s without a real identity context
  (AG-ACTIVITIES-IDENTITY-TOKEN session). The wall is identity, not
  schema, not IDs, not headers.
- THE ONE HUMAN STEP: an authenticated Agoda session (register + login).
  With it, details/availability execute for real data → then test
  booking-reference IDOR (PII), price manipulation in booking mutations,
  payment abuse. State this step once ("where I need you: one logged-in
  account") and stop — the wall already answered.

## Working request (details, validated + executed)
```
curl -s --compressed -X POST https://www.agoda.com/api/activities/graphql?operation=details \
  -H "Content-Type: application/json" \
  -H "AG-CID: -1" -H "AG-PLATFORM-ID: 0" -H "AG-LANGUAGE-ID: 1" \
  -d '{"query":"{ details(DetailsRequest:{context:{currency:\"USD\",memberId:0,experimentInfo:{forcedExperiments:[],forceUserVariant:\"\"}},contentRequest:{imageRequest:{count:1,width:100,height:100}},detailsRequest:{activityId:1563604}}){ result { activity { activityRepresentativeInfo { activityToken } } } } }"}'
```

## Takeaways for the next target
- When one operation's types are redacted, enumerate the operation enum
  (bundle grep) and probe sibling operations — one may serve a REAL
  schema (different backend, different root fields).
- Validation-pass + universal 500 = identity wall. Don't chase headers or
  IDs; identify the session requirement, park the target with the ONE
  human step labeled.
