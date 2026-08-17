# VERTICAL-021 Scorer Contract — semantic evaluation harness

**Estado:** PROPOSED — contrato del scorer/harness para Gate D. No autoriza integración productiva ni proveedor real.

Baseline: `main` @ `476bf5a974ba23c5fcf0c96dc8e69c1a7548ff02`.

## 1. Propósito

Definir cómo puntuar de forma reproducible las salidas de VERTICAL-021 contra el Golden Set semántico sin convertir al scorer en una segunda autoridad catalográfica ni mezclar calidad semántica con seguridad/contrato.

## 2. Entradas

El scorer recibe únicamente artefactos versionados:

1. `manifest.json` del Golden Set;
2. `source.json` por caso;
3. `expected.json` adjudicado;
4. output estructurado del adapter/modelo;
5. metadatos del evaluation run.

El manifest debe aportar además `golden_set_version/hash`, `catalog_contract_version/hash` y, cuando aplique, `controlled_vocabulary_id/version/hash`.

No llama a proveedores, no navega, no consulta DSpace y no modifica runtime.

## 3. Output del scorer

Cada ejecución produce un reporte machine-readable y un resumen humano. Como mínimo:

```json
{
  "evaluation_run_id": "...",
  "golden_set_version": "...",
  "catalog_contract_version": "...",
  "scorer_version": "...",
  "overall": {},
  "by_risk_stratum": {},
  "by_binding": {},
  "by_intent": {},
  "by_language": {},
  "by_document_type": {},
  "cases": [],
  "sample_sufficiency": {},
  "gate_assessment": "PASS|FAIL|INSUFFICIENT_SAMPLE|ASSESSMENT_ONLY"
}
```

El reporte no contiene secretos ni raw credentials.

## 4. Dos superficies de matching

El scorer mantiene dos superficies distintas y nunca las confunde.

### 4.1 `authoritative_match`

Determina TP/FP/FN para precision/recall. Requiere simultáneamente:

- `binding_id` exacto;
- intent exacto;
- valor válido según la regla cerrada del gold;
- grounding correcto cuando sea obligatorio;
- source refs válidas;
- restricciones de cardinalidad/identidad compatibles.

Un candidato con binding incorrecto **no** puede convertirse en TP autoritativo aunque el valor sea plausible.

### 4.2 `diagnostic_value_match`

Existe exclusivamente para diagnosticar `WRONG_BINDING`. Puede comparar un candidato con oportunidades gold de otro binding **sólo** cuando:

- el valor coincide según la misma `normalization_rule`/`closed_alias_set` del gold;
- el intent coincide;
- el grounding, cuando se exige para esa oportunidad, coincide según una política determinista aprobada.

Este match diagnóstico:

- nunca produce TP;
- nunca reduce FP/FN autoritativos;
- sólo alimenta `binding_accuracy` y `WRONG_BINDING`;
- debe usar algoritmo y desempate versionados.

No se usa fuzzy matching, embeddings ni LLM-as-a-judge en ninguna de las dos superficies.

## 5. Matching autoritativo

### Fase 1 — elegibilidad estructural

Un candidato no puede emparejarse autoritativamente si:

- el `binding_id` no coincide con uno esperado;
- el intent no pertenece al schema permitido o no coincide con el gold;
- las source refs requeridas son inválidas;
- el output no es parseable según el contrato.

### Fase 2 — matching de valor

Se aplica exclusivamente la `normalization_rule` declarada en `expected.json`:

- igualdad exacta;
- Unicode/whitespace;
- casefold permitido;
- closed alias set.

Cuando varios candidatos pueden emparejarse, el algoritmo maximiza matches válidos sin reutilizar un mismo candidato esperado o propuesto más de una vez. El algoritmo y su orden de desempate permanecen versionados.

## 6. Métricas básicas

### 6.1 True supported candidate

Cuenta como TP sólo mediante `authoritative_match`.

### 6.2 False proposal

Candidato propuesto que no obtiene `authoritative_match` en una oportunidad semántica evaluable.

### 6.3 Missing expected candidate

Candidato gold esperado y evaluable que no recibió `authoritative_match`.

## 7. Precision y recall

### Micro precision

```text
micro_precision = sum(TP) / (sum(TP) + sum(FP))
```

### Micro recall

Sólo sobre casos con `recall_applicable=true`:

```text
micro_recall = sum(TP) / (sum(TP) + sum(FN))
```

### Macro metrics

Se calcula primero la métrica por unidad y luego se promedia sin ponderar. Debe reportarse al menos:

- macro por binding;
- macro por estrato;
- macro por caso cuando sea interpretable.

Un score micro alto no puede ocultar una degradación del Estrato A.

