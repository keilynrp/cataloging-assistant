# Governance correction — candidate 003 / registered-language / rereview-v3 intent normalization

## Scope

This correction normalizes the scorer-facing `candidate_intent` for `real-evidence-candidate-003-registered-language-rereview-v3` from the non-contract label `RESOURCE_WRITING_LANGUAGE` to the VERTICAL-021 supported intent `INFERRED_VALUE`.

## Why

VERTICAL-021 model outputs use the closed intent set `INFERRED_VALUE` and `GENERATED_CONTENT`. The distinction that `dc.description.registeredLanguage` represents the language in which the resource is written/registered belongs to the semantic contract of the `registered-language` binding under ADR-012; it is not a third model intent.

## Immutability boundary

The reviewed evidence packet remains byte-for-byte unchanged and retains the historical label `RESOURCE_WRITING_LANGUAGE`. Its SHA-256 `58ec2dd6ae0c55a2118ae4c8c27fc21497ab3fc96a73acc2175f4af861c7a7b1` anchors the two completed independent human reviews and MUST NOT be rewritten after review.

The intake, candidate registry, review worksheets, adjudication worksheet, schema, and scorer-facing documentation use `INFERRED_VALUE` as the canonical intent. Worksheet edits are documentary normalization only and explicitly preserve the human decisions, candidate value `Español`, semantic proposition, evidence snapshot, timestamps, comments, abstention decisions, and adjudication outcome.

## Gold identity

The corrected case publishes `resulting_gold_version = 0.2.0-stratum-a-rereview-v3-adjudicated-gold` at case level. The aggregate intake remains `BLOCKED_FOR_INTAKE`; Gate D remains open.

## Architectural boundary

This correction does not create runtime `VERIFICADO`, activate provider egress, enable productive LLM execution, alter DSpace, or authorize OCR or mutating agent tools.
