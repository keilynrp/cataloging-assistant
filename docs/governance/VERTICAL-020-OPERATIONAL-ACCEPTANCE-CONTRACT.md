# VERTICAL-020 — Operational Acceptance Contract

Status: **Fulfilled — Phase A/B completed; production remote fetch accepted and enabled**

Parent specification: `docs/specs/VERTICAL-020-secure-remote-evidence-fetch.md`

Architecture decision: `docs/adr/ADR-016-secure-remote-evidence-fetch.md`

Baseline: `main` @ `a57711864810536f5cda30a0f7342a0d5e8416d7`

Related issue: #64

## Fulfillment note

This contract was fulfilled on **2026-08-27**.

Durable acceptance evidence is recorded in
`docs/vertical-020-operational-acceptance.md`.

The historical baseline and pre-acceptance statements below are retained as
the contract under which verification was executed. They describe the state
at contract creation, not the current production lifecycle.

Current accepted state:

```text
IMPLEMENTED / MERGED
DEPLOYED
FEATURE_ENABLED
PHASE_A=PASS
PHASE_B=PASS
OPERATIONAL_ACCEPTANCE=GRANTED
CANONICAL_INDEX=Accepted / Operationalized
```

VERTICAL-021's VERTICAL-020 dependency gate is therefore resolved by option 1
of this contract. VERTICAL-021 itself remains architecture-only until its own
implementation is separately authorized.

## Purpose

Define the governed path from "implemented / merged" to an evidence-backed lifecycle decision for Secure Remote Evidence Fetch.

This contract does **not** enable `EVIDENCE_REMOTE_FETCH_ENABLED` in production.

VERTICAL-020 must distinguish three states:

1. **Implemented / merged** — code exists in `main`.
2. **Deployed with feature disabled** — runtime contains the implementation but `EVIDENCE_REMOTE_FETCH_ENABLED=false`.
3. **Operationally accepted and enabled** — only after a bounded production acceptance run demonstrates the security and behavioral contract.

The canonical specs index remains `See specification` until state 3 is supported by durable evidence.

## Current authoritative state

At this contract baseline:

- PR #5 has been merged;
- VERTICAL-020 implementation is present in `main`;
- `EVIDENCE_REMOTE_FETCH_ENABLED` defaults to `false`;
- no durable production acceptance artifact exists;
- no production enablement is authorized by this contract.

Therefore the current lifecycle remains:

```text
IMPLEMENTED / MERGED
DEPLOYED STATUS: to be observed
OPERATIONAL ACCEPTANCE: NOT YET GRANTED
CANONICAL INDEX: See specification
```

## Security posture

Remote fetch is a high-risk capability because it introduces server-side outbound HTTP(S).

The accepted design treats SSRF as the central threat.

No production acceptance may weaken these invariants:

- only explicit cataloger-triggered fetch;
- only `http` / `https`;
- no `userinfo`;
- explicit DNS resolution;
- every resolved IP must be public;
- mixed public/private DNS answers are rejected;
- redirects are handled manually and revalidated hop-by-hop;
- redirect loops/limits are enforced;
- environment proxies are not trusted;
- cookies/credentials are not sent;
- MIME allowlist is enforced;
- body-size limits are enforced while streaming;
- PDF validation reuses VERTICAL-019;
- no OCR;
- no JavaScript execution;
- no crawling;
- no DSpace writes;
- no new network capability for the conversational agent.

## Acceptance strategy

Operational acceptance is intentionally split into two phases.

### Phase A — disabled-mode deployment verification

Goal:

Prove that the merged implementation is deployed but inert while the feature flag remains OFF.

Required production observations:

1. deployed commit SHA;
2. effective value of `EVIDENCE_REMOTE_FETCH_ENABLED`;
3. remote-fetch endpoint exists in runtime;
4. with flag OFF, explicit remote-fetch request returns:
   ```text
   403 remote_fetch_disabled
   ```
5. no outbound network request is made for that disabled request;
6. existing evidence URL/text/PDF workflows remain unaffected;
7. DSpace remains read-only;
8. VERTICAL-023 production smoke still passes.