## 8. Binding accuracy

Se calcula sobre candidatos para los que existe un `diagnostic_value_match` inequívoco o adjudicado.

```text
binding_accuracy = diagnostic_matches_with_exact_binding / binding_evaluable_diagnostic_matches
```

Reglas:

- un `authoritative_match` implica binding correcto;
- un `diagnostic_value_match` con binding distinto registra `WRONG_BINDING`;
- candidatos sin valor/intención/grounding diagnósticamente emparejables quedan fuera del denominador de binding accuracy, pero siguen siendo FP autoritativos cuando corresponda;
- el scorer no “adivina” cuál habría sido el binding correcto por similitud semántica libre.

## 9. Grounding accuracy determinista

Para candidatos con `grounding_required=true`, el scorer aplica exclusivamente `grounding_policy` + `accepted_grounding_ranges` del gold.

Políticas iniciales permitidas:

- `EXACT_RANGE`;
- `RANGE_CONTAINED_IN_ANY`;
- `GOLD_RANGE_CONTAINED_IN_CANDIDATE`;
- `EXACT_PAGE`.

El scorer no decide si un fragmento “contiene evidencia suficiente”. Esa decisión debe haberse materializado previamente mediante anotación humana como regiones gold aceptadas.

Debe reportarse:

```text
grounding_accuracy = correctly_grounded / grounding_evaluable
```

Cambiar la política de grounding o los rangos aceptados cambia la versión del Golden Set/scorer según corresponda.

## 10. Hallucination rate basado en gold

```text
hallucination_rate = gold_classified_unsupported_proposals / all_semantic_proposals
```

Una propuesta entra en el numerador sólo si su clasificación puede derivarse determinísticamente del gold adjudicado, por ejemplo:

- no coincide con ningún `accepted_value` ni alias autorizado para una oportunidad pertinente;
- coincide con un `rejected_value` explícito;
- aparece en una oportunidad marcada para abstención sin candidato permitido;
- viola una contradicción/incompatibilidad estructurada declarada en `expected.json`;
- inventa una entidad/valor que el gold ha marcado explícitamente como no autorizado.

El scorer **no relee semánticamente** el corpus para inferir por sí mismo que algo contradice la evidencia, carece de soporte o es una entidad inventada.

Los fallos puramente estructurales de contract/security se reportan fuera de esta métrica.

## 11. Abstention metrics

Sobre fixtures con abstención esperada:

```text
true_abstention_rate = correctly_abstained_cases / abstention_cases
false_proposal_rate = cases_with_false_proposal / abstention_cases
```

Para `partial-evidence-selective-abstention`, se evalúa por binding/oportunidad y no sólo a nivel de caso completo.

Las razones de abstención provienen del gold adjudicado y no se infieren semánticamente durante scoring.

## 12. Controlled vocabulary exact-match

Sólo para oportunidades donde el gold declare un valor autorizado contra un vocabulario congelado:

```text
controlled_vocab_exact_match = authorized_exact_matches / controlled_vocab_opportunities
```

La evaluación usa el `controlled_vocabulary_id/version/hash` registrado en el Golden Set. El vocabulario vigente en runtime al momento de reejecutar el scorer no puede reinterpretar un resultado histórico.

Un alias no autorizado o fuzzy near-match no cuenta, salvo que figure explícitamente en `closed_alias_set` permitido por el contrato congelado.

## 13. Intent accuracy

```text
intent_accuracy = exact_intent_matches / intent_evaluable_candidates
```

Únicamente:

- `INFERRED_VALUE`;
- `GENERATED_CONTENT`.

Un proveedor que emita estados canónicos (`EXTRAÍDO`, `VERIFICADO`, `PENDIENTE`) produce output inválido de contrato, no una tercera clase semántica.

## 14. Cardinalidad, duplicados y orden

El scorer reporta independientemente:

- `CARDINALITY_ERROR`;
- `DUPLICATE_CANDIDATE`;
- `ORDER_ERROR`.

Una propuesta puede tener valor correcto y aun así fallar estas dimensiones. El reporte conserva ambas señales en vez de colapsarlas en una sola bandera.

## 15. Human-review burden

Esta métrica no se infiere automáticamente del matching. Proviene de anotación humana del run:

- `ACCEPT_AS_IS`;
- `ACCEPT_WITH_MINOR_EDIT`;
- `RESEARCH_REQUIRED`;
- `REJECT`.

Se reportan proporciones globales y por estrato/binding. No forma parte de un PASS automático mientras los targets permanezcan provisionales.

## 16. Sample sufficiency

El scorer calcula oportunidades evaluables por estrato, binding y métrica.

Para Estrato A se requieren simultáneamente:

