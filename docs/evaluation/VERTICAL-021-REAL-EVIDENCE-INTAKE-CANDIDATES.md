# VERTICAL-021 Real Evidence Intake Candidates

**Estado:** CORRECTIVE REREVIEW COMPLETE AT CASE LEVEL — el `ADJUDICATED_GOLD` de `rereview-v2` para candidate 003 fue retirado de uso evaluativo actual por una discrepancia semántica con ADR-012; `rereview-v3` quedó revisado por dos catalogadores, cerrado formalmente por consenso y promovido a `ADJUDICATED_GOLD` a nivel de caso; candidato 002 permanece en evidencia pendiente/remediable; Gate D continúa abierto.

Baseline: `main` @ `909aac81f4d97106231d77c014f19ab0d38c07b1`.

## 1. Propósito

Registrar y corregir de forma auditable el conjunto inicial de fuentes reales para su incorporación controlada al Golden Set humano de VERTICAL-021. La autorización aplica únicamente a evaluación local: no implica data egress, activación de proveedor LLM ni permiso de escritura DSpace.

## 2. Regla semántica relevante

ADR-012 establece que `dc.description.registeredLanguage` representa la lengua de redacción/registro del recurso y debe mantenerse independiente de la lengua objeto de estudio. Por tanto, la presencia de P’urhepecha en clases, citas, análisis o contenidos temáticos no basta para catalogar el recurso como escrito en P’urhepecha.

## 3. Estado por candidato

### Candidato 001

- Título: *Spatial Language and the Use of Body-Part Terms in Nahuatl and P’urhepecha*.
- Autor: Martha Mendoza.
- Estado de autorización: `AUTHORIZED_LOCAL_EVALUATION`.
- Snapshot: no materializado.
- Licencia/reutilización: pendiente de verificación.
- Estado: `BLOCKED_FOR_INTAKE`.

Candidate 001 permanece bloqueado hasta que exista una representación inmutable y una base de reutilización/licencia verificable.

### Candidato 002

- Título: *Lenguas europeas y lenguas mexicanas: actitudes lingüísticas de universitarios en Guadalajara (México)*.
- DOI: `10.32870/punto.v1i9.75`.
- Licencia: `CC BY-NC 4.0` verificada en página editorial.
- Representación local actual: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-002.txt`.
- SHA-256: `b7c6fbc726441695d47aba958700c69527877585f6d4e32d2d0a2cd2cad9f01a`.
- Estado: `AWAITING_AUTHORIZED_EVIDENCE`.

La representación actual conserva metadatos editoriales, resumen y licencia, pero no evidencia suficiente para admitir un binding lingüístico crítico. Esta carencia es remediable mediante inspección autorizada más completa, por lo que no se modela como bloqueo permanente.

### Candidato 003 — historia y corrección

- Título: *La construcción de la identidad p’urhepechas a partir de la educación intercultural bilingüe propia*.
- DOI: `10.1590/010318138653739444541`.
- Licencia: `CC BY` verificada en página editorial.
- Binding: `registered-language` → `dc.description.registeredLanguage`.

#### Ciclo original

La primera ronda, basada en evidencia más estrecha, permanece preservada e inmutable con dos decisiones `RESEARCH_REQUIRED` y estado histórico `BLOCKED_FOR_INTAKE`.

#### `rereview-v2` — registro histórico preservado

- Snapshot: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.rereview-v2.packet.txt`.
- SHA-256: `2a1ceef24ef537796ed5ec44dc7682a8b900964fd9ea70b9647404ad54817f81`.
- Revisores: `cataloger-a`, `cataloger-b`.
- Adjudicador: `adjudicator-1`.
- Adjudicación: `FINAL`.
- Decisión histórica: `ACCEPT_WITH_MINOR_EDIT`.
- Valor histórico: `Purépecha`.

Durante la revisión pre-merge se identificó que el paquete v2 sustentaba P’urhepecha como lengua estudiada/usada en el contexto descrito, pero no como lengua de redacción del artículo. El `ADJUDICATED_GOLD` de v2 se retiró del uso evaluativo actual sin borrar ni reescribir los juicios humanos. La corrección queda documentada en:

`apps/api/tests/golden/llm-evidence/human-review/corrections/real-evidence-candidate-003.registered-language.rereview-v2.gold-withdrawal.md`

#### `rereview-v3` — gold corregido

