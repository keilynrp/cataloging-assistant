# UX/UI Governance Contract

Status: Proposed

Owner: Cataloging Assistant project

Scope: UX/UI governance for the human-in-the-loop cataloging workspace

## 1. Purpose

This document is the normative UX/UI governance contract for the Cataloging Assistant.

Its purpose is to prevent visual prototypes, frontend code, design tools, AI design agents, or future implementation work from redefining backend semantics, metadata contracts, evidence semantics, cataloging rules, or DSpace behavior.

The UX may represent, organize, explain, filter, and expose backend concepts. It must not silently reinterpret them.

## 2. Authority hierarchy

When UX/UI artifacts disagree with runtime behavior, the following authority order applies:

1. Runtime backend contract and tested behavior in `main`.
2. ADRs and vertical specifications merged in `main`.
3. Cataloging contract exposed by the application.
4. This UX/UI governance contract.
5. UX vertical specifications.
6. Lovable/Figma/other visual prototypes.
7. Mock data and exploratory interaction states.

A prototype is never a source of truth for domain semantics.

## 3. Current backend baseline

The UX contract is currently governed by the capabilities consolidated through:

- VERTICAL-017 — Evidence sessions and deterministic external-evidence ingestion.
- VERTICAL-019 — Controlled local PDF ingestion and Golden Set.
- VERTICAL-020 — Secure Remote Evidence Fetch.

The DSpace integration remains read-only.

No UX copy, control, CTA, or workflow may imply that the current application can publish, submit, update, or write metadata to DSpace.

## 4. Core product model

The application is not primarily a metadata form filler.

It is a professional comparison and review workspace where a cataloger evaluates:

`SOURCE -> EXTRACTION -> CANDIDATE -> EVIDENCE/PROVENANCE -> VALIDATION -> HUMAN REVIEW -> LOCAL DRAFT`

The UX must preserve the relationship between:

- proposed value;
- human-readable field label;
- `metadata_field`;
- `binding_id`;
- source;
- evidence/provenance;
- evidence state;
- validation result;
- human action;
- local draft impact.

## 5. Evidence states

The only canonical evidence states are:

- `EXTRAÍDO`
- `VERIFICADO`
- `INFERIDO`
- `PENDIENTE`
- `GENERADO`

The UX must not introduce additional values as `evidence_state`.

UI review labels such as "Sin revisar", "Seleccionado", "Aceptado" or "Descartado" may exist only as presentation or future workflow concepts unless a backend persistence contract explicitly defines them.

`APP_SCHEMA_GAP`, `NORMALIZADO`, validation status, source status, QA severity, and human review status are not evidence states.

## 6. Separation of concerns

The UX must visually distinguish at least three different concepts:

### Evidence state

What kind of evidence status the candidate has.

### Validation

Whether a value satisfies current contract/vocabulary rules.

Examples:

- exact valid match;
- review required;
- invalid;
- unvalidated.

### Human decision

What the cataloger decides to do with the candidate.

Human decision must not be represented as an evidence state.

## 7. Binding and metadata fidelity

The frontend must consume the runtime cataloging contract rather than maintain an independent semantic registry.

Rules:

- Preserve `binding_id` exactly.
- Preserve `metadata_field` exactly.
- Preserve duplicate technical metadata fields as separate bindings where the runtime contract does so.
- Do not infer a binding from a human label.
- Do not rename historical field literals for visual neatness.

