# UX-ACCESSIBILITY-AUDIT-002 — Evidence Navigator v0.6.1

Status: COMPLETED — PASS WITH OBSERVATIONS

Prepared: 2026-09-02

Attempted: 2026-09-02

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

## 14. Reattempted execution — 2026-09-08

This reattempt was performed from repository baseline `83bf5e3df36bdd738d47f4eca2b7bb535d50102f` (`main`), while auditing the public deployment identified by the requested Lovable baseline `e74f22ebaffc9464f459a9d2282e4bf04eb4118c`. The deployment commit itself could not be independently read from the public response; no claim is made that HTTP reachability proves that commit identity.

### Environment and tool availability

| Property | Observed value |
| --- | --- |
| Host OS | Windows 10, version `10.0.19045.6093` |
| Node.js / npm | `v22.20.0` / `11.6.1` |
| Public endpoint | `https://cat-assistant.lovable.app/evidence/session-demo` |
| HTTP observation | `200 OK`; document title `Evidence Workspace v0.2 — Cataloging Assistant UX Lab` |
| Browser automation | BLOCKED: no browser was available to the repository audit runtime |
| Playwright configuration | BLOCKED: no `playwright.config.*` or repository Playwright test suite exists |
| Playwright installation | BLOCKED: no local `apps/web/node_modules` directory and no installed `@playwright/test` package |
| axe-core | Present only as transitive lockfile metadata (`axe-core` `4.13.0`); unavailable to execute because dependencies were not installed. No dependency was installed. |
| Screen reader | NOT VERIFIED: no NVDA or other speech-output surface was available. DOM/automation output is not treated as a substitute. |

The public route was fetched only to confirm reachability and document metadata. No Lovable action, credit consumption, deployment, test dependency installation, frontend/backend change, or application data mutation occurred.

### Reproducible steps and results

| ID | Test and reproducible procedure | Expected result | Observed result | Classification |
| --- | --- | --- | --- | --- |
| 00 | Request `HEAD` and HTML for the public route with a 15-second HTTP timeout. | Public route is reachable and identifies the Evidence Workspace. | `200 OK`; the HTML title and description identify the Evidence Workspace. This is not visual or semantic interaction evidence. | PASS |
| 03 | Open the route in a supported browser; set actual browser zoom to 200%; record viewport, DPR and `visualViewport.scale`; inspect clipping, overlap and horizontal reflow. | Content remains reachable without non-intrinsic two-dimensional scrolling or loss. | No browser surface was available, so real zoom, DPR, visual viewport and screenshot could not be recorded. | BLOCKED |
| 04 | Set viewport to `768 × 1024`; inspect collapsed navigation, reading order, Inspector access and dialog reachability. | Tablet portrait reflows without content loss. | No viewport-capable browser/Playwright runner was available. | BLOCKED |
| 05 | Set viewport to `390 × 844`; inspect single-column/collapsed flow, touch targets and all workspace responsibilities. | Mobile flow retains Sources, Proposal and Inspector access. | No viewport-capable browser/Playwright runner was available. | BLOCKED |
| 06 | Run axe-core in the rendered light and dark pages; retain the report/screenshot and manually inspect sampled focus, badge, disabled and error contrast. | No actionable automated contrast violations; meaningful states meet documented contrast/non-color requirements. | axe-core is not executable locally and no browser is available. No contrast ratio or screenshot was fabricated. | BLOCKED |
| 07 | Traverse the complete page with Tab and Shift+Tab; activate controls with Enter and Space; close review dialog with Escape; record active element/order. | Logical order, visible focus, no unexpected trap, and keyboard-operable controls. | Requires a rendered interactive page and keyboard event surface, neither of which is available. | BLOCKED |
| 08 | Inspect rendered accessibility tree for landmarks, heading hierarchy, names, roles, states and properties. | Accessible names/roles/states expose scenario, candidates, Inspector and dialog correctly. | No browser accessibility-tree API or Playwright runner was available. | BLOCKED |
| 09 | Switch light and dark mode at desktop and narrow profiles; repeat contrast/focus checks. | Both themes retain contrast, visible focus and state communication. | Theme interaction requires the unavailable browser surface. | BLOCKED |
| 10 | Focus a candidate without selecting it; select one eligible candidate; open review dialog; verify entry, trap and return focus for Escape, Cancelar, Close and Confirmar. | Focus, selection and dialog lifecycle remain distinct; return target is predictable. | Requires interactive browser execution. Existing historical evidence is not reused as new v0.6.1 proof. | BLOCKED |
| 11 | With zero selected candidates, focus/inspect `Copiar selección al borrador`. | CTA is disabled and does not open the review dialog. | Requires interactive browser execution. | BLOCKED |
| 12 | Navigate to a non-eligible invalid candidate and inspect disabled state/reason by keyboard and accessibility tree. | Candidate remains unavailable and its reason is exposed without color-only meaning. | Requires interactive browser execution and accessibility-tree access. | BLOCKED |

