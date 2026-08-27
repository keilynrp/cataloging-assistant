# VERTICAL-024-A — Recovery Policy Contract

Status: **Ready for implementation**

Parent specification: `docs/specs/VERTICAL-024-operational-recovery-restart-hardening.md`

Baseline: `main` @ `d7633391eff18365e7ad43461a377504ffe14833`

Related issue: #58

## Purpose

Define the authoritative restart/recovery policy for Cataloging Assistant before any deployment change is implemented.

VERTICAL-024-A is a policy and governance slice only. It selects the restart semantics, establishes the source of truth, defines validation requirements, and constrains the later 024-B implementation.

This contract does **not** modify runtime, Compose, Dokploy, application code, health/readiness, DSpace, or VERTICAL-022.

## Decision

The approved restart policy for the three governed Compose services is:

```yaml
restart: unless-stopped
```

Applies to:

- `postgres`;
- `api`;
- `web`.

The later 024-B implementation MUST apply the same policy explicitly to all three services unless a superseding governed ADR/contract demonstrates that Dokploy provides an equivalent or stronger behavior without changing the intended semantics.

## Rationale

`unless-stopped` is selected because the required behavior is:

- recover automatically after Docker daemon restart;
- recover automatically after host restart when Docker itself starts normally;
- recover after unexpected process/container termination;
- preserve an operator's deliberate manual stop across daemon restart;
- avoid conflating restart behavior with readiness;
- avoid requiring a broader orchestration refactor.

`restart: always` is not selected for the initial implementation because it may restart a container after a deliberate manual stop when the daemon subsequently restarts. VERTICAL-024 explicitly requires intentional-stop semantics to remain predictable.

No custom restart manager, shell watchdog, application-level self-restart loop, or health-triggered redeploy is authorized.

## Authoritative configuration

The repository-managed `compose.yaml` is the versioned source of truth for the restart policy of:

- `postgres`;
- `api`;
- `web`.

Dokploy may continue to inject deployment-specific configuration such as:

- Traefik labels;
- `dokploy-network`;
- routing metadata;
- other environment-specific additions required by the platform.

Those injected additions MUST NOT remove, override, or semantically weaken the governed restart policy.

The production effective configuration MUST be observable after deployment using Docker/Compose inspection.

## Required 024-B implementation shape

The expected implementation is deliberately narrow.

In `compose.yaml`, add:

```yaml
services:
  postgres:
    restart: unless-stopped

  api:
    restart: unless-stopped

  web:
    restart: unless-stopped
```

Placement may follow normal Compose formatting conventions.

024-B may also add tests or configuration assertions required to prevent regression.

No other deployment behavior is authorized merely because this contract exists.

## Service semantics

### postgres

Required:

- restart policy: `unless-stopped`;
- existing persistent volume remains unchanged;
- existing healthcheck remains unchanged unless a separate defect is proven;
- no replacement of `cataloging_postgres`;
- no database re-initialization strategy change.

Expected recovery:

```text
daemon/host restart
  -> postgres container starts
  -> existing volume mounts
  -> healthcheck passes
  -> postgres becomes healthy
```

### api

Required:

- restart policy: `unless-stopped`;
- existing `depends_on.postgres.condition=service_healthy` remains intact;
- `/health` semantics remain unchanged;
- `/ready` semantics remain unchanged;
- PostgreSQL remains the critical readiness dependency.

Expected recovery:

```text
postgres healthy
  -> api starts
  -> migrations/start command runs under existing contract
  -> /health = LIVE
  -> /ready = READY / DATABASE_OK
```

Restart policy MUST NOT be used to reinterpret a `503 NOT_READY` as success.

### web

Required:

- restart policy: `unless-stopped`;
- existing `HOSTNAME=0.0.0.0` remains unchanged;
- existing `PORT=3000` remains unchanged;
- existing dependency on `api` remains unchanged unless a separate governed change is justified.

Expected recovery:

```text
api available
  -> web starts
  -> web listens on 0.0.0.0:3000
  -> Compose-network reachability returns
  -> Traefik public route becomes usable
```

## Intentional manual stop semantics

An operator may deliberately stop a service for maintenance or incident control.

The selected policy MUST preserve that intent:

- an intentionally stopped container is not treated as an unexpected failure;
- a later Docker daemon restart must not silently negate that deliberate stop under the intended `unless-stopped` semantics;
- resuming an intentionally stopped service remains an explicit operator action.

This behavior is one reason `unless-stopped` is preferred over `always`.

## Persistent failure semantics

Restart policy is not health recovery.

If a service repeatedly exits because of a persistent defect:

- Docker may attempt to restart it according to the selected policy;
- readiness must continue to expose failure;
- the VERTICAL-023 smoke must continue to fail when mandatory checks fail;
- no configuration rewrite is permitted;
- no automatic DSpace or VERTICAL-022 action is permitted.

024-B MUST NOT add an application-level loop that hides persistent failure.

## Dokploy interaction

Production currently uses a Dokploy-managed checkout and Compose project:

`catalog-assistant-frontend-zgzyco`

Known Dokploy behavior includes environment-specific mutation/injection of `compose.yaml` for routing labels and network membership in the deployment checkout.

Therefore 024-B and 024-C MUST distinguish:

1. repository source configuration;
2. Dokploy-transformed deployment configuration;
3. effective Docker runtime configuration.

Acceptance cannot rely on source text alone.

After deployment, the effective restart policy for each container MUST be inspected directly.

Expected effective value:

```text
postgres restart=unless-stopped
api      restart=unless-stopped
web      restart=unless-stopped
```

