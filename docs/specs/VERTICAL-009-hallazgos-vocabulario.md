# VERTICAL-009: Hallazgos por vocabulario aprobado

## Resultado observable

Una revisión de vocabulario activa forma parte del perfil diagnóstico. Después
de reconstruir diagnósticos, cada ítem con valores que no coinciden literalmente
recibe un hallazgo `CAT-VOCAB-001`, visible en la ficha y en la cola de trabajo.

## Regla determinista

- Código: `CAT-VOCAB-001`.
- Severidad: `warning`.
- Grano: un hallazgo por ítem y campo controlado.
- Evidencia: campo, revisión activa y conjunto completo de valores no coincidentes.
- Explicación: nombre, versión, fuente y hasta cinco valores observados.
- Sin vocabulario activo para el campo, la regla no se ejecuta.
- Un campo ausente no genera este hallazgo; obligatoriedad permanece separada.

La comparación es literal después de retirar espacios exteriores. No se aplican
casefold, fuzzy matching, sinónimos ni relaciones jerárquicas para autorizar un
valor.

## Perfil y obsolescencia

El perfil diagnóstico incorpora:

- versión del conjunto de reglas;
- campos obligatorios configurados;
- identificadores de las revisiones de vocabulario activas.

Activar o reemplazar un vocabulario cambia inmediatamente el perfil esperado.
Las fichas ya diagnosticadas pasan a estado `stale` hasta reconstruir. La
reconstrucción usa una instantánea inmutable de revisiones durante toda la
ejecución; si cambia la configuración en paralelo, el nuevo perfil vuelve a
marcar los resultados anteriores como obsoletos.

## Fingerprint y decisiones humanas

El fingerprint de `CAT-VOCAB-001` incluye la revisión y todos los valores no
coincidentes. Por tanto:

- cambiar un valor produce un hallazgo nuevo;
- reemplazar el vocabulario produce un hallazgo nuevo;
- una decisión sobre evidencia anterior no resuelve automáticamente la nueva;
- repetir diagnóstico con la misma fuente y perfil conserva el fingerprint.

Las reglas preexistentes conservan fingerprints reproducibles dentro de esta
versión del motor.

## Integración con sincronización

Al comenzar, la sincronización captura las revisiones activas una sola vez y usa
ese perfil durante toda la ejecución. Un ítem nuevo o modificado se diagnostica
en la misma transacción que actualiza su índice local. No se consulta ni escribe
DSpace para validar vocabularios.

## Flujo operativo

1. Un referente activa una revisión aprobada.
2. Las fichas muestran diagnóstico obsoleto y validación inmediata en lectura.
3. El operador ejecuta la reconstrucción diagnóstica.
4. Los hallazgos `CAT-VOCAB-001` aparecen en fichas y cola.
5. El catalogador confirma, descarta o pospone cada hallazgo localmente.
6. No se crea ni aplica ningún cambio en DSpace.

## Límites

- Activar una revisión no dispara procesos en segundo plano.
- Los hallazgos se materializan únicamente al sincronizar o reconstruir.
- No se generan sugerencias de reemplazo.
- No se valida todavía el contenido de borradores locales.
- No existe escritura hacia DSpace.

## Criterios de aceptación

1. Sin vocabularios activos, los hallazgos existentes no cambian por esta regla.
2. Una coincidencia literal no produce hallazgo.
3. Una diferencia de mayúsculas puede producir hallazgo.
4. El perfil cambia al cambiar la revisión activa.
5. El fingerprint cambia con revisión o evidencia.
6. La reconstrucción completa es determinista e idempotente.
7. La sincronización usa una instantánea consistente del perfil.
8. Los hallazgos ingresan a la cola mediante su contrato existente.
9. Una decisión humana anterior no se reutiliza con evidencia distinta.
10. La suite no depende de DSpace real.