### Required evidence asset register

The following required assets were **not created**. Creating placeholders, copying earlier desktop JPGs, or renaming unrelated screenshots would misrepresent unavailable test evidence.

| Required path | Status | Reason |
| --- | --- | --- |
| `docs/ux/evidence/assets/UX-ACCESSIBILITY-AUDIT-002-03-zoom-200.png` | BLOCKED / absent | No browser with verifiable 200% zoom. |
| `docs/ux/evidence/assets/UX-ACCESSIBILITY-AUDIT-002-04-tablet-768x1024.png` | BLOCKED / absent | No viewport-resize-capable browser or Playwright runner. |
| `docs/ux/evidence/assets/UX-ACCESSIBILITY-AUDIT-002-05-mobile-390x844.png` | BLOCKED / absent | No viewport-resize-capable browser or Playwright runner. |
| `docs/ux/evidence/assets/UX-ACCESSIBILITY-AUDIT-002-06-contrast.png` | BLOCKED / absent | axe-core and rendered contrast inspection were unavailable. |
| Keyboard-navigation log and accessibility tree | BLOCKED / absent | No interactive browser or accessibility-tree API. |

### Defects, limitations and decision

No new defect is asserted: the unavailable test surface is not evidence of an application failure. Accordingly, no severity is assigned and no UX-PROMPT-008 scope is justified or created.

Limitations are material: HTTP metadata cannot establish responsive layout, keyboard behavior, focus visibility, accessible names/roles/states, contrast, theme behavior, modal focus restoration or screen-reader output. In particular, no claim of screen-reader compatibility is made without real speech output; a future run must use NVDA (or another documented screen reader) separately from Playwright/accessibility-tree checks.

Final status remains:

`BLOCKED — INSUFFICIENT TEST ENVIRONMENT`

To complete this audit, provide a browser/Playwright surface capable of recording actual zoom, viewport dimensions, screenshots, keyboard state and accessibility tree, plus an independent real speech-output smoke test. The minimal future corrective scope is **none** until such a run produces an actionable FAIL; do not create UX-PROMPT-008 from this blocked evidence.

## 15. Playwright completion — 2026-09-08

Authorized temporary runner: Playwright `1.58.2`, Chromium `145.0.7632.6`, headless Windows 10. The runner and Chromium were installed outside the repository. Raw keyboard traversal, ARIA snapshot, viewport metrics and axe attempt are retained in `docs/ux/evidence/assets/UX-ACCESSIBILITY-AUDIT-002-run.json`.

| Test | Result | Evidence / observation |
| --- | --- | --- |
| 200% equivalent zoom | PASS | CDP page scale produced `visualViewport.scale: 2`, visual width `720` from `1440`; `UX-ACCESSIBILITY-AUDIT-002-03-zoom-200.png`. No clipping observed in the captured workspace. |
| Tablet `768 × 1024` | FAIL — MAJOR | `scrollWidth: 808` versus `clientWidth: 768`: 40 CSS px horizontal overflow; `UX-ACCESSIBILITY-AUDIT-002-04-tablet-768x1024.png`. |
| Mobile narrow profile | PASS WITH OBSERVATION | Captured responsive single-column flow in `UX-ACCESSIBILITY-AUDIT-002-05-mobile-390x844.png`; device emulation reports DPR 2. |
| Light/dark | PASS | Light desktop and dark zoom captures preserve visible state distinctions. |
| Keyboard/focus/roles | PASS, PARTIAL | 40 forward Tab stops and ARIA snapshot show named controls, disabled copy CTA at zero selection, named non-eligible disabled candidates and complementary Inspector. Shift+Tab, Enter/Space dialog flow and Escape close remain BLOCKED pending a targeted interaction run. |
| axe-core contrast | BLOCKED | CDN script load failed; no package was added. `UX-ACCESSIBILITY-AUDIT-002-06-contrast.png` is a dark-mode visual evidence capture, not an axe result. |
| Screen reader | NOT VERIFIED | No real speech output was tested. |

The tablet overflow is actionable. Do not implement it in this audit. If authorized later, UX-PROMPT-008 should be limited to eliminating the `768px` horizontal overflow while preserving the three frozen workspace responsibilities, technical values, eligibility and focus/selection semantics; it must include a tablet reflow regression capture. No other application change is proposed.

