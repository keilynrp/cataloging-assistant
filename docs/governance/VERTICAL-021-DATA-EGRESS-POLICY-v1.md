# VERTICAL-021 — Provider / Data Egress Policy v1

Status: **APPROVED POLICY — enforcement implementation pending**

Policy ID: `vertical-021-data-egress-v1`

Policy version: **1.0.0**

Approval date: **2026-08-27**

Parent specification: `docs/specs/VERTICAL-021-provider-independent-llm-assisted-extraction.md`

Pre-implementation gates contract: `docs/governance/VERTICAL-021-PRE-IMPLEMENTATION-GATES-CONTRACT.md`

Related issue: #69

## 1. Purpose

Define the only data-egress policy under which a future VERTICAL-021 provider adapter may be called.

This policy is provider-neutral and fail-closed.

It governs **whether already-governed textual evidence may leave the Cataloging Assistant process boundary for LLM inference**.

It does not authorize implementation, credentials, provider integration, or production traffic by itself.

## 2. Current authorization state

At policy creation:

```text
POLICY_APPROVED=YES
RUNTIME_ENFORCEMENT_IMPLEMENTED=NO
PROVIDER_ALLOWLIST=[]
REAL_PROVIDER_TRAFFIC_AUTHORIZED=NO
```

Because the provider/deployment allowlist is empty, every attempted external-provider decision under this policy must resolve to `DENY` until a later reviewed policy amendment explicitly adds an allowed deployment.

This is intentional.

Gate B may close on the existence of an approved, evaluable policy. Real-provider use remains separately blocked by the empty allowlist and by the absence of runtime enforcement.

## 3. Decision model

The runtime enforcement point must return exactly one provider-neutral decision:

- `ALLOW`
- `DENY`
- `INDETERMINATE`

Mandatory behavior:

```text
ALLOW         -> adapter call may proceed
DENY          -> fail closed; zero provider traffic
INDETERMINATE -> fail closed; zero provider traffic
```

No UI state, model response, provider SDK, request parameter, browser input, or evidence content may override the policy decision.

## 4. Enforcement position

The policy must be evaluated server-side **before**:

- provider client initialization that could create network traffic;
- construction of the final provider request body;
- provider DNS/network connection;
- transmission of any evidence fragment.

Required conceptual order:

```text
Evidence Session
  -> selected frozen textual fragments
  -> classify / redact / policy evaluate
  -> ALLOW?
       NO  -> fail closed, no adapter/network
       YES -> freeze exact authorized input manifest
             -> provider-neutral adapter
```

The provider adapter is downstream of the policy enforcement point and must not decide data eligibility.

## 5. Eligible source prerequisite

Only evidence already persisted in a governed Evidence Session is even eligible for policy evaluation.

The model may never receive:

- a live URL to fetch;
- browser cookies;
- DSpace credentials;
- raw authentication headers;
- unpersisted browser text;
- a raw PDF binary;
- an arbitrary local file path;
- direct database access.

Remote content must first pass VERTICAL-020 and exist as an immutable source snapshot.

PDF content must first pass VERTICAL-019 text extraction.

## 6. Data classification

Every fragment considered for egress must resolve to exactly one classification.

### E0 — PUBLIC_BIBLIOGRAPHIC_METADATA

Examples:

- title;
- author names already present in the bibliographic source;
- publication statement;
- DOI/ISSN/ISBN;
- public journal/book metadata;
- controlled-vocabulary labels;
- public language/subject terminology.

Policy posture: **eligible in principle**, subject to all other gates.

### E1 — PUBLIC_OPEN_TEXT

Textual evidence from a source that is publicly accessible and whose access/license context does not prohibit the contemplated external processing.

Examples:

- explicitly open-access article text;
- public institutional page text;
- public metadata descriptions;
- open-licensed excerpts.

Policy posture: **eligible in principle**, subject to minimization and all other gates.

### E2 — PUBLIC_TEXT_RIGHTS_UNCLEAR

Publicly reachable text for which the runtime/policy cannot establish that external processing is permitted under the configured institutional policy.

Policy posture: **DENY**.

Public reachability alone does not imply egress eligibility.

### E3 — USER_OR_INSTITUTION_PRIVATE

Examples:

- unpublished manuscripts;
- internal notes;
- private uploads;
- authenticated/restricted source content;
- institution-only material;
- private correspondence.

Policy posture: **DENY**.

### E4 — PERSONAL_OR_SENSITIVE

Content containing personal, sensitive, restricted, or high-risk information beyond what is necessary for ordinary public bibliographic identification.

Examples include:

- private contact details;
- government identifiers;
- account identifiers;
- authentication material;
- private biographical notes;
- health, financial, legal, disciplinary, or similarly sensitive content;
- information about minors;
- data whose disclosure restrictions are uncertain.

Policy posture: **DENY**.

Public author names and ordinary public scholarly affiliations are not automatically E4 when used only as bibliographic metadata.

### E5 — SECRET_OR_SECURITY_DATA

Examples:

