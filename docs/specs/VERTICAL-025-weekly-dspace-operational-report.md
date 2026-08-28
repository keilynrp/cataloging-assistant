# VERTICAL-025: Weekly DSpace Operational Report

## Resultado observable

La aplicación puede generar, bajo demanda y de forma read-only, un reporte operacional para un rango semanal de catalogación sobre la instancia DSpace 7.6.6.

El reporte contiene exactamente siete columnas visibles y puede exportarse a CSV, XLSX y PDF. La selección temporal, el filtro por catalogador, la resolución de responsabilidad intelectual y la normalización de caracteres son deterministas y reproducibles.

La capacidad se integra en `cataloging-assistant` a partir de un comportamiento previamente validado mediante scripts Python locales. Esta specification congela ese contrato antes de cualquier implementación productiva.

## Objetivo

Incorporar un reporte semanal sencillo para control operacional de catalogación sin introducir escritura en DSpace, automatización programada ni semántica nueva fuera del comportamiento ya validado.

La aplicación debe poder responder:

> ¿Qué registros catalogados por YCT pertenecen al periodo solicitado, cuál es su estado actual y cómo puedo abrirlos directamente en DSpace?

## Contrato visible

El reporte contiene exactamente, en este orden:

| # | ID | Título | URL interna DSpace | Autor(es) | Estado | Catalogador |
| ---: | --- | --- | --- | --- | --- | --- |

No se añaden columnas visibles de auditoría, UUID, colección, fechas técnicas ni fuente de fallback.

## Fuente de verdad

DSpace permanece como fuente externa de verdad.

Instancia validada durante la fase experimental:

```text
DSpace UI:     http://132.248.101.240:4000
DSpace server: http://132.248.101.240:8080/server
Version:       7.6.6
```

La implementación no debe hardcodear secretos ni depender de escritura DSpace.

## Superficies DSpace read-only

Como mínimo:

```text
GET /api/core/items
GET /api/submission/workspaceitems
GET /api/workflow/workflowitems
GET /api/submission/workspaceitems/{id}/item
```

La autenticación puede requerir CSRF + JWT según el contrato ya usado por la integración DSpace del proyecto.

Ninguna operación de esta vertical puede usar `POST`, `PUT`, `PATCH` o `DELETE` contra recursos catalográficos DSpace. El `POST /api/authn/login` de autenticación no se considera escritura catalográfica.

## Filtro por Catalogador

Solo se incluyen registros cuyo:

```text
dcterms.provenance
```

comience por:

```text
YCT
```

Comparación inicial:

```text
case-insensitive startswith("YCT")
```

Ejemplos válidos observados:

```text
YCT-20260824
YCT-20260825
YCT-20260826
YCT-20260827
```

Otros prefijos quedan fuera del reporte.

El filtro YCT es parte del contrato funcional inicial de VERTICAL-025; no se generaliza a multi-catalogador en este slice.

## Semántica temporal

El rango solicitado representa **fecha de catalogación operacional**.

Prioridad determinista:

1. fecha terminal `YYYYMMDD` parseada desde `dcterms.provenance`;
2. para items depositados, fallback a `dc.date.accessioned`;
3. fallback técnico al `item.lastModified` asociado cuando corresponda.

Regla de parsing para provenance:

```text
<arbitrary-prefix><YYYYMMDD at end>
```

Solo se acepta una fecha terminal válida de ocho dígitos.

Ejemplos:

```text
YCT-20260824 -> 2026-08-24
YCT20260824  -> 2026-08-24
```

No usar `WorkspaceItem.lastModified` como fecha histórica: durante la validación se observó que esa propiedad podía reflejar el momento de serialización/consulta y no el momento real de catalogación.

## Mapeo de campos

### Título

```text
dc.title
```

Si el item archivado carece excepcionalmente de `dc.title`, la implementación puede usar el `name` del Item únicamente como fallback técnico visible y debe conservar esa decisión en auditoría interna.

### Autor(es)

Prioridad:

```text
1. dc.contributor.author
2. si vacío -> dc.contributor.editor
3. si ambos vacíos -> celda vacía
```

Reglas:

- nunca mezclar author y editor cuando author existe;
- repetir valores se concatenan en una sola celda con `; `;
- la columna visible continúa llamándose `Autor(es)`;
- la fuente efectiva de responsabilidad debe quedar disponible para tests/auditoría interna, pero no como columna visible.

### Catalogador

```text
dcterms.provenance
```

Se conserva el valor completo, por ejemplo:

```text
YCT-20260824
```

No convertirlo en nombre personal ni resolverlo contra identidades externas en esta vertical.

## ID y URL por estado

### Depositado

Fuente:

```text
core/items
inArchive == true
```

