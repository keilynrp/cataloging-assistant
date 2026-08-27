# UX-ALIGNMENT-001 — Evidence Workspace v0.2

Status: **COMPLETED — ACCEPTED_FOR_FREEZE**

Runtime governance baseline reviewed: repository contracts through VERTICAL-020 and the current UX governance baseline.

Prototype target: Lovable **Evidence Navigator** v0.2

Prompt: `UX-PROMPT-002 — Cierre mínimo de trazabilidad y cobertura contractual`

Spec: `docs/ux/specs/UX-SPEC-001-evidence-workspace-reconciliation.md`

Governance: `docs/ux/UX-GOVERNANCE-CONTRACT.md`

Freeze artifact: `docs/ux/UX-CONTRACT-FREEZE-001-evidence-workspace-v02.md`

VERTICAL-021 gate tracker: #69

## 1. Review objective

Validate that the concrete Lovable Evidence Navigator v0.2 artifact is sufficiently aligned with the governed Evidence Workspace semantics to serve as a frozen UX implementation reference without redefining backend/domain behavior.

This review closes the pre-execution template using the actual Lovable execution record and explicit human approval of UX-PROMPT-002.

## 2. Execution evidence

Lovable execution evidence:

- Project ID: `cf2296b9-adde-4f34-88a0-2b0c5386da94`
- Project name: `Evidence Navigator`
- Published project: `https://cat-assistant.lovable.app`
- Prototype route: `/evidence/session-demo`
- v0.1 base commit: `86b8af9671786dba65e9c8ccec21cb42b03ffa3b`
- UX-PROMPT-002 accepted commit: `7100f3116b4dba4c2273d8e19a1a2c13c783b0eb`
- Lovable edit ID: `edt-88b45477-4eea-4c75-b610-9062e35c67b5`
- Execution timestamp: `2026-08-18T09:44:25Z`
- Human approval timestamp: `2026-08-18T09:47:14Z`
- Human approval message: `APROBACIÓN UX-PROMPT-002`
- Typecheck: `bunx tsgo --noEmit` — exit 0
- Build: reported OK by the Lovable execution
- Latest later Lovable project state inspected during gate closure: completed/ready; later UX increments continued from the frozen v0.2 lineage.

The Lovable diff for the accepted v0.2 closure contains only:

1. new UX governance documentation inside the prototype;
2. new UX-PROMPT-002 execution documentation inside the prototype;
3. one deterministic mock candidate using existing `dc.subject` / `subject`, with evidence state `VERIFICADO`.

No backend, route, dependency, DSpace, metadata-field, binding, or staleness change appears in the UX-PROMPT-002 diff.

### Screenshot evidence boundary

Lovable exposes a project-level generated screenshot for the current project, but it is not a commit-pinned screenshot of `7100f311...`.

Therefore this alignment does **not** claim that a repository-local screenshot set was produced for the exact frozen commit.

The freeze decision is grounded instead in:

- the exact Lovable execution/diff;
- the completed build/typecheck evidence;
- the explicit human audit approval of UX-PROMPT-002;
- the later UX increments that explicitly use `7100f311...` as their approved baseline.

This limitation is non-blocking for the semantic UX contract freeze; it does not constitute a pixel-level accessibility certification.

## 3. Frozen workspace topology

The accepted topology remains exactly:

1. Left — **Evidence Sources**
2. Center — **Candidate Metadata / Catalog Proposal**
3. Right — **Context / QA Inspector**

Result: **PASS**.

No later implementation may change the number or semantic responsibility of these primary regions without a superseding UX decision.

## 4. Interaction classification matrix

| Interaction / element | Classification | Finding |
|---|---|---|
| Inspect/select evidence source | `CURRENT_RUNTIME` / presentation of current source inspection | PASS |
| Add evidence: Text | `CURRENT_RUNTIME` when backed by governed runtime; prototype interaction may remain `PRESENTATION_ONLY` | PASS |
| Add evidence: PDF | `CURRENT_RUNTIME` when backed by VERTICAL-019; no OCR promise | PASS |
| Add evidence: URL | `CURRENT_RUNTIME` conceptually, backend-only fetch under VERTICAL-020 | PASS |
| Deterministic extraction | `CURRENT_RUNTIME` | PASS |
| Candidate focus/selection | `PRESENTATION_ONLY` interaction over runtime candidates | PASS |
| Copy eligible selection to local draft | `CURRENT_RUNTIME` semantics; prototype action remains non-persistent unless wired to production | PASS |
| Accept/Reject | `FUTURE_CONTRACT` if retained | PASS |
| Confidence/model score | `FUTURE_CONTRACT` / absent from current deterministic scenarios | PASS |
| Active assistant action | `FUTURE_CONTRACT` | PASS |
| Raw JSON details | `PRESENTATION_ONLY`, secondary technical disclosure | PASS |
| DSpace write/publish/review workflow | `REMOVE_OR_CORRECT` for current runtime | PASS |

No `FUTURE_CONTRACT` capability is accepted as current runtime by this freeze.

## 5. Binding and metadata fidelity

Verified contract requirements:

