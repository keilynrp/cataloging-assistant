# UX-PROMPT-003 — Candidate Selection & Copy-to-Draft Affordance v0.3

Status: RECONSTRUCTED — NOT YET EXECUTED

Target: Lovable

Project: Evidence Navigator

Pilot route: `/evidence/session-demo`

Classification: presentation-only interaction refinement

Historical status: retrospective reconstruction

## Reconstruction notice

This artifact was reconstructed on 2026-08-19 from the approved `UX-PROMPT-002` baseline, the Lovable audit history, `docs/ux/UX-GOVERNANCE-CONTRACT.md`, and the constraints preserved for the subsequent UX iteration. It is **not claimed to be a verbatim recovery of the original lost prompt**.

Directly supported historical facts:

- `UX-PROMPT-002` was approved and frozen in Lovable at prototype snapshot SHA `7100f3116b4dba4c2273d8e19a1a2c13c783b0eb`.
- The frozen structure is Evidence Sources / Candidate Metadata–Catalog Proposal / Context–QA Inspector.
- `Copiar selección al borrador` is the current CTA established by the v0.2 reconciliation.
- Accept / Reject is not a persisted CURRENT_RUNTIME workflow.
- DSpace remains read-only.
- No backend, LLM, OCR, real remote fetch, persistence, or DSpace write is authorized in this UX sandbox.

Reconstructed/inferred purpose:

- refine the candidate-selection interaction and the copy-to-draft affordance before introducing any separate pre-copy review/confirmation step in a later iteration.

Depends on:

- Lovable frozen prototype snapshot `7100f3116b4dba4c2273d8e19a1a2c13c783b0eb` (Lovable snapshot, not a GitHub commit);
- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/prompts/UX-PROMPT-002-evidence-workspace-reconciliation-v02.md`;
- the approved three-region Evidence Workspace contract.

Prototype from: v0.2

Prototype to: v0.3

## Exact reconstructed prompt

UX-PROMPT-003 — Candidate Selection & Copy-to-Draft Affordance v0.3

Trabaja sobre el proyecto existente **Evidence Navigator**, partiendo del snapshot Lovable congelado y aprobado:

`7100f3116b4dba4c2273d8e19a1a2c13c783b0eb`

No rediseñes la aplicación desde cero.

La fuente normativa es:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`
- el estado aprobado de `UX-PROMPT-002`

Objetivo: refinar exclusivamente la interacción de **selección de candidatos elegibles** y el affordance actual **`Copiar selección al borrador`**, sin introducir todavía un workflow persistido de revisión, aceptación, rechazo, confirmación o escritura.

### 1. Preservar exactamente

- `AppShell`;
- layout congelado de tres regiones:
  - izquierda: Evidence Sources;
  - centro: Candidate Metadata / Catalog Proposal;
  - derecha: Context / QA Inspector;
- ruta `/evidence/session-demo`;
- densidad compacta;
- dirección visual verde académica/documental;
- light/dark mode;
- responsive behavior existente;
- `EvidenceSourceCard`;
- `CandidateRow`;
- `EvidenceStateBadge`;
- `ValidationBadge`;
- `InspectorPanel`;
- identificadores técnicos en monospace;
- indicador permanente `DSpace · SOLO LECTURA`;
- semántica contractual de `metadataField`, `bindingId`, evidence states, validación y staleness.

### 2. Restricciones congeladas

NO modificar:

- backend;
- `src/server.ts`;
- APIs;
- base de datos;
- Supabase;
- autenticación;
- dependencias;
- servicios externos;
- rutas productivas ni crear rutas nuevas;
- `metadataField`;
- `bindingId`;
- vocabularios;
- reglas catalográficas;
- comportamiento DSpace;
- evidence states;
- semántica de staleness.

NO implementar:

- LLM;
- OCR;
- fetch remoto real;
- persistencia;
- escritura en DSpace;
- Accept / Reject persistido;
- review history persistido;
- confirmación pre-copy separada en esta iteración.

### 3. Selección de candidatos

Refinar el comportamiento visible de selección del escenario `CURRENT_RUNTIME`:

- cada candidato **copiable** debe poder seleccionarse mediante un control compacto y accesible;
- la selección representa exclusivamente **elegibilidad/intención de copiar al borrador**, no aceptación catalográfica ni verificación humana;
- seleccionar o deseleccionar un candidato NO debe modificar:
  - `evidence state`;
  - `validation`;
  - procedencia;
  - QA;
  - review history;
  - `metadataField`;
  - `bindingId`;
- candidatos no copiables deben mantener el control disabled y mostrar una razón legible;
- el estado seleccionado debe distinguirse visualmente sin depender sólo del color;
- valores repetibles deben conservar la presentación compacta y permitir selección individual;
- el foco y la operación por teclado deben seguir siendo evidentes.

### 4. Elegibilidad y razones de bloqueo

Representar explícitamente al menos estas razones:

- valor fuera de vocabulario / `not-in-vocabulary`;
- valor inválido;
- ausencia de valor extraído;
- candidato `FUTURE_CONTRACT`;
- sesión stale.

No transformar automáticamente un candidato bloqueado en copiable.

No introducir una acción que parezca resolver semánticamente el bloqueo.

### 5. CTA `Copiar selección al borrador`

Mantener una única CTA primaria:

