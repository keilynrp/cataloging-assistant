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
4. `UX-DECISION-001` — durable three-pane Evidence Workspace architecture. Status: `ACCEPTED`.
5. `UX-SPEC-001` — Evidence Workspace Contract Reconciliation.
6. `UX-PROMPT-002` — Lovable v0.2 reconciliation prompt. Status: `PROPOSED`.
7. `UX-RUNTIME-GAP-001` — pre-Lovable runtime-to-target gap analysis.
8. `UX-ALIGNMENT-001` — pre-execution acceptance template; to be completed after v0.2 execution.
9. UX contract freeze for the Evidence Workspace increment.

The historical order is intentional: the first exploration is preserved as evidence that informed the later governance contract rather than being retrospectively presented as if it had been governed from the start. `UX-DECISION-001` freezes only the durable workspace topology and pane responsibilities; it does not pre-accept the pending Lovable v0.2 implementation.
