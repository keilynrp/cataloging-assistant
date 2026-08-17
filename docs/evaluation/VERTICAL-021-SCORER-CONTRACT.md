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

No llama a proveedores, no navega, no consulta DSpace y no modifica runtime.

## 3. Output del scorer

Cada ejecución produce un reporte machine-readable y un resumen humano. Como mínimo:

```json
{
  "evaluation_run_id": "...",
  "golden_set_version": "...",
  "scorer_version": "...",
  "overall": {},
  "by_risk_stratum": {},
  "by_binding": {},
  "by_intent": {},
  "by_language": {},
  "by_document_type": {},
  "cases": [],
  "sample_sufficiency": {},
  "gate_assessment": "PASS|FAIL|INSUFFICIENT_SAMPLE"
}
```

El reporte no contiene secretos ni raw credentials.

## 4. Matching de candidatos

El matching es determinista y en dos fases.

### Fase 1 — elegibilidad estructural

Un candidato no puede emparejarse con el gold si:

- el `binding_id` no coincide con uno esperado;
- el intent no pertenece al schema permitido;
- las source refs requeridas son inválidas;
- el output no es parseable según el contrato.

### Fase 2 — matching de valor

Se aplica exclusivamente la `normalization_rule` declarada en `expected.json`:

- exacta;
- Unicode/whitespace;
- casefold permitido;
- closed alias set.

No se usa fuzzy matching, embeddings ni LLM-as-a-judge para decidir correctness autoritativa.

Cuando varios candidatos pueden emparejarse, el algoritmo debe maximizar matches válidos sin reutilizar un mismo candidato esperado o propuesto más de una vez. El algoritmo y su orden de desempate deben permanecer versionados.

## 5. Métricas básicas

### 5.1 True supported candidate

Cuenta como TP sólo si simultáneamente:

- binding correcto;
- valor válido según normalización/equivalencia cerrada;
- intent correcto;
- grounding correcto cuando es obligatorio;
- restricciones de cardinalidad/identidad no invalidan el match.

### 5.2 False proposal

Candidato propuesto que no puede emparejarse válidamente con el gold.

### 5.3 Missing expected candidate

Candidato gold esperado y evaluable que no recibió match.

## 6. Precision y recall

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

## 7. Binding accuracy

Denominador: candidatos emparejables por valor/intención para los que existe binding gold definido.

```text
binding_accuracy = candidates_with_exact_binding / binding_evaluable_candidates
```

Un valor correcto en un binding incorrecto es `WRONG_BINDING` y no TP global.

## 8. Grounding accuracy

Para candidatos con `grounding_required=true`:

- source ref debe estar permitida;
- rango/página/excerpt debe solapar una región gold aceptada según regla explícita;
- atribuir soporte inexistente falla aunque el valor sea correcto.

Debe reportarse:

```text
grounding_accuracy = correctly_grounded / grounding_evaluable
```

La política exacta de overlap se versiona. Default propuesto: el rango del candidato debe intersectar una región gold y contener evidencia suficiente para justificar el valor; una mera coincidencia lexical fuera del contexto aceptado no basta.

## 9. Hallucination rate

```text
hallucination_rate = unsupported_or_invented / all_semantic_proposals
```

Incluye:

- valor sin soporte suficiente;
- entidad inventada;
- contradicción con evidencia disponible;
- propuesta en caso de abstención cuando no existe ningún gold válido.

No incluye fallos puramente estructurales de contract/security, que se reportan aparte.

## 10. Abstention metrics

Sobre fixtures con abstención esperada:

```text
true_abstention_rate = correctly_abstained_cases / abstention_cases
false_proposal_rate = cases_with_false_proposal / abstention_cases
```

Para `partial-evidence-selective-abstention`, se evalúa por binding/oportunidad y no sólo a nivel de caso completo.

## 11. Controlled vocabulary exact-match

Sólo para oportunidades donde el gold declare un valor autorizado:

```text
controlled_vocab_exact_match = authorized_exact_matches / controlled_vocab_opportunities
```

Un alias no autorizado o fuzzy near-match no cuenta, salvo que figure explícitamente en `closed_alias_set` permitido por el contrato.

## 12. Intent accuracy

