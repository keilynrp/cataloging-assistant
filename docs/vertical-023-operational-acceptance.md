# VERTICAL-023 — Operational Acceptance

Status: **ACCEPTED / OPERATIONALIZED**

Acceptance date/time: **2026-08-27 00:46 America/Mexico_City**

Parent specification: `docs/specs/VERTICAL-023-production-readiness-operational-health.md`

Operational acceptance contract: `docs/governance/VERTICAL-023-C-OPERATIONAL-ACCEPTANCE-CONTRACT.md`

## Acceptance decision

VERTICAL-023 is **ACCEPTED / OPERATIONALIZED**.

The deployed production revision contains the governed VERTICAL-023-A liveness/readiness implementation, VERTICAL-023-B production smoke, and the corrective VERTICAL-023-B stdin fix discovered during operational acceptance.

Production commit tested:

`b399bfee500ae369a2084d90716efdc31756aaaf`

This is a known governed descendant of the VERTICAL-023-C acceptance baseline and includes PR #56, which closes stdin explicitly in `run_capture()` so `docker compose exec -T` cannot inherit an open orchestrator/SSH stdin and block the smoke sequence.

## Production target

Dokploy-managed repository directory:

`/etc/dokploy/compose/catalog-assistant-frontend-zgzyco/code`

Compose project:

`catalog-assistant-frontend-zgzyco`

Production URLs tested:

- Frontend: `https://catalog.inbounduxd.com/`
- API health: `https://api.catalog.inbounduxd.com/health`

TLS verification remained enabled.

## Deployment identity evidence

Observed in production:

```text
git rev-parse HEAD
b399bfee500ae369a2084d90716efdc31756aaaf
```

Result: **deployment commit identity satisfactory**.

## Final production smoke

Invocation:

```bash
COMPOSE="docker compose -p catalog-assistant-frontend-zgzyco" bash scripts/production-smoke.sh; rc=$?; echo "SMOKE_EXIT=$rc"
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

- all mandatory production checks passed;
- smoke result was `PASS`;
- process exit code was `0`;
- the VERTICAL-022 observation was read-only;
- `WARN dspace_contract SYNCED` is accepted as non-blocking under the VERTICAL-023-B/C policy because DSpace contract state is observable/degradable but not a default readiness dependency.

## API liveness evidence

Observed directly in the production API container:

```text
HTTP 200
{"status":"LIVE","dspace_mode":"read-only"}
```

Interpretation: API process liveness is operational and remains independent of DSpace availability.

## API readiness evidence

Observed directly in the production API container:

```text
HTTP 200
{"status":"READY","components":[{"name":"database","status":"READY","detail_code":"DATABASE_OK"}]}
```

Interpretation: the API is ready and the critical PostgreSQL dependency is reachable.

## Internal web reachability

The governed smoke reported:

```text
PASS web_internal
```

This satisfies the requirement that the frontend be reachable on `web:3000` from another Compose-network context rather than only from inside the web container itself.

## Public endpoint evidence

Frontend observation:

```text
FRONTEND_HTTP=200
```

API public health observation:

```json
{"status":"LIVE","dspace_mode":"read-only"}
```

The final governed smoke subsequently reported both:

```text
PASS public_frontend
PASS public_api
```

No final 502, 503, or terminal redirect status was observed in the accepted run.

## VERTICAL-022 observation

Observed by the governed smoke:

```text
WARN dspace_contract SYNCED
```

Human disposition: **accepted as non-blocking**.

No VERTICAL-022 approve, resolve-evidence, promote, snapshot creation, baseline mutation, or DSpace write was performed by the acceptance path.

## Corrective finding discovered during acceptance

An earlier production acceptance attempt exposed a defect in VERTICAL-023-B: `run_capture()` inherited stdin while capturing `docker compose exec -T ...` through command substitution. In the production SSH/orchestrator context, that inherited open stdin could block the probe after `PASS compose_services`.

The defect was isolated with production evidence:

- the health probe completed directly;
- the same probe completed when redirected to a regular file;
- the same probe completed inside command substitution when stdin was explicitly closed with `</dev/null`.

The corrective change was governed separately in PR #56 and merged before this final acceptance run. The accepted production commit includes that fix.

This corrective step did not alter health/readiness semantics, smoke checks, timeouts, PASS/WARN/FAIL policy, DSpace behavior, VERTICAL-022 governance, frontend behavior, Compose topology, or Dokploy configuration.

## Previous failed / incomplete attempts

Prior attempts are not treated as acceptance evidence:

1. A production run failed because the Catalog Assistant Compose services were stopped after the Docker daemon restarted.
2. A later run exposed the stdin-blocking smoke defect described above and was stopped pending the separate corrective PR.
3. Only the final clean run on `b399bfee500ae369a2084d90716efdc31756aaaf` is used for the ACCEPT decision.

## Safety and mutation confirmation

During the accepted run:

- no DSpace write was performed;
- no VERTICAL-022 governance mutation was performed;
- no ACTIVE baseline was changed;
- no runtime/application/configuration mutation was required to make the accepted smoke pass;
- TLS verification was not disabled;
- no secret value was observed in captured acceptance output.

## Residual operational risk

A separate non-blocking operational risk was discovered before the final run: the Catalog Assistant containers had Docker restart policy `restart=no` and did not recover automatically after the Docker daemon restarted.

The stack was recovered manually before the accepted run.

This does **not** block VERTICAL-023 acceptance because automatic restart/self-healing is outside the acceptance contract. It should be addressed in a separate governed operational-hardening change rather than folded into VERTICAL-023-C.

## Final determination

All mandatory VERTICAL-023-C evidence is complete and satisfactory:

- production commit identity verified;
- Compose services operational;
- API liveness passed;
- API readiness passed;
- PostgreSQL readiness passed;
- internal frontend reachability passed;
- public frontend passed;
- public API passed;
- smoke returned `RESULT PASS`;
- smoke exited `0`;
- VERTICAL-022 was observed read-only;
- warning disposition was explicitly reviewed;
- no DSpace/VERTICAL-022 mutation occurred;
- no secret exposure was observed.

**Decision: ACCEPTED / OPERATIONALIZED.**
