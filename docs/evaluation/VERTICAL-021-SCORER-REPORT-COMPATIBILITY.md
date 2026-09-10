# VERTICAL-021 Scorer Report Compatibility Note

Status: **OFFLINE D1 METRIC SURFACE MATERIALIZED / GATE D1 OPEN**

Related: #75, #69

## API compatibility

The public Python entry points remain:

```python
score_case(expected_doc, proposed_doc)
score_run(cases, run_metadata=None)
```

Existing scalar case keys (`tp`, `fp`, `fn`, `precision`, `recall`,
`binding_accuracy`, `grounding_accuracy`, `hallucination_rate`) remain available.
The report adds structured metric objects, dimensions and provenance.

The intentional compatibility correction is that a rate with an empty denominator now
returns `null` plus `status=NOT_EVALUABLE`; it no longer fabricates a perfect score.

## Report additions

- `by_risk_stratum`, `by_binding`, `by_intent`, `by_language`, `by_document_type`;
- micro/macro precision and recall with explicit denominators;
- binding, grounding, intent, controlled-vocabulary and abstention metrics;
- annotated human-review burden;
- stable error code/origin/severity/index fields;
- deterministic scorer/matching/grounding versions;
- maximum-cardinality authoritative matching with canonical tie-breaking;
- selective abstention identity across binding, `opportunity_id` and `source_refs`;
- explicit macro averages by case, binding and risk stratum;
- explicit empty buckets for all three strata and five critical bindings;
- explicit incomplete provenance when metadata is absent;
- frozen controlled-vocabulary identity sourced from expected gold or the case manifest;
- human-review burden sourced only from versioned `FINAL` adjudications joined to the case;
- informational `PROVISIONAL_TARGETS` comparison.

`SCORER_VERSION=0.3.0` uses
`MATCHING_ALGORITHM_VERSION=deterministic-maximum-bipartite-v3`. Incomplete or conflicting
controlled-vocabulary identity makes provenance incomplete and emits a schema diagnostic;
empty strings and empty hash collections cannot satisfy required run provenance.

## Governance boundary

This report cannot emit semantic `PASS` or `FAIL` while thresholds remain provisional.
It always retains:

```text
THRESHOLDS=PROVISIONAL
threshold_profile=PROVISIONAL_TARGETS
gate_assessment=ASSESSMENT_ONLY
GATE_D1=OPEN
GATE_D=OPEN
VERTICAL_021_IMPLEMENTATION=BLOCKED
```

No runtime LLM, provider, credential, network call, DSpace operation, OCR, browsing, tool
use, persistence migration, production endpoint or UI behavior is introduced.