```text
intent_accuracy = exact_intent_matches / intent_evaluable_candidates
```

Únicamente:

- `INFERRED_VALUE`;
- `GENERATED_CONTENT`.

Un proveedor que emita estados canónicos (`EXTRAÍDO`, `VERIFICADO`, `PENDIENTE`) produce output inválido de contrato, no una tercera clase semántica.

## 13. Cardinalidad, duplicados y orden

El scorer reporta independientemente:

- `CARDINALITY_ERROR`;
- `DUPLICATE_CANDIDATE`;
- `ORDER_ERROR`.

Una propuesta puede tener valor correcto y aun así fallar estas dimensiones. El reporte debe conservar ambas señales en vez de colapsarlas en una sola bandera.

## 14. Human-review burden

Esta métrica no se infiere automáticamente del matching. Proviene de anotación humana del run:

- `ACCEPT_AS_IS`;
- `ACCEPT_WITH_MINOR_EDIT`;
- `RESEARCH_REQUIRED`;
- `REJECT`.

Se reportan proporciones globales y por estrato/binding. No forma parte de un PASS automático mientras los targets permanezcan provisionales.

## 15. Sample sufficiency

El scorer calcula oportunidades evaluables por estrato y métrica.

Para Estrato A:

- `<20` oportunidades semánticas evaluables -> `INSUFFICIENT_SAMPLE` para Gate D;
- `>=20` permite evaluar targets provisionales, sujeto a revisión humana y adjudicación completa.

Un `INSUFFICIENT_SAMPLE` nunca se convierte en PASS por métricas globales.

Para estratos B/C, el manifiesto de Gate D deberá fijar mínimos antes de cierre definitivo.

## 16. Targets provisionales

El scorer puede mostrar comparación contra estos `PROVISIONAL_TARGETS`, pero debe etiquetarlos explícitamente como no-SLA:

- candidate precision micro >= 0.95;
- binding accuracy >= 0.98;
- grounding accuracy >= 0.98;
- hallucination rate <= 0.02;
- false proposal rate en abstención <= 0.05;
- controlled-vocabulary exact-match >= 0.98;
- intent accuracy >= 0.98.

Además, debe mostrar macro metrics y Estrato A de forma separada. Ningún agregado puede compensar un error crítico no adjudicado.

## 17. Gate assessment

El scorer semántico sólo evalúa la parte de calidad de Gate D. La decisión final de Gate D requiere además contract/security y artefactos de gobernanza.

Reglas del reporte semántico:

- `FAIL` si un target aprobado y aplicable no se cumple;
- `INSUFFICIENT_SAMPLE` si no existe muestra suficiente para un estrato crítico;
- `PASS` sólo si todos los targets ya **aprobados** y aplicables se cumplen y no quedan critical errors sin adjudicar.

Mientras los thresholds sean provisionales, el scorer debe usar `ASSESSMENT_ONLY` o equivalente y no declarar Gate D cerrado automáticamente.

## 18. Error taxonomy

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

Debe preservarse severity del gold (`critical`, `major`, `minor`).

## 19. Reproducibilidad

Cada report incluye:

- scorer version/hash;
- Golden Set version/hash;
- prompt/template version;
- adapter version;
- provider/model id cuando aplique;
- config hash;
- input manifest hashes;
- output hashes;
- run timestamp;
- algoritmo de matching/version;
- environment/runtime identifier suficiente.

Recalcular el mismo run con los mismos inputs y scorer version debe producir exactamente las mismas métricas.

## 20. No LLM-as-a-judge para el gate autoritativo

Puede existir en el futuro un análisis exploratorio asistido por modelo, pero:

- no determina TP/FP/FN;
- no resuelve equivalencias no anotadas;
- no adjudica disagreements humanos;
- no puede cerrar Gate D.

La autoridad evaluativa sigue en gold estructurado + reglas deterministas + adjudicación humana.

## 21. Contract/security boundary

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

## 22. Implementación permitida después de aceptar este contrato

La siguiente iteración puede materializar fixtures sintéticos/locales, schemas JSON y un scorer offline determinista. Sigue fuera de alcance conectar un proveedor real al runtime productivo, enviar evidencia externa o activar UI LLM.