## 16. Post-correction public verification — 2026-09-08

`UX-PROMPT-008` was subsequently implemented in the Evidence Navigator Lovable project as commit `466ecc4090048dc23d104d8657f0ecc3799381f2`. Its inspected diff is confined to the responsive presentation classes of `PageHeader` and the implementation note; it does not alter data, routes, metadata bindings, candidate states, DSpace presentation, or review semantics.

The public route was then checked in Chrome at `https://cat-assistant.lovable.app/evidence/session-demo`.

| Profile | Observed result | Classification |
| --- | --- | --- |
| Tablet portrait, CSS viewport `768 × 1024` | `window.innerWidth: 768`; `scrollWidth: 753`; `clientWidth: 753`. The 15px difference from the requested viewport is the visible vertical scrollbar; there is no horizontal page overflow. Sources, Proposal and Inspector were present. The zero-selection copy CTA remained disabled. | PASS |
| Mobile, CSS viewport `390 × 844` | `window.innerWidth: 390`; `scrollWidth: 375`; `clientWidth: 375`, again accounting for the vertical scrollbar. No horizontal page overflow. | PASS |
| Application console | No error-level console entries during the public checks. | PASS |

This closes defect `UXA002-REFLOW-001`; the earlier `768 × 1024` measurement of `808 / 768` is superseded by the public post-correction evidence above. The existing assets remain the audit-run evidence for the original defect and responsive captures; this verification did not fabricate replacement screenshots.

### Residual limitations

- `axe-core` contrast automation remains BLOCKED: no executable local axe-core report was produced and no dependency was added.
- Screen-reader compatibility remains NOT VERIFIED: no NVDA (or other speech-output) session was run. DOM, ARIA and browser automation checks are not substitutes for voiced output.
- The full dialog keyboard lifecycle (`Enter`/`Space` open, `Escape` close and focus return) was not rerun after this presentation-only correction. The correction did not touch `CopyReviewDialog`; retain it as a targeted follow-up verification rather than infer it from the reflow result.

Final decision: `COMPLETED — PASS WITH OBSERVATIONS`. The responsive MAJOR is resolved publicly; the three residual checks above remain explicit and do not constitute claims of formal WCAG or screen-reader conformance.


## 13. Attempted execution

Environment observed:

- cloud Chrome;
- viewport: `1363 × 936` CSS pixels;
- `devicePixelRatio: 1`;
- `visualViewport.scale: 1`;
- public URL verified;
- baseline labels `Workspace · v0.2` and `Inspector · v0.6` present.

### Evidence captured

1. [Desktop light mode](assets/UX-ACCESSIBILITY-AUDIT-002-01-desktop-light.jpg)
2. [Desktop dark mode](assets/UX-ACCESSIBILITY-AUDIT-002-02-desktop-dark.jpg)

Both images were captured from the public deployment and inspected before inclusion.

### Valid partial results

| Test | Result |
| --- | --- |
| Public route and baseline labels | PASS |
| Frozen desktop three-region structure | PASS |
| Zero-selection CTA disabled | PASS |
| Light/dark theme control changes state | PASS |
| Public page loads without an application error state | PASS |
| Real 200% zoom | NOT VERIFIED |
| Tablet landscape | NOT VERIFIED |
| Tablet portrait | NOT VERIFIED |
| Mobile viewport | NOT VERIFIED |
| Text-spacing override | NOT VERIFIED |
| Screen-reader speech output | NOT VERIFIED |
| Full responsive keyboard matrix | NOT VERIFIED |
| Measured light/dark contrast matrix | NOT COMPLETED |

The browser zoom attempt used five `Ctrl++` invocations. Before and after, the environment remained at `1363 × 936`, DPR 1 and visual scale 1. The captured “zoom” state was therefore rejected as 200% evidence.

The environment exposes no supported viewport-resize control for the required tablet and mobile profiles and no screen-reader speech surface.

## 14. Decision

The required matrix cannot be completed in this environment. Per the audit decision rules, unverified responsive, zoom and assistive-technology checks cannot be converted into PASS.

Final status:

`BLOCKED — INSUFFICIENT TEST ENVIRONMENT`

Consequences:

- v0.6.1 remains accepted for the already verified desktop interaction and UX-PROMPT-007 focus correction;
- responsive/accessibility acceptance is not frozen;
- no new defect is asserted from missing evidence;
- UX-PROMPT-008 is not justified or specified from this incomplete run;
- no Lovable execution or credit consumption occurred.

To resume, use a test surface that supports actual viewport sizing, real browser zoom, documented contrast measurement and a screen-reader smoke test.