- **>=20** oportunidades semánticas evaluables en total;
- **>=3** oportunidades evaluables distintas para cada uno de los cinco bindings lingüísticos críticos.

Si falla cualquiera de estos mínimos:

```text
sample_sufficiency = INSUFFICIENT_SAMPLE
```

Un `INSUFFICIENT_SAMPLE` nunca se convierte en PASS por métricas globales.

Los mínimos son piso inicial del diseño; Gate D puede elevarlos antes de cierre definitivo. Un cambio de mínimos debe versionarse y no puede aplicarse retroactivamente para alterar la interpretación de un reporte histórico.

Para estratos B/C, el manifiesto de Gate D deberá fijar mínimos antes de cierre definitivo.

## 17. Targets provisionales

El scorer puede mostrar comparación contra estos `PROVISIONAL_TARGETS`, pero debe etiquetarlos explícitamente como no-SLA:

- candidate precision micro >= 0.95;
- binding accuracy >= 0.98;
- grounding accuracy >= 0.98;
- hallucination rate <= 0.02;
- false proposal rate en abstención <= 0.05;
- controlled-vocabulary exact-match >= 0.98;
- intent accuracy >= 0.98.

Además, debe mostrar macro metrics, cada uno de los cinco bindings del Estrato A y el agregado del Estrato A de forma separada. Ningún agregado puede compensar un error crítico no adjudicado.

## 18. Gate assessment

El scorer semántico sólo evalúa la parte de calidad de Gate D. La decisión final requiere además contract/security y artefactos de gobernanza.

Reglas del reporte semántico:

- `FAIL` si un target **aprobado** y aplicable no se cumple;
- `INSUFFICIENT_SAMPLE` si no existe muestra suficiente para el estrato o cualquiera de los cinco bindings críticos;
- `PASS` sólo si todos los targets ya aprobados y aplicables se cumplen y no quedan critical errors sin adjudicar;
- `ASSESSMENT_ONLY` mientras los thresholds sigan siendo provisionales.

Por tanto, con `PROVISIONAL_TARGETS` el scorer no declara Gate D cerrado automáticamente.

## 19. Error taxonomy

Cada caso debe poder emitir:

- `UNSUPPORTED_VALUE`;
- `WRONG_BINDING`;
- `WRONG_INTENT`;
- `BAD_GROUNDING`;
- `MISSING_EXPECTED_CANDIDATE`;
- `FALSE_PROPOSAL_ON_ABSTENTION`;
- `CONTROLLED_VOCAB_MISMATCH`;
- `CARDINALITY_ERROR`;
- `DUPLICATE_CANDIDATE`;
- `ORDER_ERROR`;
- `INVALID_SOURCE_REF`;
- `SCHEMA_INVALID`.

Debe preservarse severity del gold (`critical`, `major`, `minor`) y distinguir si el error procede de `authoritative_match` o de diagnóstico de binding.

## 20. Reproducibilidad

Cada reporte incluye:

- scorer version/hash;
- Golden Set version/hash;
- `catalog_contract_version/hash`;
- vocabularios controlados `id/version/hash` usados;
- prompt/template version;
- adapter version;
- provider/model id cuando aplique;
- config hash;
- input manifest hashes;
- output hashes;
- run timestamp;
- algoritmo de matching/version;
- política de grounding/version;
- environment/runtime identifier suficiente.

Recalcular el mismo run con los mismos inputs, versiones y hashes debe producir exactamente las mismas métricas.

## 21. No LLM-as-a-judge para el gate autoritativo

Puede existir en el futuro un análisis exploratorio asistido por modelo, pero:

- no determina TP/FP/FN;
- no resuelve equivalencias no anotadas;
- no adjudica disagreements humanos;
- no descubre contradicciones autoritativas;
- no decide grounding;
- no puede cerrar Gate D.

La autoridad evaluativa sigue en gold estructurado + reglas deterministas + adjudicación humana.

## 22. Contract/security boundary

El scorer semántico no calcula como parte de sus denominadores:

- unauthorized network calls;
- egress failures;
- capability enforcement;
- feature flag;
- stale gate;
- atomicity;
- tool-call isolation;
- DSpace read-only.

Estas condiciones siguen siendo gates de 100%/cero tolerancia en sus suites respectivas. El reporte global del harness puede agregarlas visualmente, pero sin mezclarlas matemáticamente con semantic precision/recall.

## 23. Implementación permitida después de aceptar este contrato

La siguiente iteración puede materializar fixtures sintéticos/locales, schemas JSON y un scorer offline determinista. Sigue fuera de alcance conectar un proveedor real al runtime productivo, enviar evidencia externa o activar UI LLM.
