# UX-PROMPT-004 — Copy-to-Draft Review v0.4

Status: PROPOSED — NOT YET EXECUTED

Target: Lovable

Project: Evidence Navigator

Pilot route: `/evidence/session-demo`

Classification: PRESENTATION_ONLY interaction refinement

Depends on:

- accepted Lovable baseline from `UX-PROMPT-003`;
- Lovable commit `06669435a21037dc092c0fbba80a3aa499e11c9c`;
- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-PROMPT-003-EXECUTION-2026-08-19.md`;
- frozen three-region Evidence Workspace contract.

Prototype from: v0.3

Prototype to: v0.4

## Objective

Complete only the visual **review step immediately before `Copiar selección al borrador`**, using simulated data and without persistence.

This iteration must convert the current presentation-only copy affordance into a more explicit review interaction while preserving the existing cataloging contract. It must not create or imply a productive write workflow.

## Exact prompt for Lovable

UX-PROMPT-004 — Copy-to-Draft Review v0.4

Trabaja sobre el proyecto existente **Evidence Navigator** y parte exactamente del baseline Lovable aceptado de `UX-PROMPT-003`:

`06669435a21037dc092c0fbba80a3aa499e11c9c`

No rediseñes la aplicación desde cero.

La fuente normativa es:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- el estado aprobado y auditado de `UX-PROMPT-003`;
- la estructura congelada de tres regiones.

Objetivo: completar únicamente la experiencia visual de **revisión previa a `Copiar selección al borrador`**, usando datos simulados y sin persistencia.

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
- indicador permanente `DSpace · SOLO LECTURA`;
- `EvidenceSourceCard`;
- `CandidateRow`;
- `EvidenceStateBadge`;
- `ValidationBadge`;
- `InspectorPanel`;
- identificadores técnicos en monospace;
- selección y elegibilidad implementadas en v0.3;
- semántica de `metadataField`, `bindingId`, evidence states, validación y staleness.

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
- semántica de staleness;
- la lógica de elegibilidad aprobada en v0.3.

NO implementar:

- LLM;
- OCR;
- fetch remoto real;
- persistencia;
- escritura en DSpace;
- mutación real de borradores;
- Accept / Reject persistido;
- review history persistido;
- publicación;
- side effects productivos.

Toda interacción nueva de esta iteración debe clasificarse como `PRESENTATION_ONLY`.

### 3. Entrada al flujo de revisión

Cuando exista al menos un candidato copiable seleccionado y la Evidence Session no esté stale:

- al pulsar `Copiar selección al borrador`, abrir un **diálogo compacto de revisión previa**;
- el diálogo debe ser claramente una revisión de presentación, no una confirmación productiva;
- no debe cambiar la selección al abrirse;
- no debe alterar evidence state, validación, procedencia, QA, review history, `metadataField` ni `bindingId`;
- el foco inicial debe entrar correctamente al diálogo;
- cerrar mediante `Cancelar`, `Esc` o el control de cierre debe devolver el foco de forma predecible a la CTA.

### 4. Contenido del diálogo

Mostrar únicamente los candidatos actualmente seleccionados y elegibles para copiar.

Para cada candidato incluir de forma compacta y auditable:

- etiqueta humana;
- `metadataField`;
- `bindingId`;
- valor;
- estado de evidencia;
- validación;
- procedencia resumida.

La procedencia resumida puede incluir, cuando exista:

- fuente;
- ubicación;
- extractor o referencia equivalente.

No añadir nueva semántica de procedencia.

No mostrar candidatos no copiables como si formaran parte de la copia.

### 5. Valores repetibles

Para campos repetibles:

- conservar cada candidato como unidad individual;
- mantener visualmente la relación con su campo;
- evitar colapsar valores distintos en una sola cadena ambigua;
- preservar `metadataField` y `bindingId` sin transformación;
- mostrar el conjunto de forma compacta, evitando tarjetas grandes por cada valor.

### 6. Resumen de revisión

En el encabezado o zona superior del diálogo mostrar:

- cantidad total de candidatos seleccionados;
- cantidad de campos afectados cuando sea útil y derivable sin inventar semántica;
- una indicación `PRESENTATION_ONLY` visible o inequívoca.

No introducir confidence scores ni métricas no existentes.

### 7. Advertencia obligatoria

Mostrar explícitamente dentro del diálogo:

`Prototipo sin persistencia: ningún dato será escrito en DSpace.`

La advertencia debe ser visible sin depender únicamente de tooltip o hover.

Puede aclarar además que la acción tampoco muta un borrador real ni persiste selección, siempre sin sobrecargar la interfaz.

### 8. Acciones del diálogo

Acciones permitidas:

- `Cancelar`;
- `Confirmar copia simulada`.

`Confirmar copia simulada` debe:

- cerrar el diálogo;
- mostrar un aviso local temporal o inline claramente etiquetado `PRESENTATION_ONLY`;
- indicar cuántos candidatos habrían sido copiados;
- NO modificar un borrador real;
- NO escribir en backend, DSpace, API, almacenamiento local persistente ni base de datos;
- NO alterar evidence states;
- NO crear review history;
- NO convertir la acción en Accept / Reject.

No usar copy de éxito productivo como `Guardado`, `Publicado`, `Sincronizado`, `Escrito en DSpace` o equivalentes.

### 9. Staleness

Preservar exactamente el contrato actual:

- stale se determina a nivel de Evidence Session contra el DSpace source hash;
- la evidencia permanece visible;
- la selección puede permanecer visible;
- `Copiar selección al borrador` sigue bloqueada cuando la sesión está stale;
- por tanto, el diálogo de revisión no debe poder abrirse desde una sesión stale;
- no reintroducir staleness basada en cambios de una URL remota.

### 10. Elegibilidad

Preservar las reglas aprobadas en v0.3.

Los candidatos bloqueados por cualquiera de estas razones no deben entrar al diálogo:

- `not-in-vocabulary`;
- valor inválido;
- ausencia de valor extraído;
- `FUTURE_CONTRACT`;
- sesión stale.

No transformar automáticamente candidatos bloqueados en elegibles.

### 11. Inspector y selección

El Inspector debe seguir distinguiendo:

- `Seleccionado para copiar`;
- `Elegible · sin seleccionar`;
- `No elegible para copiar`.

Abrir o cerrar la revisión no debe crear un nuevo estado semántico en el Inspector.

No añadir estados como `REVISADO`, `CONFIRMADO`, `APROBADO` o equivalentes al contrato de evidencia.

### 12. Corrección de etiqueta de versión

Si la interfaz todavía muestra:

`UX Lab · v0.1`

corregir únicamente esa etiqueta visual a:

`UX Lab · v0.2`

Esta corrección es `PRESENTATION_ONLY` y no debe utilizarse para renombrar contratos, rutas ni artefactos técnicos.

### 13. Clasificación UX

Clasificar:

- apertura/cierre del diálogo: `PRESENTATION_ONLY`;
- resumen de selección: `PRESENTATION_ONLY`;
- render de candidatos seleccionados dentro del diálogo: `PRESENTATION_ONLY`;
- `Cancelar`: `PRESENTATION_ONLY`;
- `Confirmar copia simulada`: `PRESENTATION_ONLY`;
- aviso posterior: `PRESENTATION_ONLY`;
- reglas de elegibilidad: `CURRENT_RUNTIME`;
- bloqueo por stale: `CURRENT_RUNTIME`;
- Accept / Reject persistido: `FUTURE_CONTRACT`;
- cualquier semántica heredada incorrecta: `REMOVE_OR_CORRECT`.

### 14. Estados mínimos a comprobar

Comprobar visualmente al menos:

1. una selección elegible;
2. múltiples candidatos seleccionados;
3. valores repetibles seleccionados;
4. mezcla de campos distintos;
5. diálogo abierto con contenido auditable;
6. cancelación sin alterar la selección;
7. confirmación simulada con aviso local;
8. cero seleccionados: CTA sigue disabled;
9. sesión stale: CTA disabled y diálogo inaccesible;
10. candidatos no copiables excluidos;
11. navegación por teclado;
12. focus trap y retorno de foco razonables;
13. responsive behavior sin romper las tres regiones;
14. light/dark mode.

### 15. Fuera de alcance explícito

No implementar:

- persistencia de revisión;
- edición de valores dentro del diálogo;
- reordenamiento persistente;
- resolución de validaciones dentro del diálogo;
- reemplazo de candidatos;
- selección automática de candidatos bloqueados;
- draft real;
- escritura o sync con DSpace;
- publicación;
- Accept / Reject productivo;
- backend;
- nuevas rutas;
- nuevas dependencias;
- LLM;
- OCR;
- fetch real.

### 16. Entregables esperados

- prototipo v0.4 con diálogo de revisión previa;
- changelog v0.3 → v0.4;
- matriz de estados del review flow;
- clasificación `CURRENT_RUNTIME` vs `PRESENTATION_ONLY` vs `FUTURE_CONTRACT`;
- listado explícito de elementos no implementados;
- build/typecheck en verde;
- lista de archivos cambiados;
- confirmación expresa de que no se modificaron backend, rutas, dependencias, `metadataField`, `bindingId`, comportamiento DSpace ni semántica catalográfica;
- confirmación de que la estructura congelada de tres regiones sigue intacta.

Antes de editar, resume brevemente los cambios que realizarás. Después implementa únicamente este refinamiento.

## Expected evidence after execution

Registrar al menos:

- Lovable project;
- base commit `06669435a21037dc092c0fbba80a3aa499e11c9c`;
- resulting edit ID;
- resulting Lovable commit SHA;
- execution timestamp;
- changed files;
- build/typecheck result;
- review-flow state matrix;
- screenshot/preview reference where available;
- confirmation of frozen three-region structure;
- confirmation of no backend/routes/dependencies/metadataField/bindingId/DSpace/cataloging-semantic changes;
- acceptance outcome.

## Acceptance gate

`UX-PROMPT-004` se considera exitoso únicamente si:

1. el review dialog contiene sólo candidatos seleccionados y elegibles;
2. muestra etiqueta humana, `metadataField`, `bindingId`, valor, evidence state, validación y procedencia resumida;
3. valores repetibles permanecen individualmente auditables;
4. la advertencia de no persistencia es explícita;
5. `Cancelar` no altera la selección;
6. `Confirmar copia simulada` no produce side effects productivos;
7. stale impide abrir la revisión;
8. no aparecen capacidades productivas de Accept / Reject;
9. no se modifican backend, rutas, dependencias ni contrato semántico;
10. la estructura de tres regiones permanece congelada;
11. build/typecheck es verde.

## Review note

Esta versión actualiza el borrador histórico de `UX-PROMPT-004` para que su baseline sea el commit Lovable realmente aceptado de `UX-PROMPT-003` (`06669435a21037dc092c0fbba80a3aa499e11c9c`) en lugar del antiguo baseline de `UX-PROMPT-002` (`7100f3116b4dba4c2273d8e19a1a2c13c783b0eb`).

No se ha ejecutado todavía en Lovable.
