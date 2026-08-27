# VERTICAL-021 Human Adjudication Protocol

**Estado:** METHODOLOGY ACCEPTED / GATE D OPEN — protocolo vigente. Existen artefactos reales de revisión/adjudicación a nivel de caso, pero la cobertura empírica de Estrato A sigue incompleta; no autoriza implementación productiva.

Baseline: `main` @ `f9f0d1c4db21ecfe4605ed77279ad3d48719dd4e`.

Gobernado por:

- `docs/evaluation/VERTICAL-021-EVALUATION-PLAN.md`;
- `docs/evaluation/VERTICAL-021-GOLDEN-SET-CONTRACT.md`;
- `docs/evaluation/VERTICAL-021-SCORER-CONTRACT.md`;
- `docs/specs/VERTICAL-021-provider-independent-llm-assisted-extraction.md`;
- `docs/adr/ADR-017-provider-independent-llm-evidence-extraction.md`.

## 1. Propósito

Preparar el procedimiento auditable para convertir evidencia real/local **previamente autorizada** en un Golden Set adjudicado por catalogadores, sin inventar evidencia, decisiones humanas ni resultados de calidad.

Este protocolo no sustituye el Golden Set sintético. Lo complementa con una futura capa empírica cuya autoridad proviene de revisión humana independiente y adjudicación documentada.

## 2. Condición de entrada y estados previos

Un caso puede pasar a `READY_FOR_INDEPENDENT_REVIEW` sólo si:

1. la evidencia está autorizada para uso local en evaluación;
2. existe snapshot inmutable o representación local reproducible;
3. su procedencia y hash pueden registrarse sin exponer secretos;
4. el caso declara bindings/campos bajo evaluación;
5. no requiere enviar datos a un proveedor externo;
6. no modifica DSpace ni ningún workflow productivo.

La falta de autorización o de material todavía no constituye por sí sola un fallo. Mientras la evidencia pueda incorporarse legítimamente más adelante, el estado correcto es `AWAITING_AUTHORIZED_EVIDENCE` con `authorization_status=PENDING`.

`BLOCKED_FOR_INTAKE` se reserva para una condición explícitamente impeditiva, por ejemplo evidencia no autorizable, licencia incompatible, provenance insuficiente no corregible o incumplimiento de política institucional. `PENDING` y `BLOCKED` no son equivalentes.

## 3. Separación de roles

Para Estrato A se requieren, como mínimo:

- `reviewer_1`: catalogador independiente;
- `reviewer_2`: catalogador independiente;
- `adjudicator`: responsable de resolver desacuerdos.

Un revisor no debe ver la decisión del otro antes de enviar su juicio cuando sea operativamente viable.

El adjudicador puede coincidir con uno de los revisores sólo si la política institucional lo permite y queda registrado; el modo preferido es un tercero.

## 4. Unidad de revisión

La unidad mínima es un **caso + binding + candidato/abstención esperada**.

Cada unidad debe conservar:

- `case_id`;
- `binding_id`;
- `metadata_field` derivado del contrato;
- referencia(s) a la evidencia autorizada;
- `evidence_snapshot_sha256` real del snapshot revisado;
- valor candidato o marca de abstención;
- `candidate_intent` cuando aplique;
- grounding/source refs cuando aplique;
- versión del Golden Set;
- `catalog_contract_version` y `catalog_contract_sha256`.

## 5. Etiquetas de revisión humana

Cada revisor emite exactamente una decisión:

- `ACCEPT_AS_IS`;
- `ACCEPT_WITH_MINOR_EDIT`;
- `RESEARCH_REQUIRED`;
- `REJECT`.

Además registra:

- `review_id`;
- `reviewer_id` seudónimo/no secreto;
- `case_id` y `binding_id`;
- timestamp UTC;
- comentario breve;
- taxonomía de error cuando aplique;
- valor corregido propuesto sólo cuando la decisión requiera edición;
- evidencia/grounding que sustenta el juicio;
- `evidence_snapshot_sha256`;
- `golden_set_version`;
- `catalog_contract_version` y `catalog_contract_sha256`.

El juicio humano no cambia automáticamente el estado runtime a `VERIFICADO`.

## 6. Taxonomía cerrada de error

Cuando aplique, sólo se aceptan:

- `UNSUPPORTED_VALUE`;
- `WRONG_BINDING`;
- `WRONG_INTENT`;
- `GROUNDING_ERROR`;
- `CARDINALITY_ERROR`;
- `NORMALIZATION_ERROR`;
- `CONTROLLED_VOCABULARY_ERROR`;
- `MISSED_EXPECTED_CANDIDATE`;
- `FALSE_PROPOSAL_WHEN_ABSTENTION_EXPECTED`.

Un comentario libre puede explicar la decisión, pero no sustituye la categoría estructurada.

## 7. Evidencia de dos revisiones independientes

Para Estrato A no basta almacenar dos identificadores de revisor. Antes de promover una unidad a estado final deben existir **dos revisiones completas y materializadas**.

El intake registra dos `completed_reviews`, cada una con:

- `review_id` distinto;
- `reviewer_id` distinto;
- mismo `case_id` que la unidad;
- mismo `binding_id` bajo revisión;
- mismo `evidence_snapshot_sha256` real.

La validación estructural exige dos revisiones; la validación de consistencia debe verificar que ambas referencias pertenecen efectivamente al mismo caso, binding y snapshot. Una mera lista de nombres o IDs sin artefactos de revisión no constituye doble revisión.

## 8. Reglas de adjudicación

Un caso requiere adjudicación si:

- las decisiones de los dos revisores difieren;
- ambos aceptan, pero proponen valores corregidos incompatibles;
- existe desacuerdo sobre binding, grounding, vocabulario o abstención;
- el gold previo resulta ambiguo;
- el desacuerdo puede cambiar una métrica o threshold de Gate D.

