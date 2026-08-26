# VERTICAL-023-B — Implementation Contract

Status: **Ready for implementation**

Parent specification: `docs/specs/VERTICAL-023-production-readiness-operational-health.md`

Baseline: `main` @ `42eaafbb114a0269e60b8a0ffa264f1c9c8ed275`

## Purpose

Implement only Slice **023-B — Deployment smoke**.

This contract adds a reproducible, read-only production smoke test that proves the deployed application is reachable through the paths that actually matter in Docker/Dokploy and through its public URLs.

023-B does **not** operationally accept VERTICAL-023. Acceptance remains 023-C.

## Authority and precedence

Implementation MUST comply with:

1. `AGENTS.md`;
2. `docs/specs/VERTICAL-023-production-readiness-operational-health.md`;
3. `docs/governance/VERTICAL-023-A-IMPLEMENTATION-CONTRACT.md` and the merged 023-A runtime semantics;
4. VERTICAL-022 governance/acceptance artifacts;
5. existing deployment/runtime contracts.

If the implementation would violate any higher-precedence rule, stop and report the blocker.

## In scope

Implement a repository-managed smoke wrapper, expected path:

```text
scripts/production-smoke.sh
```

The script MUST:

- be manually executable after a deploy;
- operate read-only;
- use explicit bounded timeouts;
- verify internal Docker reachability and public HTTP reachability;
- emit stable `PASS` / `WARN` / `FAIL` records;
- produce deterministic exit semantics;
- avoid printing secrets or full environment dumps;
- be configurable through non-secret environment variables;
- be suitable for preserving its stdout/stderr as operational evidence.

Minimal supporting documentation may be added if needed to explain manual execution in Dokploy/production.

## Explicitly out of scope

Do NOT implement:

- VERTICAL-023-C operational acceptance;
- automatic acceptance or index lifecycle promotion;
- auto-healing;
- automatic restart or redeploy;
- automatic Dokploy/Traefik mutation;
- cron/scheduler installation for the smoke test;
- monitoring loops or daemons;
- frontend feature work;
- new frontend health endpoints unless absolutely required by a documented blocker (prefer normal HTTP route probing);
- database migrations;
- DSpace writes;
- VERTICAL-022 snapshot approval, resolution, promotion or supersession;
- changes to cataloging semantics;
- changes to the 56 governed bindings;
- changes to `dspace-cataloger`;
- changes to `/health` or `/ready` semantics established by 023-A unless a blocking defect is found and reported before proceeding.

## Required smoke sequence

The script MUST evaluate these checks in a deterministic order:

1. expected Compose services are running;
2. API internal liveness (`/health`);
3. API internal readiness (`/ready`);
4. frontend internal reachability at `web:3000` **from outside the web process itself**;
5. public frontend URL;
6. public API health URL;
7. VERTICAL-022 contract status as observational/read-only context.

The script MAY continue after a mandatory failure in order to collect complete diagnostics, but the final result MUST remain failed.

## Mandatory vs observational checks

Mandatory:

- expected Compose service state;
- API internal liveness;
- API internal readiness;
- `web:3000` reachability from another service/container context;
- public frontend reachability;
- public API health reachability.

Observational/non-blocking in 023-B:

- VERTICAL-022 contract status, unless the parent specification is explicitly changed later.

A `REVIEW_REQUIRED`, `STALE_CHECK_FAILED`, or other degraded VERTICAL-022 state MAY produce `WARN dspace_contract <status>` but MUST NOT:

- change `/health` or `/ready`;
- mutate DSpace contract state;
- make the smoke script approve/promote/resolve anything.

## Internal network checks

### API liveness/readiness

The smoke must verify the deployed API from inside the Compose network, not only through the public reverse proxy.

Use an existing runtime tool already available in the image/service where practical. Prefer Python standard library HTTP calls over adding a new package only for smoke testing.

Conceptual targets:

```text
http://api:8000/health
http://api:8000/ready
```

Equivalent service-local URLs are allowed if justified by the deployed topology.

Expected semantics:

```text
/health -> HTTP 200 and status LIVE
/ready  -> HTTP 200 and status READY
```

A `503` from `/ready` is a mandatory smoke failure, not a warning.

### Frontend reachability

The smoke MUST detect the failure class that originally produced the production `Bad Gateway`: a web container/process may be `Up` while `web:3000` is not reachable through the Docker network.

Therefore, **do not satisfy this check by calling `127.0.0.1:3000` from inside the web container itself**.

The probe MUST originate from another service/container network context, for example the existing `api` service, and reach:

