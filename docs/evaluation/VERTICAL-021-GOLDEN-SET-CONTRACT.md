# VERTICAL-021 Golden Set Contract — LLM-assisted evidence extraction

**Estado:** PROPOSED — diseño de fixtures/anotaciones para Gate D. No autoriza runtime LLM ni uso de proveedor real.

Baseline: `main` @ `476bf5a974ba23c5fcf0c96dc8e69c1a7548ff02`.

Gobernado por:

- `docs/specs/VERTICAL-021-provider-independent-llm-assisted-extraction.md`;
- `docs/adr/ADR-017-provider-independent-llm-evidence-extraction.md`;
- `docs/evaluation/VERTICAL-021-EVALUATION-PLAN.md`;
- ADR-014/015/016 para evidencia y provenance;
- contrato maestro de catalogación vigente.

## 1. Propósito

Definir el formato, cobertura mínima, anotación humana y reglas de versionado del Golden Set semántico de VERTICAL-021. Este Golden Set evalúa **candidatos LLM**; no reemplaza ni modifica el Golden Set determinista existente de `apps/api/tests/golden/evidence/`.

## 2. Separación de corpus

El corpus queda dividido en tres superficies no intercambiables:

1. **Deterministic Golden Set** — runtime actual; permanece intacto.
2. **Contract/security fixtures** — fake adapter, fail-closed, sin red; no entran en denominadores semánticos.
3. **Semantic Golden Set VERTICAL-021** — anotaciones humanas para medir precision, binding, grounding, intent, abstention y carga de revisión.

Un mismo texto fuente puede inspirar fixtures en más de una superficie, pero cada caso debe declarar una sola `evaluation_surface`.

## 3. Ubicación futura

Cuando se implemente el harness, la ubicación preferida es:

```text
apps/api/tests/golden/llm-evidence/
  manifest.json
  cases/
    <case-id>/
      source.json
      expected.json
      notes.md          # opcional; nunca usado por scorer
```

Este documento sólo congela el contrato; no crea todavía fixtures ejecutables.

## 4. Estratos de riesgo

### Estrato A — crítico/gobernado

Debe cubrir obligatoriamente los cinco campos lingüísticos exactos:

- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticVariant`
- `dc.description.registeredLanguage`

Reglas:

- `linguisticBranch` y `linguiscgroup` son campos independientes;
- `dc.subject.linguiscgroup` conserva exactamente el literal histórico;
- no se permite que el scorer normalice o corrija nombres técnicos;
- errores de binding en este estrato son siempre `critical`;
- debe existir doble revisión humana + adjudicación;
- un estrato A con menos de 20 oportunidades semánticas evaluables queda `INSUFFICIENT_SAMPLE`.

### Estrato B — estructurado/controlado

Bindings con vocabularios controlados, ambigüedad de `metadata_field`, cardinalidad/repetibilidad o reglas fuertes de validación. Se cubren por familias de comportamiento, no mediante 56 benchmarks independientes.

### Estrato C — descriptivo/abierto

Campos textuales o descriptivos donde puede existir más de una formulación aceptable. Deben usar conjuntos cerrados de equivalencias aceptadas o reglas de normalización explícitas; nunca similitud semántica libre como sustituto del gold.

## 5. Inventario mínimo de casos semánticos

El primer Golden Set debe contener al menos los siguientes **casos semánticos**, separados de tests de seguridad/contrato:

### A. Lingüística crítica

1. `ling-family-explicit-plus-inference` — familia explícita y una inferencia legítima distinta del texto literal.
2. `ling-branch-independent-from-group` — rama presente sin agrupación; no inventar agrupación.
3. `ling-group-independent-from-branch` — agrupación presente sin rama; no inventar rama.
4. `ling-historical-literal-preserved` — candidato correcto para `dc.subject.linguiscgroup`; cualquier spelling técnico alternativo falla binding.
5. `ling-variant-grounded` — variante sustentada por excerpt localizable.
6. `ling-registered-language-distinct` — `dc.description.registeredLanguage` no se confunde con jerarquía genealógica.
7. `ling-conflicting-sources-abstain` — fuentes incompatibles sin regla suficiente; se espera abstención.
8. `ling-multi-value-repeatable-order` — dos valores válidos, identidad y orden preservados.
9. `ling-controlled-vocab-out-of-list` — propuesta plausible pero fuera del vocabulario activo; no cuenta como authoritative match.
10. `ling-insufficient-evidence-abstain` — texto menciona contexto lingüístico sin base suficiente para el binding.

El manifiesto debe expandir estos casos hasta producir **>=20 oportunidades evaluables del Estrato A**, sin duplicar artificialmente el mismo patrón textual.

### B. Grounding y binding

11. `grounding-correct-source-wrong-range` — valor correcto con rango/excerpt incorrecto.
12. `grounding-source-within-manifest` — soporte correcto y source ref válida.
13. `binding-plausible-wrong-field` — valor correcto semánticamente, binding incorrecto; debe fallar.
14. `multi-source-supported-value` — dos fuentes apoyan la misma inferencia.
15. `multi-source-contradiction-abstain` — contradicción irresuelta; abstención esperada.

### C. Intent y generación

16. `intent-inferred-value` — salida `INFERRED_VALUE` esperada.
17. `intent-generated-content` — salida `GENERATED_CONTENT` esperada bajo una tarea explícitamente autorizada por fixture.
18. `generated-not-extracted` — contenido sintetizado no puede tratarse como `EXTRAÍDO`.
19. `inferred-not-verified` — inferencia correcta nunca nace `VERIFICADO`.

### D. Abstención y cobertura

20. `no-evidence-no-candidate` — ninguna propuesta.
21. `partial-evidence-selective-abstention` — sólo algunos bindings tienen soporte.
22. `ambiguous-entity-abstention` — entidad no desambiguada.
23. `open-task-no-exhaustive-recall` — fixture marcado `recall_applicable=false`.

### E. Multilingüe/multientidad/repetibilidad

24. `multilingual-source-language-separated`.
25. `multiple-authors-no-entity-collapse`.
26. `repeatable-values-preserve-identity`.
27. `same-value-different-source-provenance`.

## 6. Casos que NO pertenecen al Golden Set semántico

Los siguientes deben vivir exclusivamente en contract/security fixtures y no contar para precision/recall/hallucination:

- feature flag OFF;
- egress `deny` / `indeterminate`;
- credential sólo `agent`;
- ausencia de `evidence_inference` capability;
- acción humana no autenticada;
- stale-session gate;
- timeout/provider error;
- atomicidad/persistencia parcial;
- tool-call rejection;
- prompt injection como bypass de permisos;
- DSpace write prevention;
- source ref fuera de manifest cuando el objetivo del caso sea schema/authorization, no grounding semántico.

## 7. `manifest.json` — contrato

Cada caso del manifiesto debe incluir como mínimo:

```json
{
  "id": "ling-group-independent-from-branch",
  "evaluation_surface": "semantic",
  "risk_stratum": "A",
  "languages": ["es"],
  "document_type": "article",
  "bindings_under_test": ["<binding-id>"],
  "metadata_fields_under_test": ["dc.subject.linguiscgroup"],
  "intent_classes": ["INFERRED_VALUE"],
  "recall_applicable": true,
  "opportunity_count": 1,
  "human_review": "double_plus_adjudication",
  "severity": "critical"
}
```

El `binding-id` real debe provenir del contrato maestro vigente. El fixture nunca inventa IDs.

## 8. `source.json` — contrato

Debe representar exactamente la evidencia entregada al harness, no una URL viva ni una referencia reconstruible después. Debe incluir:

- `case_id`;
- una o más fuentes inmutables;
- `source_id` estable dentro del fixture;
- media type;
- texto exacto o referencia local al fixture;
- orden de fuente;
- fragmentos/rangos/páginas disponibles para grounding;
- hashes una vez materializado el fixture ejecutable;
- idioma/tipo documental cuando sea conocido.

No contiene instrucciones secretas ni credenciales y no requiere red.

## 9. `expected.json` — contrato de anotación

Estructura mínima:

```json
{
  "case_id": "ling-group-independent-from-branch",
  "expected_candidates": [
    {
      "binding_id": "<binding-id-real>",
      "metadata_field": "dc.subject.linguiscgroup",
      "candidate_intent": "INFERRED_VALUE",
      "derived_evidence_state": "INFERIDO",
      "accepted_values": ["<valor autorizado>"],
      "normalization_rule": "none",
      "source_refs_allowed": ["source-1"],
      "grounding_required": true,
      "accepted_grounding_ranges": [{"source_id":"source-1","start":0,"end":0}],
      "cardinality": "repeatable",
      "order_significant": true,
      "expected_validation": "<contract-outcome>",
      "expected_draftability": "<backend-derived>",
      "severity": "critical"
    }
  ],
  "expected_abstentions": [],
  "recall_applicable": true
}
```

`metadata_field`, validation y draftability se anotan como valores esperados **derivados del contrato/backend**, no como campos que el modelo pueda elegir.

## 10. Equivalencias y normalización

Cada candidato esperado debe declarar una de estas políticas:

- `none` — igualdad exacta;
- `unicode_whitespace` — normalización Unicode y espacios únicamente;
- `casefold_if_contract_allows` — sólo si el contrato del binding lo permite;
- `closed_alias_set` — conjunto explícito de equivalencias humanas aprobadas.

Queda prohibido para scoring autoritativo:

- fuzzy matching abierto;
- embeddings/similitud semántica;
- corrección automática del `metadata_field`;
- transformar un valor no autorizado en match porque “significa lo mismo”.

## 11. Cardinalidad, repetibilidad y orden

El gold debe declarar:

- `single` / `repeatable`;
- número mínimo/máximo esperado cuando aplique;
- si el orden es significativo;
- identidad de cada candidato esperado.

Duplicados, colapso de valores repetibles o reordenamiento no permitido deben producir errores separados del error semántico del valor.

## 12. Abstención

Una abstención puede ser:

- `INSUFFICIENT_EVIDENCE`;
- `CONFLICTING_EVIDENCE`;
- `AMBIGUOUS_ENTITY`;
- `OUT_OF_SCOPE_BINDING`;
- `NO_AUTHORIZED_VALUE`.

El harness evalúa si se omitió correctamente el candidato esperado; estas razones son anotación del gold y no obligan a que el proveedor genere exactamente esa etiqueta salvo que el schema futuro la incluya explícitamente.

## 13. Taxonomía de errores

El scorer debe poder atribuir cada fallo a una o más categorías:

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

Los errores de contrato/security se reportan en su suite y no se mezclan con esta taxonomía semántica salvo `SCHEMA_INVALID` cuando impida puntuar un run de evaluación.

## 14. Anotación humana

Estrato A:

- dos catalogadores revisan independientemente;
- cualquier desacuerdo se adjudica;
- se conserva la decisión final y breve justificación;
- no se conserva razonamiento privado extenso como entrada del scorer.

Estratos B/C:

- doble revisión recomendada para casos ambiguos/críticos;
- una revisión experta puede bastar para fixtures inequívocos, sujeto a revisión del manifiesto.

## 15. Versionado

Cambiar cualquiera de estos elementos incrementa versión del Golden Set:

- fuentes;
- expected candidates;
- equivalencias;
- binding IDs;
- clasificación de estrato;
- reglas de grounding;
- cardinalidad/orden;
- política de abstención.

Correcciones puramente editoriales de `notes.md` que no alteren scoring no cambian la versión semántica.

## 16. Criterio de aceptación del diseño

Este contrato puede aceptarse antes de que existan los fixtures ejecutables. Gate D, en cambio, sólo podrá cerrarse cuando el corpus materializado, las anotaciones adjudicadas y el scorer reproducible existan y hayan sido revisados.