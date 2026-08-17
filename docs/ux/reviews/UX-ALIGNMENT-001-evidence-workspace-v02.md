# UX-ALIGNMENT-001 — Evidence Workspace v0.2

Status: PRE-EXECUTION TEMPLATE

Runtime baseline: `main` @ `ab6ce3ee675484ec0bd01354754618b790af3a71`

Prototype target: Lovable `Evidence Navigator` v0.2

Prompt: `docs/ux/prompts/UX-PROMPT-002-evidence-workspace-reconciliation-v02.md`

Spec: `docs/ux/specs/UX-SPEC-001-evidence-workspace-reconciliation.md`

Governance: `docs/ux/UX-GOVERNANCE-CONTRACT.md`

## 1. Review objective

Validate that Lovable Evidence Navigator v0.2 represents the current runtime contract faithfully enough to serve as implementation guidance without redefining backend semantics, metadata bindings, evidence states, staleness, draftability, DSpace behavior, or future LLM/review capabilities.

This document is intentionally created before Lovable execution so that the acceptance gate is fixed in advance. Do not mark it accepted until v0.2 has been executed and reviewed against the runtime baseline or a newer `main` commit.

## 2. Required execution evidence

Complete after Lovable v0.2 execution:

- Lovable project ID:
- Project name: `Evidence Navigator`
- Prototype route: `/evidence/session-demo`
- v0.1 base commit: `86b8af9671786dba65e9c8ccec21cb42b03ffa3b`
- v0.2 commit/edit ID:
- execution timestamp:
- preview URL:
- screenshot references:
- Lovable response/changelog:
- runtime `main` commit reviewed:

## 3. Screen/state inventory

Review at minimum:

- normal deterministic extraction session;
- no sources;
- sources with no candidates;
- local PDF with page provenance;
- PDF without extractable text / no OCR;
- remote HTML source;
- remote PDF source;
- remote fetch disabled;
- controlled-vocabulary exact match;
- controlled-vocabulary review required;
- invalid/non-copyable candidate;
- multiple repeatable values;
- no copyable candidates;
- stale evidence session;
- future-only `INFERIDO` / `GENERADO` scenario if retained.

## 4. Interaction classification matrix

Every visible interaction must receive exactly one classification.

| Interaction / element | Classification | Runtime basis | Finding |
|---|---|---|---|
| Inspect/select evidence source | TBD | Current source inspection | |
| Add evidence: Text | TBD | Current evidence ingestion contract | |
| Add evidence: PDF | TBD | VERTICAL-019 | |
| Add evidence: URL | TBD | VERTICAL-020 backend-only fetch | |
| Deterministic extraction | TBD | VERTICAL-017/019/020 | |
| Select candidate | TBD | Presentation/current review interaction | |
| Copy eligible selection to local draft | TBD | Current runtime | |
| Accept/Reject | TBD | Not persisted in current runtime | |
| Confidence/model score | TBD | Not current runtime | |
| Active assistant action | TBD | Not current runtime | |
| Raw JSON details | TBD | Secondary technical presentation | |
| DSpace write/publish/review workflow | TBD | Forbidden in current baseline | |

Allowed classifications:

- `CURRENT_RUNTIME`
- `PRESENTATION_ONLY`
- `FUTURE_CONTRACT`
- `REMOVE_OR_CORRECT`

## 5. Binding and metadata fidelity

Verify all technical fields against the runtime contract.

