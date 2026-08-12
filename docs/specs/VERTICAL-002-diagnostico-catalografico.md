# VERTICAL-002: Diagnóstico catalográfico reproducible

## Objetivo

Evaluar cada ítem sincronizado con reglas deterministas y mostrar hallazgos versionados en su ficha.

## Reglas activas

- `CAT-LING-001`: familia presente y rama ausente; severidad `warning`.
- `CAT-LING-002`: rama presente y familia ausente; severidad `error`.
- `CAT-META-001`: sólo se activa para claves confirmadas en `CATALOG_REQUIRED_FIELDS`.

## Límites

- Las reglas son propuestas del piloto, no reglas institucionales aprobadas.
- No se activan relaciones controladas, variantes preferidas ni deduplicación.
- El motor no depende de un proveedor de modelo y no escribe en DSpace.

## Contrato

Cada hallazgo conserva identificador, código, severidad, campos afectados,
explicación, huella reproducible, versión de regla y hash del registro fuente.
El ítem conserva la versión del perfil y la fecha de evaluación, incluso cuando
no tiene hallazgos.

## Aceptación

1. La misma entrada y perfil producen los mismos códigos y huellas.
2. Los valores vacíos se consideran ausentes.
3. Un cambio de registro o perfil deja el diagnóstico identificable como obsoleto.
4. La reconstrucción sustituye hallazgos sin duplicarlos.
5. La ficha distingue hallazgos, ausencia de hallazgos y diagnóstico obsoleto.
6. La suite automatizada no depende de la instancia DSpace real.
