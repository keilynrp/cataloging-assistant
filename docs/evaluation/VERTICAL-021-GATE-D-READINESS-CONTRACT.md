# VERTICAL-021 — Gate D Closure / Readiness Contract

Status: **READINESS RECORDED — Gate D remains OPEN**

Date: **2026-08-27**

Parent specification: `docs/specs/VERTICAL-021-provider-independent-llm-assisted-extraction.md`

Architecture: `docs/adr/ADR-017-provider-independent-llm-evidence-extraction.md`

Evaluation plan: `docs/evaluation/VERTICAL-021-EVALUATION-PLAN.md`

Golden Set contract: `docs/evaluation/VERTICAL-021-GOLDEN-SET-CONTRACT.md`

Scorer contract: `docs/evaluation/VERTICAL-021-SCORER-CONTRACT.md`

Human adjudication protocol: `docs/evaluation/VERTICAL-021-HUMAN-ADJUDICATION-PROTOCOL.md`

Related gate tracker: #69

## 1. Purpose

Record the actual readiness state of VERTICAL-021 Gate D without converting design artifacts into evidence they do not yet provide.

Gate D is the evaluation-methodology gate.

It must establish a reproducible, cataloging-aware quality framework before VERTICAL-021 implementation is authorized.

A semantic-quality score can never compensate for a contract or security failure.

## 2. What is already materialized

The repository contains an unusually complete preparatory evaluation surface.

### 2.1 Evaluation methodology

`docs/evaluation/VERTICAL-021-EVALUATION-PLAN.md` defines:

- separate contract, security and semantic-quality layers;
- provider-independent evaluation;
- risk strata A/B/C;
- candidate precision/recall;
- binding accuracy;
- grounding/source-attribution accuracy;
- hallucination rate;
- abstention quality;
- controlled-vocabulary exact-match;
- intent accuracy;
- human-review burden;
- sample sufficiency;
- reproducible evaluation-run provenance.

### 2.2 Semantic Golden Set

Materialized under:

`apps/api/tests/golden/llm-evidence/`

Current manifest:

```text
golden_set_version=0.2.1-stratum-a-diverse
status=STRATUM_A_SAMPLE_FLOOR_MET_SYNTHETIC_ONLY
methodology_status=DIVERSITY_RECONCILED_SYNTHETIC_ONLY
```

The synthetic Stratum A corpus covers all five critical linguistic bindings:

- `linguistic-family`;
- `linguistic-branch`;
- `linguistic-group`;
- `linguistic-variant`;
- `registered-language`.

The historical literal remains preserved:

`dc.subject.linguiscgroup`.

The manifest declares at least 20 Stratum A opportunities and at least three opportunities for each critical binding.

### 2.3 Schemas

Materialized schemas include:

- `manifest.schema.json`;
- `source.schema.json`;
- `expected.schema.json`;
- human-review intake/reviewer/adjudication schemas.

### 2.4 Offline deterministic scorer

Materialized implementation:

`apps/api/src/cataloging_api/evaluation/scorer.py`

Existing tests include:

- `apps/api/tests/test_llm_evaluation_scorer.py`;
- `apps/api/tests/test_llm_evaluation_stratum_a_coverage.py`.

The scorer already evaluates:

- authoritative TP/FP/FN;
- micro/macro precision and recall with explicit non-evaluable denominators;
- exact binding diagnostics;
- grounding diagnostics;
- intent accuracy;
- controlled-vocabulary exact-match against frozen gold metadata;
- hallucination annotations;
- full and selective abstention metrics;
- human-review burden from supplied versioned annotations;
- breakdowns by binding, stratum, intent, language and document type;
- stable error provenance/severity/indexes;
- deterministic provenance status and input-order stability;
- Stratum A sample sufficiency.

It deliberately returns:

```text
gate_assessment=ASSESSMENT_ONLY
```

which is correct while thresholds remain provisional.

### 2.5 Human-review protocol and real adjudication

Human-review schemas/templates and real-review artifacts are materialized.

At least one current case has valid case-level adjudicated gold:

```text
case_id=real-evidence-candidate-003-registered-language-rereview-v3
binding_id=registered-language
metadata_field=dc.description.registeredLanguage
final_value=Español
adjudication_status=FINAL
review_status=ADJUDICATED_GOLD
```

That case has:

- two independent reviewer records;
- a final adjudicator;
- immutable evidence SHA-256;
- catalog-contract version/hash;
- resulting gold version.

This is valid evidence for that case only.

## 3. What is not yet sufficient

Gate D must not be closed by extrapolating from the above.

### D-BLOCKER-001 — Thresholds remain provisional

The evaluation plan and scorer contract still label semantic targets as `PROVISIONAL_TARGETS`.

Current targets include:

- candidate precision micro >= 0.95;
- binding accuracy >= 0.98;
- grounding accuracy >= 0.98;
- hallucination rate <= 0.02;
- false proposal rate on abstention <= 0.05;
- controlled-vocabulary exact-match >= 0.98;
- intent accuracy >= 0.98.

They have not yet been ratified as the final model-qualification thresholds.

### D-BLOCKER-002 — Gate semantics remain coupled to threshold ratification

The offline scorer now materializes the D1 metric/report surface required for evidence-based
threshold review, including:

- explicit micro/macro metric objects and non-evaluable denominators;
- breakdowns by binding, risk stratum, intent, language and document type;
- controlled-vocabulary exact-match and intent accuracy;
- full/selective abstention metrics;
- annotated human-review-burden aggregation;
- stable error provenance/severity/indexes;
- deterministic run provenance and input-order stability;
- informational comparison against `PROVISIONAL_TARGETS`.

The scorer deliberately does not implement approved-threshold `PASS|FAIL` semantics while
D-BLOCKER-001 remains open. Implementing that decision before ratification would convert
provisional targets into an unauthorized gate. Therefore it continues to emit:

```text
threshold_profile=PROVISIONAL_TARGETS
gate_assessment=ASSESSMENT_ONLY
```

### D-BLOCKER-003 — Human empirical coverage is incomplete

The current aggregate real-evidence intake remains:

```text
status=BLOCKED_FOR_INTAKE
```

One valid `registered-language` case is `ADJUDICATED_GOLD`, but this does not provide empirical human-reviewed coverage across all five critical Stratum A bindings.

Historical blocked/withdrawn cases remain correctly preserved rather than silently rewritten.

### D-BLOCKER-004 — No qualified model evaluation exists yet

No provider/model has been evaluated against the approved semantic thresholds because:

- VERTICAL-021 runtime implementation does not yet exist;
- Gate B provider/deployment allowlist remains empty;
- real-provider traffic remains unauthorized.

This is **not** itself a reason to weaken Gate D.

The project must distinguish:

1. **pre-implementation evaluation methodology readiness**; and
2. **post-implementation model qualification**.

The latter can occur only after an implementation contract creates the offline/runtime boundary and a later governed provider decision permits an evaluation deployment.

## 4. Avoiding a circular gate

Gate D must not create a logical impossibility where implementation is forbidden until a real model is evaluated, while model evaluation is impossible until implementation exists.

Therefore the gate is split conceptually into two decisions.

### Gate D1 — Evaluation methodology readiness

Pre-implementation requirement.

D1 requires:

- approved Evaluation Plan;
- approved Golden Set contract;
- approved Scorer contract;
- approved Human Adjudication Protocol;
- materialized synthetic Golden Set and schemas;
- materialized deterministic scorer/harness;
- ratified qualification thresholds;
- scorer support for every authoritative threshold metric.

### Gate D2 — Model qualification

Post-implementation / pre-production-use requirement.

D2 requires:

- an implemented provider-neutral inference path;
- contract/security suite PASS;
- an explicitly allowlisted evaluation deployment;
- governed evaluation runs;
- semantic thresholds met with adequate sample;
- human review/adjudication as required;
- no critical unresolved errors.

**Gate D in issue #69 closes only when D1 passes.**

D2 becomes a mandatory acceptance gate in the later VERTICAL-021 Implementation Contract and cannot be bypassed before productive LLM use.

This separation removes circularity without weakening semantic acceptance.

## 5. Current Gate D1 assessment

```text
EVALUATION_PLAN=METHOD_READY_BUT_STATUS_STALE
GOLDEN_SET_CONTRACT=METHOD_READY_BUT_STATUS_STALE
SCORER_CONTRACT=METHOD_READY_BUT_STATUS_STALE
HUMAN_ADJUDICATION_PROTOCOL=METHOD_READY_BUT_STATUS_STALE
SYNTHETIC_GOLDEN_SET=MATERIALIZED
STRATUM_A_SAMPLE_FLOOR_SYNTHETIC=MET
SCORER=MATERIALIZED_D1_METRIC_SURFACE
SCORER_GATE_SEMANTICS=DEFERRED_UNTIL_THRESHOLDS_RATIFIED
REAL_ADJUDICATED_CASES_PRESENT=YES
REAL_STRATUM_A_COVERAGE=INCOMPLETE
THRESHOLDS=PROVISIONAL
GATE_D1=OPEN
GATE_D2=NOT_YET_APPLICABLE
GATE_D=OPEN
```

## 6. Remaining authorized work before Gate D1 closure

The only work authorized by this readiness contract is evaluation infrastructure/governance work:

1. review the materialized metric/report surface;
2. ratify final qualification thresholds;
3. implement the approved threshold profile and its `PASS|FAIL` semantics;
4. reconcile evaluation-document lifecycle statuses;
5. preserve the synthetic/real evidence distinction;
6. record a durable Gate D1 acceptance artifact.

This work must remain:

- offline;
- deterministic;
- provider-independent;
- free of real provider credentials;
- free of external provider traffic;
- free of DSpace writes;
- separate from production inference runtime.

## 7. Work still forbidden

This readiness contract does not authorize:

- VERTICAL-021 production endpoints;
- inference-run database migrations;
- provider adapter integration into runtime;
- provider credentials for evidence inference;
- adding a provider to the Gate B allowlist;
- real-provider traffic;
- LLM UI as `CURRENT_RUNTIME`;
- OCR;
- browsing/crawling/tool use;
- model-initiated fetch;
- auto-accept;
- auto-copy;
- DSpace write.

## 8. Gate tracker state

After this readiness record:

```text
GATE_A=PASS
GATE_B=PASS
GATE_C=PASS
GATE_D=OPEN
VERTICAL_021_IMPLEMENTATION=BLOCKED
```

## Final determination

**Gate D is materially prepared but not yet closable.**

The next implementation-safe unit of work is to review observed scorer outputs and ratify
thresholds. Approved gate semantics must be implemented only after that governance decision,
followed by a separate Gate D1 acceptance review.
