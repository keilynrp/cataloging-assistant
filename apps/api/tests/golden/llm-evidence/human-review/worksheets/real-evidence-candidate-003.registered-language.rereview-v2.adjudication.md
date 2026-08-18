# Adjudication worksheet — candidate 003 / registered-language / rereview-v2

**Case:** `real-evidence-candidate-003-registered-language-rereview-v2`

**Binding:** `registered-language`

**Metadata field:** `dc.description.registeredLanguage`

**Evidence packet:** `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.rereview-v2.packet.txt`

**Evidence snapshot SHA-256:** `2a1ceef24ef537796ed5ec44dc7682a8b900964fd9ea70b9647404ad54817f81`

**Catalog contract:** `dspace-cataloger-v3.6`

**Catalog contract SHA-256:** `a68fbf9664b7165ea240508da85167058cd57796fbda9c1a9869986afb0178bb`

## Purpose

Resolve the formal disagreement between the two completed independent v2 reviews. This worksheet preserves the historical human decision and does not rewrite it after later governance corrections.

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

## Adjudicator response

- Adjudicator ID: `adjudicator-1`
- Final decision: `ACCEPT_WITH_MINOR_EDIT`
- Final value: `Purépecha`
- Final abstention: `false`
- Error codes: none
- Comment: `Aunque ambas revisiones de catalogadores humanos aceptaron el término Purépecha como autoridad verificada, es necesario reconsiderar la revisión final con mayor profundidad. Si es preciso, debe documentarse en una nota interna de catalogación para que quede como evidencia trazable, tanto para catalogadores humanos como para LLM, redes neuronales futuras y otros algoritmos especializados.`
- Timestamp UTC: `2026-08-18T05:51:00Z`

## Subsequent governance correction

The canonical v2 adjudication remains `FINAL` as an immutable historical human-decision record. A later pre-merge review identified that the v2 evidence supported P’urhepecha as a language studied/used in the resource, while ADR-012 defines `dc.description.registeredLanguage` as the resource's own writing/registration language. Therefore the v2 case-level `ADJUDICATED_GOLD` promotion was withdrawn from current evaluation use without deleting or rewriting the human adjudication.

The correction is recorded in:

`apps/api/tests/golden/llm-evidence/human-review/corrections/real-evidence-candidate-003.registered-language.rereview-v2.gold-withdrawal.md`

A new `rereview-v3` evaluates the corrected proposition `dc.description.registeredLanguage = Español`. Gate D remains open; no runtime `VERIFICADO`, provider egress, productive LLM behavior, or DSpace write is authorized.
