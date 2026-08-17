# UX-DECISION-001 — Three-Pane Evidence Workspace Architecture

Status: PROPOSED

Decision scope: Evidence Workspace information architecture

Applies to: Cataloging Assistant human-in-the-loop evidence review surface

Related artifacts:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`
- `docs/ux/UX-VERTICAL-001-evidence-workspace-contract-reconciliation.md`
- `docs/ux/specs/UX-SPEC-001-evidence-workspace-reconciliation.md`
- `docs/ux/prompts/UX-PROMPT-001-evidence-workspace-exploration-v01.md`
- `docs/ux/prompts/UX-PROMPT-002-evidence-workspace-reconciliation-v02.md`
- `docs/ux/reviews/UX-RUNTIME-GAP-001-evidence-workspace.md`
- `docs/ux/reviews/UX-ALIGNMENT-001-evidence-workspace-v02.md`

## 1. Decision

Adopt the three-pane Evidence Workspace as the durable information-architecture baseline for cataloger review workflows:

1. **Left — Evidence Sources**
2. **Center — Candidate Metadata / Catalog Proposal**
3. **Right — Context / QA / Evidence Inspector**

This decision freezes the workspace topology and responsibility boundaries of the three panes. It does **not** freeze visual styling, exact dimensions, component implementation, responsive breakpoints, interaction microcopy, or future domain capabilities.

## 2. Rationale

The Cataloging Assistant is not primarily a metadata form filler. The governed product model is a professional comparison and review workspace where a cataloger evaluates source evidence, proposed metadata, provenance, validation, QA findings and local-draft impact before taking a human action.

A three-pane architecture supports this model because it keeps the three principal review contexts simultaneously addressable:

- where the evidence comes from;
- what metadata is being proposed;
- why the proposal is supported, valid, blocked, or requires review.

The existing production Evidence Session page is semantically aligned with the runtime but vertically stacked and raw-JSON-heavy. The original Lovable v0.1 exploration demonstrated that a dense three-pane workspace is a useful visual direction. The runtime gap analysis therefore identifies information architecture, not missing backend semantics, as the principal UX delta.

## 3. Pane responsibilities

### 3.1 Left pane — Evidence Sources

Primary responsibility: source context and source-level provenance.

It may expose, when supported by runtime:

- immutable evidence source snapshots;
- source kind/media type;
- source identifier/locator;
- filename or requested/final URL;
- extraction status;
- page count or byte count;
- timestamp;
- SHA-256/source hash;
- redirect count;
- source selection state;
- session-level stale context;
- one governed `Añadir evidencia` entry point.

It must not:

- redefine backend source kinds;
- perform browser-side remote fetch;
- imply OCR support;
- treat origin changes as retroactively mutating or staling immutable snapshots;
- independently decide stale-sensitive mutation rules.

### 3.2 Center pane — Candidate Metadata / Catalog Proposal

Primary responsibility: proposed cataloging values and human review selection.

It may expose, when supported by runtime:

- human-readable field label;
- `binding_id`;
- `metadata_field`;
- proposed value;
- canonical evidence state;
- validation status;
- copy eligibility;
- repeatable values while preserving canonical order and identity;
- selection for `Copiar selección al borrador`.

It must not:

- rename or normalize technical field literals;
- collapse distinct bindings sharing a metadata field;
- present validation as evidence state;
- present human selection as evidence state;
- invent persistent Accept/Reject state;
- invent confidence scores for deterministic runtime;
- decide draftability independently of the backend contract.

### 3.3 Right pane — Context / QA / Evidence Inspector

Primary responsibility: structured explanation and provenance for the selected source/candidate context.

It should prefer structured presentation of available data such as:

- field label;
- `binding_id`;
- `metadata_field`;
- value;
- evidence state;
- validation;
- source;
- location/page;
- evidence excerpt;
- source hash;
- extracted-text hash;
- extractor;
- requested/final URL;
- redirect information;
- timestamp;
- QA/diagnostic findings when actually supported.

Raw JSON may be available as progressive technical disclosure but must not be the primary cataloger-facing inspection experience.

## 4. Cross-pane interaction model

The three panes form one coordinated review surface rather than three independent applications.

Expected relationships:

- selecting a source may constrain/highlight related candidates without rewriting canonical candidate order;
- selecting a candidate updates the Inspector to the candidate's evidence/provenance context;
- source, candidate and inspector selections must remain visually legible and auditable;
- filters may hide items but must not silently reorder canonical arrays;
- repeated candidate values retain separate provenance and identity;
- stale-session state is global workspace context, not a source-card-local semantic state.

The backend remains authoritative for eligibility, validation, staleness and allowed mutations.

## 5. Durable semantic constraints

This architecture must preserve the following runtime/domain boundaries regardless of visual implementation:

### Evidence states

Only:

- `EXTRAÍDO`
- `VERIFICADO`
- `INFERIDO`
- `PENDIENTE`
- `GENERADO`

### Linguistic technical fields

Preserve exactly:

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticVariant`
- `dc.description.registeredLanguage`