ID visible:

```text
item.handle
```

URL interna:

1. primer `dc.identifier.uri` que pertenezca al host UI configurado;
2. fallback `{ui_base}/handle/{handle}`.

Estado visible:

```text
Depositado
```

Si `withdrawn == true`, estado visible:

```text
Retirado
```

### Guardado

Fuente:

```text
submission/workspaceitems
```

ID visible:

```text
workspaceitem.id
```

URL interna:

```text
{ui_base}/workspaceitems/{workspaceitem.id}/edit
```

Estado visible:

```text
Guardado
```

El metadata source preferido es el Item asociado mediante el enlace HAL `item`; si no puede resolverse, se puede usar el metadata presente en `sections` del WorkspaceItem.

### Workflow

Fuente:

```text
workflow/workflowitems
```

Estado visible provisional:

```text
En flujo de trabajo
```

Durante la validación experimental la instancia observada tenía `totalElements = 0` en esta superficie. Por ello:

- la implementación puede soportar la superficie read-only;
- no debe reclamar validación empírica completa de una ruta UI directa por workflow item;
- mientras no exista evidencia real, el enlace visible puede dirigir a la vista general de workflow configurada;
- la aparición futura de workflow items requiere evidencia antes de endurecer un mapping de ruta más específico.

## Normalización textual

La normalización ocurre únicamente en la capa de salida del reporte.

Pipeline inicial:

1. reparación conservadora de mojibake conocido;
2. normalización Unicode NFC;
3. normalización de espacios no separables y finales de línea;
4. canonicalización de variantes comunes de apóstrofo a `U+2019 RIGHT SINGLE QUOTATION MARK`;
5. colapso de whitespace redundante para celdas de una sola línea.

Ejemplos equivalentes de entrada:

```text
P'urhépecha
Pʼurhépecha
P´urhépecha
P’urhépecha
```

Salida canónica:

```text
P’urhépecha
```

Invariante:

> Esta vertical corrige representación Unicode y mojibake; no corrige ortografía, transliteración, autoridad, idioma ni semántica bibliográfica.

No modificar silenciosamente el valor almacenado en DSpace ni el metadata normalizado persistido por otras verticales.

## Exportación

### CSV

- UTF-8 con BOM (`utf-8-sig`) para interoperabilidad con Excel en Windows;
- exactamente las siete columnas visibles;
- una fila por registro.

### XLSX

- exactamente las siete columnas visibles;
- encabezado congelado;
- autofiltro;
- URL interna como hipervínculo;
- wrap de texto;
- Unicode preservado.

### PDF

- tabla legible en orientación horizontal;
- encabezado repetible por página;
- fuente TrueType Unicode disponible en el sistema;
- no distribuir ni versionar archivos de fuentes;
- preservar tildes, diacríticos y apóstrofes.

## Orden

Orden determinista:

```text
catalog_date ASC
status ASC
id ASC
```

Después del ordenamiento se asigna la columna `#` desde 1.

Mismo dataset + mismo periodo -> mismo orden visible.

## Auditoría interna

Aunque no aparezcan como columnas visibles, la implementación debe poder conservar o derivar durante la ejecución:

- `catalog_date`;
- `catalog_date_source`;
- `source_surface`;
- `responsibility_source`;
- `item_uuid` cuando exista.

Valores esperados de `responsibility_source`:

```text
dc.contributor.author
dc.contributor.editor
unavailable
```

Estos campos sirven para tests, diagnóstico y trazabilidad; no amplían el contrato visible.

## API / superficie de aplicación propuesta

La forma exacta debe ajustarse a convenciones existentes del backend, pero el comportamiento mínimo puede exponerse conceptualmente como:

```text
GET /api/reports/dspace-weekly?from=YYYY-MM-DD&to=YYYY-MM-DD
GET /api/reports/dspace-weekly.csv?from=...&to=...
GET /api/reports/dspace-weekly.xlsx?from=...&to=...
GET /api/reports/dspace-weekly.pdf?from=...&to=...
```

No es requisito que existan cuatro endpoints si una única superficie con negociación/formato explícito encaja mejor con la arquitectura existente.

La specification congela comportamiento, no obliga una forma HTTP concreta mientras los criterios de aceptación se cumplan.

## Seguridad

1. DSpace catalográfico permanece read-only.
2. Username, password y JWT no se persisten en el reporte.
3. No incluir secretos en CSV/XLSX/PDF.
4. No exponer payloads HAL+JSON crudos en la descarga.
5. La autenticación debe reutilizar los mecanismos protegidos existentes del proyecto cuando sea posible.
6. No introducir credenciales nuevas en frontend.
7. No usar parámetros de usuario para construir URLs DSpace arbitrarias.

