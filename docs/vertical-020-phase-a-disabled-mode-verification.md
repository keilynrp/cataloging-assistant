# VERTICAL-020 — Phase A Disabled-Mode Deployment Verification

Status: **PASS — DEPLOYED / FEATURE DISABLED / NOT OPERATIONALLY ACCEPTED**

Parent specification: `docs/specs/VERTICAL-020-secure-remote-evidence-fetch.md`

Acceptance contract: `docs/governance/VERTICAL-020-OPERATIONAL-ACCEPTANCE-CONTRACT.md`

Related issue: #64

## Decision

VERTICAL-020 Phase A is **PASS**.

The merged implementation is deployed in production and the remote-fetch capability is inert because `EVIDENCE_REMOTE_FETCH_ENABLED=False`.

This artifact does **not** promote VERTICAL-020 to `Accepted / Operationalized`.

The canonical lifecycle remains:

```text
See specification
```

Phase B remains unauthorised until an explicit human decision enables a controlled production acceptance run.

## Production identity

Observed production commit:

```text
01b600380f1ee91bc42c63e18a64e5bb752b85c5
```

Result: **PASS**.

## Effective feature-flag state

Observed from the running API container:

```text
EVIDENCE_REMOTE_FETCH_ENABLED=False
```

Result: **PASS**.

The feature is deployed but disabled.

## Disabled-mode endpoint verification

A dedicated evidence session was created successfully:

```text
CREATE_STATUS=200
SESSION_ID=a13d6f79-dafe-46e7-85ec-edc70e8b7aba
```

A remote-fetch request was then attempted against that session while the feature flag remained OFF.

Observed result:

```text
REMOTE_STATUS=403
REMOTE_BODY={"detail":"remote_fetch_disabled"}
```

Result: **PASS**.

The implementation gate in `add_remote_evidence_source` checks `evidence_remote_fetch_enabled` before calling the remote fetch layer. Therefore this disabled-mode request is rejected before DNS resolution or outbound HTTP fetch.

## API liveness

Observed after the disabled-mode check:

```text
HTTP_STATUS=200
{"status":"LIVE","dspace_mode":"read-only"}
```

Result: **PASS**.

## API readiness

Observed after the disabled-mode check:

```text
HTTP_STATUS=200
{"status":"READY","components":[{"name":"database","status":"READY","detail_code":"DATABASE_OK"}]}
```

Result: **PASS**.

## Governed production smoke

Observed:

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

Result: **PASS**.

The non-blocking `WARN dspace_contract SYNCED` remains governed by VERTICAL-023 semantics.

## DSpace / VERTICAL-022 safety

Phase A did not:

- write to DSpace;
- approve, promote, resolve, or supersede a VERTICAL-022 snapshot;
- change the ACTIVE DSpace baseline;
- modify cataloging semantics;
- change the governed 56 bindings.

DSpace remained read-only.

## Network-safety interpretation

Phase A does not claim full production validation of the enabled remote-fetch path.

It demonstrates only:

- the implementation is deployed;
- the effective production feature flag is OFF;
- the remote-fetch endpoint exists;
- an explicit remote-fetch request fails closed with `403 remote_fetch_disabled`;
- the feature-disabled gate precedes the outbound fetch layer;
- normal production liveness/readiness/smoke remain healthy.

No live positive remote fetch was executed.

No live SSRF rejection matrix was executed beyond the disabled gate.

## Lifecycle state after Phase A

```text
IMPLEMENTED / MERGED
DEPLOYED
FEATURE_DISABLED
PHASE_A=PASS
OPERATIONAL_ACCEPTANCE=NOT_GRANTED
CANONICAL_INDEX=See specification
```

## Phase B gate

Phase B requires a separate explicit human authorization because it changes effective production behavior:

```text
EVIDENCE_REMOTE_FETCH_ENABLED=false
  ->
EVIDENCE_REMOTE_FETCH_ENABLED=true
```

Until that authorization occurs:

- remote fetch remains disabled;
- no lifecycle promotion is allowed;
- VERTICAL-021 remains blocked unless a separate governance decision explicitly allows it to proceed without remote-fetch enablement.

## Final determination

**VERTICAL-020 Phase A: PASS.**

**VERTICAL-020 operational acceptance: NOT YET GRANTED.**

**Production remote fetch: DISABLED.**