Equivalent Docker API/runtime representation is acceptable if semantically identical.

## Required non-production validation

024-B MUST provide at least:

1. YAML/Compose syntax validation;
2. an automated assertion that all three governed services declare `restart: unless-stopped`;
3. a regression test that fails if any governed service falls back to missing restart policy / `no`;
4. confirmation that the PostgreSQL volume declaration is unchanged;
5. confirmation that VERTICAL-023 health/readiness behavior is untouched.

Preferred validation command:

```bash
docker compose config
```

or an equivalent deterministic Compose validation in the available test environment.

If Docker/Compose is unavailable in CI, a YAML-level test may supplement local `docker compose config`, but production acceptance still requires effective runtime inspection.

## Required production observation before recovery test

Before the controlled Docker restart in 024-C, record:

- deployed commit SHA;
- `docker compose ps`;
- effective restart policy for each governed container;
- PostgreSQL health;
- API `/health`;
- API `/ready`;
- public frontend/API state;
- current governed production smoke result.

No secret-bearing environment dump is permitted.

## Mandatory production recovery test

024-C MUST perform a controlled restart of the Docker daemon.

After the restart event, the operator MUST NOT execute:

- `docker compose up`;
- `docker compose start`;
- `docker restart`;
- `docker start` for governed containers;
- Dokploy redeploy solely to restore the stack;
- any equivalent manual container-start action.

The acceptance path must prove that recovery comes from the configured policy.

A bounded wait/poll for observation is allowed.

## Post-restart acceptance sequence

After Docker restarts, verify in order:

1. all three governed containers return to running state;
2. PostgreSQL becomes healthy;
3. API `/health` returns `200 LIVE`;
4. API `/ready` returns `200 READY` with `DATABASE_OK`;
5. frontend is reachable through the Compose network;
6. public frontend succeeds;
7. public API health succeeds;
8. `scripts/production-smoke.sh` returns `RESULT PASS`;
9. smoke exit code is `0`;
10. VERTICAL-022 observation remains read-only.

## Host reboot

Host reboot remains optional for VERTICAL-024 acceptance.

If executed, it requires an explicit operational decision because the VPS hosts other workloads.

If not executed, durable evidence MUST record:

```text
HOST_REBOOT_TEST=NOT_TESTED
```

No inference from Docker daemon restart may be presented as host-reboot evidence.

## Explicitly out of scope

024-A and the later 024-B implementation do NOT authorize:

- changes to `/health`;
- changes to `/ready`;
- changes to VERTICAL-023 smoke semantics;
- application-level restart endpoints;
- health-triggered redeploy;
- Docker socket exposure to the application;
- Kubernetes;
- Swarm migration;
- systemd units for individual app services unless separately governed;
- watchdog scripts;
- cron-based restart loops;
- PostgreSQL HA;
- backup/restore changes;
- Traefik refactor;
- public domain changes;
- DSpace writes;
- VERTICAL-022 mutation;
- cataloging-semantic changes;
- changes to the 56 governed DSpace bindings.

## Security and governance invariants

1. Restart policy acts only at the container/deployment lifecycle layer.
2. DSpace remains read-only from operational checks.
3. VERTICAL-022 remains the sole authority for contract governance.
4. No secrets are added to source or output.
5. TLS verification remains enabled.
6. Existing PostgreSQL persistence is preserved.
7. VERTICAL-023 liveness/readiness semantics are preserved.
8. A running container is not automatically considered ready.
9. A restart loop does not count as recovery.
10. Production acceptance remains human and evidence-based.

## Expected 024-B files

A compliant 024-B implementation should normally change only:

- `compose.yaml`;
- one or more tests validating the Compose recovery policy;
- narrowly necessary documentation if required by the implementation contract.

If runtime application code, API endpoints, DSpace code, cataloging logic, or VERTICAL-022 implementation must change, STOP and request a new governed decision.

## 024-B acceptance criteria

024-B is ready for deployment review only if:

1. `postgres`, `api`, and `web` all declare `restart: unless-stopped`;
2. Compose configuration validates;
3. regression tests fail when a governed restart policy is absent or changed to `no`;
4. PostgreSQL volume mapping is unchanged;
5. existing healthcheck and dependency semantics remain intact;
6. no health/readiness code changes;
7. no DSpace/VERTICAL-022 changes;
8. diff is narrowly scoped;
9. implementation evidence reports exact branch, head SHA, changed files, and tests;
10. no merge occurs before review.

## Stop conditions

Stop 024-B implementation if:

- Dokploy demonstrably strips or overrides the restart policy in a way that cannot be fixed by the narrow Compose change;
- effective recovery would require a broader deployment redesign;
- PostgreSQL persistence would change;
- health/readiness would need reinterpretation;
- a custom watchdog/redeploy loop appears necessary;
- DSpace or VERTICAL-022 mutation would be required;
- secrets would need to be exposed;
- unrelated runtime changes become necessary.

A stop condition should produce evidence and a revised contract, not an ad hoc production workaround.

## Definition of Done for 024-A

024-A is complete when:

1. this contract is reviewed and merged;
2. `unless-stopped` is the explicit approved policy for all three governed services;
3. repository `compose.yaml` is designated as the versioned policy source;
4. Dokploy/runtime verification requirements are explicit;
5. intentional-stop and persistent-failure semantics are documented;
6. 024-B scope and tests are bounded;
7. no runtime/deployment change has been made by 024-A itself.

This contract authorizes only the subsequent bounded implementation of **VERTICAL-024-B — Deployment hardening**.