Important runtime linguistic fields currently include:

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticVariant`
- `dc.description.registeredLanguage`

The literal `dc.subject.linguiscgroup` must remain unchanged in technical UI because it is the runtime field name.

`dc.language.iso6391` is a distinct field and must not be presented as `dc.description.registeredLanguage`.

## 8. Linguistic hierarchy governance

The UI may explain the conceptual relationship:

`Family -> Branch? -> Grouping -> Variant`

with the following constraints:

- Family is not dependent on Branch.
- Branch is an optional secondary genealogical authority.
- Grouping does not require Branch.
- Variant does not require Grouping to be visually or operationally auto-filled.
- Registered Language is separate from the controlled linguistic hierarchy.
- UI order does not redefine semantic hierarchy.

The frontend must not create fuzzy or implicit mappings among linguistic terms.

## 9. Controlled vocabularies

Vocabulary validation belongs to the backend/domain contract.

The UX may display:

- proposed value;
- exact match result;
- vocabulary name;
- validation explanation;
- review requirement.

The UX must not:

- perform fuzzy replacement as an authoritative action;
- silently normalize an unmatched value;
- invent aliases;
- infer equivalence from lexical similarity;
- replace an active vocabulary decision with mock logic.

## 10. Source model

The UX must represent the current source kinds without inventing new persistence kinds.

Current source concepts include:

- URL locator;
- text snapshot;
- local PDF;
- remote fetched source.

Remote MIME differences such as PDF/HTML/text are represented by source metadata/media type, not by arbitrary frontend source kinds unless the backend contract changes.

## 11. Source snapshots and immutability

Evidence sources are snapshots.

For remote evidence:

- each explicit fetch creates a new append-only source;
- fetching the same URL twice may produce different hashes;
- previous snapshots are not overwritten;
- a changed remote page does not retroactively mutate a stored source.

The UX must not present a remote snapshot as automatically "stale" merely because the origin might later change.

## 12. Staleness

Canonical staleness currently refers to an evidence session becoming stale against the linked DSpace item source hash.

Conceptually:

`evidence_session.base_source_hash != current DSpace item source_hash -> session stale`

When the session is stale, the UX must:

- preserve all evidence for historical inspection;
- show a prominent session-level warning;
- block all evidence mutations and downstream draft mutations that the backend governs as stale-sensitive, including adding local or remote sources, extraction, and copy-to-draft where applicable;
- not imply that individual immutable remote/PDF snapshots are being rewritten.

The backend remains authoritative for the exact stale-session mutation set; the UX must reflect those disabled actions rather than maintain an independent list.

## 13. PDF governance

The UX may expose local and remote PDF evidence, but must preserve these backend guarantees:

- text PDFs only;
- no OCR;
- no JavaScript execution;
- no attachment execution/extraction;
- no link following;
- configured size/page/time limits;
- deterministic extraction;
- page-aware provenance when available.

"Sin texto extraíble" must not promise automatic OCR.

## 14. Remote fetch governance

Remote fetch is backend-only and explicit.

The UX may initiate the server-side action, but must not implement the network request in the browser.

The UI must not weaken or duplicate SSRF security logic.

The backend owns:

- URL validation;
- public-IP policy;
- DNS validation;
- redirect revalidation;
- redirect limit;
- MIME allowlist;
- streaming limits;
- timeouts;
- non-2xx rejection;
- provenance hashes.

The UX may display safe user-facing results such as requested/final URL, MIME, size, timestamp, hash, redirect count and extraction status.

Resolved IPs and low-level network provenance should remain progressive-disclosure technical details rather than default cataloger-facing content.

## 15. Provenance

The UX must make provenance inspectable without requiring the cataloger to read raw JSON.

A candidate inspector should prefer structured presentation of available data such as:

- source;
- source type;
- source identifier;
- page/location;
- quotation/evidence excerpt;
- offsets when useful;
- source hash;
- extracted-text hash;
- extractor;
- requested/final URL for remote evidence;
- redirect information;
- fetch/capture timestamp.

Raw JSON may remain available as a secondary technical/debug view.

## 16. Stable order

Frontend presentation must preserve canonical source and candidate order received from the backend.

- Do not alphabetically reorder by default.
- Do not mutate `position` semantics.
- Filters may hide items but must not rewrite their canonical order.
- Repeated values must preserve individual provenance and candidate identity.

## 17. Copy to draft

The current production action is copy-to-local-draft, not publication.

UX language should prefer:

- "Copiar selección al borrador"
- "Borrador local"
- "DSpace · solo lectura"

Avoid current-runtime CTAs such as:

- "Guardar en DSpace"
- "Publicar"
- "Enviar a DSpace"
- "Enviar a revisión" unless a real review workflow is implemented.

Only candidates eligible under backend rules may be offered as copyable.

The frontend must not independently decide runtime draftability.

## 18. Human review state

The Lovable exploration currently includes mock `Accept / Reject` decisions.

These are useful interaction explorations but are not yet a persisted backend workflow contract.

Until a dedicated human-review vertical defines persistence, audit, actor, timestamps and transitions:

- do not represent Accept/Reject as durable backend truth;
- prefer selection for copy-to-draft for current-runtime flows;
- future review-state UI may remain in prototype scenarios if explicitly labeled as future.

## 19. LLM governance boundary

The current baseline through VERTICAL-020 does not include LLM-assisted extraction.

Therefore:

- no current-runtime confidence score should be invented by the UX;
- no current deterministic extraction should be labeled as AI analysis;
- `INFERIDO` and `GENERADO` may remain in future-state prototype scenarios but must not be presented as current runtime output unless a later vertical implements them;
- an assistant entry point may remain visually reserved/disabled as a future affordance.

A future LLM vertical must preserve the distinction between deterministic evidence, model inference/generation, validation, and human verification.

## 20. DSpace safety language

The UX must consistently communicate that DSpace is read-only in the current architecture.

Recommended status label:

`DSpace · SOLO LECTURA`

Any future DSpace write capability requires a separate explicit ADR/spec and cannot be introduced only through UI work.

## 21. Lovable prototype governance

Current UX exploration project:

- Project: `Evidence Navigator`
- Purpose: visual UX sandbox for the Cataloging Assistant Evidence Workspace.
- Pilot route: `/evidence/session-demo`
- Architecture: three-zone Evidence Workspace (Sources / Candidate Proposal / Context & QA Inspector).

The current architecture and visual direction are considered valuable exploratory assets and should be evolved rather than discarded.

However, its mock semantics must be reconciled with the runtime contract before being treated as implementation guidance.

Known reconciliation areas include:

- session-level staleness versus mock source-level staleness;
- exact linguistic field names/bindings;
- removal of obsolete Branch/Grouping ambiguity assumptions;
- remote source provenance from VERTICAL-020;
- no invented runtime confidence score;
- current copy-to-draft action versus mock Save/Review workflow;
- Accept/Reject as future review workflow rather than current persisted contract.

## 22. UX architecture baseline

The three-zone professional workspace is the preferred current direction:

1. Left: Evidence Sources.
2. Center: Candidate Metadata / Catalog Proposal.
3. Right: Context / QA / Evidence Inspector.

The global shell may include work, cataloging, intelligence and system navigation, but menu items must not imply implemented features unless clearly marked as prototype/future.

The interface should remain:

- desktop-first;
- information-dense;
- calm;
- technical/editorial;
- accessible;
- audit-oriented;
- restrained in decorative effects.

## 23. Change governance

Any UX change that would alter one of the following requires backend/domain review before implementation:

- evidence state;
- source kind;
- metadata field;
- binding identity;
- controlled vocabulary semantics;
- staleness behavior;
- copy eligibility;
- DSpace write behavior;
- agent permissions;
- LLM authority;
- persisted human review workflow.

Pure presentation changes that preserve the contract do not require a domain ADR.

## 24. UX vertical workflow

UX work should follow this sequence:

1. Inspect current runtime contract and merged verticals.
2. Inspect current Lovable/prototype state.
3. Produce a reconciliation delta.
4. Implement visual/prototype changes without redefining backend semantics.
5. Perform UX/backend alignment review.
6. Freeze the accepted UX contract for that increment.
7. Only then introduce the next domain capability.

## 25. Current next step

The next UX increment is:

`UX-VERTICAL-001 — Evidence Workspace Contract Reconciliation`

Its purpose is not to redesign the Evidence Workspace from scratch.

It must evolve the existing Lovable v0.1 prototype into a v0.2 aligned with VERTICAL-017, VERTICAL-019 and VERTICAL-020 while preserving the successful three-pane architecture and visual foundation.
