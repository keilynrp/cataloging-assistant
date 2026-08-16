# UX Alignment Reviews

This directory stores post-execution evidence that a UX artifact remains aligned with the governed runtime contract.

## Naming

`UX-ALIGNMENT-NNN-<scope>.md`

## Required review sections

Each alignment review should record:

1. Runtime `main` commit reviewed.
2. UX spec and prompt identifiers.
3. Prototype/tool version or edit identifier.
4. Screen/state inventory reviewed.
5. Interaction classification:
   - `CURRENT_RUNTIME`
   - `PRESENTATION_ONLY`
   - `FUTURE_CONTRACT`
   - `REMOVE_OR_CORRECT`
6. Binding/metadata fidelity checks.
7. Evidence-state and validation separation checks.
8. Staleness semantics.
9. Provenance representation.
10. DSpace read-only language.
11. Unsupported/future workflow leakage.
12. Accessibility/responsive observations when relevant.
13. Blocking and non-blocking findings.
14. Verdict: `BLOCKED`, `NEEDS_RECONCILIATION`, or `ACCEPTED_FOR_FREEZE`.

The first planned review is `UX-ALIGNMENT-001` for Evidence Navigator v0.2 after execution of `UX-PROMPT-002`.
