# UX-CONTRACT-FREEZE-001 — Evidence Workspace v0.2

Status: **FROZEN / ACCEPTED**

Freeze date: **2026-08-27**

Applies to: Cataloging Assistant Evidence Workspace information architecture and semantic presentation contract.

Lovable project: **Evidence Navigator**

Lovable project ID: `cf2296b9-adde-4f34-88a0-2b0c5386da94`

Frozen Lovable commit: `7100f3116b4dba4c2273d8e19a1a2c13c783b0eb`

Alignment decision: `docs/ux/reviews/UX-ALIGNMENT-001-evidence-workspace-v02.md`

Related gate tracker: #69

## 1. Freeze decision

The Evidence Workspace v0.2 increment is accepted as the durable UX reference for subsequent implementation work.

The freeze is semantic and architectural.

It freezes:

1. the three-pane topology;
2. pane responsibility boundaries;
3. presentation of governed metadata identity;
4. separation of evidence state, validation and human action;
5. DSpace read-only language;
6. session-level staleness semantics;
7. provenance-first inspection model;
8. current-runtime versus future-contract classification.

It does **not** freeze every pixel, spacing value, responsive breakpoint or microcopy.

## 2. Frozen topology

The primary regions are:

```text
LEFT   = Evidence Sources
CENTER = Candidate Metadata / Catalog Proposal
RIGHT  = Context / QA Inspector
```

Any future change to the number of primary regions or their semantic responsibility requires an explicit superseding UX decision.

## 3. Frozen semantic boundaries

### DSpace

```text
DSpace · SOLO LECTURA
```

No UX derived from this freeze may imply current publication, submission, metadata write, workflow transition or administration in DSpace.

### Evidence states

Only the canonical values remain valid:

- `EXTRAÍDO`
- `VERIFICADO`
- `INFERIDO`
- `PENDIENTE`
- `GENERADO`

Evidence state must remain distinct from:

- validation;
- copy eligibility;
- selection;
- human decision;
- QA severity;
- future review workflow.

### Metadata identity

The UX must preserve exact runtime identity.

In particular:

- `binding_id` remains authoritative;
- `metadata_field` remains exact;
- human labels do not redefine technical identity;
- `dc.subject.linguiscgroup` remains literal;
- Branch and Grouping remain independent technical fields;
- repeated values preserve individual identity/provenance.

### Staleness

Staleness remains a property of the Evidence Session against the linked DSpace item source hash.

Immutable evidence snapshots do not become retroactively stale because their remote origin later changes.

### Provenance

The right Inspector remains the primary structured provenance surface.

Raw JSON may exist only as secondary technical disclosure.

### LLM / future capability

Until VERTICAL-021 is implemented and separately accepted:

- LLM-produced `INFERIDO` / `GENERADO` is `FUTURE_CONTRACT`;
- no confidence/model score is current deterministic runtime;
- no active inference control may be labeled current runtime;
- no assistant capability may gain mutable evidence or DSpace powers.

## 4. Execution evidence

UX-PROMPT-002 was executed in Lovable on 2026-08-18.

Observed execution:

```text
COMMIT=7100f3116b4dba4c2273d8e19a1a2c13c783b0eb
EDIT_ID=edt-88b45477-4eea-4c75-b610-9062e35c67b5
TYPECHECK=bunx tsgo --noEmit / EXIT 0
BUILD=OK
```

The accepted diff added only:

- prototype-local UX governance documentation;
- prototype-local UX-PROMPT-002 execution documentation;
- one deterministic mock `VERIFICADO` candidate reusing existing `dc.subject` / `subject`.

No backend, route, dependency, DSpace, metadata-field, binding or staleness change was introduced by UX-PROMPT-002.

## 5. Human acceptance evidence

After execution, the project owner explicitly recorded:

```text
UX-PROMPT-002 queda APROBADO.
SHA congelado y validado:
7100f3116b4dba4c2273d8e19a1a2c13c783b0eb
```

The approval also confirmed:

- Evidence Sources / Candidate Metadata–Catalog Proposal / Context–QA Inspector remains frozen;
- no backend change;
- no productive route or dependency change;
- no metadata-field or binding change;
- no DSpace behavior change;
- no out-of-scope semantic change.

## 6. Relationship to later UX increments

Later UX-PROMPT-003/004/005 work may refine interactions and visual presentation while preserving this freeze.

They do not retroactively rewrite the v0.2 contract.

If a later increment conflicts with this frozen semantic contract, the conflict must be resolved explicitly rather than silently treating the later prototype as authority.

## 7. Accessibility boundary

This freeze does not claim full accessibility certification.

Keyboard/focus semantics, non-color-only state communication, responsive state preservation and technical-identifier readability remain mandatory implementation requirements.

A later implementation QA may discover non-semantic accessibility defects without invalidating this architecture freeze.

## 8. VERTICAL-021 Gate A effect

This freeze satisfies the UX prerequisites stated by VERTICAL-021:

```text
UX-PROMPT-002_EXECUTED=YES
UX-ALIGNMENT-001=ACCEPTED_FOR_FREEZE
UX_CONTRACT_FREEZE=RECORDED
GATE_A=PASS
```

This does **not** authorize VERTICAL-021 implementation by itself.

Gates B, C and D remain independently blocking.

## 9. Supersession rule

This freeze remains authoritative until a later UX decision explicitly supersedes it.

Presentation-only refinements that preserve topology and semantics do not require supersession.

## Final determination

```text
UX_CONTRACT_FREEZE_001=FROZEN
VERTICAL_021_GATE_A=PASS
```
