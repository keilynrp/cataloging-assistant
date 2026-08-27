# VERTICAL-023-C — Operational Acceptance Contract

Status: **Ready for execution**

Parent specification: `docs/specs/VERTICAL-023-production-readiness-operational-health.md`

Baseline: `main` @ `5772f8a340860d857f0d25f0dd94407721743be7`

## Purpose

Close VERTICAL-023 with durable, reviewable production evidence.

023-C adds **no new runtime feature**. It validates the already-merged 023-A liveness/readiness model and 023-B deployment smoke against the real production deployment, records the evidence, and only then authorizes the lifecycle transition of VERTICAL-023 to `Accepted / Operationalized`.

## Authority and precedence

Execution MUST comply with:

1. `AGENTS.md`;
2. `docs/specs/VERTICAL-023-production-readiness-operational-health.md`;
3. `docs/governance/VERTICAL-023-A-IMPLEMENTATION-CONTRACT.md`;
4. `docs/governance/VERTICAL-023-B-IMPLEMENTATION-CONTRACT.md`;
5. VERTICAL-022 governance and operational acceptance artifacts;
6. the deployed production topology and current Dokploy/Compose contract.

If production evidence contradicts a previous assumption, stop acceptance and record the failure. Do not edit runtime behavior inside 023-C to make acceptance pass.

## In scope

023-C may only:

- verify that the intended commit is deployed;
- execute the repository-managed production smoke test manually;
- capture exact smoke output and exit code;
- capture API `/health` and `/ready` observations;
- capture internal `api -> web:3000` reachability as represented by the smoke;
- capture public frontend/API observations;
- capture VERTICAL-022 status read-only;
- record warnings/exceptions and their human disposition;
- create/update the durable acceptance artifact;
- update the canonical vertical index **only after acceptance evidence is complete and satisfactory**.

Expected durable evidence artifact:

`docs/vertical-023-operational-acceptance.md`

## Explicitly out of scope

Do NOT:

- add or modify runtime features;
- change `/health` or `/ready`;
- modify `scripts/production-smoke.sh` unless a defect is discovered, in which case stop 023-C and fix it in a separate governed PR;
- change frontend behavior;
- change Compose/Dokploy/Traefik configuration;
- restart/redeploy automatically;
- install cron/schedulers;
- mutate DSpace;
- approve, resolve, promote, supersede, or create VERTICAL-022 snapshots;
- alter the ACTIVE DSpace baseline;
- change cataloging semantics;
- change the 56 governed bindings;
- change `dspace-cataloger`;
- mark VERTICAL-023 accepted when any mandatory smoke check fails.

## Production identity requirement

Acceptance evidence MUST identify the production code under test.

Record at minimum:

- expected repository commit SHA;
- deployed repository commit SHA when observable;
- whether they match;
- production URLs tested.

Target accepted baseline begins from:

`5772f8a340860d857f0d25f0dd94407721743be7`

If production is not deployed at that commit or a known descendant containing 023-A and 023-B, stop acceptance and report `DEPLOYMENT_COMMIT_MISMATCH`.

Do not infer deployed version from image age or container uptime alone.

## Production execution

Run from the Dokploy-managed repository directory:

`/etc/dokploy/compose/catalog-assistant-frontend-zgzyco/code`

Use the existing Compose project:

`catalog-assistant-frontend-zgzyco`

Recommended invocation:

```bash
cd /etc/dokploy/compose/catalog-assistant-frontend-zgzyco/code

COMPOSE="docker compose -p catalog-assistant-frontend-zgzyco" \
  bash scripts/production-smoke.sh
```

Do not pass secrets on the command line.

## Mandatory production evidence

A successful 023-C acceptance requires evidence for all of the following:

1. expected Compose services are running;
2. API internal liveness passes;
3. API internal readiness passes;
4. `web:3000` is reachable from another Compose-network context;
5. public frontend passes;
6. public API health passes;
7. smoke returns `RESULT PASS`;
8. smoke process exit code is `0`;
9. no secret values appear in captured output;
10. VERTICAL-022 is only observed read-only;
11. no DSpace or governance mutation occurs during acceptance.

A VERTICAL-022 observational warning may coexist with `RESULT PASS` only if it is allowed by 023-B policy and is explicitly recorded and accepted by the human reviewer.

## Expected evidence shape

Capture the smoke output verbatim enough to preserve stable operational lines such as:

```text
PASS compose_services
PASS api_liveness
PASS api_readiness
PASS web_internal
PASS public_frontend
PASS public_api
WARN dspace_contract <status>
RESULT PASS
```

Do not capture environment dumps, credentials, tokens, full connection strings, or raw sensitive payloads.

## Health/readiness evidence

Record the observed semantics separately:

### API liveness

Expected:

```text
GET /health
HTTP 200
status = LIVE
```

