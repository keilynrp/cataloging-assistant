# UX-PROMPT-005 — Inspector Provenance Focus v0.5

Status: PROPOSED — NOT YET EXECUTED

Target: Lovable
Project: Evidence Navigator
Pilot route: `/evidence/session-demo`
Classification: PRESENTATION_ONLY inspector/provenance refinement

Depends on:

- UX-PROMPT-004 execution baseline `1946fc1ce884c23e6fbe2b553d406e9c2f709be1`;
- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-PROMPT-004-EXECUTION-2026-08-21.md`;
- frozen three-region Evidence Workspace contract.

Prototype from: v0.4
Prototype to: v0.5

## Objective

Refine only the right-side `Context / QA Inspector` so that the currently focused candidate can be audited more quickly and precisely without introducing new domain semantics, persistence, backend behavior or productive workflows.

The inspector should make provenance, validation and technical identity easier to inspect while preserving the existing candidate-selection and copy-review flows.

## Exact prompt for Lovable

UX-PROMPT-005 — Inspector Provenance Focus v0.5

Trabaja sobre el proyecto existente **Evidence Navigator** y parte exactamente del baseline Lovable aceptado para continuidad visual de UX-PROMPT-004:

`1946fc1ce884c23e6fbe2b553d406e9c2f709be1`

No rediseñes la aplicación desde cero.

La fuente normativa es:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-PROMPT-004-EXECUTION-2026-08-21.md`;
- la estructura congelada de tres regiones.

Objetivo principal: mejorar únicamente la **auditabilidad visual del panel derecho `Context / QA Inspector`** para el candidato actualmente enfocado.

### 0. Corrección de deuda heredada obligatoria

Antes del refinamiento visual principal, resolver únicamente `UX004-DEBT-001`:

- en `CopyReviewDialog`, mostrar el `bindingId` propio de cada candidato dentro de su fila individual;
- usar exactamente `c.bindingId`;
- no transformar, inferir, normalizar ni sustituir el identificador;
- conservar la agrupación actual por `metadataField`;
- no cambiar reglas de elegibilidad, selección, staleness ni copy flow.

Esta corrección es `PRESENTATION_ONLY` y debe quedar explícitamente reportada como deuda cerrada.

### 1. Preservar exactamente

- `AppShell`;
- estructura congelada de tres regiones:
  - izquierda: Evidence Sources;
  - centro: Candidate Metadata / Catalog Proposal;
  - derecha: Context / QA Inspector;
- ruta `/evidence/session-demo`;
- indicador permanente `DSpace · SOLO LECTURA`;
- densidad compacta y estilo académico/documental;
- light/dark mode;
- responsive behavior existente;
- selección de candidatos;
- elegibilidad aprobada;
- flujo de revisión/copia simulada de UX-PROMPT-004;
- `metadataField`;
- `bindingId`;
- evidence states;
- validation states;
- source/provenance semantics;
- staleness semantics.

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
- contratos de datos;
- `metadataField`;
- `bindingId`;
- vocabularios;
- reglas catalográficas;
- DSpace;
- evidence states;
- validación;
- staleness;
- lógica de elegibilidad;
- lógica de selección;
- comportamiento de copy-to-draft simulado salvo la corrección UX004-DEBT-001.

NO implementar LLM, OCR, fetch remoto real, persistencia, escritura en DSpace, draft real, Accept/Reject persistido, review history, publicación ni side effects productivos.

### 3. Jerarquía visual del Inspector

Cuando exista un candidato enfocado, organizar el Inspector en secciones compactas claramente diferenciadas:

1. **Resumen del candidato**
2. **Identidad técnica**
3. **Evidencia y procedencia**
4. **Validación / QA**
5. **Contexto de fuente** cuando ya exista en los datos simulados

No convertir estas secciones en tarjetas grandes independientes. Mantener densidad de herramienta profesional.

### 4. Resumen del candidato

Mostrar de forma compacta:

- etiqueta humana;
- valor actual;
- evidence state;
- validation state;
- estado de selección para copiar ya existente.

No introducir nuevos estados semánticos.

### 5. Identidad técnica

Mostrar explícitamente, en monospace:

- `metadataField` exacto;
- `bindingId` exacto;
- candidate ID sólo si ya existe en el mock actual y es útil para auditoría.

No derivar un `bindingId` desde la etiqueta humana.
No renombrar `dc.subject.linguiscgroup`.

### 6. Evidencia y procedencia

Usar exclusivamente datos de procedencia ya existentes en el mock/baseline.

Cuando estén disponibles, mostrar:

- fuente;
- source ID;
- ubicación/página/offset o locator existente;
- extractor;
- evidencia textual o fragmento ya disponible;
- hashes existentes si ya forman parte del mock actual.

No inventar provenance fields ni completar valores ausentes.

Si un dato no existe, omitirlo o mostrar una ausencia neutra; no sintetizar información.

### 7. Validación / QA

Mantener visualmente separadas:

- evidence state;
- validation state;
- selección humana para copiar.

