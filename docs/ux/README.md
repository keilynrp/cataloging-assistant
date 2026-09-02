# UX/UI Design Evidence

This directory contains the governed UX/UI design record for the Cataloging Assistant.

The normative authority remains `UX-GOVERNANCE-CONTRACT.md`. Design prompts, prototypes, mock data and exploratory interactions must not redefine backend semantics, cataloging contracts, DSpace behavior or evidence semantics.

## Artifact types

- `specs/UX-SPEC-NNN-*.md` — execution-oriented UX specifications derived from the governance contract and current runtime.
- `prompts/UX-PROMPT-NNN-*.md` — exact prompt evidence used with Lovable, Figma or another design agent. The prompt text is preserved verbatim where available.
- `reviews/UX-ALIGNMENT-NNN-*.md` — post-execution UX/backend alignment reviews.
- `decisions/UX-DECISION-NNN-*.md` — durable UX decisions that have moved beyond exploration.

## Traceability model

`UX-GOVERNANCE-CONTRACT -> UX-DECISION -> UX-SPEC -> UX-PROMPT -> PROTOTYPE -> UX-ALIGNMENT -> UX CONTRACT FREEZE`

A durable UX decision may freeze a narrow architectural invariant before the complete prototype increment is frozen. A later domain capability may start only after the relevant UX increment has passed its alignment gate when the UX contract requires it.

## Status vocabulary

Prompt/spec/decision artifacts should use one of:

- `PROPOSED`
- `EXECUTED`
- `SUPERSEDED`
- `ACCEPTED`

Execution evidence should record the target tool/project, prototype route or artifact, date/commit when known, resulting version, and subsequent alignment review.

## Current sequence

1. `UX-PROMPT-001` — original Evidence Workspace exploration in Lovable. Status: `EXECUTED`.
2. Evidence Navigator v0.1 — exploratory three-pane prototype.
3. `UX-GOVERNANCE-CONTRACT.md` — normative UX/UI governance established after the exploration.
4. `UX-DECISION-001` — durable three-region Evidence Workspace architecture. Status: `ACCEPTED`.
5. `UX-SPEC-001` — Evidence Workspace Contract Reconciliation.
6. `UX-PROMPT-002` — Lovable v0.2 reconciliation. Status: `EXECUTED — ACCEPTED`.
7. `UX-RUNTIME-GAP-001` and `UX-ALIGNMENT-001` — runtime gap and alignment evidence for the frozen workspace.
8. `UX-PROMPT-003` — candidate selection and copy affordance. Status: `EXECUTED — ACCEPTED`.
9. `UX-PROMPT-004` — pre-copy review flow. Status: `EXECUTED — ACCEPTED FOR CONTINUITY`; `UX004-DEBT-001` carried forward.
10. `UX-PROMPT-005` — Inspector provenance focus. Status: `EXECUTED — AUDITED — ACCEPTED`; `UX004-DEBT-001` closed.
11. `UX-PROMPT-006` — Inspector accessibility and density refinement. Status: `EXECUTED — AUDITED — ACCEPTED`; Lovable commit `9301e649fca3f789e16777f96ea88efd7e920fac`.
12. `UX-ACCESSIBILITY-AUDIT-001` — public keyboard, focus and observable contrast audit. Status: `COMPLETED — PASS WITH ONE CORRECTIVE DEBT`; `UX006-DEBT-001` opened for CopyReviewDialog focus restoration.
13. `UX-PROMPT-007` — CopyReviewDialog focus restoration corrective patch. Status: `EXECUTED — AUDITED — ACCEPTED`; Lovable commit `e74f22ebaffc9464f459a9d2282e4bf04eb4118c`; `UX006-DEBT-001` closed.
14. `UX-ACCESSIBILITY-AUDIT-002` — responsive, zoom, keyboard and assistive-technology acceptance plan for v0.6.1. Status: `BLOCKED — INSUFFICIENT TEST ENVIRONMENT`; baseline `e74f22ebaffc9464f459a9d2282e4bf04eb4118c`; no UX-PROMPT-008 created.

The historical order is intentional: the first exploration is preserved as evidence that informed the later governance contract rather than being retrospectively presented as if it had been governed from the start. The three-region workspace topology and pane responsibilities remain frozen; subsequent iterations must continue to respect the governance contract.