- passwords;
- API keys;
- review tokens;
- cookies;
- bearer tokens;
- private keys;
- environment secrets;
- internal network addresses/configuration;
- stack traces containing secrets;
- raw request headers with credentials.

Policy posture: **DENY — absolute**.

These values must be removed before policy evaluation where technically possible and must never enter the input manifest.

### E6 — UNKNOWN

Any fragment whose class cannot be established deterministically.

Policy posture: **INDETERMINATE -> fail closed**.

## 7. Permitted classifications

A future provider call may include only:

```text
E0 PUBLIC_BIBLIOGRAPHIC_METADATA
E1 PUBLIC_OPEN_TEXT
```

and only when every remaining policy condition passes.

Mixed payload rule:

- if any selected fragment is E2, E3, E4, E5 or E6, the entire run is denied;
- the runtime must not silently drop a disallowed fragment and continue unless the user explicitly creates a new selection/run after the denial.

This preserves auditability between human selection and exact provider payload.

## 8. Explicitly prohibited data

The following are prohibited regardless of provider:

- secrets and credentials;
- review/auth tokens;
- cookies;
- raw authorization headers;
- private/internal URLs or network configuration;
- raw binary PDFs;
- raw DSpace HAL+JSON not selected as textual evidence;
- evidence from other users/sessions;
- private or institution-restricted content;
- personal/sensitive data classified E4;
- unknown-classification content;
- content whose rights/egress eligibility is indeterminate.

No provider configuration may override these prohibitions.

## 9. Provider / deployment allowlist

Current allowlist:

```yaml
allowed_provider_deployments: []
```

Therefore current policy behavior is:

```text
ANY_EXTERNAL_PROVIDER -> DENY
```

A future policy amendment may add a provider/deployment only if its entry records at minimum:

- normalized provider ID;
- deployment/endpoint ID;
- approved purpose;
- deployment region/residency;
- prompt retention policy;
- output retention policy;
- training/improvement use policy;
- logging/telemetry posture;
- contractual or technical data-use controls;
- approval date;
- policy version introducing the entry.

Provider brand alone is insufficient; the exact deployment must be allowlisted.

## 10. Minimum requirements for future allowlisting

A provider/deployment must not be added unless all of the following are known and approved:

1. prompts/outputs are not used for model training or general service improvement unless a later explicit policy decision authorizes that use;
2. retention is explicitly documented;
3. region/residency is explicitly documented;
4. provider-side logging/telemetry behavior is known;
5. credentials remain server-side;
6. endpoint supports the required structured-output/request contract or can be safely adapted;
7. deployment terms are compatible with the permitted evidence classes;
8. no provider tool-use/web-browsing capability is enabled for VERTICAL-021;
9. model requests can be made without transmitting hidden application secrets;
10. the deployment can be uniquely identified in provenance.

Unknown answers -> deployment not allowlisted.

## 11. Retention policy

Until a deployment-specific amendment says otherwise, acceptable future deployment posture is:

- provider prompt retention: **zero or shortest technically/contractually available approved duration**;
- provider output retention: **zero or shortest technically/contractually available approved duration**;
- application-side inference provenance: durable only as defined by VERTICAL-021, without secrets or raw credentials;
- application logs: no full evidence payloads by default.

Any provider with unknown or unbounded retention is not eligible for allowlisting.

## 12. Training / model improvement policy

Default policy:

```text
PROVIDER_TRAINING_USE=PROHIBITED
PROVIDER_GENERAL_SERVICE_IMPROVEMENT_USE=PROHIBITED
```

A provider/deployment may be allowlisted only when the applicable account/deployment terms or technical controls establish that submitted evidence is not used for training/general model improvement.

A future change to this posture requires a new policy version and explicit approval.

## 13. Region / residency policy

No universal region is assumed by this policy.

For any future allowlisted deployment:

- region/residency must be explicit;
- the deployment region must be approved for the project/institutional context;
- `unknown`, `global-unspecified`, or ambiguous routing -> `DENY`;
- cross-region failover not covered by the approved deployment entry -> `DENY`.

This avoids silently embedding jurisdictional assumptions into application code.

## 14. Logging / telemetry / redaction

### Application logs

Must not log:

- full evidence text;
- provider API keys;
- review tokens;
- raw provider request bodies;
- raw provider responses when they may contain evidence;
- system/developer prompts in full;
- secrets detected/redacted from evidence.

May log provider-neutral metadata such as:

- inference_run_id;
- policy version;
- policy decision;
- normalized denial reason;
- provider/deployment ID;
- request/config hash;
- fragment count;
- byte/character totals;
- latency;
- provider-neutral usage metadata.

### Redaction

Redaction is a defensive control, not a mechanism for upgrading prohibited evidence into automatically eligible evidence.

If E4/E5 content is detected in a selected fragment:

- default decision is `DENY`;
- the runtime may report a sanitized reason;
- it must not silently redact and send the remainder as the same run.

## 15. Payload minimization

Only the minimum textual fragments necessary for the cataloging inference task may be sent.

Maximum policy envelope for future implementation:

```text
MAX_FRAGMENTS_PER_RUN=8
MAX_CHARS_PER_FRAGMENT=16000
MAX_TOTAL_CHARS_PER_RUN=64000
MAX_OUTPUT_CHARS=16000
```

