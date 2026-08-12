# VERTICAL-006: Borrador catalográfico local versionado

## Resultado observable

Desde la ficha de un ítem, un catalogador puede preparar valores para los cuatro
campos lingüísticos y guardar revisiones locales. El borrador no cambia el índice
sincronizado, no invoca DSpace y no convierte los valores ingresados en vocabulario
autorizado.

## Campos permitidos

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.description.registeredLanguage`

`dc.subject.linguiscgroup` se conserva literalmente. Una línea del editor se
normaliza como un valor repetible con `place` consecutivo. Un campo vacío
representa una propuesta explícita de reemplazo por una lista vacía.

## Persistencia

- `catalog_drafts`: un borrador por ítem, hash y metadatos lingüísticos base,
  estado, autor y fechas.
- `catalog_draft_revisions`: revisiones append-only con versión, solicitud
  idempotente, parche normalizado, autor, nota y fecha.
- `base_metadata` conserva valor, idioma, autoridad, confianza y posición de la
  instantánea sincronizada.
- `metadata_patch` usa la misma forma normalizada y queda preparado para una
  futura traducción controlada al contrato REST de DSpace.

## Contratos HTTP

- Crear: `POST /api/items/{item_uuid}/drafts`.
- Revisar: `POST /api/items/{item_uuid}/drafts/{draft_id}/revisions`.
- Ambas operaciones requieren `X-Catalog-Review-Token` entre Next.js y FastAPI.
- Cada solicitud aporta `request_id`, autor, nota y cambios.
- Una nueva revisión exige `expected_version` para control optimista.

## Concurrencia y obsolescencia

El borrador conserva `base_source_hash`. Si una sincronización modifica el
`source_hash` del ítem, se marca obsoleto y la API rechaza nuevas revisiones con
409. No existe rebase automático: requerirá una decisión humana y un contrato
posterior.

## Límites

- No se generan ni recomiendan valores.
- No se consultan ni inventan vocabularios.
- No se actualizan metadatos sincronizados.
- No existen operaciones para aplicar, publicar o eliminar borradores.
- La identidad del autor continúa siendo autodeclarada durante el piloto.

## Criterios de aceptación

1. Sólo se aceptan los cuatro campos lingüísticos.
2. Se conserva el orden de valores repetibles.
3. Crear con el mismo `request_id` no duplica el borrador.
4. Las revisiones se numeran de forma consecutiva.
5. Una versión esperada incorrecta produce conflicto.
6. Un cambio del registro fuente bloquea nuevas revisiones.
7. El detalle del ítem expone la instantánea base, revisiones y estado obsoleto.
8. El secreto no llega al navegador y una solicitud sin token responde 401.
9. La interfaz declara que el borrador no modifica DSpace.