## Relación con verticales existentes

### VERTICAL-001

Puede reutilizar conceptos y cliente read-only de DSpace, pero VERTICAL-025 no redefine la sincronización general ni su modelo PostgreSQL.

### VERTICAL-018

El contrato maestro runtime continúa vigente. VERTICAL-025 no modifica bindings catalográficos.

### VERTICAL-022

VERTICAL-022 sigue siendo autoridad para drift y baseline del contrato DSpace. VERTICAL-025 no aprueba, promueve ni altera snapshots.

### VERTICAL-023 / 024

El reporte no introduce nuevas reglas de readiness, recovery o auto-healing.

## Primer slice implementable

### Backend

- servicio de consulta semanal read-only;
- filtro `YCT*`;
- mapping de states;
- resolución de metadata;
- regla author -> editor;
- normalización Unicode de salida;
- serializer tabular canónico;
- exporters CSV/XLSX/PDF.

### Tests unitarios

- provenance YCT incluido;
- provenance MEO/WMG/AGG excluido;
- fecha terminal provenance válida;
- provenance sin fecha usa fallback documentado;
- author presente -> editor ignorado;
- author vacío + editor presente -> editor visible;
- ambos vacíos -> celda vacía;
- NFC produce salida estable;
- variantes de apóstrofo -> U+2019;
- CSV abre como UTF-8 BOM;
- orden determinista.

### Tests con fixtures DSpace

Fixtures deben cubrir:

- archived item YCT;
- workspace item YCT;
- item con múltiples autores;
- item sin author y con editor;
- item con mojibake/diacríticos;
- item no YCT;
- withdrawn item;
- workflow vacío.

La suite no debe requerir la instancia DSpace real.

### Web

Primer slice mínimo:

- seleccionar rango `from/to`;
- generar/descargar CSV;
- generar/descargar XLSX;
- generar/descargar PDF;
- presentar error claro si el rango es inválido.

No se requiere dashboard.

## Acceptance criteria

1. Para un fixture estable, mismo rango produce las mismas filas en el mismo orden.
2. Solo aparecen registros cuyo `dcterms.provenance` comienza por `YCT`.
3. El reporte contiene exactamente siete columnas visibles en el orden congelado.
4. `Autor(es)` usa author y cae a editor solo cuando author está vacío.
5. Múltiples responsables se concatenan con `; `.
6. Tildes, diacríticos y apóstrofes permanecen consistentes en CSV, XLSX y PDF.
7. CSV usa UTF-8 con BOM.
8. URLs depositadas resuelven por URI interna/Handle; workspace usa `/workspaceitems/{id}/edit`.
9. No existe escritura catalográfica a DSpace.
10. Credenciales/JWT no aparecen en archivos ni logs de reporte.
11. Los tests no requieren acceso a la instancia real.
12. Workflow vacío no rompe el reporte.
13. La lógica temporal no usa `WorkspaceItem.lastModified` como fuente histórica primaria.
14. La implementación no modifica semantics de VERTICAL-001/018/022.
15. CSV, XLSX y PDF representan el mismo conjunto y orden de registros.

## Stop conditions

La implementación debe detenerse y requerir revisión si fuera necesario:

- habilitar escritura en DSpace;
- modificar `dcterms.provenance` en origen;
- inferir nombres personales desde el código YCT;
- convertir normalización Unicode en corrección semántica/ortográfica;
- añadir scheduling o jobs recurrentes;
- introducir dashboards;
- añadir persistencia nueva no necesaria para el reporte;
- modificar el contrato maestro de metadata;
- declarar workflow item routing como validado sin evidencia real;
- incorporar fuentes tipográficas al repositorio.

## Fuera de alcance

- cron/scheduler del reporte;
- envío automático por email;
- dashboards o series temporales;
- KPIs de productividad;
- scoring de completitud;
- LLM;
- análisis narrativo;
- comparación entre catalogadores;
- multi-catalogador configurable en UI;
- escritura DSpace;
- edición desde el reporte;
- auto-corrección bibliográfica;
- gestión de identidades YCT;
- cambios al modelo DSpace;
- promoción automática a Accepted / Operationalized.

## Definition of Done

VERTICAL-025 está implementado cuando:

1. backend y exporters cumplen los acceptance criteria;
2. existe cobertura automatizada con fixtures;
3. la UI mínima permite rango + descarga de los tres formatos;
4. la implementación conserva read-only DSpace;
5. existe evidencia durable de validación local/reproducible;
6. el índice canónico solo cambia de lifecycle status cuando exista evidencia explícita de aceptación.

La existencia de esta specification o de una implementación parcial no equivale por sí misma a aceptación u operacionalización.
