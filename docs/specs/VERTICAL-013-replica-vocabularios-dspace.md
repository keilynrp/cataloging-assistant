# VERTICAL-013 — Réplica de vocabularios DSpace

Los vocabularios expuestos por DSpace se sincronizan en tablas locales separadas mediante `python -m cataloging_api.vocabularies.dspace_sync`.

- El cliente sólo autentica y ejecuta GET sobre vocabularios y entradas.
- `dspace_vocabularies` conserva definición, URI, HAL+JSON, hash y fecha.
- `dspace_vocabulary_entries` conserva identificador, valor, presentación, jerarquía, posición, HAL+JSON y hash.
- La sincronización es paginada e idempotente; cada vocabulario se reemplaza dentro de la transacción local.
- Estas tablas son evidencia de DSpace, no vocabularios institucionalmente aprobados.
- Ninguna operación escribe en DSpace ni activa automáticamente reglas catalográficas.
