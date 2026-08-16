# UX-VERTICAL-001 — Evidence Workspace Contract Reconciliation

Status: Proposed

Depends on VERTICAL-017, VERTICAL-019, VERTICAL-020 and `docs/ux/UX-GOVERNANCE-CONTRACT.md`.

## Goal

Reconcile the existing Lovable Evidence Navigator prototype with the current runtime contract without redesigning the workspace from scratch.

Target evolution: `Lovable Evidence Workspace v0.1 -> contract reconciliation -> v0.2`.

## Preserve

Preserve the successful three-zone desktop workspace: Evidence Sources on the left, Candidate Metadata / Catalog Proposal in the center, and Context / QA Inspector on the right. Preserve the compact high-density layout, restrained academic/documentary green direction, technical identifiers in monospace, evidence-state badges, validation badges, source cards, candidate rows, contextual inspector, global navigation shell, light/dark-mode exploration, and disabled contextual assistant affordance as future-state exploration.

## Do not implement

This vertical is UX/UI reconciliation only. Do not modify backend behavior, create or rename metadata fields, create new binding IDs, redefine evidence states, implement DSpace writes, OCR, LLM extraction, browser-side remote fetch, a persisted Accept/Reject workflow without a backend contract, or publication/submission/review workflows that do not exist in runtime.

## Reconciliation deltas

### Session staleness

Replace the mock concept of a remote source becoming stale because its origin changed with the canonical session-level staleness against the linked DSpace item. Show the stale state at session level, keep historical evidence inspectable, and disable backend-governed mutations. Immutable source snapshots remain snapshots.

### Linguistic metadata fidelity

Use the current runtime literals exactly:

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticVariant`
- `dc.description.registeredLanguage`

Do not normalize `dc.subject.linguiscgroup`. Do not present `dc.language.iso6391` as Registered Language.

### Branch and Grouping

Remove the mock assertion that Branch and Grouping share a technical field or are inherently ambiguous. They are independent runtime fields. Branch may be explained as optional secondary genealogical authority.

### Remote source

Represent the VERTICAL-020 remote source using requested URL, final URL, media type, bytes, fetch timestamp, source/body SHA-256, redirect count and extraction status. Technical progressive disclosure may expose redirect chain, per-hop network provenance, extractor and derived-text hash. Resolved IPs are not primary cataloger-facing content.

### Local PDF

Represent original filename, page count, extraction status, source hash and the no-extractable-text state. Keep the no-OCR rule explicit. Show page provenance for candidates when available.

### Deterministic runtime versus future LLM behavior

The current baseline remains deterministic. Remove invented confidence values from current-runtime scenarios and do not label deterministic extraction as AI analysis. Preserve `INFERIDO` and `GENERADO` only in clearly labeled future-state scenarios until a later vertical implements them.

### Human decision

Current prototype Accept/Reject interactions are exploratory. For current-runtime scenarios, prefer copy eligibility and candidate selection, with non-copyable candidates disabled or review-only. The governed primary action is `Copiar selección al borrador`. If Accept/Reject remains in the sandbox, mark it as future human-review workflow and do not imply persistence.

### Header actions

Remove or demote mock current-runtime actions not backed by runtime, especially `Enviar a revisión`. Prefer `Copiar selección al borrador` and visible safety context `DSpace · SOLO LECTURA`.

### Evidence Inspector

Keep the right-panel pattern. Reconcile it to actual provenance and use structured sections for candidate identity, evidence state, validation, source/provenance, evidence excerpt/location, QA/diagnostics when supported, and technical details via progressive disclosure. Raw JSON must not be the primary cataloger experience.

### Add Evidence

The prototype may explore one `Añadir evidencia` entry point with Text, PDF and URL options. Remote URL must be represented as backend-only fetch. PDF must state no OCR.

### Empty and blocked states

Cover no sources; sources present but no candidates; extraction complete; no copyable candidates; session stale; remote fetch disabled; no-extractable-text PDF; validation review required; and invalid/non-copyable candidates.

## Current-runtime scenarios

At minimum v0.2 should cover deterministic text evidence, local PDF with page provenance, PDF without extractable text, remote HTML, remote PDF, controlled-vocabulary exact match, controlled-vocabulary review required, session stale, multiple repeatable values, and no copyable candidates.

## Future-state scenarios

The Lovable sandbox may retain these only when visibly marked as future/not current runtime: LLM-produced `INFERIDO`, LLM-produced `GENERADO`, confidence/model scores, persisted Accept/Reject workflow, durable review history, and active conversational assistant actions.

## UX acceptance questions

A cataloger should be able to answer quickly: where a value came from; which field and binding it targets; whether it is valid; whether it requires review; whether it is copyable; whether the action writes to DSpace; whether the evidence session is current against DSpace; what exact fragment supports the value; and whether the displayed behavior is current deterministic runtime or future LLM behavior.

## Review gate

Before v0.2 is treated as an implementation reference, perform an explicit UX/backend alignment review against `main`. Classify each visible interaction as `CURRENT_RUNTIME`, `PRESENTATION_ONLY`, `FUTURE_CONTRACT`, or `REMOVE_OR_CORRECT`. No `FUTURE_CONTRACT` behavior may silently cross into production frontend implementation.

## Deliverables

Expected outputs are Lovable v0.2, a reconciliation changelog from v0.1, screen/state inventory, component inventory, current-runtime versus future-state matrix, UX/backend alignment report, and an accepted UX contract freeze for this Evidence Workspace increment.

## Exit criteria

UX-VERTICAL-001 is complete when the successful v0.1 architecture is preserved; known semantic mismatches are corrected; all current-runtime labels/actions are backed by backend behavior; future LLM/review behavior is visibly separated from current runtime; staleness is modeled correctly; linguistic fields match runtime exactly; provenance is represented without requiring raw JSON; DSpace read-only behavior is unmistakable; and the final UX/backend alignment review has no blocking contract mismatches.
