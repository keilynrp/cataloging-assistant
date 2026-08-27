# VERTICAL-024 — Operational Recovery Acceptance

Status: **ACCEPTED / OPERATIONALIZED**

Acceptance date: **2026-08-27**

Production server timezone: **CEST (UTC+02:00)**

Parent specification: `docs/specs/VERTICAL-024-operational-recovery-restart-hardening.md`

Policy authority: `docs/governance/VERTICAL-024-A-RECOVERY-POLICY-CONTRACT.md`

Implementation authority: `docs/governance/VERTICAL-024-B-DEPLOYMENT-HARDENING-IMPLEMENTATION-CONTRACT.md`

Related issue: #58

## Acceptance decision

VERTICAL-024 is **ACCEPTED / OPERATIONALIZED**.

The production deployment recovered automatically after a controlled Docker daemon restart with no manual container-start or redeploy action after the restart event.

The final governed smoke passed with exit code 0 after recovery.

Production commit tested:

`8a3e155345b3aa6f94408da62897032aacbf0658`

## Production target

Dokploy-managed repository directory:

`/etc/dokploy/compose/catalog-assistant-frontend-zgzyco/code`

Compose project:

`catalog-assistant-frontend-zgzyco`

Governed services:

- `postgres`
- `api`
- `web`

## Deployment identity

Observed in production before the recovery test:

```text
git rev-parse HEAD
8a3e155345b3aa6f94408da62897032aacbf0658
```

Result: **deployment identity satisfactory**.

## Effective restart policy

Observed directly from Docker runtime before the recovery test:

```text
postgres restart=unless-stopped
api restart=unless-stopped
web restart=unless-stopped
```

This confirms that the policy governed in the repository survived Dokploy deployment transformation and was effective in Docker runtime.

## Pre-restart baseline

Compose state before the controlled Docker daemon restart:

```text
NAME                                           IMAGE                                   COMMAND                  SERVICE    CREATED         STATUS                   PORTS
catalog-assistant-frontend-zgzyco-api-1        catalog-assistant-frontend-zgzyco-api   "sh -c 'alembic upgr…"   api        9 minutes ago   Up 8 minutes             8000/tcp
catalog-assistant-frontend-zgzyco-postgres-1   postgres:17-alpine                      "docker-entrypoint.s…"   postgres   9 minutes ago   Up 8 minutes (healthy)   5432/tcp
catalog-assistant-frontend-zgzyco-web-1        catalog-assistant-frontend-zgzyco-web   "docker-entrypoint.s…"   web        8 minutes ago   Up 8 minutes             3000/tcp
```

PostgreSQL baseline:

```text
postgres status=running health=healthy restart=unless-stopped
```

API liveness baseline:

```text
HTTP_STATUS=200
{"status":"LIVE","dspace_mode":"read-only"}
```

API readiness baseline:

```text
HTTP_STATUS=200
{"status":"READY","components":[{"name":"database","status":"READY","detail_code":"DATABASE_OK"}]}
```

Governed smoke before restart:

```text
PASS compose_services
PASS api_liveness
PASS api_readiness
PASS web_internal
PASS public_frontend
PASS public_api
WARN dspace_contract SYNCED
RESULT PASS
SMOKE_EXIT=0
```

Result: production was healthy before the recovery event.

## Controlled Docker daemon restart

Observed timestamp before restart:

```text
2026-08-27T09:41:05+02:00
```

Docker daemon active timestamp before restart:

```text
ActiveEnterTimestamp=Thu 2026-08-27 06:32:39 CEST
```

Controlled command executed:

```bash
systemctl restart docker
```

Observed timestamp after restart:

```text
2026-08-27T09:44:27+02:00
```

Docker daemon active timestamp after restart:

```text
ActiveEnterTimestamp=Thu 2026-08-27 09:42:36 CEST
```

The changed `ActiveEnterTimestamp` confirms that the Docker daemon actually restarted during the acceptance session.

## No manual recovery intervention

After `systemctl restart docker`, no manual Catalog Assistant recovery action was used.

Specifically, the acceptance path did **not** execute:

- `docker compose up`
- `docker compose start`
- `docker start` for the governed containers
- `docker restart`
- Dokploy redeploy to restore the stack
- ad hoc `docker update --restart`
- manual Compose restart-policy edits
- Dokploy UI changes to recover the stack

The observed recovery therefore came from the governed `restart: unless-stopped` policy.

