# VERTICAL-005: Revisión humana local y auditable

## Resultado observable

Desde una ficha con hallazgos vigentes, un catalogador puede confirmar, descartar
o posponer un hallazgo y dejar una nota. La decisión aparece en el historial
local y no modifica metadatos ni ejecuta llamadas de escritura contra DSpace.

## Contrato

- Operación: `POST /api/items/{item_uuid}/findings/{finding_id}/decisions`.
- Autorización: cabecera servidor-a-servidor `X-Catalog-Review-Token`.
- El token se mantiene en los entornos de API y Next.js; nunca se serializa al navegador.
- Decisiones: `confirmed`, `dismissed`, `deferred`.
- Revisor: etiqueta autodeclarada de 2 a 120 caracteres.
- Nota: evidencia o justificación obligatoria, de 1 a 2000 caracteres.
- `request_id`: UUID idempotente. Repetirlo para el mismo ítem devuelve la misma decisión.
- Persistencia: append-only; no hay rutas de actualización o eliminación.

## Evidencia preservada

Cada decisión conserva una instantánea del hallazgo: huella, código, severidad,
campos afectados, explicación, versión de regla y hash del ítem fuente. El
historial sobrevive a la regeneración de hallazgos deterministas.

## Límites de seguridad

- Si `CATALOG_REVIEW_TOKEN` está vacío, la mutación local responde 503.
- Un token ausente o incorrecto responde 401.
- La política CORS continúa permitiendo únicamente GET desde el navegador.
- La mutación ocurre mediante una Server Action de Next.js.
- No hay autenticación institucional todavía; el revisor es autodeclarado y
  este flujo se limita al piloto controlado.

## Criterios de aceptación

1. Una solicitud autorizada para un hallazgo vigente crea una sola decisión.
2. Repetir el `request_id` no duplica la decisión.
3. Una solicitud sin token es rechazada.
4. Un hallazgo inexistente no crea historial.
5. La respuesta de detalle incluye decisiones previas y la huella del hallazgo.
6. El formulario declara explícitamente que no modifica DSpace.
7. La suite demuestra que el historial persiste si el hallazgo desaparece.