The literal `dc.subject.linguiscgroup` must not be corrected for visual neatness.

### DSpace boundary

Current architecture is read-only with respect to DSpace.

The workspace should communicate:

`DSpace · SOLO LECTURA`

The governed current action is local-draft copy, not DSpace publication or submission.

### Deterministic/runtime boundary

Through the current baseline:

- deterministic extraction is not AI analysis;
- no current-runtime confidence score is invented;
- LLM-produced `INFERIDO` / `GENERADO` remains future capability until implemented by a later vertical;
- active assistant actions remain future-only unless separately implemented.

## 6. Responsive interpretation

The decision freezes pane responsibilities, not a requirement that all three panes remain simultaneously visible at every viewport width.

Responsive implementations may:

- collapse panes;
- use drawers/sheets;
- switch to tabs or sequential inspection on narrow screens;
- preserve the currently selected source/candidate/inspector context across transitions.

Responsive behavior must not erase provenance, hide safety state, or make it impossible to determine the relationship between source, candidate and evidence.

Desktop remains the primary high-density cataloging workspace.

## 7. What this decision intentionally does not freeze

The following remain open to UX refinement and later freeze:

- exact grid ratios and panel widths;
- resizable-pane behavior;
- typography scale;
- spacing density details;
- exact component library implementation;
- iconography;
- color token details beyond the governed restrained academic/documentary direction;
- exact empty-state illustrations/copy;
- final tablet/mobile interaction pattern;
- final keyboard shortcuts;
- final source/candidate filtering controls;
- future LLM/review workflow UI;
- durable Accept/Reject workflow;
- future DSpace write operations.

## 8. Consequences

### Positive

- establishes a stable UX topology before further domain growth;
- reduces redesign churn across Lovable and production frontend work;
- keeps provenance inspectable beside catalog proposals;
- aligns the UI with the human-in-the-loop product model;
- provides a clear component/refactor seam for the production Evidence Session page;
- allows future capabilities to enter a known workspace without redefining its basic information architecture.

### Costs / constraints

- narrow-screen behavior requires careful state preservation;
- three simultaneous contexts increase density and accessibility requirements;
- component implementations must coordinate selection state without duplicating backend semantics;
- future workflows must fit pane responsibilities or explicitly supersede this decision.

## 9. Supersession rule

Changing the number of primary workspace regions or materially moving their semantic responsibilities requires a new UX decision that explicitly supersedes `UX-DECISION-001`.

Pure presentation changes inside the established responsibilities do not require a superseding decision.

## 10. Acceptance relationship to Lovable v0.2

This decision is intentionally narrower than the pending Evidence Navigator v0.2 acceptance gate.

The three-pane architecture may be accepted as a durable product decision independently of whether the first v0.2 implementation requires visual reconciliation. `UX-ALIGNMENT-001` remains authoritative for deciding whether a concrete Lovable v0.2 artifact is safe to freeze as implementation guidance.

Therefore:

- this decision freezes **architecture topology and pane responsibilities**;
- `UX-ALIGNMENT-001` validates the **specific v0.2 representation**;
- the later UX contract freeze governs the **accepted implementation reference** for the full Evidence Workspace increment.

## 11. Proposed outcome

If accepted, this document becomes the durable architecture baseline for subsequent Evidence Workspace UX specs, prototypes and production refactors.
