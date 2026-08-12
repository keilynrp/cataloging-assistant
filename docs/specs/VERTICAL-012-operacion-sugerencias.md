# VERTICAL-012 — Operación supervisada de sugerencias

## Resultado observable

Un catalogador puede generar sugerencias deterministas para un ítem, congelarlas como artefactos auditables y aceptar, corregir, rechazar o posponer cada una desde la ficha. Aceptar o corregir crea una revisión del borrador local; ninguna operación escribe en DSpace.

## Flujo

1. `POST /api/items/{uuid}/suggestions/generate` exige el token interno y persiste de forma idempotente la evidencia vigente.
2. La ficha recupera el historial con sus identificadores estables.
3. `POST /api/suggestions/{suggestion_id}/decisions` registra una decisión humana y su trazabilidad.
4. La ficha y la cola se revalidan tras una mutación local exitosa.
5. La cola admite `suggestions=pending|none`.

## Guardas

- El token nunca se expone al navegador: las mutaciones pasan por acciones de servidor.
- Se bloquean decisiones sobre una sugerencia cuya fuente quedó obsoleta.
- La corrección exige un valor explícito.
- Aceptar o corregir sólo modifica el borrador local versionado.
- Rechazar o posponer no crea revisiones.

## Verificación

- Lint de API y 35 pruebas automatizadas en verde.
- Compilación de producción de Next.js dentro de la imagen del proyecto.
- Validación manual de estados degradados cuando falta el token o la API local.