El Inspector puede explicar brevemente una validación si ya existe texto/razón en el mock, pero NO debe crear un nuevo motor de reglas, score, confidence o recomendación automática.

No usar `confidence`, porcentajes de certeza ni semáforos inventados.

### 8. Contexto de fuente

Cuando el candidato esté asociado a una fuente existente, permitir una lectura resumida y compacta del contexto de esa fuente utilizando sólo datos disponibles.

Puede incluir nombre/título de fuente, tipo, ubicación y referencia existente.

No introducir fetch, preview remoto real, scraping, descarga o navegación externa.

### 9. Relación Candidate ↔ Inspector

- enfocar un `CandidateRow` debe actualizar el Inspector sin cambiar selección para copiar;
- seleccionar/deseleccionar para copiar no debe cambiar evidence state ni validation state;
- el Inspector no debe introducir un nuevo estado `REVISADO`, `APROBADO`, `CONFIRMADO` o equivalente;
- el candidato enfocado y el candidato seleccionado para copiar son conceptos visualmente distintos.

### 10. Estado vacío

Cuando no exista candidato enfocado, mostrar un estado vacío compacto y útil que indique que debe seleccionarse/enfocarse un candidato para inspeccionar su contexto.

No llenar el espacio con marketing, ilustraciones decorativas ni tarjetas de onboarding grandes.

### 11. Progressive disclosure

Los detalles técnicos secundarios pueden usar un bloque colapsable compacto si ya existe un patrón compatible en el proyecto.

No añadir dependencias para ello.

Los datos primarios —valor, `metadataField`, `bindingId`, evidence state, validación y procedencia esencial— deben permanecer visibles sin requerir expansión.

### 12. Clasificación UX

Clasificar:

- reorganización visual del Inspector: `PRESENTATION_ONLY`;
- secciones compactas y progressive disclosure: `PRESENTATION_ONLY`;
- render de provenance existente: `PRESENTATION_ONLY`;
- corrección UX004-DEBT-001: `PRESENTATION_ONLY`;
- evidence states: `CURRENT_RUNTIME`;
- validation states: `CURRENT_RUNTIME`;
- selection/copy eligibility: `CURRENT_RUNTIME`;
- Accept/Reject persistido: `FUTURE_CONTRACT`;
- confidence score inexistente: `DO_NOT_INTRODUCE`.

### 13. Estados mínimos a comprobar

Comprobar visualmente al menos:

1. candidato enfocado y no seleccionado;
2. candidato enfocado y seleccionado para copiar;
3. candidato no elegible;
4. candidato con validation warning/error existente;
5. candidato con provenance completa;
6. candidato con provenance parcial;
7. valor repetible;
8. campo lingüístico con identificador técnico exacto;
9. `dc.subject.linguiscgroup` sin corrección silenciosa;
10. Inspector vacío;
11. navegación por teclado razonable;
12. responsive behavior manteniendo las tres regiones;
13. light mode;
14. dark mode;
15. CopyReviewDialog mostrando `c.bindingId` individual por candidato.

### 14. Fuera de alcance explícito

No implementar:

- edición desde Inspector;
- Accept / Reject;
- persistencia;
- review history;
- nuevos evidence states;
- nuevas reglas de validación;
- confidence scores;
- recomendaciones automáticas;
- resolución automática de vocabularios;
- backend;
- nuevas rutas;
- nuevas dependencias;
- LLM;
- OCR;
- fetch remoto;
- draft real;
- escritura/sync DSpace;
- publicación.

### 15. Entregables esperados

- prototipo v0.5 con Inspector refinado;
- cierre explícito de `UX004-DEBT-001`;
- changelog v0.4 → v0.5;
- matriz de estados del Inspector;
- clasificación `CURRENT_RUNTIME` vs `PRESENTATION_ONLY` vs `FUTURE_CONTRACT`;
- listado explícito de elementos no implementados;
- build/typecheck en verde;
- lista de archivos cambiados;
- confirmación de que no se modificaron backend, rutas, dependencias, contratos de datos, `metadataField`, `bindingId`, comportamiento DSpace ni semántica catalográfica;
- confirmación de que la estructura congelada de tres regiones sigue intacta.

Antes de editar, resume brevemente los cambios que realizarás. Después implementa únicamente este refinamiento.

## Acceptance gate

UX-PROMPT-005 se considera exitoso únicamente si:

1. `UX004-DEBT-001` queda corregido mostrando `c.bindingId` por candidato en CopyReviewDialog;
2. el Inspector distingue resumen, identidad técnica, provenance y validación sin inventar semántica;
3. `metadataField` y `bindingId` permanecen exactos;
4. evidence state, validation y selección humana permanecen conceptos separados;
5. provenance usa sólo datos existentes;
6. no aparecen confidence scores ni inferencias nuevas;
7. enfocar un candidato no altera su selección para copiar;
8. no hay persistencia ni side effects productivos;
9. no se modifican backend, rutas, dependencias ni DSpace;
10. la estructura congelada de tres regiones permanece intacta;
11. build/typecheck es verde.

## Execution policy

DO NOT execute this prompt in Lovable until credits are available and execution is explicitly authorized.
