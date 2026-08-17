# UX-RUNTIME-GAP-001 — Evidence Workspace

Status: PRE-LOVABLE GAP ANALYSIS

Runtime baseline: `main` @ `ab6ce3ee675484ec0bd01354754618b790af3a71`

Production surface reviewed: `apps/web/app/evidence/[sessionId]/page.tsx`

Normative references:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`
- `docs/ux/UX-VERTICAL-001-evidence-workspace-contract-reconciliation.md`
- `docs/ux/specs/UX-SPEC-001-evidence-workspace-reconciliation.md`
- `docs/ux/prompts/UX-PROMPT-002-evidence-workspace-reconciliation-v02.md`

## 1. Purpose

Record the concrete delta between the current production Evidence Session page and the governed Evidence Navigator v0.2 target before any visual implementation is copied back from Lovable.

This document does not authorize frontend changes. It exists to prevent the prototype from replacing runtime truth and to make later implementation work traceable.

## 2. Current production strengths

The existing runtime already implements several governed behaviors correctly:

- DSpace-linked evidence-session staleness is server-derived and blocks extraction/copy actions when stale.
- Evidence sources are presented as frozen/local snapshots.
- Local PDF upload is constrained to PDF, max 25 MB, text extraction only, no OCR.
- Remote evidence fetch is backend-only and explicitly communicates that the browser does not fetch the URL.
- Remote evidence exposes final URL, MIME/media type, extraction status, byte count when available, redirect count, fetch timestamp and SHA-256.
- Deterministic extraction is explicitly described as deterministic.
- Candidate rows expose binding, metadata field, value, evidence state and validation status.
- Copy-to-draft eligibility is computed from the runtime cataloging contract, not hard-coded by the page.
- Copy-to-draft creates/revises a local PostgreSQL draft and does not write to DSpace.
- No persisted Accept/Reject workflow is implemented.

These are runtime facts and must remain authoritative during UX reconciliation.

## 3. Current production gaps relative to governed UX target

### A. Workspace architecture

Current production is a vertically stacked page. The governed UX direction is a three-zone professional workspace:

1. Evidence Sources.
2. Candidate Metadata / Catalog Proposal.
3. Context / QA / Evidence Inspector.

Gap: source/candidate/provenance comparison requires scrolling and context switching rather than simultaneous inspection.

Classification: `PRESENTATION_ONLY` gap.

### B. Evidence Inspector

Current candidate evidence is primarily exposed through:

- binding/metadata/value labels;
- validation text;
- a `<details>` block containing raw `evidence_json`.

Gap: raw JSON is still the primary deep-inspection mechanism. Governance requires structured provenance first, with raw JSON only as secondary technical disclosure.

Classification: `PRESENTATION_ONLY` gap with strong usability impact.

### C. Candidate selection and copy flow

Current production separates the candidate list from a later copy-to-draft form containing only eligible candidates.

Gap: the cataloger cannot review a candidate in context and select it for copy within the same candidate workspace. The governed UX target should preserve backend draftability while making selection/copy eligibility visible at candidate level.

Classification: `PRESENTATION_ONLY`; backend eligibility remains `CURRENT_RUNTIME` and authoritative.

### D. Source ingestion entry points

Current production renders separate forms for PDF upload and remote URL fetch. Text evidence ingestion is not exposed through a unified `Añadir evidencia` control on this page.

Gap: UX-VERTICAL-001 permits one consolidated `Añadir evidencia` entry point with Text/PDF/URL while retaining current backend actions and constraints.

Classification: `PRESENTATION_ONLY`; no backend behavior change should be inferred.

### E. Source cards / progressive provenance

Current production correctly shows important PDF/remote metadata but uses relatively flat cards.

Gap: requested URL vs final URL, extraction metadata, derived-text hash/extractor and detailed redirect provenance are not organized into an inspector/progressive-disclosure model.

Classification: mostly `PRESENTATION_ONLY`; only fields actually returned by backend may be shown.

### F. Explicit DSpace read-only status

Current page behavior is read-only with respect to DSpace, and copy text states that only PostgreSQL local drafts are changed.

Gap: there is no consistently prominent `DSpace · SOLO LECTURA` status label in the page header/workspace shell.

Classification: `PRESENTATION_ONLY` gap; safety wording should be strengthened.

### G. Empty/blocked states

Current production covers:

- stale session;
- no candidates / extraction CTA;
- no copyable candidates;
- remote fetch disabled via server messages;
- PDF no-extractable-text through source extraction status/messages.

Gap: the target UX should make these states systematic and visually consistent rather than relying on separate forms/messages.

Classification: `PRESENTATION_ONLY`.

### H. Stable-order visibility

Current page maps backend arrays directly, which preserves source/candidate order.

No semantic gap identified. Any future filter/search UI must hide without reordering canonical positions.

Classification: `CURRENT_RUNTIME` behavior to preserve.

### I. LLM/future-state leakage

Current production does not display model confidence, model inference UI, active assistant actions, or current `INFERIDO`/`GENERADO` LLM output.

No current runtime gap. Lovable must not reintroduce these as present capabilities.

Classification: protect as `CURRENT_RUNTIME` boundary; future examples are `FUTURE_CONTRACT` only.

### J. Human review state

Current production does not persist Accept/Reject, which is aligned with governance.

No current runtime gap. Lovable v0.2 must replace mock Accept/Reject for current scenarios with selection/copy eligibility or visibly mark Accept/Reject as future-only.

Classification: current absence is correct; prototype Accept/Reject is `REMOVE_OR_CORRECT` unless explicitly future-labeled.

## 4. Runtime-to-target mapping

| Runtime capability | Current production representation | Governed v0.2 representation | Classification |
|---|---|---|---|
| Evidence session stale | top-level warning; disabled actions | persistent session banner + disabled stale-sensitive actions | `CURRENT_RUNTIME` + presentation refinement |
| Frozen sources | stacked cards | left Source pane, immutable snapshot semantics | `CURRENT_RUNTIME` + presentation refinement |
| PDF upload | standalone form | `Añadir evidencia > PDF`, no OCR | `CURRENT_RUNTIME` + presentation refinement |
| Remote fetch | standalone form, backend-only copy | `Añadir evidencia > URL`, backend-only | `CURRENT_RUNTIME` + presentation refinement |
| Deterministic extraction | form/button + messages | current-runtime extraction action/state | `CURRENT_RUNTIME` |
| Candidate identity | card with binding/field/value | compact candidate row + inspector | `CURRENT_RUNTIME` + presentation refinement |
| Validation | inline status | validation badge/details separate from evidence state | `CURRENT_RUNTIME` + presentation refinement |
| Candidate evidence | raw JSON details | structured provenance + optional raw JSON | `PRESENTATION_ONLY` target |
| Copy eligibility | derived from contract, later form | candidate-level eligibility + selected copy flow | `CURRENT_RUNTIME` + presentation refinement |
| Local draft copy | submit form | `Copiar selección al borrador` | `CURRENT_RUNTIME` |
| DSpace write | absent | visible `DSpace · SOLO LECTURA` | safety presentation |
| Accept/Reject | absent | absent for current runtime; future-only if shown | protect boundary |
| LLM confidence | absent | absent for current runtime | protect boundary |
| Active assistant | absent | disabled/future affordance only | `FUTURE_CONTRACT` |

## 5. Implementation constraints for later production work

When the accepted Lovable v0.2 is eventually implemented in `apps/web`, the frontend must not:

- duplicate draftability rules already supplied by the runtime contract;
- hard-code stale-sensitive mutation rules independently of backend responses;
- rename `dc.subject.linguiscgroup`;
- collapse Branch and Grouping;
- treat `dc.language.iso6391` as Registered Language;
- perform remote fetch from the browser;
- promise OCR;
- invent confidence scores;
- create persistent Accept/Reject state without a backend vertical;
- imply DSpace write/review/publication capability;
- reorder canonical source/candidate arrays by default.

## 6. Candidate production refactor seams

Potential UI-only seams after UX freeze:

- extract source list into a left-pane component;
- extract candidate list/selection into a center-pane component;
- replace raw-JSON-first details with a structured inspector component;
- unify PDF/URL/Text presentation behind a single add-evidence launcher while retaining existing server actions;
- surface contract-derived labels and draftability alongside each candidate;
- preserve existing server actions (`extractEvidence`, `uploadPdfEvidence`, `fetchRemoteEvidence`, `copyEvidenceToDraft`) rather than replacing their semantics;
- keep stale blocking and validation authoritative on the server.

These are refactor candidates, not approved implementation tasks until `UX-ALIGNMENT-001` reaches `ACCEPTED_FOR_FREEZE`.

## 7. Pre-Lovable conclusion

The current production page is semantically stronger than the original Lovable v0.1 prototype in the areas that matter most: staleness, PDF/remote evidence safety, deterministic extraction, draftability, and DSpace read-only behavior.

The largest gap is therefore not missing backend capability but information architecture: production is functionally correct yet comparatively raw, stacked and JSON-heavy. Evidence Navigator v0.2 should solve that presentation problem without changing the runtime model.

This conclusion becomes the reference delta for `UX-ALIGNMENT-001` after Lovable v0.2 execution.