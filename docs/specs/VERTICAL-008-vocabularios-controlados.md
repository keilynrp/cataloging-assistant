# VERTICAL-008: Vocabularios aprobados y validación literal

## Resultado observable

El referente catalográfico puede registrar una revisión local aprobada para cada
campo lingüístico. La ficha de un ítem compara sus valores con esas revisiones y
muestra evidencia de procedencia, sin sugerir reemplazos ni modificar DSpace.

## Campos admitidos

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.description.registeredLanguage`

`dc.subject.linguiscgroup` se conserva literalmente. No se permite asociar un
vocabulario a otros campos mediante este contrato.

## Gobernanza y persistencia

- `catalog_vocabulary_revisions` conserva fuente, versión, aprobador, nota,
  fingerprint de solicitud, estado activo y fecha.
- `catalog_controlled_terms` conserva valor literal, identidad normalizada,
  autoridad opcional, idioma opcional y posición.
- Sólo existe una revisión activa por campo.
- Activar una revisión desactiva la anterior, pero no elimina su historial.
- `request_id` hace idempotente la operación; reutilizarlo con datos distintos
  produce conflicto.
- La base real se entrega sin términos precargados porque P-002 continúa pendiente.

La normalización NFKC, trim y casefold sólo detecta duplicados dentro de una
revisión. No autoriza variantes: la validación de metadatos exige coincidencia
literal exacta tras retirar espacios exteriores.

## Contratos HTTP

- `GET /api/controlled-vocabularies`: revisiones activas.
- `GET /api/controlled-vocabularies?include_history=true`: historial completo.
- `POST /api/controlled-vocabularies`: activa una revisión local aprobada.
- `GET /api/items/{uuid}/metadata-validation`: evidencia por campo y valor.

El POST requiere `X-Catalog-Review-Token` entre Next.js y FastAPI. El token no
llega al navegador. Los GET son de lectura sobre PostgreSQL local.

## Estados de validación

Por campo:

- `no_vocabulary`: no existe fuente aprobada.
- `no_values`: hay vocabulario activo, pero el ítem no contiene el campo.
- `valid`: todos los valores coinciden literalmente.
- `invalid`: al menos un valor no coincide literalmente.

Por ítem:

- `not_configured`: ningún campo tiene vocabulario activo.
- `valid`: existe configuración y no hay valores fuera de vocabulario.
- `invalid`: existe al menos un valor fuera de vocabulario.

`no_values` no implica campo obligatorio; esa decisión permanece separada en
`CATALOG_REQUIRED_FIELDS`.

## Límites deliberados

- No se infieren términos desde frecuencias de la colección.
- No se cargan catálogos externos automáticamente.
- No hay fuzzy matching, equivalencias ortográficas ni relaciones jerárquicas.
- La validación no crea hallazgos persistentes ni altera la cola en esta vertical.
- Los borradores no se corrigen, bloquean ni publican automáticamente.
- No existe escritura hacia DSpace.

## Criterios de aceptación

1. Sin fuente aprobada, la UI declara validación no configurada.
2. Sólo se aceptan los cuatro campos lingüísticos.
3. Cada revisión registra procedencia y aprobación humana.
4. El orden de términos se conserva.
5. Los duplicados normalizados se rechazan.
6. Repetir la misma solicitud no duplica datos.
7. Reutilizar el identificador con otro contenido produce 409.
8. Reemplazar una revisión conserva el historial.
9. Cada valor validado muestra coincidencia o falta de coincidencia literal.
10. Las escrituras locales requieren token y nunca invocan DSpace.
11. La suite automatizada usa transacciones revertidas y no depende de DSpace real.