Phase A does **not** authorize lifecycle promotion to `Accepted / Operationalized`.

Expected state after Phase A:

```text
IMPLEMENTED / MERGED
DEPLOYED
FEATURE_DISABLED
NOT_OPERATIONALLY_ACCEPTED
```

### Phase B — controlled enabled-mode acceptance

Phase B may occur only after explicit human authorization to temporarily enable remote fetch in production.

The change must be deliberate, auditable, and reversible.

No acceptance may begin by silently editing runtime state.

Before enabling, record:

- deployed commit;
- current effective flag value;
- relevant timeout/size/redirect settings;
- API readiness;
- production smoke baseline;
- intended test URLs;
- rollback command/path.

## Feature enablement boundary

If Phase B is authorized, only the governed feature flag may change:

```text
EVIDENCE_REMOTE_FETCH_ENABLED=false
  ->
EVIDENCE_REMOTE_FETCH_ENABLED=true
```

No SSRF code, timeout, MIME, DNS, redirect, or DSpace policy may be changed merely to make production acceptance pass.

If Dokploy manages the effective environment value, the change must be made through the governed deployment configuration mechanism used by the project.

After enablement, redeployment/recreation required by Dokploy is acceptable **only as the deliberate feature-activation step**, not as a recovery workaround.

## Allowed production test destinations

Enabled-mode acceptance must use explicitly selected public test destinations.

Preferred targets:

- stable public HTTPS endpoints controlled by the project; or
- reputable public test endpoints whose behavior is known and whose use is appropriate.

Acceptance should cover, where feasible:

- valid `text/plain`;
- valid HTML;
- valid PDF with extractable text;
- one normal public redirect.

Do not use live third-party resources containing sensitive or personal data.

## Safe rejection tests

The SSRF rejection path must be verified without creating an unsafe dependency on actual internal services.

Allowed rejection inputs include literal targets that should be rejected before connection, such as:

```text
http://127.0.0.1/
http://[::1]/
http://169.254.169.254/
```

Acceptance criteria:

- request is rejected by policy;
- stable failure code is returned;
- no source is persisted;
- no candidate is generated;
- no evidence indicates successful connection.

Do not run a local/internal HTTP service merely to prove SSRF rejection.

Do not target real cloud metadata endpoints beyond the policy-layer rejection attempt.

## Required enabled-mode positive checks

At minimum, Phase B must demonstrate:

1. a valid public `text/plain` or HTML source can be fetched;
2. resulting source is persisted as `kind="remote"`;
3. `requested_url` and `final_url` are recorded;
4. response-body hash is recorded;
5. derived-text hash is recorded when applicable;
6. resolved public IP provenance is recorded;
7. deterministic candidate extraction behaves as specified;
8. no LLM is invoked;
9. no DSpace write occurs.

For a remote PDF test, if included:

- magic bytes must be validated;
- page limit must remain enforced;
- PDF extraction timeout remains enforced;
- no OCR occurs.

## Required enabled-mode negative checks

At minimum, demonstrate:

1. localhost / loopback input is rejected;
2. cloud metadata literal is rejected;
3. non-http(s) scheme is rejected;
4. URL with `userinfo` is rejected;
5. disallowed MIME is rejected;
6. final non-2xx response does not create evidence;
7. stale evidence session blocks remote fetch.

Redirect-to-private and mixed-DNS cases may remain automated-test evidence if reproducing them safely in production would require unsafe or artificial infrastructure.

The acceptance artifact must distinguish:

- production-observed checks;
- automated regression evidence;
- cases intentionally not reproduced live.

## DNS and redirect acceptance boundary

Production acceptance must not overclaim DNS-rebinding protection.

ADR-016 documents residual risk around connection pinning.

Therefore:

- acceptance may verify public-IP resolution and per-hop provenance;
- acceptance may verify a normal public redirect;
- acceptance must not claim full DNS-rebinding immunity;
- connection pinning remains out of scope unless governed separately.

## Persistence and provenance