`Copiar selección al borrador`

Comportamiento de presentación en v0.3:

- disabled cuando no hay candidatos copiables seleccionados;
- mostrar o acompañar con un contador compacto de selección;
- disabled cuando la Evidence Session está stale;
- cuando está stale, la razón debe ser comprensible y visible/accesible;
- no escribir realmente en un draft, backend, DSpace ni persistencia;
- no simular éxito productivo;
- cualquier feedback local debe estar etiquetado o ser inequívocamente `PRESENTATION_ONLY`.

**No añadir todavía un diálogo, drawer o pantalla de revisión/confirmación previa a la copia.** Ese patrón queda fuera de esta iteración.

### 6. Staleness

Preservar exactamente la semántica aprobada:

- stale se determina a nivel de Evidence Session contra el DSpace source hash;
- la evidencia permanece visible;
- los snapshots históricos no se modifican;
- las acciones stale-sensitive permanecen bloqueadas;
- la selección existente puede visualizarse, pero no debe permitir una copia efectiva mientras la sesión esté stale.

No reintroducir staleness basada en cambios de una URL remota.

### 7. Inspector y trazabilidad de selección

El panel derecho continúa mostrando la información estructurada del candidato seleccionado.

No convertir la selección para copy-to-draft en un nuevo evidence state.

Cuando ayude a la comprensión, puede mostrarse una indicación compacta de:

- `Seleccionado para copiar`;
- `No elegible para copiar` + razón;

pero estas etiquetas son de interacción/presentación y no forman parte del contrato semántico de metadatos.

### 8. Clasificación UX

Clasificar internamente las interacciones de esta iteración:

- selección local de candidato: `PRESENTATION_ONLY`;
- contador de seleccionados: `PRESENTATION_ONLY`;
- filtros/búsqueda: `PRESENTATION_ONLY`;
- CTA visual `Copiar selección al borrador`: `PRESENTATION_ONLY` en este sandbox;
- reglas de elegibilidad derivadas del contrato actual: `CURRENT_RUNTIME`;
- bloqueo por session stale: `CURRENT_RUNTIME`;
- Accept / Reject persistido: `FUTURE_CONTRACT` y no visible como capacidad actual;
- cualquier semántica incorrecta heredada: `REMOVE_OR_CORRECT`.

Ninguna interacción `PRESENTATION_ONLY` debe aparentar persistencia o escritura real.

### 9. Estados mínimos a comprobar

La iteración debe comprobar visualmente:

1. cero candidatos seleccionados;
2. un candidato copiable seleccionado;
3. múltiples candidatos seleccionados;
4. valores repetibles seleccionados individualmente;
5. candidato no copiable;
6. mezcla de candidatos copiables y no copiables;
7. ningún candidato copiable;
8. session stale con selección visible pero CTA bloqueada;
9. candidato FUTURE_CONTRACT no elegible;
10. navegación por teclado y focus visible en los controles de selección.

### 10. Fuera de alcance explícito

No implementar en UX-PROMPT-003:

- modal/drawer de revisión final antes de copiar;
- confirmación irreversible;
- persistencia de selección;
- mutación de borradores;
- publicación;
- Accept / Reject productivo;
- cambios de backend;
- nuevas rutas;
- cambios semánticos catalográficos;
- LLM;
- OCR;
- fetch real;
- DSpace write.

### 11. Entregables esperados

- prototipo v0.3 con selección refinada;
- changelog v0.2 → v0.3;
- matriz de estados de selección/elegibilidad;
- clasificación `CURRENT_RUNTIME` vs `PRESENTATION_ONLY` vs `FUTURE_CONTRACT`;
- listado de elementos explícitamente no implementados;
- build/typecheck disponible en verde;
- confirmación expresa de que no se modificó backend ni la estructura congelada de tres regiones.

Antes de editar, resume brevemente los cambios que vas a realizar. Después implementa únicamente este refinamiento de selección y affordance de copia.

## Expected evidence after execution

Record at minimum:

- Lovable project;
- base snapshot SHA;
- resulting edit/commit identifier;
- execution timestamp;
- resulting prototype version v0.3;
- changed files;
- build/typecheck result;
- selection/elegibility state matrix;
- confirmation that the three-region structure remained unchanged;
- confirmation that backend, routes, dependencies, metadataField, bindingId, DSpace behavior and cataloging semantics remained unchanged;
- screenshot/preview references where available.

## Acceptance gate

This reconstructed UX-PROMPT-003 is considered successfully executed only when:

1. selection is clearly distinguished from cataloging acceptance/verification;
2. non-copyable candidates cannot be selected for copy;
3. stale sessions block copy-sensitive interaction without hiding evidence;
4. no pre-copy confirmation step has been introduced yet;
5. no backend or semantic contract changes occur;
6. the three-region structure remains frozen;
7. build/typecheck is green.

## Reconstruction confidence

- **High confidence:** frozen baseline, structural constraints, copy-to-draft CTA, eligibility/non-copyability semantics, stale behavior, no backend/LLM/OCR/DSpace write.
- **Moderate confidence / inferred:** this prompt's specific role as a selection-affordance refinement immediately before a later pre-copy review step.
- **Not recovered:** verbatim wording, original filename, original version label, or proof that a UX-PROMPT-003 text was ever committed or sent to Lovable.
