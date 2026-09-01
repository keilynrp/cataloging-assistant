# UX-PROMPT-007 — CopyReviewDialog Focus Restoration v0.6.1

Status: PROPOSED — NOT YET EXECUTED

Target: Lovable

Project: Evidence Navigator

Pilot route: `/evidence/session-demo`

Classification: PRESENTATION_ONLY accessibility defect correction

Depends on:

- accepted UX-PROMPT-006 Lovable baseline `9301e649fca3f789e16777f96ea88efd7e920fac`;
- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-PROMPT-006-EXECUTION-2026-09-01.md`;
- `docs/ux/evidence/UX-ACCESSIBILITY-AUDIT-001-2026-09-01.md`;
- frozen three-region Evidence Workspace contract.

Prototype from: v0.6

Prototype to: v0.6.1 corrective patch

Debt addressed: `UX006-DEBT-001`

## Objective

Correct only the focus-restoration defect observed in the public `CopyReviewDialog`: after the dialog closes, keyboard focus must return predictably to the control that opened it, normally `Copiar selección al borrador`.

This is a narrow accessibility correction. It must not redesign the dialog, change candidate selection or eligibility, alter evidence semantics, introduce persistence, or modify the Inspector v0.6 refinement.

## Exact prompt for Lovable

UX-PROMPT-007 — CopyReviewDialog Focus Restoration v0.6.1

Trabaja sobre el proyecto existente **Evidence Navigator** y parte exactamente del baseline Lovable aceptado de UX-PROMPT-006:

`9301e649fca3f789e16777f96ea88efd7e920fac`

No rediseñes la aplicación.

La fuente normativa es:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-PROMPT-006-EXECUTION-2026-09-01.md`;
- `docs/ux/evidence/UX-ACCESSIBILITY-AUDIT-001-2026-09-01.md`;
- la estructura congelada de tres regiones.

Objetivo único: cerrar `UX006-DEBT-001` corrigiendo la restauración de foco de `CopyReviewDialog`.

### 1. Defecto observado

Flujo reproducible actual:

1. seleccionar un candidato elegible;
2. activar `Copiar selección al borrador`;
3. el foco entra correctamente al diálogo;
4. Tab permanece correctamente contenido en el diálogo;
5. cerrar con Escape;
6. el diálogo desaparece;
7. el foco termina en `body` en lugar de regresar a la CTA que abrió el diálogo.

### 2. Comportamiento requerido

Después de cerrar el diálogo mediante cualquiera de estas vías:

- Escape;
- `Cancelar`;
- botón de cierre;

el foco debe volver al control iniciador `Copiar selección al borrador`, siempre que continúe montado y habilitado.

Si el control iniciador deja de estar disponible por un cambio legítimo de estado, usar un fallback documentado, estable y cercano al contexto de trabajo. No enfocar `body`, un elemento oculto ni un control ajeno al flujo.

La restauración debe ocurrir una sola vez, sin saltos visibles y sin reabrir el diálogo.

### 3. Confirmación simulada

Para `Confirmar copia simulada`:

- mantener el aviso local `PRESENTATION_ONLY`;
- cerrar el diálogo;
- restaurar el foco de forma predecible a la CTA iniciadora si sigue disponible;
- no cambiar ni limpiar automáticamente la selección;
- no crear persistencia, review history ni estados nuevos.

### 4. Preservar exactamente

- `AppShell`;
- estructura congelada de tres regiones;
- ruta `/evidence/session-demo`;
- `Workspace · v0.2`;
- `Inspector · v0.6`;
- indicador `DSpace · SOLO LECTURA`;
- light/dark mode;
- responsive behavior existente;
- contenido, orden visual y advertencias de `CopyReviewDialog`;
- navegación interna y semántica accesible del Inspector v0.6;
- selección de candidatos;
- elegibilidad;
- `metadataField`;
- `bindingId`;
- candidate IDs;
- evidence states;
- validation states;
- provenance;
- staleness;
- separación entre foco, selección y elegibilidad.

### 5. Restricciones congeladas

NO modificar:

- backend ni `src/server.ts`;
- APIs, base de datos, Supabase o autenticación;
- dependencias o servicios externos;
- rutas;
- contratos de datos;
- vocabularios o reglas catalográficas;
- comportamiento DSpace;
- evidence, validation, provenance, eligibility o staleness;
- estilos generales, densidad o arquitectura del workspace;
- etiquetas de versión.

NO implementar LLM, OCR, fetch real, persistencia, draft real, escritura DSpace, Accept/Reject ni review history productivo.

### 6. Implementación permitida

Usar el mecanismo de foco ya disponible en las dependencias existentes, preferentemente el comportamiento nativo/documentado del diálogo o una referencia explícita al trigger.

Se permite únicamente:

- conservar una referencia estable al control iniciador;
- manejar el cierre para restaurar foco;
- establecer un fallback accesible cuando el iniciador ya no exista;
- añadir pruebas o documentación estrictamente necesarias.

No añadir una dependencia nueva para resolver el foco.

### 7. Pruebas mínimas obligatorias

Comprobar separadamente:

1. apertura por clic;
2. apertura por teclado;
3. foco inicial dentro del diálogo;
4. Tab y Shift+Tab permanecen contenidos;
5. Escape cierra y devuelve foco a la CTA;
6. `Cancelar` cierra y devuelve foco a la CTA;
7. botón de cierre cierra y devuelve foco a la CTA;
8. `Confirmar copia simulada` cierra, anuncia el resultado local y devuelve foco;
9. la selección permanece intacta después de Cancelar/Escape/cierre;
10. evidence y validation no cambian;
11. sesión stale mantiene la CTA deshabilitada y el diálogo inaccesible;
12. cero seleccionados mantiene la CTA deshabilitada;
13. light mode;
14. dark mode;
15. sin errores de consola propios de la aplicación;
16. typecheck/build verde.

### 8. Criterios de aceptación

- Ninguna vía de cierre deja foco en `body`.
- El foco vuelve al trigger cuando permanece disponible.
- El fallback, si se usa, está documentado y probado.
- No hay doble restauración, parpadeo ni reapertura.
- El focus trap existente permanece correcto.
- Selección, evidencia, validación, procedencia y staleness permanecen intactos.
- No se modifican backend, rutas, dependencias, contratos ni DSpace.
- La estructura congelada de tres regiones permanece intacta.
- Typecheck/build termina en verde.

### 9. Entregables esperados

- parche correctivo v0.6.1;
- changelog mínimo;
- matriz de las cuatro vías de cierre;
- lista de archivos cambiados;
- typecheck/build;
- confirmación expresa de cierre de `UX006-DEBT-001`;
- confirmación de que no se modificaron backend, rutas, dependencias, contratos, DSpace ni semántica catalográfica;
- no publicar automáticamente.

Antes de editar, resume brevemente el cambio. Después implementa únicamente esta corrección.

## Acceptance gate

UX-PROMPT-007 se considera exitoso únicamente si las cuatro vías de cierre restauran el foco de forma predecible, no se altera ningún estado de dominio y el diff permanece estrictamente acotado.

## Execution policy

DO NOT execute this prompt in Lovable until execution is explicitly authorized.

Current state: specification saved only; no Lovable message, edit, execution commit or credit consumption exists for UX-PROMPT-007.
