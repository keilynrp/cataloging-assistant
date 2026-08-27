# VERTICAL-020 — Operational Acceptance

Status: **Accepted / Operationalized**

Acceptance date: **2026-08-27**

Acceptance decision time: **2026-08-27 03:33 America/Mexico_City (UTC-06:00)**

Production evidence fetch time: **2026-08-27T09:20:44.606624+00:00**  
Equivalent local time: **2026-08-27 03:20:44 America/Mexico_City**

Parent specification: `docs/specs/VERTICAL-020-secure-remote-evidence-fetch.md`

Acceptance contract: `docs/governance/VERTICAL-020-OPERATIONAL-ACCEPTANCE-CONTRACT.md`

Related issue: #64

Implementation PR: #5

Phase A durable evidence: `docs/vertical-020-phase-a-disabled-mode-verification.md`

## Decision

VERTICAL-020 is **Accepted / Operationalized** for governed production use with remote evidence fetch enabled.

The accepted production state is:

```text
IMPLEMENTED / MERGED
DEPLOYED
FEATURE_ENABLED
PHASE_A=PASS
PHASE_B=PASS
OPERATIONAL_ACCEPTANCE=GRANTED
CANONICAL_INDEX=Accepted / Operationalized
```

This decision is based on bounded production verification plus the automated regression coverage already carried by the merged implementation.

The acceptance does not expand scope beyond the existing VERTICAL-020 specification and ADR-016 security model.

## Production identity

Observed production commit during Phase B:

```text
58d72df0ca160a6948cee389e326b423a522a06e
```

Result: **PASS**.

## Feature flag lifecycle

### Pre-enable state

Observed before Phase B activation:

```text
EVIDENCE_REMOTE_FETCH_ENABLED=False
EVIDENCE_REMOTE_FETCH_TIMEOUT_SECONDS=10.0
EVIDENCE_REMOTE_FETCH_MAX_BYTES=26214400
EVIDENCE_REMOTE_FETCH_MAX_REDIRECTS=3
EVIDENCE_REMOTE_FETCH_USER_AGENT=CatalogingAssistantEvidenceFetcher/1.0
```

### Enablement method

The production feature flag was changed through the governed Dokploy environment/deployment configuration path and applied through the normal redeploy/recreate mechanism.

Only this effective behavior change was authorized:

```text
EVIDENCE_REMOTE_FETCH_ENABLED=false
  ->
EVIDENCE_REMOTE_FETCH_ENABLED=true
```

No SSRF, DNS, redirect, MIME, size, timeout, DSpace, or agent-network policy was weakened or changed for acceptance.

### Effective post-enable state

Observed from the running API container:

```text
EVIDENCE_REMOTE_FETCH_ENABLED=True
```

Result: **PASS**.

## Phase A — disabled-mode verification

Phase A passed before production enablement.

Observed:

```text
CREATE_STATUS=200
REMOTE_STATUS=403
REMOTE_BODY={"detail":"remote_fetch_disabled"}
```

The feature-disabled gate is evaluated before the remote fetch layer, so the disabled request failed closed before DNS or outbound HTTP.

Health/readiness after the disabled-mode check:

```text
HTTP_STATUS=200
{"status":"LIVE","dspace_mode":"read-only"}

HTTP_STATUS=200
{"status":"READY","components":[{"name":"database","status":"READY","detail_code":"DATABASE_OK"}]}
```

Governed smoke:

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

Phase A result: **PASS**.

## Phase B — post-activation health gate

After `EVIDENCE_REMOTE_FETCH_ENABLED=True` became effective:

```text
HTTP_STATUS=200
{"status":"LIVE","dspace_mode":"read-only"}

HTTP_STATUS=200
{"status":"READY","components":[{"name":"database","status":"READY","detail_code":"DATABASE_OK"}]}
```

Governed production smoke remained:

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

## Positive production fetch

Dedicated acceptance session:

```text
SESSION_ID=ccf1c499-ba15-41fd-8d76-abd092712aa0
```

Controlled public target:

```text
https://example.com/
```

Observed:

```text
STATUS=200
KIND=remote
MEDIA_TYPE=text/html
EXTRACTION_STATUS=extracted
REQUESTED_URL=https://example.com/
FINAL_URL=https://example.com:443/
STATUS_CODE=200
RESPONSE_BODY_SHA256_PRESENT=True
DERIVED_TEXT_SHA256_PRESENT=True
REMOTE_FETCH_POLICY_VERSION=2026-08-16
EXTRACTOR=html_stdlib_parser
```

Result: **PASS**.

## Persisted provenance

A subsequent read-only inspection of the persisted remote source produced:

```text
REMOTE_SOURCE_COUNT=1
REQUESTED_URL=https://example.com/
FINAL_URL=https://example.com:443/
REDIRECT_CHAIN=[]
RESOLVED_IPS=['172.66.147.243', '104.20.23.154', '2606:4700:10::6814:179a', '2606:4700:10::ac42:93f3']
RESOLVED_HOPS=[{'url': 'https://example.com:443/', 'host': 'example.com', 'resolved_ips': ['172.66.147.243', '104.20.23.154', '2606:4700:10::6814:179a', '2606:4700:10::ac42:93f3']}]
STATUS_CODE=200
CONTENT_LENGTH=559
FETCHED_AT=2026-08-27T09:20:44.606624+00:00
RESPONSE_BODY_SHA256_PRESENT=True
DERIVED_TEXT_SHA256_PRESENT=True
REMOTE_FETCH_POLICY_VERSION=2026-08-16
EXTRACTOR=html_stdlib_parser
KIND=remote
MEDIA_TYPE=text/html
EXTRACTION_STATUS=extracted
```

Required provenance fields were therefore observed for the accepted positive source:

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

Result: **PASS**.

