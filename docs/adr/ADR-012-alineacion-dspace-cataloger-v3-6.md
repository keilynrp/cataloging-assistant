# ADR-012: Alineación con dspace-cataloger v3.6

**Estado:** Aceptada el 15 de agosto de 2026.

## Contexto

La aplicación y el skill `dspace-cataloger` evolucionaron en paralelo. La aplicación ya implementa una capa determinista y auditable sobre DSpace, mientras el skill incorporó reglas catalográficas derivadas de casos reales y de la autoridad CLIN/INALI. La divergencia principal estaba en el modelo lingüístico: la aplicación trataba cuatro campos y asumía relaciones que confundían la lengua del recurso con la lengua objeto de estudio.

## Decisión

1. Mantener DSpace como fuente de verdad y PostgreSQL como índice local reconstruible.
2. Mantener el agente generativo estrictamente de solo lectura; ninguna regla del skill autoriza escritura automática en DSpace.
3. Ampliar el contrato local de borradores y vocabularios a cinco campos:
   - `dc.subject.linguisticFamily`
   - `dc.subject.linguisticBranch`
   - `dc.subject.linguiscgroup`
   - `dc.subject.linguisticVariant`
   - `dc.description.registeredLanguage`
4. Para lenguas indígenas de México, usar como columna normativa CLIN:
   **Familia → Agrupación → Variante**.
5. Tratar `dc.subject.linguisticBranch` como enriquecimiento genealógico opcional, no como nivel obligatorio CLIN. Por tanto, familia sin rama deja de ser hallazgo.
6. Tratar `dc.description.registeredLanguage` como eje independiente: lengua de redacción/registro del recurso, no descendiente de la agrupación lingüística estudiada.
7. Conservar validación literal de vocabularios y aprobación humana. La variante puede tener un vocabulario local aprobado aun cuando DSpace no exponga una lista promocionable para ese campo.
8. No habilitar sugerencias automáticas de variante en esta decisión. Las variantes requieren reconciliación de autoridad más estricta; por ahora sólo pueden ser capturadas/revisadas manualmente y validadas contra una revisión local aprobada.
9. Preservar literalmente `dc.subject.linguiscgroup`.

## Consecuencias

- El perfil de colección pasa de cuatro a cinco dimensiones lingüísticas.
- Las relaciones observadas dejan de modelar `Agrupación → Lengua de registro`; ahora registran únicamente relaciones del eje temático/genealógico.
- Los borradores locales pueden representar variantes sin escribir en DSpace.
- Los diagnósticos cambian de versión; los resultados previos pueden quedar obsoletos y deben reconstruirse.
- El modelo multientidad completo (pares explícitos entre familia, rama, agrupación y variante) sigue siendo una evolución posterior: los metadatos DSpace continúan serializados como listas planas repetibles.

## Compatibilidad

Se preservan ADR-002, ADR-005, ADR-006, ADR-008 y ADR-010. Esta ADR no añade autenticación DSpace, publicación, workflow ni escritura remota.
