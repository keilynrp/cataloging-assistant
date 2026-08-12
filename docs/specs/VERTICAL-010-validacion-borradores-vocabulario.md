# Vertical 010: validación de borradores con vocabulario

## Resultado

El editor de borradores lingüísticos muestra una validación literal antes de
guardar. La validación es informativa: un catalogador puede conservar un valor
no coincidente si aporta su justificación. No hay corrección automática, ni
escritura hacia DSpace.

## Contrato de evidencia

La migración `0006` añade `validation_snapshot` JSONB a cada revisión de
`catalog_draft_revisions`. El servidor recalcula la instantánea al crear o
versionar el borrador, usando sólo revisiones locales activas de vocabulario.
La instantánea guarda `generated_at`, perfil de vocabularios y, por campo, el
estado, procedencia (revisión, fuente, versión y aprobador) y cada valor literal
con su coincidencia. Así la vista previa no se convierte en una fuente de verdad
ni puede falsear el historial.

Estados globales: `not_configured`, `valid` e `invalid`. Por campo:
`no_vocabulary`, `no_values`, `valid` o `invalid`.

## Límites

- La coincidencia es literal y no propone sustituciones.
- No hay vocabulario activo por defecto para la colección piloto.
- La evidencia se congela por revisión; una revisión posterior de vocabulario no
  reescribe el historial.
- El control de token sigue en la acción local de Next.js y nunca se expone al
  navegador.
