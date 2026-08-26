# VERTICAL-023-A — Implementation Contract

Status: **Ready for implementation**

Parent specification: `docs/specs/VERTICAL-023-production-readiness-operational-health.md`

Baseline: `main` @ `6ece2d14978f06f436837f94a329f184fe3a947b`

## Purpose

Implement only Slice **023-A — Health model**. This contract is intentionally narrow. It introduces deterministic liveness/readiness semantics for the API and a minimal structured operational health model without implementing deployment smoke automation (023-B) or production acceptance (023-C).

## Authority and precedence

Implementation MUST comply with:

1. `AGENTS.md`;
2. VERTICAL-023 specification;
3. VERTICAL-022 governance and acceptance artifacts;
4. existing runtime contracts and tests.

If a conflict appears, stop and report it instead of inventing a new rule.

## In scope

- normalize or preserve `GET /health` as API liveness;
- add `GET /ready` as API readiness;
- add a short-timeout PostgreSQL readiness check;
- expose structured component status for the checks evaluated by readiness;
- expose VERTICAL-022 contract health only as read-only operational context if a stable read path already exists;
- add tests for all behavior changes;
- keep response payloads free of secrets and stack traces.

## Explicitly out of scope

Do NOT implement:

- `scripts/production-smoke.sh`;
- frontend health endpoints;
- Dokploy/Traefik automation;
- auto-healing, restart or redeploy;
- alerting/notification changes;
- database migrations unless strictly required by an existing health persistence model (prefer none);
- DSpace writes;
- DSpace authentication changes;
- snapshot approval, promotion, resolution or supersession;
- cataloging contract changes;
- changes to the 56 governed bindings;
- changes to `dspace-cataloger`;
- VERTICAL-023 operational acceptance.

## Required endpoint semantics

### `GET /health`

Purpose: liveness only.

Required behavior:

- HTTP `200` when the API process is alive and can serve the request;
- MUST NOT query DSpace;
- SHOULD NOT depend on PostgreSQL availability;
- MUST NOT perform mutations;
- response MUST be deterministic and non-secret.

Minimum response contract:

```json
{
  "status": "LIVE"
}
```

Existing non-breaking fields may be preserved when already part of the public contract, but do not add unrelated diagnostics to liveness.

### `GET /ready`

Purpose: determine whether the API can perform its minimum production function.

Required behavior:

- HTTP `200` when all critical readiness dependencies pass;
- HTTP `503` when any critical readiness dependency fails or times out;
- PostgreSQL is critical for this slice;
- DSpace remote availability is NOT a liveness dependency and MUST NOT become a hidden critical readiness dependency in 023-A unless the parent spec is explicitly amended;
- MUST NOT perform mutations.

Minimum success shape:

```json
{
  "status": "READY",
  "components": [
    {
      "name": "database",
      "status": "READY",
      "detail_code": "DATABASE_OK"
    }
  ]
}
```

Minimum failure shape:

```json
{
  "status": "NOT_READY",
  "components": [
    {
      "name": "database",
      "status": "NOT_READY",
      "detail_code": "DATABASE_UNREACHABLE"
    }
  ]
}
```

Additional fields such as `checked_at` or `latency_ms` are allowed only when deterministic enough for tests and do not leak internals.

## Stable operational vocabulary

For 023-A, use only the minimum required states/codes:

Statuses:

- `LIVE`
- `READY`
- `NOT_READY`
- `DEGRADED` only if an actually implemented non-critical component needs it
- `UNKNOWN` only for a genuinely unevaluated component

Detail codes:

- `PROCESS_OK`
- `DATABASE_OK`
- `DATABASE_UNREACHABLE`
- `RUNTIME_CONFIG_INVALID` only if this slice explicitly validates an already-required runtime setting
- `DSPACE_CONTRACT_SYNCED` / `DSPACE_CONTRACT_DEGRADED` only if exposed by an existing safe read path

Do not create free-form codes for tests.

## PostgreSQL readiness check

Requirements:

- use the application's existing DB/session abstraction;
- issue the smallest safe read-only probe supported by the stack, e.g. `SELECT 1`;
- no schema writes;
- no transaction side effects beyond the framework's normal read connection lifecycle;
- enforce a short bounded timeout;
- a timeout and connection failure map to HTTP `503` and `DATABASE_UNREACHABLE`;
- do not return raw exception text, hostnames, credentials or connection strings.

Default implementation target: timeout <= 2 seconds. If the current DB library makes a per-probe timeout unsafe or materially invasive, stop and document the constraint rather than silently using an unbounded call.

## VERTICAL-022 boundary

023-A may read contract health if an existing stable read function already exposes it.

