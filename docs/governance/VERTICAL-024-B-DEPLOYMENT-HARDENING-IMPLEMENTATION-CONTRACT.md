# VERTICAL-024-B — Deployment Hardening Implementation Contract

Status: **Ready for implementation**

Parent specification: `docs/specs/VERTICAL-024-operational-recovery-restart-hardening.md`

Policy authority: `docs/governance/VERTICAL-024-A-RECOVERY-POLICY-CONTRACT.md`

Baseline: `main` @ `796b7017d71a1c8c12aadb578dfafcfc9e21bd85`

Related issue: #58

## Purpose

Implement the restart policy approved by VERTICAL-024-A with the smallest possible repository change.

024-B is limited to deployment configuration hardening and regression coverage. It does not perform production acceptance; that belongs to 024-C.

## Required implementation

Update repository `compose.yaml` so these three services explicitly declare:

```yaml
restart: unless-stopped
```

Required services:

- `postgres`;
- `api`;
- `web`.

No governed service may omit the restart policy.

## Expected diff

A compliant implementation should normally change only:

- `compose.yaml`;
- one test file dedicated to deployment/Compose policy validation.

If a narrowly necessary test fixture/helper must change, document why.

Do not change application runtime files merely to test Compose policy.

## Preserve exactly

The implementation MUST preserve the following existing behavior and configuration.

### postgres

Preserve:

- image `postgres:17-alpine`;
- environment keys/defaults;
- volume `cataloging_postgres:/var/lib/postgresql/data`;
- existing healthcheck command;
- healthcheck interval, timeout, and retries.

### api

Preserve:

- build context `./apps/api`;
- `.env` usage;
- existing `DATABASE_URL` semantics;
- expose port `8000`;
- `depends_on.postgres.condition=service_healthy`;
- all VERTICAL-023 `/health` and `/ready` behavior.

### web

Preserve:

- build context `./apps/web`;
- current build args;
- `HOSTNAME=0.0.0.0`;
- `PORT=3000`;
- current API URL variables;
- expose port `3000`;
- dependency on `api`.

## Forbidden changes

024-B MUST NOT:

- modify `/health`;
- modify `/ready`;
- modify `scripts/production-smoke.sh`;
- alter PASS/WARN/FAIL semantics;
- add health-triggered restarts;
- add watchdog scripts;
- add cron restart jobs;
- expose Docker socket to the application;
- modify Dokploy labels/networks in repository source;
- refactor Traefik;
- change public domains;
- modify PostgreSQL persistence;
- add DSpace writes;
- mutate VERTICAL-022;
- change cataloging semantics;
- change the 56 governed DSpace bindings;
- add unrelated dependencies;
- mark VERTICAL-024 accepted.

## Test requirements

Implementation MUST add deterministic regression coverage proving the policy is present and stable.

At minimum, tests must verify:

1. `postgres.restart == "unless-stopped"`;
2. `api.restart == "unless-stopped"`;
3. `web.restart == "unless-stopped"`;
4. no governed service has restart missing, null, or `no`;
5. PostgreSQL volume mapping remains exactly `cataloging_postgres:/var/lib/postgresql/data`;
6. PostgreSQL healthcheck remains present;
7. API dependency on healthy PostgreSQL remains present;
8. web `HOSTNAME` and `PORT` remain `0.0.0.0` / `3000`.

The tests should fail if a future change removes or weakens the restart policy.

## Validation

Run, when available:

```bash
docker compose config
```

This command must complete successfully.

Also run the targeted test suite for the new Compose policy assertions.

If Docker Compose is unavailable in the implementation environment:

- report that explicitly;
- still run a deterministic YAML/configuration-level test;
- do not claim Compose runtime validation passed.

## Preferred test location

Prefer a focused repository-level or API test file whose purpose is clear, for example:

`apps/api/tests/test_compose_recovery_policy.py`

An equivalent existing deployment-config test file is acceptable if one already exists.

Do not mix these assertions into unrelated domain/cataloging tests.

## Implementation evidence

The implementation PR must report:

- branch name;
- PR number/URL;
- exact head SHA;
- base SHA;
- changed files;
- diff stat;
- validation commands executed;
- tests passed/failed/skipped;
- whether `docker compose config` was actually executed;
- confirmation that tests fail against the pre-fix Compose state;
- confirmation that no health/readiness/DSpace/VERTICAL-022/runtime files changed.

## Regression proof

At least one new test must be demonstrated to fail against the baseline `compose.yaml` where restart policy is absent and pass after the change.

A structural test that merely checks for the literal string is acceptable only if it parses the Compose YAML/service structure sufficiently to prevent false positives in comments or unrelated text.

Prefer parsed YAML semantics.

## Production deployment boundary

024-B ends at a reviewed and merged implementation.

Do not perform the controlled Docker daemon restart as part of 024-B.

After merge and deploy, first verify the effective runtime policy:

```text
postgres restart=unless-stopped
api      restart=unless-stopped
web      restart=unless-stopped
```

Only then may 024-C execute the governed recovery test.

## Dokploy guard

Repository source is authoritative for restart policy, but Dokploy may transform the deployment checkout.

If production inspection after deployment shows any governed service with:

```text
restart=no
```

or any value semantically weaker/different than `unless-stopped`, STOP.

Do not compensate manually with `docker update --restart`, ad hoc Compose edits, or Dokploy UI changes inside 024-C.

Instead, return to governance with evidence showing where the policy was lost or overridden.

## Security and governance invariants

1. No DSpace writes.
2. No VERTICAL-022 mutation.
3. No secret exposure.
4. No runtime endpoint changes.
5. No readiness reinterpretation.
6. No automatic configuration rewrite.
7. PostgreSQL persistence remains unchanged.
8. Restart policy does not constitute readiness.
9. A restart loop is not accepted as recovery.
10. Production acceptance remains a separate human-reviewed 024-C step.

## Acceptance criteria for 024-B

024-B is acceptable for merge only if:

1. all three governed services explicitly use `restart: unless-stopped`;
2. Compose/YAML validation passes;
3. regression tests cover all three services;
4. a regression test is shown to fail against the pre-change baseline;
5. PostgreSQL volume mapping is unchanged;
6. existing healthcheck/dependency semantics are unchanged;
7. web bind invariants remain unchanged;
8. no health/readiness code changes;
9. no smoke semantics changes;
10. no DSpace/VERTICAL-022 changes;
11. diff remains narrow;
12. no production acceptance claim is made.

## Stop conditions

STOP implementation and report evidence if:

- Dokploy requires a non-repository restart mechanism;
- `restart: unless-stopped` is rejected by the actual Compose version;
- deployment config validation exposes a broader incompatibility;
- preserving PostgreSQL persistence is not possible;
- runtime/application changes appear necessary;
- health/readiness changes appear necessary;
- a custom restart supervisor appears necessary;
- DSpace/VERTICAL-022 mutation would be involved;
- unrelated deployment refactor becomes necessary.

## Definition of Done for 024-B

024-B is complete when:

1. the bounded implementation PR is reviewed and merged;
2. the restart policy is versioned in `compose.yaml`;
3. regression coverage protects all three services;
4. Compose/config validation evidence exists;
5. no prohibited scope changes occurred;
6. VERTICAL-024 remains `See specification` pending 024-C;
7. production recovery has not yet been declared accepted.

This contract authorizes only **VERTICAL-024-B — Deployment hardening**.
