# UX-PROMPT-006 — Inspector Accessibility & Density Refinement v0.6

Status: EXECUTED — AUDITED — ACCEPTED

Target: Lovable
Project: Evidence Navigator
Pilot route: `/evidence/session-demo`
Classification: PRESENTATION_ONLY accessibility/density refinement

Depends on:

- accepted UX-PROMPT-005 Lovable baseline `414097bf6f1f2a98a4e0b30e018b9eb26a1fa5a3`;
- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-PROMPT-005-EXECUTION-2026-08-23.md`;
- frozen three-region Evidence Workspace contract.

Prototype from: v0.5
Prototype to: v0.6

## Objective

Improve the accessibility, scanability and navigation efficiency of the existing right-side `Context / QA Inspector` without hiding essential audit evidence, changing domain semantics, introducing persistence, or altering the accepted selection and copy-review flows.

The refinement must reduce avoidable visual density, make keyboard and assistive-technology behavior testable, and clarify the distinction between the global workspace version and the Inspector iteration.

## Exact prompt for Lovable

UX-PROMPT-006 — Inspector Accessibility & Density Refinement v0.6

Trabaja sobre el proyecto existente **Evidence Navigator** y parte exactamente del baseline Lovable aceptado de UX-PROMPT-005:

`414097bf6f1f2a98a4e0b30e018b9eb26a1fa5a3`

No rediseñes la aplicación desde cero.

La fuente normativa es:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-PROMPT-005-EXECUTION-2026-08-23.md`;
- la estructura congelada de tres regiones.

Objetivo principal: mejorar únicamente la **accesibilidad, escaneabilidad, densidad y navegación interna del panel derecho `Context / QA Inspector`**, conservando intactas la semántica, los datos simulados y los flujos aceptados.

### 1. Preservar exactamente

- `AppShell`;
- estructura congelada de tres regiones:
  - izquierda: Evidence Sources;
  - centro: Candidate Metadata / Catalog Proposal;
  - derecha: Context / QA Inspector;
- ruta `/evidence/session-demo`;
- indicador permanente `DSpace · SOLO LECTURA`;
- light/dark mode;
- responsive behavior existente;
- selección de candidatos;
- elegibilidad aprobada;
- flujo de revisión/copia simulada;
- `metadataField`;
- `bindingId`;
- candidate IDs existentes;
- evidence states;
- validation states;
- source/provenance semantics;
- staleness semantics;
- separación entre foco, selección humana y elegibilidad.

### 2. Restricciones congeladas

NO modificar:

- backend ni `src/server.ts`;
- APIs, base de datos, Supabase o autenticación;
- dependencias o servicios externos;
- rutas productivas ni crear rutas nuevas;
- contratos de datos;
- `metadataField`, `bindingId` o vocabularios;
- reglas catalográficas o comportamiento DSpace;
- evidence states, validation states o staleness;
- lógica de elegibilidad, selección o copy-to-draft simulado;
- procedencia existente ni sus valores.

NO implementar LLM, OCR, fetch remoto real, persistencia, escritura en DSpace, draft real, Accept/Reject persistido, review history, publicación ni side effects productivos.

### 3. Densidad y jerarquía del Inspector

Mantener visibles sin expansión:

- valor actual;
- `metadataField`;
- `bindingId`;
- evidence state;
- validation state;
- selección humana;
- procedencia esencial.

Reducir ruido visual sin eliminar evidencia:

- agrupar hashes, IDs secundarios y detalles técnicos repetitivos en un bloque compacto de detalles;
- usar etiquetas breves y consistentes;
- conservar valores exactos y copiables cuando el patrón actual lo permita;
- evitar tarjetas grandes, espacios decorativos y duplicación de la misma información;
- no truncar un identificador de manera que impida auditarlo; si se abrevia visualmente, el valor completo debe seguir disponible de forma accesible.

### 4. Navegación interna

Añadir únicamente navegación PRESENTATION_ONLY compatible con los patrones y dependencias existentes:

- orden lógico de secciones;
- enlaces internos o control compacto de salto entre Resumen, Identidad técnica, Evidencia/procedencia, Validación/QA y Contexto de fuente;
- destino de salto con foco programático visible;
- retorno razonable al control de navegación;
- encabezados semánticos en orden coherente.

No convertir la navegación en una nueva ruta, pestaña de dominio o estado persistente.

### 5. Teclado y foco

Verificar y corregir sólo presentación/interacción accesible:

- recorrido completo con Tab y Shift+Tab;
- indicador de foco visible en light y dark mode;
- activación con teclado de controles interactivos;
- ausencia de trampas de foco;
- foco inicial y restauración razonables en `CopyReviewDialog`;
- cerrar el diálogo sin perder el contexto de trabajo;
- enfocar o navegar el Inspector no debe seleccionar/deseleccionar candidatos.

No añadir atajos globales que entren en conflicto con navegador o tecnologías de asistencia.

### 6. Contraste, zoom y reflow

Comprobar:

- contraste de texto, badges, bordes relevantes y foco visible;
- zoom al 200%;
- reflow sin pérdida de contenido ni solapamientos;
- identificadores técnicos largos sin romper el layout;
- tres regiones conservadas en viewports donde ya están soportadas;
- responsive behavior existente sin redefinir la arquitectura congelada.

No ocultar evidencia primaria para hacer pasar la prueba de densidad o reflow.

### 7. Tecnologías de asistencia

