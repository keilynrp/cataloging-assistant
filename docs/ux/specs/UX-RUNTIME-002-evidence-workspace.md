# UX-RUNTIME-002 — Evidence Workspace runtime implementation

Status: IMPLEMENTED — ready for review

Repository baseline: 83bf5e3df36bdd738d47f4eca2b7bb535d50102f.
Authorization: explicit owner approval of the runtime implementation plan.
Governance: UX-CONTRACT-FREEZE-001 and UX-ALIGNMENT-001.
Presentation reference: Evidence Navigator, including UX-PROMPT-007 focus restoration
and UX-PROMPT-008 narrow viewport reflow.

## Runtime mapping

| Surface | Runtime authority | Implementation |
| --- | --- | --- |
| Sources | EvidenceSession.sources in backend order | Left region, source inspection and immutable provenance |
| Proposal | EvidenceSession.candidates in backend order | Center region, local filtering, inspection and independent selection |
| Inspector | candidate evidence_json/validation_json and matching source | Right region; quote, page/line/offsets, technical identity, hashes and source metadata; raw JSON secondary |
| Eligibility | Existing server-page contract draftable_fields and invalid-validation rule | Server supplies candidate IDs; backend still validates submissions |
| Staleness | EvidenceSession.stale | Session warning and disabled sensitive actions; history remains inspectable |
| PDF / URL | Existing uploadPdfEvidence/fetchRemoteEvidence | Existing server forms inside disclosure; no browser fetch |
| Copy | Existing copyEvidenceToDraft | Review dialog followed by attributed, versioned local draft copy |
| Shell | Existing production layout/navigation | Retained; flex child permits shrinking for reflow |

## Scope and boundaries

The production route stays /evidence/[sessionId]. There is no demo/scenario
route, copied mock dataset, new backend endpoint, dependency, or persistence model.
Text evidence remains available through session creation; this increment does not
invent an add-text endpoint for existing sessions.

Local UI state contains only focus, source inspection, filtering and selected IDs.
Filtering preserves canonical order and retains selections. Submission derives IDs
from the latest server candidate order and server eligibility list.
Evidence state, validation and human selection remain separate.

The review dialog uses the native modal dialog: Escape/Cancel restores the trigger
and preserves selection. Confirm submits the existing server action with author,
note, draft identity and expected version. Successful navigation uses the existing
server result message; it does not simulate persistence or change lifecycle.

DSpace remains read-only. No LLM/OCR, confidence, persisted Accept/Reject,
publication, workflow or domain-contract change is included.

## Acceptance and recorded validation

- TypeScript and the existing web unit tests pass. The production Docker web
  build completed successfully. Full-repository lint and backend test outcomes
  are recorded below because they include existing, unrelated repository debt.
- Sources/Proposal/Inspector remain accessible at desktop, 768x1024, 390x844
  and a documented zoom/reflow condition, in both themes.
- Inspecting candidates does not select them; repeated fields remain distinct.
- Zero-selection, stale and ineligible cases cannot submit through the UI.
- Review preserves selection on cancellation and returns focus to its trigger.
- Existing remote/PDF failure messages and source evidence remain inspectable.
- Automated contrast and keyboard evidence are recorded separately from NVDA.
  No screen-reader compatibility is claimed without actual voice-output testing.

### Automated runtime evidence — 2026-09-08

Environment: WSL, Node 22.20.0, Next.js 16.3.0, Playwright 1.58.2 with its
Chromium runtime, and the already-transitive axe-core package. The fixture API
is process-local and in-memory; it never reads or writes DSpace or PostgreSQL.

`apps/web/tests/evidence-workspace.mjs` passed against the production route
adapter and a controlled fixture. It verified all of the following:

- inspection without selection; independent selection; filtered selections
  retained in server order; valid, invalid and non-draftable candidates;
- zero-selection, stale and unlinked disabled actions; empty state; remote
  public-target rejection message; attributed, versioned draft-copy payload;
- Enter, Space, Escape, Cancel, close control, forward/reverse Tab containment
  and return focus from the native review dialog;
- no horizontal overflow at 1440x900, 768x1024, 390x844 and 720x450 in light
  and dark mode; and zero axe `color-contrast` violations scoped to the
  workspace.

Saved visual evidence:

- `docs/ux/evidence/assets/UX-RUNTIME-002/1440-light.png`
- `docs/ux/evidence/assets/UX-RUNTIME-002/1440-dark.png`
- `docs/ux/evidence/assets/UX-RUNTIME-002/768-light.png`
- `docs/ux/evidence/assets/UX-RUNTIME-002/768-dark.png`
- `docs/ux/evidence/assets/UX-RUNTIME-002/390-light.png`
- `docs/ux/evidence/assets/UX-RUNTIME-002/390-dark.png`
- `docs/ux/evidence/assets/UX-RUNTIME-002/720-light.png`
- `docs/ux/evidence/assets/UX-RUNTIME-002/720-dark.png`

The screenshots were visually reviewed: the three panes are visible at desktop
size and stack without clipping at narrow widths. Long source identifiers wrap
inside their panes.

### Repository checks

- `npm test` in `apps/web`: PASS (3 existing tests).
- `docker compose build web`: PASS (Next compilation, TypeScript and static
  generation completed).
- Final `npm run typecheck` after the keyboard-focus correction: PASS.
- `make lint`: FAIL in the baseline backend with 45 pre-existing Ruff findings;
  none are in files changed by this increment.
- `make test` in the isolated verification worktree: BLOCKED during collection
  by three existing tests that assume a deeper checkout path
  (`Path(__file__).resolve().parents[3]`). No application test executed, and no
  backend source was modified.

### Remaining manual limitations

The 720x450 check is a reduced-width reflow condition, not a claim of browser
zoom at 200%. A real 200% browser-zoom pass and NVDA voice-output pass remain
manual release checks. Automated accessibility-tree and Playwright evidence do
not substitute for them. This increment does not claim screen-reader
compatibility beyond the tested names, roles, states and keyboard behavior.
