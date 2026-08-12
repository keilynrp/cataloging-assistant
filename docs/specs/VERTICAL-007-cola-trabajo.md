# VERTICAL-007: Cola de trabajo catalográfica

## Resultado observable

El equipo puede abrir una cola única para priorizar ítems con hallazgos vigentes
o borradores locales. La vista ordena trabajo; no crea reglas, sugerencias ni
operaciones sobre DSpace.

## Fuente, población y grano

- Fuente: PostgreSQL operacional, derivado de DSpace.
- Población de las tarjetas: los 173 ítems activos de la colección piloto.
- Grano: un ítem activo con al menos un hallazgo vigente o un borrador local.
- Frescura: fecha y estado de la última sincronización registrada.
- Los filtros modifican la lista y su total, pero no las tarjetas de colección.

## Definiciones de métricas

- **Atención**: ítems con uno o más hallazgos vigentes o un borrador local.
- **Pendientes**: ítems con al menos un fingerprint de hallazgo vigente sin
  decisión humana asociada.
- **Revisados**: ítems con hallazgos vigentes cuyos fingerprints tienen decisión.
- **Con borrador**: ítems con un borrador local abierto.
- **Obsoletos**: ítems cuyo borrador conserva un `base_source_hash` distinto del
  `source_hash` sincronizado actual.

Cada métrica cuenta ítems distintos, no hallazgos ni valores de metadatos.

## Priorización

1. `critical`: existe un error pendiente.
2. `high`: existe otro hallazgo pendiente.
3. `rebase`: el borrador está obsoleto.
4. `draft`: existe un borrador abierto.
5. `reviewed`: todos los hallazgos vigentes tienen decisión y no hay borrador.

Dentro de la cola se ordena por prioridad, cantidad de pendientes, obsolescencia
y nombre. Las decisiones anteriores sólo resuelven un hallazgo si coincide el
fingerprint vigente; un hallazgo reconstruido con otro fingerprint vuelve a
quedar pendiente.

## Contrato HTTP

`GET /api/work-queue` admite:

- `q`: fragmento de título o handle.
- `severity`: `error` o `warning`.
- `finding_code`: código exacto de regla.
- `review`: `pending` o `reviewed`.
- `draft`: `none`, `open` o `stale`.
- `page`: página basada en cero.
- `size`: entre 1 y 100.

La respuesta expone fuente, grano, frescura, códigos disponibles, resumen
estable, página y total filtrado. El endpoint es estrictamente de lectura.

## Rendimiento y límite deliberado

Para el piloto, el servicio carga los ítems activos de una sola colección y sus
relaciones mediante carga por lotes, y clasifica los estados en memoria. Con 173
ítems, la medición local de 20 solicitudes dio p95 de 302.8 ms. Antes de ampliar
a colecciones sustancialmente mayores se debe mover filtrado, agregación y
paginación a consultas SQL y volver a fijar un presupuesto de rendimiento.

## Conciliación observada

En la instantánea validada el 10 de agosto de 2026:

- 173 ítems activos.
- 20 ítems con atención pendiente.
- 5 ítems con `CAT-LING-002` y severidad error.
- 15 ítems con `CAT-LING-001` y severidad warning.
- 0 ítems revisados, con borrador u obsoletos.

Los conteos de API se reconciliaron con `count(distinct item_uuid)` en
`catalog_findings`.

## Criterios de aceptación

1. Las tarjetas conservan el denominador y no cambian al filtrar.
2. El total filtrado usa grano de ítem.
3. Severidad, regla, revisión, borrador y búsqueda pueden combinarse.
4. Un error pendiente aparece antes que una advertencia pendiente.
5. Cada resultado enlaza a la ficha del ítem.
6. Fuente, grano y frescura son visibles.
7. El estado degradado no inventa datos cuando la API no responde.
8. La vista funciona en escritorio, tableta y móvil.
9. No existe llamada ni credencial de escritura hacia DSpace.
