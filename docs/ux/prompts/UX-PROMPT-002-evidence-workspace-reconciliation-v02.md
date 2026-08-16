# UX-PROMPT-002 — Evidence Workspace Contract Reconciliation v0.2

Status: PROPOSED

Target: Lovable

Project: Evidence Navigator

Pilot route: `/evidence/session-demo`

Classification: contract reconciliation prompt

Depends on:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`
- `docs/ux/specs/UX-SPEC-001-evidence-workspace-reconciliation.md`
- `docs/ux/UX-VERTICAL-001-evidence-workspace-contract-reconciliation.md`
- VERTICAL-017
- VERTICAL-019
- VERTICAL-020

Prototype from: v0.1

Prototype to: v0.2

## Exact prompt

UX-VERTICAL-001 — Evidence Workspace Contract Reconciliation v0.2

Trabaja sobre el proyecto existente **Evidence Navigator**.
No rediseñes la aplicación desde cero.
No cambies backend, rutas productivas, contratos, metadata fields, binding IDs, evidence states, DSpace behavior ni reglas catalográficas.

La fuente normativa es:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`
- `docs/ux/UX-VERTICAL-001-evidence-workspace-contract-reconciliation.md`

Objetivo: evolucionar el prototipo actual `/evidence/session-demo` de **v0.1 a v0.2** mediante una reconciliación contractual.

**Preservar sin rediseñar:**
- AppShell
- layout de tres zonas:
  - izquierda: Evidence Sources
  - centro: Candidate Metadata / Catalog Proposal
  - derecha: Context / QA Inspector
- densidad compacta
- dirección visual verde académica/documental
- light/dark mode
- EvidenceSourceCard
- CandidateRow
- EvidenceStateBadge
- ValidationBadge
- InspectorPanel
- identificadores técnicos en monospace
- assistant contextual disabled como affordance futura

**Reconciliar exactamente estos puntos:**

1. **Staleness**
   - eliminar la idea de que una URL remota se vuelve stale porque cambió el origen;
   - modelar `stale` a nivel de Evidence Session contra el DSpace source hash;
   - mostrar banner persistente de sesión stale;
   - mantener la evidencia visible;
   - deshabilitar acciones stale-sensitive;
   - no modificar snapshots históricos.

2. **Campos lingüísticos**
   Usar exactamente:
   - `dc.subject.linguisticFamily`
   - `dc.subject.linguisticBranch`
   - `dc.subject.linguiscgroup`
   - `dc.subject.linguisticVariant`
   - `dc.description.registeredLanguage`

   No corregir el literal `dc.subject.linguiscgroup`.
   No usar `dc.language.iso` ni `dc.language.iso6391` como sustituto de Registered Language.

3. **Branch / Grouping**
   - eliminar cualquier mock que diga que Branch y Grouping comparten campo o binding;
   - representarlos como campos runtime independientes;
   - Branch puede mostrarse como autoridad genealógica secundaria opcional.

4. **Remote evidence**
   Representar source remoto con:
   - requested URL
   - final URL
   - media type
   - bytes
   - fetched_at
   - SHA-256
   - redirect count
   - extraction status

   En “Detalles técnicos” puede mostrarse:
   - redirect chain
   - extractor
   - derived text hash
   - provenance por hop

   No mostrar resolved IPs como información primaria.

5. **PDF**
   Mostrar:
   - original filename
   - page count
   - extraction status
   - SHA-256
   - page provenance

   Incluir estado:
   - “Sin texto extraíble”
   - “OCR no soportado”

   No prometer OCR.

6. **Runtime determinista**
   - eliminar confidence scores de todos los escenarios CURRENT_RUNTIME;
   - no etiquetar extracción determinista como AI;
   - `INFERIDO` y `GENERADO` sólo pueden permanecer en escenarios claramente marcados como FUTURE / VERTICAL-021.

7. **Human review**
   - Accept / Reject no existe todavía como workflow persistido;
   - para current runtime sustituirlo por selección de candidatos elegibles para copy-to-draft;
   - candidatos no copiables deben mostrarse disabled/review-only;
   - si se conserva Accept/Reject en algún escenario, etiquetarlo explícitamente “Future workflow — not current runtime”.

8. **Header actions**
   Eliminar o demotar:
   - Guardar borrador
   - Enviar a revisión

   CTA actual:
   - `Copiar selección al borrador`

   Mostrar permanentemente:
   - `DSpace · SOLO LECTURA`

9. **Evidence Inspector**
   Mantener el panel derecho.
   Debe mostrar información estructurada, no JSON como experiencia principal:
   - field label
   - binding_id
   - metadata_field
   - value
   - evidence state
   - validation
   - source
   - location/page
   - evidence excerpt
   - source hash
   - extracted-text hash cuando exista
   - extractor
   - requested/final URL cuando aplique
   - redirect info
   - timestamp

   Raw JSON sólo en “Detalles técnicos”.

10. **Add Evidence**
    Mantener una sola entrada:
    - `Añadir evidencia`

    Presentar:
    - Texto
    - PDF
    - URL

    URL debe indicar que el fetch ocurre desde backend.
    PDF debe indicar sin OCR.

11. **Estados que debe cubrir v0.2**
    - no sources
    - sources sin candidates
    - extracción completada
    - no copyable candidates
    - session stale
    - remote fetch disabled
    - PDF sin texto extraíble
    - controlled vocabulary exact match
    - controlled vocabulary review required
    - invalid/non-copyable candidate
    - multiple repeatable values

12. **Clasificación UX obligatoria**
    Cada interacción visible debe clasificarse internamente como:
    - `CURRENT_RUNTIME`
    - `PRESENTATION_ONLY`
    - `FUTURE_CONTRACT`
    - `REMOVE_OR_CORRECT`

    Ningún `FUTURE_CONTRACT` debe parecer una capacidad productiva actual.

**Entregables de esta iteración**

- prototipo Lovable v0.2;
- changelog v0.1 → v0.2;
- screen/state inventory;
- component inventory;
- matriz Current Runtime vs Future State;
- listado explícito de elementos eliminados/corregidos;
- no backend integration;
- no LLM;
- no OCR;
- no DSpace write.

Antes de editar, resume brevemente los cambios que vas a realizar. Después implementa únicamente esta reconciliación.

## Expected evidence after execution

Record at minimum:

- Lovable project and resulting edit/commit identifier;
- execution timestamp;
- resulting prototype version;
- changelog v0.1 -> v0.2;
- interaction classification matrix;
- resulting screenshots/preview references where available;
- `UX-ALIGNMENT-001` outcome;
- any backend gaps discovered but not implemented by Lovable.

## Acceptance gate

This prompt is considered successfully executed only when the resulting v0.2 passes `UX-ALIGNMENT-001` against current `main`. The prompt itself does not authorize backend changes or future-contract behavior to enter production.