Usar semántica HTML y atributos accesibles existentes o nativos:

- nombres accesibles claros para controles;
- encabezados y regiones comprensibles;
- estados expuestos sin depender sólo del color;
- cambios del candidato enfocado anunciados de manera mesurada;
- apertura/cierre y resultado de acciones simuladas anunciables;
- evitar anuncios duplicados o excesivamente verbosos.

No inventar nuevos estados de dominio para alimentar anuncios.

### 8. Claridad de versionado

Mantener `UX Lab · v0.2` únicamente si representa la versión global del workspace.

Mostrar por separado, de forma compacta y no ambigua:

- `Workspace · v0.2` para la versión global existente;
- `Inspector · v0.6` para esta iteración de presentación.

No reinterpretar estas etiquetas como versiones de backend, esquema, DSpace o contratos de datos.

### 9. Relación Candidate ↔ Inspector

- enfocar un `CandidateRow` actualiza el Inspector sin cambiar selección;
- seleccionar/deseleccionar para copiar no cambia evidence state ni validation state;
- el candidato enfocado y el candidato seleccionado para copiar siguen siendo conceptos distintos;
- navegación, expansión de detalles y anuncios accesibles no crean estados `REVISADO`, `APROBADO`, `CONFIRMADO` o equivalentes;
- el Inspector no edita datos.

### 10. Clasificación UX

Clasificar:

- reducción de densidad y agrupación visual: `PRESENTATION_ONLY`;
- navegación interna y foco programático: `PRESENTATION_ONLY`;
- semántica HTML y anuncios accesibles: `PRESENTATION_ONLY`;
- etiquetas separadas de versión: `PRESENTATION_ONLY`;
- evidence/validation/selection/provenance actuales: `CURRENT_RUNTIME`;
- Accept/Reject persistido y review history: `FUTURE_CONTRACT`;
- nuevos scores, estados o inferencias: `DO_NOT_INTRODUCE`.

### 11. Estados mínimos a comprobar

Comprobar visual y funcionalmente al menos:

1. candidato enfocado no seleccionado;
2. candidato enfocado seleccionado para copiar;
3. candidato no elegible;
4. validation warning/error existente;
5. provenance completa;
6. provenance parcial;
7. valor repetible;
8. identificador técnico largo;
9. `dc.subject.linguiscgroup` exacto;
10. Inspector vacío;
11. navegación completa con teclado;
12. foco visible y restauración del foco en CopyReviewDialog;
13. zoom 200% y reflow;
14. light mode;
15. dark mode;
16. anuncios accesibles sin duplicación;
17. versionado global e iteración del Inspector claramente separados;
18. estructura congelada de tres regiones intacta.

### 12. Fuera de alcance explícito

No implementar:

- edición desde Inspector;
- Accept / Reject;
- persistencia o review history;
- nuevos evidence states o validation states;
- nuevas reglas, confidence scores o recomendaciones;
- backend, APIs, rutas o dependencias;
- LLM, OCR o fetch remoto;
- draft real, escritura/sync DSpace o publicación;
- cambios semánticos catalográficos.

### 13. Entregables esperados

- prototipo v0.6 con refinamiento acotado;
- changelog v0.5 → v0.6;
- matriz de pruebas de teclado, foco, contraste, zoom/reflow y anuncios;
- matriz de estados del Inspector;
- clasificación `CURRENT_RUNTIME` vs `PRESENTATION_ONLY` vs `FUTURE_CONTRACT`;
- lista explícita de elementos no implementados;
- build/typecheck en verde;
- lista de archivos cambiados;
- confirmación de que no se modificaron backend, rutas, dependencias, contratos de datos, `metadataField`, `bindingId`, DSpace ni semántica catalográfica;
- confirmación de que la estructura congelada de tres regiones sigue intacta.

Antes de editar, resume brevemente los cambios que realizarás. Después implementa únicamente este refinamiento.

## Acceptance gate

UX-PROMPT-006 se considera exitoso únicamente si:

1. la información primaria de auditoría permanece visible y exacta;
2. la densidad disminuye sin ocultar ni inventar evidencia;
3. teclado, foco visible y restauración de foco funcionan;
4. contraste, zoom 200% y reflow no causan pérdida de contenido;
5. los cambios relevantes son anunciables sin crear estados de dominio;
6. el versionado global y el del Inspector quedan diferenciados;
7. enfocar o navegar no altera la selección para copiar;
8. `metadataField`, `bindingId`, evidence, validation y provenance permanecen exactos;
9. no hay persistencia ni side effects productivos;
10. no se modifican backend, rutas, dependencias, contratos ni DSpace;
11. la estructura congelada de tres regiones permanece intacta;
12. build/typecheck es verde.

## Execution policy

Execution was explicitly authorized and completed in Lovable on 2026-09-01.

- Resulting Lovable commit: `9301e649fca3f789e16777f96ea88efd7e920fac`
- Edit ID: `edt-9addfe65-8794-4ccc-a262-75fc52abf169`
- Typecheck/build: PASS
- Public audit: PASS WITH MINOR OBSERVATIONS
- Acceptance evidence: `docs/ux/evidence/UX-PROMPT-006-EXECUTION-2026-09-01.md`
- Public route: https://cat-assistant.lovable.app/evidence/session-demo
- Exact credit cost: not returned because the initiating MCP request timed out while Lovable continued and completed the accepted message.

Current state: `EXECUTED — AUDITED — ACCEPTED`.