- [x] `dc.subject.linguiscgroup` remains literal and must not be normalized.
- [x] `dc.description.registeredLanguage` remains distinct from `dc.language.iso6391`.
- [x] Branch and Grouping remain independent technical fields/bindings.
- [x] Human labels do not override technical identity.
- [x] Repeated values preserve candidate identity/provenance.
- [x] UX-PROMPT-002 reused existing `metadataField: dc.subject` and `bindingId: subject`; it did not invent a new contract.

Result: **PASS**.

## 6. Evidence state, validation and human action

Canonical evidence states remain:

- `EXTRAÍDO`
- `VERIFICADO`
- `INFERIDO`
- `PENDIENTE`
- `GENERADO`

Verified:

- [x] current deterministic output is not represented as LLM inference;
- [x] no current-runtime confidence score is authoritative;
- [x] `INFERIDO` / `GENERADO` remain future-contract concepts until VERTICAL-021 implementation;
- [x] validation remains separate from evidence state;
- [x] human interaction/selection remains separate from evidence state;
- [x] UX-PROMPT-002 added one explicit `VERIFICADO` demonstration candidate with deterministic provenance and human verification history.

Result: **PASS**.

## 7. Staleness

Accepted semantics:

- staleness is session-level against the linked DSpace item source hash;
- immutable remote/PDF/text snapshots remain historical evidence;
- origin changes do not retroactively stale a remote snapshot;
- historical evidence remains inspectable;
- stale-sensitive actions are blocked under backend authority.

UX-PROMPT-002 explicitly preserved these semantics.

Result: **PASS**.

## 8. Source and provenance representation

The v0.2 contract requires structured representation of governed provenance for local PDF, remote sources and candidates, with raw JSON as secondary disclosure.

The accepted UX direction preserves:

- PDF filename/page/extraction/hash/page provenance;
- explicit no-OCR language;
- remote requested/final URL, media type, size, fetched timestamp, hash, redirect count and extraction status;
- candidate label, binding, metadata field, value, evidence state, validation, source/location/excerpt and hashes/extractor when available;
- progressive disclosure for low-level network provenance.

Result: **PASS FOR CONTRACT FREEZE**.

This verdict freezes the information architecture and semantic presentation contract, not a claim that every possible runtime state has pixel-perfect visual coverage.

## 9. DSpace and draft safety

Verified:

- [x] permanent `DSpace · SOLO LECTURA` semantics;
- [x] no current UX is allowed to imply publication/write/submit to DSpace;
- [x] current governed downstream action is local draft copy;
- [x] draftability remains backend-authoritative;
- [x] UX-PROMPT-002 introduced no DSpace behavior.

Result: **PASS**.

## 10. Stable order and repeatability

The frozen contract preserves canonical source/candidate order and individual provenance for repeatable values.

UX-PROMPT-002 added a candidate without redefining ordering semantics or collapsing repeated bindings.

Result: **PASS**.

## 11. Empty / blocked state coverage

The reconciled v0.2 contract includes explicit scenarios for:

- no sources;
- sources without candidates;
- extraction complete;
- no copyable candidates;
- stale session;
- remote fetch disabled;
- PDF without extractable text;
- controlled-vocabulary exact match;
- controlled-vocabulary review required;
- invalid/non-copyable candidate;
- repeatable values.

Result: **PASS FOR FREEZE** based on the accepted prototype contract and human audit approval.

## 12. Accessibility and responsive boundary

The frozen design direction requires:

- visible focus/keyboard affordances;
- status communication not dependent on color alone;
- compact desktop density;
- responsive preservation of source/candidate/inspector context;
- readable technical identifiers.

The Lovable v0.2 lineage preserves responsive behavior and explicit accessible-state requirements.

This review does **not** claim WCAG conformance from screenshots or static diff evidence alone. Full accessibility testing remains an implementation QA concern.

Result: **NON-BLOCKING LIMITATION**.

## 13. Blocking findings

**None remaining for the v0.2 semantic contract freeze.**

The human approval recorded after UX-PROMPT-002 explicitly confirmed:

- three-region structure frozen;
- no backend change;
- no productive route/dependency change;
- no `metadataField` / `bindingId` change;
- no DSpace behavior change;
- no out-of-scope semantic change.

## 14. Non-blocking findings / future work

- Exact commit-pinned screenshot evidence for `7100f311...` is not retained in this repository.
- Pixel-level accessibility and responsive QA remain separate from semantic contract freeze.
- Later UX-PROMPT-003/004/005 increments continue from the accepted v0.2 lineage and do not retroactively change this freeze.
- VERTICAL-021 LLM controls remain `FUTURE_CONTRACT` until that vertical is implemented under its own gates.

## 15. Verdict

```text
UX-PROMPT-002_EXECUTED=YES
UX-PROMPT-002_COMMIT=7100f3116b4dba4c2273d8e19a1a2c13c783b0eb
HUMAN_AUDIT_APPROVAL=YES
THREE_PANE_ARCHITECTURE=PRESERVED
BACKEND_SEMANTICS_CHANGED=NO
BLOCKING_FINDINGS=0
VERDICT=ACCEPTED_FOR_FREEZE
```

**UX-ALIGNMENT-001: ACCEPTED_FOR_FREEZE.**
