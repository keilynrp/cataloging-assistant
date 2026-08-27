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

Status: **OPEN / BLOCKING**

Authoritative evidence:

`docs/ux/reviews/UX-ALIGNMENT-001-evidence-workspace-v02.md`

Current repository state:

```text
Status: PRE-EXECUTION TEMPLATE
Current verdict: BLOCKED — AWAITING LOVABLE v0.2 EXECUTION
```

Required closure:

1. execute the governed Evidence Navigator v0.2 reconciliation;
2. complete `UX-ALIGNMENT-001` against the actual artifact;
3. obtain verdict `ACCEPTED_FOR_FREEZE`;
4. record the corresponding UX Contract Freeze;
5. keep all LLM interactions as `FUTURE_CONTRACT` until this gate closes.

The accepted three-pane topology in `UX-DECISION-001` is necessary but not sufficient to close Gate A.

### Gate B — Provider / data-egress policy

Status: **OPEN / BLOCKING**

Before any real external provider call, a versioned and approved policy must define and make runtime-evaluable:

- eligible/prohibited evidence categories;
- provider/deployment allowlist;
- processing purpose;
- prompt/output retention;
- training/improvement use policy;
- region/residency requirements where applicable;
- logging/telemetry/redaction;
- prohibited fields/data classes;
- payload and fragment limits;
- treatment of personal/sensitive/restricted content;
- private/on-prem deployment rules when applicable;
- policy version;
- persisted provider-neutral policy decision.

Mandatory runtime behavior:

```text
ALLOW         -> provider call may proceed
DENY          -> fail closed, zero provider traffic
INDETERMINATE -> fail closed, zero provider traffic
```

The UI and adapter cannot override this decision.

A real-provider smoke is forbidden before this gate is closed and the enforcement point exists.

### Gate C — Architecture Decision Record

Status: **OPEN / BLOCKING**

A VERTICAL-021-specific ADR must be merged before implementation.

It must cover at minimum:

- provider-neutral adapter boundary;
- provider configuration boundary;
- exact immutable input manifest;
- request/config hashing;
- structured-output/schema boundary;
- evidence-state derivation;
- server-side binding authority;
- data-egress enforcement point;
- prompt-injection threat model;
- secrets boundary;
- inference-run persistence;
- transactional candidate persistence;
- failure taxonomy;
- staleness/concurrency;
- deterministic-baseline preservation;
- agent capability boundary;
- rollback.

The ADR must not authorize DSpace writes, browsing, crawling, OCR, tool use, or model-initiated fetch.

### Gate D — Evaluation plan

Status: **OPEN / BLOCKING**

A versioned evaluation plan must be approved before cataloging use.

It must define:

- fixture corpus;
- expected field/binding outcomes;
- contradictory-evidence cases;
- multilingual/multientity cases;
- closed-vocabulary cases;
- prompt-injection fixtures;
- grounding/source-attribution fixtures;
- inferred-vs-generated classification cases;
- hallucination fixtures;
- stale-session cases;
- provider failure/schema failure cases.

Required metric definitions must include at least:

- proposal precision;
- recall where meaningful;
- hallucination rate;
- binding accuracy;
- grounding/source-attribution accuracy;
- controlled-vocabulary exact-match rate;
- human-review-required rate.

Quality evaluation must remain separate from functional/security tests.

Gate D is not closed merely because a provider returns syntactically valid JSON.

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
GATE_A=OPEN
GATE_B=OPEN
GATE_C=OPEN
GATE_D=OPEN
VERTICAL-021_IMPLEMENTATION=BLOCKED
```