These are policy ceilings, not implementation targets.

Implementation may use stricter limits.

Any limit breach -> `DENY` with a normalized `llm_input_too_large`-class outcome.

No automatic truncation may silently alter an accepted human selection. If a selection exceeds limits, the run is denied and the user must create a smaller selection.

## 16. Purpose limitation

Permitted purpose:

```text
BIBLIOGRAPHIC_CATALOGING_CANDIDATE_EXTRACTION
```

The same egress path may not be reused for:

- general chat;
- web research;
- user profiling;
- document summarization unrelated to cataloging;
- autonomous decision-making;
- training/fine-tuning;
- marketing;
- surveillance;
- unrelated analytics.

A new purpose requires a new policy decision/version.

## 17. Prompt-injection treatment

Evidence content is hostile data.

Policy evaluation and provider requests must preserve:

- evidence cannot change provider allowlist;
- evidence cannot change data classification;
- evidence cannot request more context;
- evidence cannot enable tools;
- evidence cannot request browsing/fetch;
- evidence cannot request secrets;
- evidence cannot override system instructions.

Strings inside evidence such as "ignore previous instructions" have no policy authority.

## 18. Required policy input

The future runtime evaluator must receive, at minimum:

- policy version;
- purpose;
- normalized provider ID;
- deployment ID;
- deployment region;
- session ID;
- ordered selected source/fragment descriptors;
- data classification for every fragment;
- source access/license eligibility signal;
- fragment lengths;
- aggregate length;
- redaction/security scan result;
- requested model-neutral parameters.

It must not require raw secrets to make the decision.

## 19. Required policy output

Persistable provider-neutral decision record:

```json
{
  "policy_id": "vertical-021-data-egress-v1",
  "policy_version": "1.0.0",
  "decision": "DENY",
  "reason_codes": ["provider_not_allowlisted"],
  "purpose": "BIBLIOGRAPHIC_CATALOGING_CANDIDATE_EXTRACTION",
  "provider_id": "normalized-provider-id",
  "deployment_id": "deployment-id",
  "fragment_count": 0,
  "total_chars": 0
}
```

Rules:

- no evidence text in the decision record;
- no API keys/tokens;
- no raw provider credentials;
- reason codes are closed/sanitized;
- policy decision is immutable within an inference run.

## 20. Minimum reason-code taxonomy

At minimum:

- `provider_not_allowlisted`
- `deployment_not_allowlisted`
- `deployment_region_not_approved`
- `retention_policy_not_approved`
- `training_use_not_approved`
- `source_rights_not_approved`
- `private_evidence_denied`
- `personal_or_sensitive_data_denied`
- `secret_detected`
- `classification_unknown`
- `mixed_payload_denied`
- `payload_too_large`
- `purpose_not_allowed`
- `policy_configuration_invalid`

Unknown/malformed policy configuration -> `INDETERMINATE` and zero traffic.

## 21. Runtime test requirements

The later implementation must prove with an offline fake adapter that:

1. empty provider allowlist produces zero adapter calls;
2. `DENY` produces zero adapter calls;
3. `INDETERMINATE` produces zero adapter calls;
4. E2/E3/E4/E5/E6 each fail closed;
5. mixed eligible/prohibited payload fails closed;
6. secret detection fails closed;
7. unknown region fails closed;
8. unapproved retention/training posture fails closed;
9. payload over any ceiling fails closed;
10. evidence cannot alter policy outcome through prompt injection;
11. policy decision is persisted without evidence text/secrets;
12. request manifest contains only fragments approved by an `ALLOW` decision;
13. provider adapter cannot bypass the enforcement point.

These are future implementation requirements, not evidence that runtime enforcement exists today.

## 22. Change control

Any change to the following requires a new policy version and reviewed durable artifact:

- permitted data classes;
- prohibited data classes;
- provider/deployment allowlist;
- purpose;
- retention posture;
- training/improvement posture;
- residency/region;
- logging/redaction;
- payload ceilings;
- sensitive-data handling.

Provider enablement must never be accomplished solely through an environment variable without a corresponding approved policy version.

## 23. Rollback

Provider access can be disabled without changing evidence/session data by either:

1. feature flag OFF; or
2. removing the deployment from the approved policy allowlist.

Both must result in fail-closed zero provider traffic.

Historical inference-run provenance remains readable.

## 24. Gate B determination

This artifact closes the **policy-definition** requirement of Gate B.

It does not claim runtime enforcement.

At approval:

```text
DATA_EGRESS_POLICY=APPROVED
POLICY_VERSION=1.0.0
PROVIDER_ALLOWLIST_EMPTY=YES
RUNTIME_ENFORCEMENT_IMPLEMENTED=NO
REAL_PROVIDER_TRAFFIC_AUTHORIZED=NO
GATE_B=PASS
```

VERTICAL-021 remains blocked by Gates C and D and by the absence of a later implementation contract.

## Final determination

**VERTICAL-021 Gate B: PASS — policy approved, provider traffic remains denied.**
