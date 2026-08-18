# Adjudication worksheet — candidate 003 / registered-language / rereview-v2

**Case:** `real-evidence-candidate-003-registered-language-rereview-v2`

**Binding:** `registered-language`

**Metadata field:** `dc.description.registeredLanguage`

**Evidence packet:** `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.rereview-v2.packet.txt`

**Evidence snapshot SHA-256:** `2a1ceef24ef537796ed5ec44dc7682a8b900964fd9ea70b9647404ad54817f81`

**Catalog contract:** `dspace-cataloger-v3.6`

**Catalog contract SHA-256:** `a68fbf9664b7165ea240508da85167058cd57796fbda9c1a9869986afb0178bb`

## Purpose

Resolve the formal disagreement between the two completed independent v2 reviews. The adjudicator may inspect both reviewer decisions and the shared evidence packet. This worksheet does not prescribe an outcome.

## Input review A

- Reviewer: `cataloger-a`
- Review ID: `review-real-evidence-candidate-003-registered-language-cataloger-a-rereview-v2`
- Decision: `ACCEPT_WITH_MINOR_EDIT`
- Proposed corrected value: `Purépecha`
- Abstention: `false`
- Error codes: none
- Comment: `Verifiqué contra fuentes confiables como el INALI para tomar la decisión.`

## Input review B

- Reviewer: `cataloger-b`
- Review ID: `review-real-evidence-candidate-003-registered-language-cataloger-b-rereview-v2`
- Decision: `ACCEPT_AS_IS`
- Proposed corrected value: none
- Abstention: `false`
- Error codes: none
- Comment: `Acepto Purépecha como clasificación adoptada por el INALI.`

## Disagreement resolved

Both reviewers converged on `Purépecha` as the accepted catalog value and neither recommended abstention or assigned an error code. The formal disagreement was whether the result should be classified as `ACCEPT_AS_IS` or `ACCEPT_WITH_MINOR_EDIT`.

## Adjudicator response

- Adjudicator ID: `adjudicator-1`
- Final decision: `ACCEPT_WITH_MINOR_EDIT`
- Final value: `Purépecha`
- Final abstention: `false`
- Error codes: none
- Comment: `Aunque ambas revisiones de catalogadores humanos aceptaron el término Purépecha como autoridad verificada, es necesario reconsiderar la revisión final con mayor profundidad. Si es preciso, debe documentarse en una nota interna de catalogación para que quede como evidencia trazable, tanto para catalogadores humanos como para LLM, redes neuronales futuras y otros algoritmos especializados.`
- Timestamp UTC: `2026-08-18T05:51:00Z`

## Governance status

The canonical adjudication JSON is `FINAL` under explicit governance authorization and references the frozen real catalog-contract SHA-256. Under a subsequent explicit governance decision, this v2 case is also `ADJUDICATED_GOLD` at case level. The aggregate intake remains `BLOCKED_FOR_INTAKE` because the original narrow review cycle is still blocked. This case-level gold state does not close Gate D, does not convert runtime evidence to `VERIFICADO`, and does not authorize LLM provider egress or DSpace write.
