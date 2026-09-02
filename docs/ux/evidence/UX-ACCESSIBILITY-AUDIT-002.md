# UX-ACCESSIBILITY-AUDIT-002 — Evidence Navigator v0.6.1

Status: PROPOSED — NOT YET EXECUTED

Prepared: 2026-09-02

Target: public Evidence Navigator v0.6.1

Public URL: https://cat-assistant.lovable.app/evidence/session-demo

Accepted Lovable baseline: `e74f22ebaffc9464f459a9d2282e4bf04eb4118c`

Related evidence:

- `docs/ux/evidence/UX-ACCESSIBILITY-AUDIT-001-2026-09-01.md`;
- `docs/ux/evidence/UX-PROMPT-007-EXECUTION-2026-09-02.md`;
- `docs/ux/UX-GOVERNANCE-CONTRACT.md`.

Classification: read-only responsive and accessibility acceptance audit

Lovable execution: NOT AUTHORIZED

## 1. Purpose

Verify the accessibility and responsive behaviors that could not be completed reliably in UX-ACCESSIBILITY-AUDIT-001, and confirm that the accepted v0.6.1 focus-restoration correction remains stable across representative environments.

This audit must produce evidence and defects only. It must not modify the application, execute Lovable, consume agent credits, change documentation status to accepted without evidence, or claim formal WCAG conformance.

## 2. Frozen invariants

The audit must preserve and verify:

- three-region Evidence Workspace on desktop;
- appropriate responsive collapse without loss of sources, proposal or Inspector access;
- route `/evidence/session-demo`;
- `Workspace · v0.2`;
- `Inspector · v0.6`;
- DSpace read-only presentation;
- separation among candidate focus, copy selection and eligibility;
- exact `metadataField`, `bindingId`, evidence, validation, provenance and staleness;
- `PRESENTATION_ONLY` copy review;
- focus restoration accepted in UX-PROMPT-007.

## 3. Environment matrix

Record browser, operating system, viewport, device-pixel ratio, zoom level, color scheme and input method for every run.

Minimum matrix:

| Profile | Viewport / condition | Required checks |
| --- | --- | --- |
| Desktop | 1440 × 900 or equivalent | three regions, keyboard, dialog, Inspector |
| Tablet landscape | 1024 × 768 or equivalent | collapse, navigation, Inspector access |
| Tablet portrait | 768 × 1024 or equivalent | reflow, reading order, dialogs |
| Mobile | 390 × 844 or equivalent | single-column/collapsed flow, no horizontal loss |
| Desktop zoom | 200% browser zoom | reflow, clipping, overlap, focus visibility |
| Dark mode | desktop and one narrow profile | contrast, states, focus, dialog |
| Text spacing | WCAG 1.4.12 test values when tooling permits | clipping and content loss |

Equivalent dimensions are acceptable only when the actual dimensions are recorded.

## 4. Keyboard acceptance

Verify separately:

1. logical initial focus and skip/navigation behavior;
2. complete forward Tab traversal;
3. complete reverse Shift+Tab traversal;
4. visible focus indicator on every interactive control;
5. candidate focus remains distinct from copy selection;
6. disabled candidates remain unavailable and explain why;
7. Inspector internal navigation moves focus to the intended heading;
8. return controls restore a predictable navigation point;
9. CopyReviewDialog opens by keyboard;
10. focus enters the dialog;
11. focus remains contained;
12. Escape, Cancelar, Close and Confirmar return focus to the CTA;
13. no keyboard trap outside modal behavior;
14. no focus loss after responsive collapse or theme change.

Record any excessively long traversal as a usability observation even when technically operable.

## 5. Responsive, zoom and reflow acceptance

At each required profile verify:

- no two-dimensional scrolling at 200% zoom except for intrinsically two-dimensional content;
- no clipped headings, controls, badges, warnings or technical identifiers;
- no overlap between shell, CTA, scenario selector and pane controls;
- all three workspace responsibilities remain reachable;
- source cards and candidate rows retain complete accessible names;
- long hashes, UUIDs, `metadataField` and `bindingId` wrap or disclose without truncating the underlying value;
- dialogs fit the viewport and their actions remain reachable;
- focus is not placed off-screen without a predictable scroll adjustment;
- touch targets remain usable on narrow profiles;
- the public Lovable badge does not obscure product controls materially.

## 6. Contrast and non-color communication

Use a documented contrast-measurement method rather than visual estimation alone.

Check:

- normal text: at least 4.5:1 where WCAG AA applies;
- large text: at least 3:1;
- focus indicators and meaningful UI component boundaries: at least 3:1 against adjacent colors where applicable;
- light and dark themes;
- evidence and validation badges;
- disabled and error states;
- selected, focused and non-eligible candidates.

Confirm that evidence, validation, selection and error meaning never depends on color alone.

## 7. Assistive-technology smoke test

When a supported screen reader is available, record product, version and browser, then verify:

- page title, landmarks and headings;
- accessible names for scenario, filters, candidate controls and Inspector;
- candidate focus and selection state announcements;
- disabled reasons;
- Inspector section navigation;
- dialog name, description, initial focus and close behavior;
- `PRESENTATION_ONLY` result announcement after simulated confirmation.

If speech output cannot be tested, mark it `NOT VERIFIED`; do not infer success from DOM semantics alone.

## 8. Scenarios

At minimum cover:

- nominal extraction;
- stale session;
- no sources;
- no candidates;
- future/non-runtime scenario;
- zero selected candidates;
- one eligible selected candidate;
- a non-eligible invalid candidate;
- a verified candidate.

Staleness must continue to disable the copy CTA and prevent dialog access.

## 9. Evidence requirements

For every matrix profile:

- capture the initial workspace state;
- capture any responsive/collapsed navigation state;
- capture the Inspector with a focused candidate;
- capture the copy dialog where available;
- capture each discovered defect;
- record DOM/focus evidence for keyboard assertions;
- record measured contrast values and tooling;
- distinguish application console errors from browser-extension messages.

Screenshots must be saved, inspected and linked from the completed audit record.

## 10. Severity and decision rules

Classify findings as:

- BLOCKER — core task or information becomes inaccessible;
- MAJOR — material accessibility failure without a reliable workaround;
- MINOR — localized defect with a usable workaround;
- OBSERVATION — improvement opportunity or unverified risk.

Decision:

- any BLOCKER or MAJOR finding requires a corrective UX prompt;
- MINOR findings may be grouped into one narrowly governed prompt;
- no actionable finding permits v0.6.1 responsive/accessibility acceptance without creating UX-PROMPT-008;
- unverified screen-reader or platform-specific checks must remain explicit and cannot be converted into PASS.

## 11. Deliverables

On completion, update this record with:

- execution date and environments;
- results matrix;
- screenshots and focus evidence;
- contrast measurements;
- defect IDs and severities;
- application-console result;
- overall verdict;
- recommendation to freeze v0.6.1 or define UX-PROMPT-008.

Permitted final statuses:

- `COMPLETED — PASS`;
- `COMPLETED — PASS WITH OBSERVATIONS`;
- `COMPLETED — CORRECTIVE PROMPT REQUIRED`;
- `BLOCKED — INSUFFICIENT TEST ENVIRONMENT`.

## 12. Execution policy

This document authorizes no application changes and no Lovable execution.

Current state: audit plan saved only. No audit run, defect conclusion, UX-PROMPT-008 specification or credit consumption exists.