## Deterministic extraction and persistence

Before explicit extraction:

```text
REMOTE_SOURCE_COUNT_BEFORE=1
CANDIDATE_COUNT_BEFORE=0
```

After `POST /extract`:

```text
EXTRACT_STATUS=200
REMOTE_SOURCE_COUNT_AFTER=1
CANDIDATE_COUNT_AFTER=0
```

For `example.com`, zero candidates is the expected deterministic result because the source contains no supported explicit cataloging identifiers or field-value lines.

No DOI, ISSN, ISBN, or cataloging field was invented.

Result: **PASS**.

## Production-observed negative checks

### Loopback

Input:

```text
http://127.0.0.1/
```

Observed:

```text
STATUS=422
DETAIL=remote_target_not_public
```

Result: **PASS**.

### Cloud metadata literal

Input:

```text
http://169.254.169.254/
```

Observed:

```text
STATUS=422
DETAIL=remote_target_not_public
```

Result: **PASS**.

The test exercised policy rejection only. No internal service was created and no successful metadata connection is claimed.

### Non-HTTP(S) scheme

Input:

```text
ftp://example.com/file
```

Observed:

```text
STATUS=422
DETAIL=remote_url_invalid
```

Result: **PASS**.

### URL userinfo

Input:

```text
https://user:pass@example.com/
```

Observed:

```text
STATUS=422
DETAIL=remote_url_invalid
```

Result: **PASS**.

### Disallowed MIME

Input:

```text
https://httpbin.org/image/png
```

Observed:

```text
STATUS=422
BODY={"detail":"remote_content_type_not_allowed"}
```

Result: **PASS**.

### Final non-2xx response

Input:

```text
https://example.com/vertical-020-definitely-not-found
```

Observed:

```text
STATUS=502
DETAIL=remote_upstream_error
```

Result: **PASS**.

A final public `404` was not converted into persisted evidence.

## Stale-session disposition

A read-only production search for an already-stale evidence session returned:

```text
STALE_FOUND=0
```

No stale session existed naturally in production.

The project intentionally did **not** fabricate one by mutating a DSpace item, source hash, or production evidence record.

Therefore stale-session rejection is classified as:

```text
PRODUCTION_OBSERVED=NOT_REPRODUCED
AUTOMATED_REGRESSION_EVIDENCE=REQUIRED / RETAINED
BLOCKING=NO
```

This treatment follows the operational acceptance contract.

## Automated-only / intentionally not reproduced live

The following controls remain supported by the merged automated regression coverage and were not recreated with artificial production infrastructure during this acceptance:

- stale-session remote-fetch rejection;
- mixed public/private DNS answer rejection;
- redirect-to-private rejection;
- redirect loop rejection;
- redirect-limit rejection;
- streaming size-limit edge cases;
- remote PDF validation edge cases and timeout behavior.

The acceptance does not claim that these cases were observed live during this Phase B run.

## DNS-rebinding residual risk

VERTICAL-020 validates resolved addresses before each connection/redirect hop and records resolution provenance.

It does **not** implement TCP connection pinning to the prevalidated IP.

Therefore this acceptance does **not** claim complete DNS-rebinding immunity.

That residual risk remains explicitly governed by ADR-016 and is outside the accepted scope of this vertical.

## DSpace / VERTICAL-022 safety

Throughout Phase A and Phase B:

- DSpace remained read-only;
- no DSpace submission, workflow, administration, or metadata write occurred;
- no VERTICAL-022 ACTIVE baseline was approved, promoted, superseded, or otherwise mutated;
- the governed DSpace contract observation remained `SYNCED`;
- no cataloging contract binding was changed.

Result: **PASS**.

## Conversational-agent boundary

Operational acceptance did not add a network tool or remote-fetch capability to the conversational agent.

Remote evidence fetch remains a separate, explicit cataloger-triggered evidence workflow.

Result: **PASS**.

## Final post-test health/readiness/smoke

After all enabled-mode acceptance checks:

```text
HTTP_STATUS=200
{"status":"LIVE","dspace_mode":"read-only"}

HTTP_STATUS=200
{"status":"READY","components":[{"name":"database","status":"READY","detail_code":"DATABASE_OK"}]}

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

## Rollback readiness

The governed rollback remains:

1. set `EVIDENCE_REMOTE_FETCH_ENABLED=false` through Dokploy environment configuration;
2. apply the normal Dokploy redeploy/recreate;
3. verify `403 remote_fetch_disabled`;
4. verify `/health`;
5. verify `/ready`;
6. rerun `scripts/production-smoke.sh`.

No network-policy weakening is part of rollback.

## Warnings and limitations

- `WARN dspace_contract SYNCED` is the expected non-blocking VERTICAL-023 observation.
- No stale production session existed for live rejection testing.
- Redirect-to-private and mixed-DNS behavior were intentionally not reproduced live.
- A normal public redirect was not required for the minimum positive acceptance path and was not used in the accepted source; `redirect_chain=[]`.
- DNS-rebinding protection does not include TCP connection pinning.
- This acceptance does not authorize crawling, JavaScript execution, OCR, LLM extraction, DSpace writes, or agent network access.

## Human decision

The project owner explicitly authorized Phase B production enablement and controlled acceptance on 2026-08-27.

After reviewing the collected Phase A and Phase B evidence, VERTICAL-020 is accepted for governed production operation with remote fetch enabled.

## Final determination

```text
VERTICAL-020
IMPLEMENTED / MERGED
DEPLOYED
FEATURE_ENABLED
PHASE_A=PASS
PHASE_B=PASS
OPERATIONAL_ACCEPTANCE=GRANTED
LIFECYCLE=Accepted / Operationalized
```

**VERTICAL-020: ACCEPTED / OPERATIONALIZED.**