- Case: `real-evidence-candidate-003-registered-language-rereview-v3`.
- Metadata field: `dc.description.registeredLanguage`.
- Candidate value: `Español`.
- Candidate intent: `INFERRED_VALUE`.
- Semantic boundary: `registered-language` representa la lengua de redacción/registro del recurso bajo ADR-012.
- Expected abstention: `false`.
- Evidence packet: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.rereview-v3.registered-language.packet.txt`.
- Evidence SHA-256: `58ec2dd6ae0c55a2118ae4c8c27fc21497ab3fc96a73acc2175f4af861c7a7b1`.
- `cataloger-a`: `ACCEPT_AS_IS`, sin abstención, sin errores, sin valor corregido.
- `cataloger-b`: `ACCEPT_AS_IS`, sin abstención, sin errores, sin valor corregido.
- Adjudicador: `adjudicator-1`.
- Adjudicación: `FINAL` por cierre formal de consenso.
- Valor final: `Español`.
- `supersedes_adjudication_id`: `adjudication-real-evidence-candidate-003-registered-language-rereview-v2-v1`.
- Estado del caso: `ADJUDICATED_GOLD`.
- Resulting gold version: `0.2.0-stratum-a-rereview-v3-adjudicated-gold`.

El paquete v3 materializa evidencia explícita sobre la lengua de redacción del recurso y separa esa dimensión de las menciones o fragmentos en P’urhepecha. El label histórico `RESOURCE_WRITING_LANGUAGE` permanece únicamente dentro del snapshot inmutable revisado; no se reescribe porque su SHA-256 ancla las dos revisiones humanas. Para consumo del scorer, el intent canónico es `INFERRED_VALUE`, mientras que la distinción de lengua de redacción permanece en la semántica del binding. Las worksheets documentan esta normalización sin modificar el juicio humano. La adjudicación v3 conserva trazabilidad completa hacia v2 y constituye el gold empírico vigente para este caso.

## 4. Contrato catalográfico congelado

El contrato maestro usado para evaluación es `dspace-cataloger-v3.6`.

SHA-256 autoritativo del contrato:

`a68fbf9664b7165ea240508da85167058cd57796fbda9c1a9869986afb0178bb`

El contrato continúa siendo el mismo; la corrección afecta la semántica aplicada al caso de revisión, no la identidad del contrato.

## 5. Intake y schema

El schema de intake exige para `READY_FOR_INDEPENDENT_REVIEW`, `UNDER_INDEPENDENT_REVIEW` y `ADJUDICATED_GOLD` una proposición estructurada con `metadata_field`, `candidate_value` o abstención explícita, un `candidate_intent` soportado por el scorer (`INFERRED_VALUE` o `GENERATED_CONTENT`) y `expected_abstention`. En esos estados también exige hashes SHA-256 reales para evidencia y contrato; los placeholders `REPLACE_*` quedan restringidos a estados preparatorios anteriores al review activo.

Para un caso `ADJUDICATED_GOLD`, el schema exige además dos revisiones, adjudicador, evidencia congelada y `resulting_gold_version`. El caso v3 publica `0.2.0-stratum-a-rereview-v3-adjudicated-gold` a nivel de caso, de modo que el scorer puede distinguir el gold corregido de los ciclos históricos retirados.

El intake de candidate 003 conserva los ciclos históricos y añade v3. El estado global permanece `BLOCKED_FOR_INTAKE` porque contiene ciclos históricos bloqueados; un caso puede estar `ADJUDICATED_GOLD` sin declarar gold global.

## 6. Gate D

Gate D permanece abierto. Aún faltan, entre otros elementos:

1. cobertura empírica de los cinco bindings críticos;
2. tamaños de muestra suficientes por binding;
3. adjudicación de las oportunidades restantes;
4. identidades/hashes congelados de vocabularios controlados;
5. comparación/provenance de proveedores y demás evidencia del plan de evaluación.

La promoción de `rereview-v3` a `ADJUDICATED_GOLD` resuelve únicamente una oportunidad empírica de `registered-language`; no cierra la fase humana de Estrato A ni ratifica por sí sola thresholds de Gate D.

## 7. Frontera arquitectónica

Este gold es un estado del artefacto de evaluación. No convierte evidencia runtime en `VERIFICADO`, no activa proveedor LLM, no autoriza data egress, no crea candidatos runtime, no habilita OCR y no escribe en DSpace. El PR #17 permanece separado de cualquier implementación productiva.
