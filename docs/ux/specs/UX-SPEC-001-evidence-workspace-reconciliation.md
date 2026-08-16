# UX-SPEC-001 — Evidence Workspace Contract Reconciliation

Status: PROPOSED

Depends on:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`
- `docs/ux/UX-VERTICAL-001-evidence-workspace-contract-reconciliation.md`
- VERTICAL-017
- VERTICAL-019
- VERTICAL-020

Target: Lovable Evidence Navigator

Prototype evolution: `v0.1 -> v0.2`

## 1. Purpose

Convert the successful exploratory Evidence Navigator v0.1 into a contract-aligned v0.2 without redesigning the workspace from scratch.

The spec governs UX representation only. Runtime/backend behavior remains authoritative.

## 2. Preserve

Preserve the three-zone workspace:

1. Evidence Sources.
2. Candidate Metadata / Catalog Proposal.
3. Context / QA / Evidence Inspector.

Also preserve compact density, restrained academic/documentary green direction, monospace technical identifiers, evidence-state badges, validation badges, source cards, candidate rows, global shell, light/dark exploration and the disabled contextual assistant affordance as future-state exploration.

## 3. Required reconciliation

### Session staleness

Represent staleness at Evidence Session level against the linked DSpace item source hash. Immutable remote/PDF/text sources remain historical snapshots. When stale, preserve evidence inspection and disable stale-sensitive mutations as directed by backend.

### Linguistic fields

Use exactly:

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticVariant`
- `dc.description.registeredLanguage`

Do not normalize `dc.subject.linguiscgroup`. Do not substitute `dc.language.iso6391` for Registered Language.

### Branch and Grouping

Remove the old mock assumption that Branch and Grouping share a technical field or binding. Treat them as independent runtime fields. Branch is optional secondary genealogical authority.

### Remote evidence

Represent safe cataloger-facing provenance from VERTICAL-020: requested URL, final URL, media type, bytes, fetch timestamp, SHA-256, redirect count and extraction status. Technical progressive disclosure may expose redirect chain, extractor, derived-text hash and per-hop network provenance. Resolved IPs are not primary cataloger-facing content.

### PDF evidence

Represent original filename, page count, extraction status, SHA-256, page provenance and no-extractable-text state. Explicitly state that OCR is not supported.

### Deterministic versus future LLM behavior

Current runtime is deterministic. Do not invent confidence/model scores. Do not label deterministic extraction as AI analysis. `INFERIDO` and `GENERADO` may remain only in visibly future-state scenarios until a later vertical implements them.

### Human decision

Current persisted workflow does not define Accept/Reject. Current-runtime scenarios should use copy eligibility and selection for copy-to-draft. Any retained Accept/Reject interaction must be visibly labeled future/non-persisted.

### Primary action

Use `Copiar selección al borrador` as the governed current-runtime action. Keep `DSpace · SOLO LECTURA` visible. Remove or demote `Enviar a revisión` and other unsupported workflow CTAs.

### Evidence Inspector

Use structured provenance instead of raw JSON as the primary experience. Show candidate identity, value, evidence state, validation, source, location/page, evidence excerpt, hashes/extractor where available, remote URL/redirect provenance where applicable, and technical details through progressive disclosure.

### Add Evidence

One entry point may expose Text, PDF and URL. URL fetch is backend-only. PDF explicitly states no OCR.

## 4. Required runtime scenarios

The v0.2 prototype should cover:

- no sources;
- sources with no candidates;
- deterministic text extraction;
- local PDF with page provenance;
- PDF without extractable text;
- remote HTML;
- remote PDF;
- remote fetch disabled;
- exact controlled-vocabulary match;
- controlled-vocabulary review required;
- invalid/non-copyable candidate;
- session stale;
- repeated values with individual provenance;
- no copyable candidates.

## 5. Future-state scenarios

These may appear only when visibly marked `FUTURE_CONTRACT` or equivalent:

- LLM-produced `INFERIDO`;
- LLM-produced `GENERADO`;
- confidence/model scores;
- persisted Accept/Reject workflow;
- durable review history not supported by runtime;
- active conversational assistant actions.

## 6. Interaction classification gate

Each visible interaction must be classified during review as one of:

- `CURRENT_RUNTIME`
- `PRESENTATION_ONLY`
- `FUTURE_CONTRACT`
- `REMOVE_OR_CORRECT`

No `FUTURE_CONTRACT` behavior may silently cross into production implementation.

## 7. Deliverables

- Lovable Evidence Navigator v0.2.
- Reconciliation changelog v0.1 -> v0.2.
- Screen/state inventory.
- Component inventory.
- Current-runtime vs future-state matrix.
- Explicit removed/corrected-items list.
- UX/backend alignment report (`UX-ALIGNMENT-001`).
- Accepted UX contract freeze for the Evidence Workspace increment.

## 8. Acceptance criteria

A cataloger can quickly determine:

- where a proposed value came from;
- which field and binding it targets;
- whether it is valid;
- whether it requires review;
- whether it is copyable;
- whether the action writes to DSpace;
- whether the session is current against DSpace;
- which exact evidence supports it;
- whether a displayed behavior is current deterministic runtime or future functionality.

The v0.2 prototype cannot become an implementation reference until `UX-ALIGNMENT-001` has no blocking contract mismatches.