It MUST NOT:

- call approve endpoints/functions;
- call resolve-evidence functions;
- create or promote snapshots;
- mutate ACTIVE baseline state;
- translate a health failure into DSpace drift;
- reinterpret an observation failure as field removal.

A DSpace/contract degradation MUST NOT make `/health` fail.

## Security contract

Responses and logs produced by this slice MUST NOT expose:

- `POSTGRES_PASSWORD`;
- `DATABASE_URL` with credentials;
- `CATALOG_REVIEW_TOKEN`;
- `DSpace_READ_PASSWORD`;
- full `.env` values;
- stack traces in public endpoint payloads;
- raw DSpace HAL+JSON.

The implementation must not add a generic environment dump or diagnostic endpoint.

## Error handling

Readiness failures are operational states, not uncaught 500s.

Expected mapping:

```text
API process alive                         -> /health 200
DB reachable                              -> /ready 200 READY
DB connection refused                    -> /ready 503 NOT_READY / DATABASE_UNREACHABLE
DB timeout                               -> /ready 503 NOT_READY / DATABASE_UNREACHABLE
DSpace unavailable                       -> /health 200
VERTICAL-022 REVIEW_REQUIRED             -> /health 200
```

If detailed operational context is returned, it must not change these core semantics.

## Tests required

At minimum add regression coverage for:

1. `/health` returns `200` and `LIVE` without requiring a DB query;
2. `/ready` returns `200`, `READY`, `DATABASE_OK` when DB probe succeeds;
3. `/ready` returns `503`, `NOT_READY`, `DATABASE_UNREACHABLE` on connection failure;
4. `/ready` returns `503` on DB timeout and does not hang indefinitely;
5. DSpace unavailability does not change `/health=200`;
6. a degraded VERTICAL-022 status does not mutate any DSpace-contract state;
7. health/readiness payloads do not contain known secret environment values;
8. no DSpace mutation path is reachable from health/readiness handlers.

Where practical, use dependency injection/mocking at the narrowest boundary. Do not require real external DSpace access for the unit/integration test suite.

## Non-regression requirements

Implementation MUST preserve:

- DSpace read-only architecture;
- current VERTICAL-022 ACTIVE baseline and governance semantics;
- exact `dc.subject.linguiscgroup` spelling;
- current cataloging contract version and 56 bindings;
- existing `/health` consumers unless a documented incompatibility is unavoidable;
- existing API startup behavior;
- existing Docker/Dokploy port contract (`api:8000`, `web:3000`).

## Files likely to change

Claude may identify exact paths after inspection, but expected change classes are limited to:

- API health/readiness router or application entrypoint;
- a small health service/helper;
- tests;
- minimal documentation if endpoint contract documentation already exists.

Do not modify frontend, compose, migrations, DSpace sync code or cataloging semantics unless the implementation cannot proceed without doing so; if so, stop and report the blocker.

## Validation commands

Run from WSL under `/home/keilyn/cat` per `AGENTS.md`.

Claude must first inspect the repository's existing test tooling and then run the narrowest relevant tests plus the normal backend test suite required by project conventions.

Do not claim PASS without command output.

At minimum report:

- exact commands run;
- exit status;
- tests passed/failed/skipped;
- any existing unrelated failures separately.

## Deliverable requirements

Claude's implementation response must include:

- summary of files changed;
- exact endpoint behavior implemented;
- test evidence;
- confirmation that no migrations were added unless explicitly justified;
- confirmation that no DSpace write/mutation path was added;
- confirmation that VERTICAL-022 governance was not modified;
- any deviation from this contract.

## Stop conditions

Stop implementation and report before proceeding if any of the following becomes necessary:

- DSpace write or auth mutation;
- VERTICAL-022 baseline/snapshot mutation;
- automatic restart/redeploy;
- secret exposure;
- database schema migration not clearly required by the parent spec;
- frontend changes;
- modification of cataloging rules or 56 bindings;
- unbounded dependency probes;
- changing `/health` into a full dependency/readiness check;
- weakening tests to make the slice pass.

## Acceptance criteria for 023-A

023-A is ready for review when all are true:

1. `/health` is deterministic liveness and returns `200` while the API process is alive.
2. `/ready` distinguishes DB-ready from DB-unavailable with `200` vs `503`.
3. DB checks are read-only and bounded.
4. DSpace is not a liveness dependency.
5. No health/readiness path mutates DSpace or VERTICAL-022 state.
6. No secrets are exposed.
7. Required regression tests pass with recorded evidence.
8. No scope from 023-B or 023-C is implemented.

This contract authorizes only the implementation of **VERTICAL-023-A**.