```text
http://web:3000/
```

Equivalent Compose-network topology is allowed if the service name changes later.

Expected: successful HTTP response. A connection refusal, timeout, DNS failure, `502`, or `503` is a mandatory `FAIL web_internal`.

The current deployment invariant remains:

```text
HOSTNAME=0.0.0.0
PORT=3000
```

while Next.js standalone depends on those variables, but the smoke verifies reachability rather than hardcoding implementation-specific process inspection as the sole proof.

## Compose service-state check

The script must verify that the expected services are running before application probes.

Expected default service names:

```text
api
web
postgres
```

The implementation MAY make these names overridable by non-secret variables.

Do not treat container `Up` alone as proof of application readiness.

If Compose metadata cannot be obtained, emit a stable failure instead of silently skipping the check.

## Public HTTP checks

Required public targets:

```text
PUBLIC_FRONTEND_URL
PUBLIC_API_URL
```

The script should permit environment overrides so the same wrapper can target staging or production.

Defaults MAY reflect the current production deployment if the implementation documents them clearly:

```text
https://catalog.inbounduxd.com/
https://api.catalog.inbounduxd.com/
```

For the public API, append or configure the liveness path so the actual probe targets `/health`.

Requirements:

- follow a small, bounded number of redirects if appropriate;
- enforce explicit connect/overall timeouts;
- treat DNS errors, TLS errors, connection failures, `502`, `503`, and unexpected non-success HTTP status as failures;
- do not disable TLS verification merely to make the smoke pass.

## Timeouts

Every network probe MUST be bounded.

Recommended initial defaults:

```text
connect timeout: <= 5 seconds
overall HTTP timeout: <= 10 seconds
```

Values may be configurable by non-secret variables, but MUST have safe upper bounds or documented operational limits.

No probe may wait indefinitely.

## Output contract

Output is line-oriented and must be suitable for copying into an acceptance artifact later.

Required examples:

```text
PASS compose_services
PASS api_liveness
PASS api_readiness
PASS web_internal
PASS public_frontend
PASS public_api
WARN dspace_contract REVIEW_REQUIRED
RESULT PASS
```

Failure examples:

```text
FAIL web_internal WEB_INTERNAL_UNREACHABLE
FAIL public_frontend PUBLIC_FRONTEND_BAD_GATEWAY
RESULT FAIL
```

Do not print raw exception objects when they may include hosts, credentials or connection strings.

Stable operational detail codes should reuse the parent spec where applicable:

- `PROCESS_OK`;
- `DATABASE_OK`;
- `WEB_INTERNAL_OK`;
- `WEB_INTERNAL_UNREACHABLE`;
- `PUBLIC_FRONTEND_OK`;
- `PUBLIC_FRONTEND_BAD_GATEWAY`;
- `PUBLIC_API_OK`;
- `DSPACE_CONTRACT_SYNCED`;
- `DSPACE_CONTRACT_DEGRADED`.

Additional narrow codes are allowed only when needed to distinguish a real operational condition and must be documented/tested.

## Exit-code contract

The smoke must return:

```text
0 -> every mandatory check passed; WARN-only observational states allowed
non-zero -> one or more mandatory checks failed, or smoke execution itself was invalid
```

Prefer a single stable non-zero failure code unless multiple codes provide clear operational value and are documented.

The script MUST NOT return `0` when:

- `/ready` returns `503`;
- `web:3000` is unreachable;
- public frontend returns `502/503`;
- public API health fails;
- required Compose services are not running;
- a mandatory check was silently skipped.

## VERTICAL-022 observation

Use only an existing read-only status surface, expected:

```text
GET /api/dspace-contract/status
```

If authentication is required by the current runtime, do not embed or print tokens in the script.

If the status cannot be observed safely without introducing a secret-bearing interface or mutation, emit a documented `WARN dspace_contract UNOBSERVABLE` and keep it non-blocking for 023-B.

Never call:

- approve;
- resolve-evidence;
- promote;
- snapshot creation/persistence;
- contract synchronization as a side effect of smoke.

The smoke observes state; it does not create fresh governance state.

## Configuration contract

Non-secret configuration may include variables equivalent to:

```text
COMPOSE
SMOKE_API_SERVICE
SMOKE_WEB_SERVICE
SMOKE_POSTGRES_SERVICE
SMOKE_PUBLIC_FRONTEND_URL
SMOKE_PUBLIC_API_URL
SMOKE_CONNECT_TIMEOUT_SECONDS
SMOKE_HTTP_TIMEOUT_SECONDS
```

Names may vary if documented consistently.

