# VERTICAL-021 — Pre-Implementation Gates Contract

Status: **GATED — no production implementation authorized**

Parent specification: `docs/specs/VERTICAL-021-provider-independent-llm-assisted-extraction.md`

Related issue: #69

Baseline: `main` @ `5860c9dfcd26f1b89ff0df93a5e4861bf60c409c`

## Purpose

Define the mandatory closure path for VERTICAL-021 before any production LLM-assisted extraction code is authorized.

VERTICAL-020 is already **Accepted / Operationalized**, so its dependency gate is resolved.

VERTICAL-021 itself remains architecture-only.

This contract does **not** authorize:

- inference-run persistence;
- provider adapters;
- provider credentials;
- provider SDK integration;
- production LLM calls;
- UI controls presented as current runtime;
- DSpace writes;
- agent tool expansion.

## Current gate state

### Gate A — UX

Status: **PASS / CLOSED — 2026-08-27**

Authoritative evidence:

- `docs/ux/reviews/UX-ALIGNMENT-001-evidence-workspace-v02.md`
- `docs/ux/UX-CONTRACT-FREEZE-001-evidence-workspace-v02.md`

Closure evidence:

```text
UX-PROMPT-002_EXECUTED=YES
LOVABLE_COMMIT=7100f3116b4dba4c2273d8e19a1a2c13c783b0eb
HUMAN_AUDIT_APPROVAL=YES
UX-ALIGNMENT-001=ACCEPTED_FOR_FREEZE
UX_CONTRACT_FREEZE=RECORDED
GATE_A=PASS
```

The accepted three-pane topology and semantic presentation contract are now frozen for this increment.

All LLM interactions remain `FUTURE_CONTRACT` until VERTICAL-021 is implemented and accepted under its remaining gates.

### Gate B — Provider / data-egress policy

Status: **PASS / CLOSED — 2026-08-27**

Authoritative evidence:

- `docs/governance/VERTICAL-021-DATA-EGRESS-POLICY-v1.md`

Closure state:

```text
DATA_EGRESS_POLICY=APPROVED
POLICY_VERSION=1.0.0
PROVIDER_ALLOWLIST_EMPTY=YES
RUNTIME_ENFORCEMENT_IMPLEMENTED=NO
REAL_PROVIDER_TRAFFIC_AUTHORIZED=NO
GATE_B=PASS
```

The policy defines a provider-neutral `ALLOW / DENY / INDETERMINATE` decision model, explicit data classifications, fail-closed treatment of private/sensitive/unknown content, retention/training/region/logging requirements, payload ceilings, purpose limitation and an immutable provider-neutral decision record.

The provider/deployment allowlist is intentionally empty. Therefore all real external-provider traffic remains denied until a later reviewed policy amendment and implementation contract authorize a specific deployment and runtime enforcement exists.

The UI and adapter cannot override this decision.

### Gate C — Architecture Decision Record

Status: **PASS / CLOSED — 2026-08-27**

Authoritative evidence:

- `docs/adr/ADR-017-provider-independent-llm-evidence-extraction.md`

Closure state:

```text
ADR_017=ACCEPTED
PROVIDER_BOUNDARY=DEFINED
INPUT_MANIFEST=DEFINED
DATA_EGRESS_ENFORCEMENT_POINT=DEFINED
PROMPT_INJECTION_BOUNDARY=DEFINED
PERSISTENCE_ATOMICITY=DEFINED
ROLLBACK=DEFINED
GATE_C=PASS
```

ADR-017 covers the provider-neutral adapter boundary, credential/capability separation, exact immutable input manifest and request hashing, structured-output/schema boundary, server-side binding/evidence-state authority, data-egress enforcement point, prompt-injection threat model, secrets boundary, inference-run persistence, transactional candidate persistence, staleness/concurrency, deterministic-baseline preservation, agent capability boundary and rollback.

The ADR does not authorize DSpace writes, browsing, crawling, OCR, model tool use, model-initiated fetch or real-provider traffic.

### Gate D — Evaluation plan

Status: **OPEN / BLOCKING — methodology materially prepared**

Authoritative readiness evidence:

- `docs/evaluation/VERTICAL-021-EVALUATION-PLAN.md`
- `docs/evaluation/VERTICAL-021-GOLDEN-SET-CONTRACT.md`
- `docs/evaluation/VERTICAL-021-SCORER-CONTRACT.md`
- `docs/evaluation/VERTICAL-021-HUMAN-ADJUDICATION-PROTOCOL.md`
- `docs/evaluation/VERTICAL-021-GATE-D-READINESS-CONTRACT.md`