La adjudicación final registra y congela:

- `adjudication_status=FINAL`;
- `final_decision`;
- `final_value` o `final_abstention`;
- error taxonómico final cuando aplique;
- `adjudicator_id`;
- timestamp UTC;
- comentario breve;
- las dos revisiones de entrada con `review_id`, `reviewer_id`, `case_id`, `binding_id` y hash de evidencia;
- `evidence_snapshot_sha256` real;
- `input_golden_set_version`;
- `catalog_contract_version`;
- `catalog_contract_sha256` real;
- `resulting_gold_version`.

Los templates preparatorios usan `adjudication_status=TEMPLATE` y pueden contener `REPLACE_*`. Un artefacto `FINAL` no puede conservar placeholders en hashes de evidencia o contrato.

Nunca se reescribe silenciosamente una adjudicación previa. Una corrección posterior produce nueva versión y referencia explícita a la adjudicación sustituida.

## 9. Reglas de construcción del gold empírico

Un caso del Estrato A puede promoverse a `ADJUDICATED_GOLD` sólo cuando:

1. la evidencia está `AUTHORIZED_LOCAL_EVALUATION`;
2. `evidence_snapshot_sha256` es un hash real y no un placeholder;
3. existen dos revisiones independientes completas y enlazadas al mismo caso/binding/snapshot;
4. los dos `reviewer_id` son distintos;
5. existe adjudicador cuando corresponde cierre final;
6. no quedan desacuerdos abiertos;
7. toda discrepancia relevante fue adjudicada;
8. el snapshot de evidencia sigue siendo exactamente el mismo que se revisó;
9. el binding y `metadata_field` coinciden con el contrato registrado;
10. la versión y hash del contrato están congelados;
11. la anotación estructurada puede ser consumida por el scorer sin interpretación humana adicional;
12. la provenance no contiene credenciales ni secretos.

La promoción a `ADJUDICATED_GOLD` es un estado del **artefacto de evaluación**, no del runtime catalográfico.

## 10. Consistencia del estado global

El `status` global del intake es un agregado del estado de sus casos; no puede contradecirlos.

En particular, `status=ADJUDICATED_GOLD` sólo es válido cuando **todos** los casos incluidos en ese intake tienen `review_status=ADJUDICATED_GOLD`, el `catalog_contract_sha256` global es real y no existen casos pendientes, bloqueados o bajo revisión.

Si existe al menos un caso pendiente o no final, el intake debe permanecer en el estado agregado no final que corresponda (`AWAITING_AUTHORIZED_EVIDENCE`, `READY_FOR_INDEPENDENT_REVIEW`, `UNDER_INDEPENDENT_REVIEW`, `AWAITING_ADJUDICATION` o `BLOCKED_FOR_INTAKE`).

## 11. Privacidad y autorización

Los artefactos persistidos en el repositorio no deben contener:

- credenciales;
- tokens;
- datos personales innecesarios;
- documentos completos si su licencia/autorización no permite versionarlos;
- URLs privadas con secretos en query strings;
- nombres reales de revisores si la política exige seudonimización.

Cuando el documento real no pueda almacenarse, se registra un identificador local autorizado, hash y selector reproducible; el contenido fuente permanece fuera del repositorio.

## 12. Estados de intake

Estados permitidos:

- `AWAITING_AUTHORIZED_EVIDENCE`;
- `READY_FOR_INDEPENDENT_REVIEW`;
- `UNDER_INDEPENDENT_REVIEW`;
- `AWAITING_ADJUDICATION`;
- `ADJUDICATED_GOLD`;
- `BLOCKED_FOR_INTAKE`.

No se permite declarar `ADJUDICATED_GOLD` con datos sintéticos que no hayan sido efectivamente revisados por dos catalogadores.

## 13. Evidencia mínima para cerrar la fase humana de Estrato A

Antes de usar resultados empíricos para ratificar thresholds de Gate D debe existir:

- cobertura de los cinco bindings críticos;
- al menos dos revisores independientes por oportunidad de Estrato A incluida en el cálculo;
- artefactos de revisión materializados y enlazados al mismo snapshot;
- adjudicación de todo desacuerdo material;
- reporte de `n` por binding/familia;
- provenance/version/hash del corpus y del contrato;
- distribución de las cuatro etiquetas de revisión;
- errores por taxonomía;
- documentación de exclusiones y casos bloqueados.

El mínimo aritmético del corpus sintético no se convierte automáticamente en evidencia empírica suficiente.

## 14. Artefactos preparados por este protocolo

La implementación preparatoria incluye:

```text
apps/api/tests/golden/llm-evidence/human-review/
  schemas/
    intake-manifest.schema.json
    reviewer-decision.schema.json
    adjudication.schema.json
  templates/
    intake-manifest.template.json
    reviewer-decision.template.json
    adjudication.template.json
```

Los templates usan identificadores `REPLACE_*` y estados no finales para impedir que se interpreten como adjudicaciones reales.

## 15. Qué no autoriza

Este protocolo no autoriza:

- inventar revisores o adjudicaciones;
- convertir el corpus sintético en gold humano por declaración;
- usar un proveedor LLM real;
- data egress;
- endpoints/migraciones LLM;
- UI runtime LLM;
- OCR/tool use/browsing;
- auto-accept/auto-copy;
- escritura DSpace.

## 16. Próximo paso permitido

Tras aceptar este protocolo, el siguiente paso es seleccionar evidencia real/local autorizada y asignar dos catalogadores humanos para completar los artefactos de revisión. Hasta entonces, el estado correcto permanece `AWAITING_AUTHORIZED_EVIDENCE`.
