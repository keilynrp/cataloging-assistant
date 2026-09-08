# UX-PROMPT-008 — Tablet Reflow 768 px v0.6.2

Status: PROPOSED

Target: Lovable

Project: Evidence Navigator

Pilot route: `/evidence/session-demo`

Classification: PRESENTATION_ONLY responsive accessibility correction

Depends on:

- accepted Lovable baseline `e74f22ebaffc9464f459a9d2282e4bf04eb4118c`;
- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-ACCESSIBILITY-AUDIT-002.md`;
- frozen three-region Evidence Workspace contract.

Prototype from: v0.6.1

Prototype to: v0.6.2 corrective patch

Debt addressed: `UXA002-REFLOW-001`

## Objective

Correct only the horizontal overflow measured on the public Evidence Workspace at viewport `768 × 1024`: `scrollWidth: 808` versus `clientWidth: 768`.

The correction must preserve access to Sources, Catalog Proposal and Context/QA Inspector without introducing two-dimensional page scrolling, clipping, overlap or loss of technical audit data.

## Exact prompt for Lovable

Trabaja sobre el proyecto existente **Evidence Navigator** y parte exactamente del baseline Lovable aceptado:

`e74f22ebaffc9464f459a9d2282e4bf04eb4118c`

No rediseñes la aplicación.

Fuentes normativas:

- `docs/ux/UX-GOVERNANCE-CONTRACT.md`;
- `docs/ux/evidence/UX-ACCESSIBILITY-AUDIT-002.md`;
- estructura congelada de tres regiones.

Objetivo único: cerrar `UXA002-REFLOW-001` eliminando el overflow horizontal de página a `768 × 1024`.

### Defecto reproducible

1. abrir `/evidence/session-demo`;
2. usar viewport CSS `768 × 1024`;
3. observar que el documento mide `scrollWidth: 808` y `clientWidth: 768`;
4. el workspace requiere 40 px de desplazamiento horizontal.

### Comportamiento requerido

- En `768 × 1024`, `document.documentElement.scrollWidth` no debe superar `document.documentElement.clientWidth` salvo contenido intrínsecamente bidimensional.
- Ningún encabezado, CTA, selector de escenario, badge, advertencia, identificador técnico, candidato, fuente o control del Inspector puede quedar recortado u oculto.
- Fuentes, Propuesta e Inspector deben conservar una ruta de acceso clara en el flujo responsive.
- Valores largos (`metadataField`, `bindingId`, UUID, hash y URL) deben envolver, desplazarse dentro de un contenedor intrínseco documentado o revelarse completamente sin generar overflow de página.
- Mantener foco visible y un orden de teclado predecible tras el colapso.

### Preservar exactamente

- `AppShell`, ruta `/evidence/session-demo`, `Workspace · v0.2`, `Inspector · v0.6` y `DSpace · SOLO LECTURA`;
- tres responsabilidades congeladas del workspace;
- datos, orden, `metadataField`, `bindingId`, candidate IDs, evidence, validation, provenance y staleness;
- separación entre foco, selección y elegibilidad;
- CopyReviewDialog, su corrección v0.6.1 y CTA de cero seleccionados;
- light/dark mode y comportamiento de candidatos no elegibles.

### Prohibiciones

NO modificar backend, APIs, rutas, datos, dependencias, autenticación, DSpace, contratos semánticos, vocabularios, reglas catalográficas, persistencia, LLM, OCR ni copy-to-draft real.

NO convertir el Inspector en información inaccesible ni eliminar evidencia para ganar espacio.

### Pruebas mínimas obligatorias

1. capturar `768 × 1024` y registrar `scrollWidth`/`clientWidth`;
2. verificar visualmente encabezado, selector, CTA, fuentes, candidatos e Inspector;
3. Tab y Shift+Tab a través de controles visibles tras reflow;
4. cero seleccionados: CTA sigue deshabilitada;
5. candidato no elegible: razón sigue disponible sin depender sólo del color;
6. light y dark mode;
7. `390 × 844` no regresa a overflow de página;
8. zoom equivalente verificable de 200 %;
9. sin errores de consola propios;
10. no publicar automáticamente.

### Entregables esperados

- parche visual mínimo;
- captura antes/después de `768 × 1024`;
- métricas `scrollWidth` y `clientWidth`;
- lista de archivos cambiados;
- confirmación expresa de que no cambiaron contratos ni semántica;
- typecheck/build y resultados de la matriz responsive.

Antes de editar, resume brevemente el cambio. Después implementa únicamente esta corrección.

## Acceptance gate

UX-PROMPT-008 sólo se acepta cuando el overflow de página medido a `768 × 1024` desaparece, las tres responsabilidades siguen accesibles, la navegación por teclado permanece coherente y el diff es exclusivamente de presentación.

## Execution policy

This document authorizes no execution, Lovable action, credit consumption, deployment or publication. A separate explicit authorization is required before implementation.