Current state:

```text
METHODOLOGY=ACCEPTED
SYNTHETIC_GOLDEN_SET=MATERIALIZED
STRATUM_A_SYNTHETIC_SAMPLE_FLOOR=MET
SCORER=MATERIALIZED_PARTIAL
REAL_ADJUDICATED_CASES_PRESENT=YES
REAL_STRATUM_A_COVERAGE=INCOMPLETE
THRESHOLDS=PROVISIONAL
GATE_D=OPEN
```

The evaluation methodology, synthetic Golden Set, schemas, scorer foundation and human-adjudication process are already materialized.

Gate D remains open because final qualification thresholds are still provisional and the scorer does not yet implement the complete authoritative metric/report contract. Human empirical coverage is also incomplete and must not be overstated.

The readiness contract separates pre-implementation methodology readiness (D1) from later post-implementation model qualification (D2) to avoid a circular dependency. Closing D1 does not qualify or enable any provider.

Quality evaluation remains separate from functional/security tests, and syntactically valid provider output can never close this gate by itself.

## Cross-gate non-negotiable invariants

All gate artifacts and later implementation must preserve:

1. DSpace remains read-only.
2. Deterministic extraction remains independently runnable.
3. LLM extraction is additive, never a replacement for deterministic extraction.
4. `EVIDENCE_LLM_EXTRACTION_ENABLED=false` by default.
5. Disabled mode performs zero provider traffic.
6. Main functional tests run with an offline deterministic fake adapter.
7. Evidence is hostile data, never authority.
8. No model tool use.
9. No browser/navigation/crawling.
10. No model-initiated URL fetch.
11. No OCR.
12. Provider SDK/types do not leak into cataloging-domain contracts.
13. Model may propose only allowed `binding_id` values.
14. Backend derives `metadata_field`.
15. Model emits only closed `candidate_intent`.
16. Backend derives `INFERIDO` or `GENERADO`.
17. LLM output never becomes `EXTRAÍDO`, `VERIFICADO`, or `PENDIENTE` automatically.
18. No auto-accept.
19. No auto-copy-to-draft.
20. Provider/schema/validation failure leaves no partial candidates.
21. API keys and credentials remain server-side.
22. Conversational agent receives no inference-run or mutable evidence tool.
23. No gate may weaken VERTICAL-020 SSRF/network policy.
24. Existing VERTICAL-017/019/020 behavior and Golden Set must remain non-regressive.

## Closure order

The preferred sequence is:

```text
Gate A — UX reconciliation/freeze
    ->
Gate B — provider/data-egress policy
    ->
Gate C — ADR
    ->
Gate D — evaluation plan
    ->
VERTICAL-021 Implementation Contract
    ->
implementation PR(s)
    ->
offline functional/security acceptance
    ->
separate governed real-provider decision, if desired
```

Gate B and Gate C may be drafted in parallel after Gate A semantics are sufficiently stable, but neither may be considered closed by an implementation patch.

## Gate evidence rule

Each gate closes only through a durable artifact merged into `main`.

A conversation, prototype comment, local file, provider console setting, or unmerged branch is not sufficient evidence.

The gate tracker in issue #69 must link the merged artifact/PR for each closure.

## Implementation authorization rule

A VERTICAL-021 implementation contract may be created only when:

```text
GATE_A=PASS
GATE_B=PASS
GATE_C=PASS
GATE_D=PASS
```

Until then:

```text
VERTICAL-021
STATUS=PROPOSED / ARCHITECTURE_ONLY
IMPLEMENTATION_AUTHORIZED=NO
PRODUCTION_LLM_TRAFFIC_AUTHORIZED=NO
```

## Definition of Done

This pre-implementation contract is complete when:

1. it is reviewed and merged;
2. issue #69 tracks Gates A–D explicitly;
3. each gate has durable merged evidence;
4. no production LLM implementation starts early;
5. after all four gates pass, a separate VERTICAL-021 Implementation Contract is created and reviewed before code.

## Final determination at contract creation

```text
VERTICAL-020_DEPENDENCY=RESOLVED
GATE_A=PASS
GATE_B=PASS
GATE_C=PASS
GATE_D=OPEN
VERTICAL-021_IMPLEMENTATION=BLOCKED
```