Required linguistic literals:

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticVariant`
- `dc.description.registeredLanguage`

Checks:

- [ ] `dc.subject.linguiscgroup` is preserved literally.
- [ ] `dc.description.registeredLanguage` is not replaced by `dc.language.iso` or `dc.language.iso6391`.
- [ ] Branch and Grouping are independent fields/bindings.
- [ ] Human labels never override technical identity.
- [ ] Repeated values retain individual identity/provenance.

## 6. Evidence-state / validation / human-action separation

Canonical evidence states only:

- `EXTRAÍDO`
- `VERIFICADO`
- `INFERIDO`
- `PENDIENTE`
- `GENERADO`

Checks:

- [ ] Current deterministic output is not labeled AI-generated/inferred.
- [ ] No confidence score is presented as current runtime output.
- [ ] `INFERIDO` / `GENERADO`, if visible, are explicitly future-state.
- [ ] Validation status is visually distinct from evidence state.
- [ ] Human selection/decision is visually distinct from evidence state.

## 7. Staleness semantics

Checks:

- [ ] Staleness is represented at Evidence Session level against the linked DSpace item source hash.
- [ ] Remote/PDF/text snapshots remain immutable historical evidence.
- [ ] A changed remote origin is not represented as retroactively staling a stored remote snapshot.
- [ ] Historical evidence remains inspectable while stale.
- [ ] Stale-sensitive actions are disabled in accordance with backend behavior rather than a frontend-invented rule set.

## 8. Source/provenance representation

### Local PDF

- [ ] original filename;
- [ ] page count;
- [ ] extraction status;
- [ ] SHA-256/source hash;
- [ ] page-aware provenance where available;
- [ ] explicit no-OCR language;
- [ ] no promise of automatic OCR.

### Remote source

- [ ] requested URL;
- [ ] final URL;
- [ ] media type;
- [ ] byte count where available;
- [ ] fetched timestamp;
- [ ] SHA-256/source hash;
- [ ] redirect count;
- [ ] extraction status;
- [ ] low-level network details relegated to progressive disclosure.

### Candidate inspector

- [ ] field label;
- [ ] `binding_id`;
- [ ] `metadata_field`;
- [ ] value;
- [ ] evidence state;
- [ ] validation;
- [ ] source;
- [ ] page/location;
- [ ] excerpt;
- [ ] source hash;
- [ ] extracted-text hash/extractor when available;
- [ ] requested/final URL and redirect info when applicable;
- [ ] raw JSON is secondary only.

## 9. DSpace and draft safety language

Checks:

- [ ] `DSpace · SOLO LECTURA` is visible and unambiguous.
- [ ] Primary current action is `Copiar selección al borrador` or equivalent local-draft wording.
- [ ] No current CTA implies publish/write/submit to DSpace.
- [ ] `Enviar a revisión` is absent or visibly future-only.
- [ ] Draftability is represented as backend-authoritative.

## 10. Stable order and repeatability

- [ ] Source order is not silently re-sorted.
- [ ] Candidate order is not silently re-sorted.
- [ ] Filters hide but do not redefine canonical order.
- [ ] Repeated metadata values preserve their separate provenance.

## 11. Empty / blocked states

Verify explicit UX for:

- [ ] no sources;
- [ ] sources but no candidates;
- [ ] extraction complete;
- [ ] no copyable candidates;
- [ ] stale session;
- [ ] remote fetch disabled;
- [ ] PDF without extractable text;
- [ ] vocabulary review required;
- [ ] invalid/non-copyable candidate.

## 12. Accessibility and responsive review

Record observations for:

- keyboard focus and selection semantics;
- status communication without color-only dependence;
- compact desktop density;
- tablet collapse behavior;
- narrow-screen access to source, candidate and inspector context;
- readable technical identifiers and provenance.

## 13. Blocking findings

Populate after execution.

A blocking finding is any visible behavior that contradicts current runtime/domain semantics, especially around metadata identity, staleness, evidence states, copy eligibility, DSpace write implications, OCR, browser-side remote fetch, or present-vs-future LLM/review behavior.

## 14. Non-blocking findings

Populate after execution with presentation/accessibility improvements that preserve semantics.

## 15. Verdict

Current verdict: `BLOCKED — AWAITING LOVABLE v0.2 EXECUTION`

Allowed final verdicts:

- `BLOCKED`
- `NEEDS_RECONCILIATION`
- `ACCEPTED_FOR_FREEZE`

The Evidence Workspace UX contract may be frozen only after all blocking findings are cleared.