## Automatic post-restart recovery

Compose observation after Docker restarted:

```text
catalog-assistant-frontend-zgzyco-api-1        ...   api        ...   Up About a minute             8000/tcp
catalog-assistant-frontend-zgzyco-postgres-1   ...   postgres   ...   Up About a minute (healthy)   5432/tcp
catalog-assistant-frontend-zgzyco-web-1        ...   web        ...   Up About a minute             3000/tcp
```

Effective runtime state:

```text
postgres status=running health=healthy restart=unless-stopped
api status=running restart=unless-stopped
web status=running restart=unless-stopped
```

Result: all governed services recovered automatically.

## PostgreSQL recovery

PostgreSQL returned to:

```text
status=running
health=healthy
restart=unless-stopped
```

The existing persistent volume mapping was not changed by VERTICAL-024-B, and no database re-initialization or persistence migration was performed during acceptance.

## API liveness after recovery

Observed after the Docker daemon restart:

```text
HTTP_STATUS=200
{"status":"LIVE","dspace_mode":"read-only"}
```

Result: **PASS**.

VERTICAL-023 liveness semantics remained unchanged.

## API readiness after recovery

Observed after the Docker daemon restart:

```text
HTTP_STATUS=200
{"status":"READY","components":[{"name":"database","status":"READY","detail_code":"DATABASE_OK"}]}
```

Result: **PASS**.

This confirms PostgreSQL-backed readiness recovered correctly.

## Final governed production smoke

Invocation:

```bash
COMPOSE="docker compose -p catalog-assistant-frontend-zgzyco" \
  bash scripts/production-smoke.sh; rc=$?; echo "SMOKE_EXIT=$rc"
```

Observed output:

```text
PASS compose_services
PASS api_liveness
PASS api_readiness
PASS web_internal
PASS public_frontend
PASS public_api
WARN dspace_contract SYNCED
RESULT PASS
SMOKE_EXIT=0
```

Disposition:

- all mandatory checks passed;
- internal web reachability passed;
- public frontend passed;
- public API passed;
- smoke result was `PASS`;
- process exit code was `0`;
- `WARN dspace_contract SYNCED` remained a non-blocking read-only observation under the established VERTICAL-023 policy.

## VERTICAL-022 / DSpace safety

During the recovery acceptance path:

- DSpace remained read-only;
- no DSpace write was performed;
- no VERTICAL-022 approve action occurred;
- no resolve-evidence action occurred;
- no promote action occurred;
- no snapshot was created by the acceptance path;
- no ACTIVE baseline was changed;
- no cataloging-semantic change occurred.

The DSpace contract state was only observed through the existing governed smoke.

## Security confirmation

During the accepted run:

- no secrets were intentionally printed;
- no environment dump was captured;
- TLS verification was not disabled;
- no credentials or connection strings were added to the acceptance artifact;
- no Docker socket was exposed to application services;
- no watchdog, cron restart loop, or health-triggered redeploy was introduced.

## Host reboot status

```text
HOST_REBOOT_TEST=NOT_TESTED
```

A full host reboot was not executed.

This is non-blocking under the VERTICAL-024 specification because controlled Docker daemon restart is the mandatory acceptance case; host reboot is secondary and may remain `NOT TESTED` when a reboot would affect other workloads on the shared VPS.

No claim is made that host-reboot recovery has been empirically validated.

## Residual risks

The following remain outside the accepted scope:

- full host-reboot recovery has not been tested;
- no formal RTO/SLO has been established;
- no multi-host failover or PostgreSQL HA exists;
- no dedicated alerting/observability platform is introduced by VERTICAL-024.

These are non-blocking for the accepted scope.

## Final determination

All mandatory VERTICAL-024 acceptance criteria are satisfied:

- restart policy is explicit and versioned;
- effective runtime policy is `unless-stopped` for `postgres`, `api`, and `web`;
- controlled Docker daemon restart was executed and evidenced;
- no manual stack-start or redeploy action was required afterward;
- PostgreSQL recovered healthy;
- API liveness recovered;
- API readiness recovered with `DATABASE_OK`;
- internal frontend reachability passed;
- public frontend and API passed;
- governed production smoke returned `RESULT PASS`;
- smoke exited `0`;
- VERTICAL-022 remained read-only;
- no DSpace or governance mutation occurred;
- durable evidence is recorded here.

**Decision: ACCEPTED / OPERATIONALIZED.**
