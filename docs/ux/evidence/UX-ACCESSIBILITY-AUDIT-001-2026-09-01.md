# UX-ACCESSIBILITY-AUDIT-001 — Evidence Navigator v0.6

Status: COMPLETED — PASS WITH ONE CORRECTIVE DEBT

Recorded: 2026-09-01

Target: public Evidence Navigator v0.6

Public URL: https://cat-assistant.lovable.app/evidence/session-demo

Lovable baseline: `9301e649fca3f789e16777f96ea88efd7e920fac`

Related acceptance evidence: `docs/ux/evidence/UX-PROMPT-006-EXECUTION-2026-09-01.md`

Classification: read-only accessibility and responsive audit

## 1. Scope

This audit evaluated observable public behavior without modifying the application:

- sequential keyboard navigation;
- keyboard activation of candidate focus;
- Inspector internal navigation and programmatic focus;
- distinction between candidate focus and copy selection;
- CopyReviewDialog focus containment and close behavior;
- light/dark theme switching;
- approximate computed-color contrast scan for visible text;
- visible semantic regions, headings, names and states;
- long technical-identifier behavior.

No Lovable execution or credit consumption occurred.

## 2. Environment and limits

The audit used the public deployment in a cloud Chrome browser at approximately 1363 × 936 CSS pixels.

The environment did not expose reliable viewport resizing or browser zoom control. Attempts to invoke browser zoom did not change `devicePixelRatio`, `innerWidth` or `visualViewport.scale`. Therefore:

- real 200% zoom is NOT VERIFIED;
- tablet/mobile reflow is NOT VERIFIED in this audit;
- screen-reader speech output is NOT VERIFIED;
- this audit is not a WCAG conformance certification.

## 3. Results matrix

| Test | Result | Evidence |
| --- | --- | --- |
| Public v0.6 labels | PASS | `UX Lab · Workspace · v0.2` and `Inspector · v0.6` visible |
| Frozen three-region structure | PASS | Sources, proposal and Inspector remain distinct |
| Accessible Inspector region | PASS | complementary region named `Contexto y QA — Inspector` |
| Sequential Tab order | PASS WITH OBSERVATION | Focus reaches global shell, sources, filters, candidate rows and selection controls without a trap |
| Disabled selection controls | PASS | Non-eligible candidates expose disabled checkboxes and textual reasons |
| Candidate keyboard activation | PASS | Candidate row activated with Enter and Inspector updated |
| Focus versus selection | PASS | Keyboard focus/activation did not select candidate; explicit checkbox selection remained separate |
| Inspector internal navigation | PASS | Section control moves programmatic focus to the requested `h4` |
| Return to Inspector navigation | PASS | Each section exposes an accessible return control |
| Inspector control names | PASS | Copy, collapsible and return controls expose accessible names |
| Dialog initial focus | PASS | Initial focus enters `Cancelar` |
| Dialog focus trap | PASS | Tab cycles through `Cancelar`, `Confirmar copia simulada` and `Close` |
| Dialog Escape close | PASS | Escape dismisses the dialog |
| Dialog focus restoration | FAIL | After close, active focus falls to `body`, not the originating `Copiar selección al borrador` CTA |
| Light/dark theme toggle | PASS | Control changes from dark-theme action to light-theme action |
| Visible text contrast scan | PASS, APPROXIMATE | No sampled visible text fell below its computed 4.5:1/3:1 threshold |
| Application console | PASS | No application-origin errors; observed errors came from the cloud-browser extension |
| Real 200% zoom | NOT VERIFIED | Browser zoom could not be changed reliably |
| Responsive viewport matrix | NOT VERIFIED | Fixed cloud viewport |
| Screen reader | NOT VERIFIED | No speech-output test surface |

## 4. Corrective debt

### UX006-DEBT-001 — CopyReviewDialog focus restoration

Status: OPEN

Severity: MINOR ACCESSIBILITY DEFECT

Observed behavior:

1. select an eligible candidate;
2. activate `Copiar selección al borrador`;
3. initial focus enters the dialog;
4. Tab remains trapped inside the dialog;
5. press Escape;
6. dialog closes;
7. focus resolves to `body` instead of the originating CTA.

Expected behavior:

- closing by Escape, Cancel or the close control restores focus predictably to `Copiar selección al borrador`, or to another documented originating control when the CTA is no longer available.

Constraints for correction:

- presentation-only;
- no changes to selection, eligibility, evidence, validation, provenance or staleness;
- no backend, route, dependency, DSpace or persistence changes;
- preserve Radix dialog focus containment;
- do not automatically reopen or submit the dialog;
- verify Escape, Cancel and close-control paths independently.

Recommended vehicle: a minimal `UX-PROMPT-007` focused solely on dialog focus restoration and the remaining verifiable responsive/accessibility checks.

## 5. Observations

- The full page has a long sequential focus order because every candidate row and eligible selection control is independently focusable. This is consistent with the current comparison/review model, but future usability testing should measure efficiency for expert catalogers.
- After programmatic focus lands on a section heading, Tab proceeds through that section's controls. Returning to the navigation chips requires the explicit accessible return button; this matches the implemented design.
- The approximate contrast scan resolves effective opaque ancestor backgrounds and visible computed foreground colors. It is useful screening evidence, not a substitute for a dedicated accessibility engine or manual visual review.

## 6. Verdict

Overall: PASS WITH ONE CORRECTIVE DEBT

UX-PROMPT-006 remains accepted. The audit does not reopen its architectural or semantic acceptance.

Before treating the accessibility work as fully closed:

1. resolve `UX006-DEBT-001`;
2. verify focus restoration across Escape, Cancel and close-control paths;
3. run real 200% zoom and responsive viewport tests in a capable environment;
4. perform a basic screen-reader smoke test.

No code changes were made by this audit.
