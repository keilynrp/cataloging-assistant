# UX-PROMPT-001 — Evidence Workspace Exploration v0.1

Status: EXECUTED

Target: Lovable

Project: Evidence Navigator

Pilot route: `/evidence/session-demo`

Classification: exploratory design prompt

Result: Evidence Navigator v0.1

Historical note: this prompt predates `UX-GOVERNANCE-CONTRACT.md`. It is preserved as design evidence because the resulting exploration informed the later governance contract. It must not be treated as normative where it conflicts with current runtime or UX governance.

## Exact prompt

Create a UX/UI exploration project named "Cataloging Assistant — UX Lab" focused on a single pilot screen: an Evidence Workspace for a professional human-in-the-loop bibliographic cataloging application.

Context and goals:
- This is a visual sandbox only. Do NOT connect to any real backend, database, DSpace instance, external HTTP service, or LLM.
- Use realistic mock data only.
- The production application is a cataloging assistant for librarians/catalogers, with DSpace as read-only source of truth and human approval required before any draft action.
- Optimize for expert users processing many records: professional, information-dense, calm, precise, auditable. Avoid SaaS-marketing aesthetics, oversized cards, excessive whitespace, gradients, glassmorphism, playful illustrations, and decorative animation.
- Build with TypeScript, Tailwind and shadcn/ui.
- The goal is to discover a future Design Foundation incrementally, not to create a complete Design System now.

Pilot screen: /evidence/session-demo

Design a 3-zone Evidence Workspace:
1) Left pane — Evidence Sources
   - compact source list/cards for PDF, URL/HTML and plain text
   - show source type, title/file name, page count or size where relevant, status, timestamp, SHA-256 short hash
   - selected source state
   - primary action: add evidence source
   - source states should include extracted, stale, unsupported, pending

2) Center pane — Candidate Metadata / Catalog Proposal
   - this is the main working surface
   - show metadata candidates grouped by bibliographic/linguistic field
   - each candidate must expose both a human-readable label and technical metadata/binding identity, for example:
     Variante lingüística
     dc.subject.linguisticVariant
     binding: linguistic-variant
   - candidate cards/rows show value, evidence state, validation status, source/page provenance, and actions such as Accept / Reject
   - include examples using these canonical evidence states exactly:
     EXTRAÍDO
     VERIFICADO
     INFERIDO
     PENDIENTE
     GENERADO
   - include linguistic examples such as:
     Lengua de registro
     Agrupación lingüística
     Familia lingüística
     Rama lingüística
     Variante lingüística
   - preserve the conceptual distinction that Family → Group → Variant is a semantic relationship, while UI order is independent
   - make repeated metadata values visually compact

3) Right pane — Context / QA Inspector
   - selected candidate details
   - provenance excerpt / quotation
   - source reference and page
   - vocabulary validation
   - stale/source-hash warning if applicable
   - QA findings
   - review history summary
   - compact assistant entry point, but do NOT implement an AI chat service

Global shell:
- left application sidebar with grouped navigation:
  TRABAJO: Cola de trabajo, Registros, Pospuestos
  CATALOGACIÓN: Evidencias, Borradores, Vocabularios
  INTELIGENCIA: Asistente, Diagnóstico, Perfil de colección
  SISTEMA: Notificaciones, Configuración
- sticky top header with global search, notifications, user menu, theme toggle
- Evidence Workspace should be the active nav item
- responsive behavior: desktop-first, with sensible tablet/mobile collapse
- support light and dark mode

Visual direction:
- retain a restrained academic/documentary green as the primary brand direction around #176B52
- neutral palette with excellent contrast
- use semantic status colors, but never rely on color alone
- use a modern UI font such as Inter or Geist; use monospace for UUIDs, hashes, DOI, metadataField and binding IDs
- compact density by default
- radius and shadows subtle; borders do most of the structural work
- strong focus states and accessible keyboard affordances

Initial reusable patterns to establish visually:
- AppShell
- PageHeader
- EvidenceSourceCard
- MetadataField
- CandidateRow/Card
- EvidenceStateBadge
- ValidationBadge
- InspectorPanel
- Alert
- EmptyState
- compact Button/Input/Select/Textarea

Mock content:
Use one realistic demo record about Indigenous/Maya language or archaeology research, with 3 evidence sources and 8–12 metadata candidates. Include at least one valid vocabulary candidate, one stale warning, one ambiguous/shared-field technical note, and one repeated metadata field.

Important architectural UX principle:
The application is not fundamentally a form filler. It is a comparison/review workspace where the cataloger evaluates evidence, a proposed catalog description, and QA/context before deciding.

For this first iteration, prioritize information architecture, hierarchy, density, states and interaction affordances over visual polish. Build a complete working visual prototype for the pilot screen only, with mocked interactions where useful.

## Execution evidence

Lovable produced the Evidence Navigator project with a three-pane Evidence Workspace, compact academic/documentary visual direction, mocked evidence sources and metadata candidates, evidence-state and validation badges, contextual QA inspector, responsive shell and disabled assistant affordance.

The execution also surfaced semantic assumptions that were later identified as non-normative or obsolete, including source-level staleness, mocked Accept/Reject persistence, confidence values, and outdated linguistic field assumptions. These are explicitly governed by `UX-SPEC-001` and the v0.2 reconciliation prompt.