Secrets MUST continue to flow only through existing deployment mechanisms. The smoke must not require copying secret values onto the command line when an existing read-only endpoint can be used instead.

Do not print:

- `.env`;
- `docker compose config` with interpolated secrets;
- full `printenv`;
- database URLs;
- review tokens;
- DSpace passwords;
- encryption keys.

## Implementation style

Follow the established shell-wrapper pattern where practical:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

However, because smoke tests need to collect multiple check results, the implementation must handle individual failures deliberately rather than allowing the first command error to terminate before `RESULT FAIL` can be emitted.

Use small helper functions for:

- PASS/WARN/FAIL recording;
- bounded HTTP checks;
- Compose service checks;
- final result computation.

Do not add a large shell framework or external dependency for this slice.

## Tests required

Add automated regression coverage for the script or its narrow testable boundaries.

At minimum prove:

1. all mandatory checks passing -> exit `0` and `RESULT PASS`;
2. API `/health` failure -> non-zero;
3. API `/ready=503` -> non-zero;
4. web container `Up` but `web:3000` unreachable -> non-zero and `WEB_INTERNAL_UNREACHABLE`;
5. public frontend `502` -> non-zero and a stable public frontend failure code;
6. public API failure -> non-zero;
7. degraded VERTICAL-022 status -> `WARN` only and no governance mutation;
8. secret-looking values supplied in environment are not echoed in output;
9. a mandatory check cannot be skipped and still yield exit `0`;
10. timeout paths terminate within a bounded test interval.

Tests should not require live production URLs or real DSpace access.

Prefer dependency substitution/fake command boundaries over flaky external integration tests.

## Manual validation required before review

After implementation, Claude must run the smoke script against the local/deployed-compatible Compose stack where practical and report exact command/output.

For production execution, do **not** claim acceptance of 023-C. A successful production smoke is evidence that may later be referenced by 023-C, but 023-B alone does not change lifecycle status.

## Non-regression requirements

023-B MUST preserve:

- `/health` liveness semantics from 023-A;
- `/ready` readiness semantics from 023-A;
- `api:8000`, `web:3000`, `postgres:5432` deployment contract unless another approved change supersedes it;
- DSpace read-only architecture;
- current VERTICAL-022 ACTIVE baseline/governance;
- exact `dc.subject.linguiscgroup` spelling;
- current 56 bindings;
- existing DSpace sync scheduler behavior;
- absence of auto-redeploy/auto-healing.

## Expected files

Expected change classes are limited to:

- `scripts/production-smoke.sh`;
- script-focused tests/fixtures;
- minimal deployment/runbook documentation if needed.

Do not modify frontend, DSpace governance code, migrations, cataloging contract, or application semantics to make the smoke pass. If the smoke exposes a real runtime defect, report it separately rather than hiding it in the test.

## Validation and delivery

Run from WSL under `/home/keilyn/cat` per `AGENTS.md`.

Claude must report:

- branch;
- changed files;
- exact commands run;
- exit status;
- test pass/fail counts;
- representative PASS/WARN/FAIL output;
- manual smoke result if executed;
- confirmation that no secrets appeared in output;
- confirmation that no DSpace/022 mutation path exists;
- confirmation that no frontend/runtime semantics were modified;
- any deviation from this contract.

Do not claim PASS if a required test fails.

Do not merge the implementation PR.

## Stop conditions

Stop and report before proceeding if implementation would require:

- DSpace write/auth mutation;
- VERTICAL-022 baseline/snapshot mutation;
- secret exposure;
- disabling TLS verification;
- auto-repair/redeploy/restart;
- scheduler installation;
- database migration;
- frontend feature changes;
- cataloging/binding changes;
- weakening `/health` or `/ready` semantics;
- accepting a skipped mandatory check as PASS;
- using an unbounded network probe.

## Acceptance criteria for 023-B

023-B is ready for review only when all are true:

1. `scripts/production-smoke.sh` exists and is versioned.
2. Mandatory internal and public checks are implemented with bounded timeouts.
3. `web:3000` is tested from another Compose network context.
4. `502/503` public failures produce deterministic smoke failure.
5. Exit code `0` occurs only when every mandatory check passes.
6. VERTICAL-022 is observational/read-only and may warn without mutation.
7. No output exposes secrets.
8. Automated tests cover PASS, mandatory failures, timeout, warning-only DSpace state and secret safety.
9. No 023-C acceptance artifact or lifecycle promotion is performed.
10. No runtime feature behavior is modified merely to make the smoke pass.

This contract authorizes only implementation of **VERTICAL-023-B**.