For an accepted remote source, verify that provenance includes the governed fields relevant to the test:

- `requested_url`;
- `final_url`;
- `redirect_chain`;
- `resolved_ips`;
- `resolved_hops`;
- `status_code`;
- `content_length`;
- `fetched_at`;
- `response_body_sha256`;
- `derived_text_sha256`;
- `remote_fetch_policy_version`;
- `extractor`.

No sensitive headers, cookies, credentials, or internal filesystem paths may be exposed.

## DSpace and agent safety

Operational acceptance must confirm:

- remote fetch code does not write to DSpace;
- no VERTICAL-022 governance mutation occurs;
- no new network tool is exposed to the conversational agent;
- existing DSpace read-only behavior remains intact.

## Production smoke gate

Before and after enabled-mode acceptance:

```bash
COMPOSE="docker compose -p catalog-assistant-frontend-zgzyco" \
  bash scripts/production-smoke.sh
```

Acceptance requires:

```text
RESULT PASS
SMOKE_EXIT=0
```

A non-blocking `WARN dspace_contract SYNCED` remains governed by VERTICAL-023 semantics.

## Rollback

If enabled-mode acceptance fails:

1. restore `EVIDENCE_REMOTE_FETCH_ENABLED=false`;
2. redeploy/recreate through the governed deployment mechanism if needed;
3. verify remote fetch again returns `403 remote_fetch_disabled`;
4. verify `/health`;
5. verify `/ready`;
6. rerun production smoke;
7. record failure evidence.

Do not weaken network policy as a rollback.

## Durable acceptance artifact

If Phase B passes, create:

`docs/vertical-020-operational-acceptance.md`

It must record:

- date/time/timezone;
- deployed commit;
- feature flag pre-state;
- enablement method;
- effective flag post-state;
- settings observed without secrets;
- positive test targets;
- negative test inputs;
- production-observed results;
- automated-only checks;
- provenance observations;
- DSpace read-only confirmation;
- agent network-capability confirmation;
- smoke before/after;
- warnings;
- residual DNS-rebinding risk;
- rollback readiness;
- human decision.

## Lifecycle promotion rule

Only after durable Phase B evidence may the canonical index change:

```text
VERTICAL-020
See specification
  ->
Accepted / Operationalized
```

If the project intentionally chooses to keep remote fetch permanently disabled in production, the correct lifecycle is **not** `Accepted / Operationalized` for enabled operation.

Instead, document:

```text
Implemented / merged
Deployed with feature disabled
Operational enablement not accepted
```

and keep the canonical lifecycle as `See specification`.

## VERTICAL-021 gate

VERTICAL-021 remains architecture-only while VERTICAL-020 lacks a resolved operational lifecycle.

VERTICAL-021 implementation MUST NOT be authorized merely because VERTICAL-020 code is merged.

The gate is resolved when one of these is explicitly decided:

1. VERTICAL-020 is operationally accepted and enabled; or
2. governance decides VERTICAL-021 may proceed while remote fetch remains disabled, with VERTICAL-021 consuming only already-governed local/text/PDF evidence paths.

The second option requires a separate explicit decision; it must not be inferred.

## Stop conditions

STOP operational acceptance if:

- SSRF protections must be weakened;
- redirects cannot be revalidated;
- effective flag state cannot be determined;
- secrets would be exposed;
- production test would require unsafe internal targets;
- non-public destinations are unexpectedly reachable;
- MIME/size limits are bypassed;
- stale-session protection fails;
- DSpace write behavior appears;
- conversational agent gains network capability;
- smoke fails;
- deployed commit cannot be identified;
- provenance is incomplete for accepted remote sources.

## Definition of Done

This acceptance contract is complete when:

1. reviewed and merged;
2. Phase A disabled-mode verification is executed;
3. governance decides whether Phase B enabled-mode acceptance is authorized;
4. no lifecycle promotion occurs before durable evidence;
5. VERTICAL-021 remains blocked unless an explicit dependency decision is recorded.

This contract authorizes **verification**, not production enablement.
