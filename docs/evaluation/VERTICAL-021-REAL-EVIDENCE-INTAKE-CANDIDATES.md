# VERTICAL-021 Real Evidence Intake Candidates

**Estado:** CORRECTIVE REREVIEW ACTIVE — el `ADJUDICATED_GOLD` de `rereview-v2` para candidate 003 fue retirado de uso evaluativo actual por una discrepancia semántica con ADR-012; `rereview-v3` está preparado para revisión humana independiente sobre la lengua de redacción del recurso; candidato 002 pasa a estado de evidencia pendiente/remediable; Gate D continúa abierto.

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

La representación actual conserva metadatos editoriales, resumen y licencia, pero no evidencia suficiente para admitir un binding lingüístico crítico. Esta carencia es remediable mediante inspección autorizada más completa, por lo que ya no se modela como bloqueo permanente.

### Candidato 003 — historia y corrección

- Título: *La construcción de la identidad p’urhepechas a partir de la educación intercultural bilingüe propia*.
- DOI: `10.1590/010318138653739444541`.
- Licencia: `CC BY` verificada en página editorial.
- Binding: `registered-language` → `dc.description.registeredLanguage`.

#### Ciclo original

La primera ronda, basada en evidencia más estrecha, permanece preservada e inmutable con dos decisiones `RESEARCH_REQUIRED`.

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

#### `rereview-v3` — proposición corregida

- Case: `real-evidence-candidate-003-registered-language-rereview-v3`.
- Metadata field: `dc.description.registeredLanguage`.
- Candidate value: `Español`.
- Candidate intent: `RESOURCE_WRITING_LANGUAGE`.
- Expected abstention: `false`.
- Evidence packet: `apps/api/tests/golden/llm-evidence/human-review/snapshots/real-evidence-candidate-003.rereview-v3.registered-language.packet.txt`.
- Evidence SHA-256: `58ec2dd6ae0c55a2118ae4c8c27fc21497ab3fc96a73acc2175f4af861c7a7b1`.
- Estado: `READY_FOR_INDEPENDENT_REVIEW`.

El paquete v3 materializa evidencia explícita sobre la lengua de redacción del recurso: título, resumen e inicio del cuerpo principal en español, distinguiendo esa evidencia de las menciones o fragmentos en P’urhepecha. No hay todavía decisiones humanas v3 registradas.

## 4. Contrato catalográfico congelado

El contrato maestro usado para evaluación es `dspace-cataloger-v3.6`.

SHA-256 autoritativo del contrato:

`a68fbf9664b7165ea240508da85167058cd57796fbda9c1a9869986afb0178bb`

El contrato continúa siendo el mismo; la corrección afecta la semántica aplicada al caso de revisión, no la identidad del contrato.

## 5. Intake y schema

El schema de intake ahora permite materializar para casos `READY_FOR_INDEPENDENT_REVIEW` / `UNDER_INDEPENDENT_REVIEW` los elementos que exige el protocolo: `metadata_field`, `candidate_value` o abstención esperada, `candidate_intent` y `expected_abstention`. Esto impide abrir nuevos casos de revisión humana sin una proposición concreta.

El intake de candidate 003 conserva los ciclos históricos y añade v3. El estado global permanece no final porque contiene ciclos históricos bloqueados; v3 puede estar `READY_FOR_INDEPENDENT_REVIEW` a nivel de caso sin declarar gold global.

## 6. Gate D

Gate D permanece abierto. Aún faltan, entre otros elementos:

1. dos decisiones humanas independientes para `rereview-v3` y adjudicación si existe desacuerdo;
2. cobertura empírica de los cinco bindings críticos;
3. tamaños de muestra suficientes por binding;
4. adjudicación de las oportunidades restantes;
5. identidades/hashes congelados de vocabularios controlados;
6. comparación/provenance de proveedores y demás evidencia del plan de evaluación.

## 7. Frontera arquitectónica

Esta corrección no convierte evidencia runtime en `VERIFICADO`, no activa proveedor LLM, no autoriza data egress, no crea candidatos runtime y no escribe en DSpace. La adjudicación v2 permanece como registro histórico; cualquier nueva adjudicación v3 que la sustituya deberá enlazarla explícitamente mediante `supersedes_adjudication_id`.