### API readiness

Expected:

```text
GET /ready
HTTP 200
status = READY
database = READY
detail_code = DATABASE_OK
```

The acceptance artifact may reference the smoke output for these observations if the evidence is unambiguous.

## Public endpoint evidence

Record:

- frontend URL checked;
- API URL checked;
- final HTTP outcome;
- whether redirects were followed successfully;
- absence of final 502/503/terminal 3xx.

Current production defaults:

- `https://catalog.inbounduxd.com/`
- `https://api.catalog.inbounduxd.com/health`

Do not disable TLS verification.

## VERTICAL-022 observation

Record the read-only contract status returned through the existing status surface.

Acceptable handling:

- healthy/synced status: record as informational PASS;
- degraded/review-required/baseline-required/unobservable status: record as WARN and state explicitly whether it is acceptable for VERTICAL-023 under the current policy.

Never turn this observation into:

- approve;
- resolve-evidence;
- promote;
- snapshot creation;
- baseline mutation;
- DSpace write.

## Evidence artifact requirements

Create:

`docs/vertical-023-operational-acceptance.md`

It MUST contain:

- title and VERTICAL-023 identifier;
- acceptance date/time and timezone;
- production commit tested;
- production URLs tested;
- exact smoke invocation;
- smoke exit code;
- representative complete PASS/WARN/FAIL output;
- `/health` observation;
- `/ready` observation;
- internal web reachability result;
- public frontend/API result;
- VERTICAL-022 observed status;
- warning disposition;
- confirmation of no DSpace writes;
- confirmation of no VERTICAL-022 mutation;
- confirmation of no secret exposure;
- reviewer/operator identity only if appropriate for the repository;
- explicit acceptance decision;
- residual risks or known non-blocking limitations.

Do not fabricate evidence. If a datum was not observed, mark it `NOT OBSERVED` and do not accept until mandatory evidence is complete.

## Acceptance decision

### ACCEPT

Allowed only if:

- every mandatory production smoke check passed;
- smoke exit code is 0;
- production commit identity is satisfactory;
- no stop condition occurred;
- warnings are explicitly reviewed and non-blocking;
- no mutation or secret exposure occurred.

### REJECT / NOT ACCEPTED

Required if:

- any mandatory check failed;
- smoke returned non-zero;
- deployed commit cannot be reconciled;
- a secret appeared in output;
- acceptance required a runtime/config mutation;
- VERTICAL-022/DSpace was mutated by the acceptance path;
- evidence is incomplete for a mandatory criterion.

A failed 023-C attempt should be recorded as evidence but MUST NOT update the lifecycle status to accepted.

## Canonical index update

Only after a successful acceptance artifact exists, update:

`docs/specs/README.md`

from:

`VERTICAL-023 ... See specification`

to:

`VERTICAL-023 ... Accepted / Operationalized`

Also update the “Current operational milestone” prose so it no longer says VERTICAL-023 is not yet accepted.

The index update and acceptance artifact should preferably live in the same acceptance PR so the lifecycle claim is directly supported by the evidence.

## Validation before PR

Before opening the acceptance PR:

1. confirm the acceptance artifact contains all mandatory fields;
2. confirm the smoke evidence shows `RESULT PASS` and exit 0;
3. confirm the tested commit;
4. confirm no secrets are present;
5. confirm no runtime/application files are changed;
6. confirm only acceptance documentation/index lifecycle metadata is modified.

## Expected files for successful 023-C

Normally only:

- `docs/vertical-023-operational-acceptance.md`;
- `docs/specs/README.md`.

If any runtime/script/application file must change, STOP. That is not 023-C and requires a separate governed fix before re-attempting acceptance.

## Stop conditions

Stop and report before acceptance if any of the following occurs:

- production is not on the expected governed implementation;
- any mandatory smoke check fails;
- `RESULT FAIL` or non-zero exit;
- public 502/503/terminal 3xx;
- `/ready` returns 503;
- `web:3000` is internally unreachable;
- secret exposure;
- TLS verification would need to be disabled;
- runtime/config must be modified to make the smoke pass;
- DSpace write would be required;
- VERTICAL-022 mutation would be required;
- acceptance evidence is incomplete.

## Definition of Done for 023-C

023-C is complete only when:

1. production runs the governed 023-B smoke;
2. all mandatory checks pass;
3. smoke exits 0;
4. production evidence is durable in `docs/vertical-023-operational-acceptance.md`;
5. warnings are human-reviewed;
6. no secrets or mutations occurred;
7. the acceptance PR contains only evidence/lifecycle documentation;
8. the canonical index marks VERTICAL-023 `Accepted / Operationalized`.

Until all eight conditions are met, VERTICAL-023 remains `See specification`.

This contract authorizes only **VERTICAL-023-C — Operational acceptance**.
