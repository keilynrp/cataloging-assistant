# VERTICAL-021 Evaluation Plan — LLM-assisted evidence extraction

**Estado:** PROPOSED — Gate D artifact. No autoriza implementación productiva.

Baseline: `main` @ `4cf1134e25075fecc4eb5e5e7357771b6bae27b9`.

Gobernado por:

- `docs/specs/VERTICAL-021-provider-independent-llm-assisted-extraction.md`;
- `docs/adr/ADR-017-provider-independent-llm-evidence-extraction.md`;
- ADR-014/015/016 para evidencia determinista, PDF y fetch remoto;
- `UX-DECISION-001` para presentación futura.

## 1. Propósito

Definir cómo evaluar la calidad, seguridad, grounding y utilidad catalográfica de una futura implementación de VERTICAL-021 antes de usar un proveedor real en trabajo de catalogación.

Este plan mantiene separados tres tipos de evidencia de calidad:

1. **tests funcionales/contractuales**, deterministas y obligatorios en CI;
2. **tests de seguridad**, deterministas y fail-closed;
3. **evaluación semántica de modelo**, ejecutada en un harness separado, reproducible y versionado.

Un buen score semántico nunca compensa un fallo de contrato o seguridad.

## 2. Principios de evaluación

1. El LLM genera candidatos; no es autoridad catalográfica.
2. El baseline determinista permanece intacto y sirve de control.
3. `INFERIDO` y `GENERADO` se evalúan por separado.
4. La evaluación se hace por campo/binding y por fixture, no sólo con un promedio global.
5. Grounding y binding correctness tienen prioridad sobre cobertura agresiva.
6. La abstención correcta es preferible a una propuesta inventada.
7. Los vocabularios controlados se juzgan contra exact-match backend, no contra similitud semántica del modelo.
8. Ningún proveedor real forma parte de `make test`.
9. Todo run de evaluación debe ser reproducible mediante versión de dataset, prompt, adapter, modelo/config y hashes de entrada/salida.
10. El paso a pilotaje humano requiere aprobar thresholds explícitos; no se decide por impresión visual.

## 3. Capas de evaluación

### 3.1 Contract suite — obligatoria

Debe validar, con fake adapter y sin red:

- schema cerrado;
- allowlist de bindings;
- `metadata_field` derivado server-side;
- `INFERRED_VALUE -> INFERIDO`;
- `GENERATED_CONTENT -> GENERADO`;
- rechazo de intents fuera de enum;
- source refs limitadas al input manifest;
- exact input manifest y orden;
- request/config hash sensible a cambios relevantes;
- atomicidad de persistencia;
- sesiones stale bloqueadas;
- feature flag OFF sin red;
- capability `evidence_inference` obligatoria;
- egress deny/indeterminate sin red;
- acción humana obligatoria;
- adapter de evidencia sin tools/tool calls;
- DSpace read-only;
- inventario del agente sin nuevas herramientas mutables.

**Gate:** 100% de estos tests deben pasar. No existe tolerancia porcentual.

### 3.2 Security/adversarial suite — obligatoria

Debe incluir fixtures con:

- prompt injection explícita;
- instrucciones embebidas en HTML/PDF/texto;
- intento de inventar bindings;
- intento de pedir tool use/browsing;
- intento de exfiltrar secretos;
- source refs inexistentes;
- outputs sobredimensionados;
- contenido contradictorio entre fuentes;
- datos sensibles/restringidos clasificados como no elegibles para egress;
- credencial activa sólo para `agent`;
- policy decision `deny` e `indeterminate`.

**Gate:** cero bypasses de autorización, cero tool calls aceptados, cero tráfico externo cuando corresponde fail-closed y cero secretos en logs/provenance/output.

### 3.3 Semantic quality harness — separado

Evalúa respuestas de uno o más adapters/modelos contra anotaciones humanas de referencia. No modifica runtime ni persiste resultados como candidatos productivos.

Debe producir resultados por:

- fixture;
- binding;
- tipo `INFERIDO` / `GENERADO`;
- idioma/tipo documental;
- proveedor/modelo/config;
- versión de prompt;
- versión del Golden Set.

## 4. Golden Set VERTICAL-021

La extensión no debe alterar ni reescribir los casos existentes de VERTICAL-019/020. Se propone una capa adicional versionada, conceptualmente:

```text
apps/api/tests/golden/llm-evidence/
  manifest.json
  cases/
    <case-id>/
      source.json
      expected.json
      notes.md        # opcional, sólo para razonamiento del anotador
```

La ubicación exacta puede ajustarse en implementación, pero debe quedar separada del Golden Set determinista actual.

### 4.1 Estratificación de riesgo y cobertura

El Golden Set no convierte los 56 bindings del contrato maestro en 56 benchmarks independientes. La cobertura debe organizarse por **estratos de riesgo**, familias de bindings y casos catalográficos representativos.

#### Estrato A — crítico/gobernado

Debe cubrir de forma explícita y repetida los bindings cuyo error puede producir una asignación semántica incorrecta o una falsa autoridad. Como mínimo:

- `dc.subject.linguisticFamily`;
- `dc.subject.linguisticBranch`;
- `dc.subject.linguiscgroup`;
- `dc.subject.linguisticVariant`;
- `dc.description.registeredLanguage`;
- bindings de vocabulario controlado;
- bindings ambiguos que dependen de `binding_id` exacto;
- cualquier binding que la política institucional marque posteriormente como crítico.

Los cinco campos lingüísticos deben probarse tanto individualmente como en combinaciones que permitan detectar confusiones jerárquicas. `dc.subject.linguiscgroup` se preserva exactamente con su literal histórico.

#### Estrato B — estructurado/repetible

Cubre familias de campos donde importan cardinalidad, repetibilidad, identidad de entidad, normalización y source attribution, por ejemplo autores múltiples, identificadores, relaciones y valores repetidos.

#### Estrato C — descriptivo/abierto

Cubre campos textuales o de generación controlada donde puede existir más de una salida aceptable y donde precision, grounding, intent y carga de revisión son más informativos que una coincidencia literal.

La versión inicial del Golden Set debe declarar en `manifest.json` qué bindings/familias cubre cada fixture y qué huecos permanecen. La cobertura estratificada puede crecer por versiones sin bloquear el MVP por exigir exhaustividad artificial sobre los 56 bindings.

### 4.2 Tipos mínimos de casos semánticos

El primer corte semántico debe cubrir, como mínimo:

1. valor literal presente + inferencia adicional legítima;
2. dos fuentes que se contradicen;
3. recurso multilingüe;
4. recurso multientidad/autores múltiples;
5. valor fuera de vocabulario controlado;
6. binding ambiguo que exige identidad exacta;
7. candidato `INFERIDO` correcto pero no draftable;
8. `GENERADO` claramente distinguible de texto autoral `EXTRAÍDO`;
9. falta de evidencia suficiente: resultado esperado = abstención/no candidato;
10. supporting excerpt inválido o no localizable;
11. variante lingüística / agrupación / rama donde los campos exactos no se confundan;
12. literal histórico `dc.subject.linguiscgroup` preservado exactamente;
13. cardinalidad/repetibilidad: múltiples valores correctos sin pérdida ni fusión;
14. equivalencias aceptables bajo normalización autorizada;
15. caso crítico con distractores semánticamente plausibles pero binding incorrecto.

Los casos de prompt injection, egress, stale session, capability, atomicidad, tool-calling y provider failure pertenecen a contract/security suites. Pueden reutilizar infraestructura de fixtures, pero **no forman parte de los denominadores semánticos** de precision, recall, hallucination, grounding o exact-match.

### 4.3 Contrato de anotación de referencia

Cada `expected.json` debe poder expresar, cuando aplique:

- `binding_id` esperado;
- valor esperado, lista de valores esperados o conjunto cerrado de equivalencias aceptables;
- reglas de normalización permitidas antes del scoring;
- cardinalidad y repetibilidad esperadas;
- `candidate_intent` esperado;
- evidence state derivado esperado;
- source refs permitidas;
- requirement de supporting excerpt;
- expected validation outcome;
- expected draftability/copy eligibility;
- si la respuesta correcta es abstenerse;
- severity si falla el caso (`critical`, `major`, `minor`);
- taxonomía de error esperada/aplicable para adjudicación.

No se debe usar una respuesta textual libre del anotador como único gold estándar.

La taxonomía mínima de error semántico debe distinguir:

- `UNSUPPORTED_VALUE`;
- `WRONG_BINDING`;
- `WRONG_INTENT`;
- `GROUNDING_ERROR`;
- `CARDINALITY_ERROR`;
- `NORMALIZATION_ERROR`;
- `CONTROLLED_VOCABULARY_ERROR`;
- `MISSED_EXPECTED_CANDIDATE`;
- `FALSE_PROPOSAL_WHEN_ABSTENTION_EXPECTED`.

## 5. Métricas semánticas

Las métricas se calculan únicamente sobre fixtures etiquetados como **semantic-quality eligible**. Casos contract/security se reportan por separado y nunca inflan ni deprimen estas tasas.

### 5.1 Candidate precision

`precision = true_supported_candidates / all_proposed_candidates`

Mide cuánto de lo propuesto por el modelo es correcto y sustentado.

Debe reportarse como:

- **micro precision**: agregando candidatos de todos los fixtures elegibles;
- **macro precision**: promedio de precision por binding/familia o estrato, según corresponda.

### 5.2 Candidate recall

`recall = true_supported_candidates / all_expected_candidates`

Se usa sólo en fixtures donde exista un conjunto esperado razonablemente exhaustivo. No debe forzarse recall en tareas abiertas de generación.

También debe reportarse micro/macro cuando el tamaño de muestra lo permita.

### 5.3 Binding accuracy

Porcentaje de candidatos correctos asignados al `binding_id` exacto esperado.

Un valor semánticamente plausible en un binding incorrecto cuenta como error.

Debe reportarse globalmente y por estrato, con desglose obligatorio del Estrato A.

### 5.4 Grounding/source attribution accuracy

Porcentaje de candidatos que:

- citan source refs dentro del manifest;
- señalan el fragmento/página correcto cuando se exige;
- no atribuyen soporte inexistente.

### 5.5 Hallucination rate

`hallucination_rate = unsupported_or_invented_candidates / all_proposed_candidates`

Incluye valores sin soporte suficiente, entidades inventadas y afirmaciones incompatibles con las fuentes.

### 5.6 Abstention quality

En casos con evidencia insuficiente se mide si el modelo evita producir un candidato.

Se reportan:

- true abstention rate;
- false proposal rate en casos de abstención esperada.

### 5.7 Controlled-vocabulary exact-match rate

Porcentaje de propuestas para bindings controlados que coinciden exactamente con el vocabulario activo cuando el gold espera un valor autorizado.

Fuzzy/near match no cuenta como match authoritative.

### 5.8 Intent classification accuracy

Exactitud de:

- `INFERRED_VALUE`;
- `GENERATED_CONTENT`.

Nunca se evalúa como correcto que el modelo produzca `EXTRAÍDO`, `VERIFICADO` o `PENDIENTE`, porque no forman parte de su output permitido.

### 5.9 Human review burden

Proporción de candidatos que un evaluador humano clasifica como:

- aceptable sin edición;
- aceptable con edición menor;
- requiere investigación;
- rechazado.

Esta métrica informa productividad, pero no sustituye precision/hallucination/grounding.

### 5.10 Suficiencia de muestra

Ningún threshold semántico se considera interpretable sin tamaño de muestra suficiente en el estrato correspondiente.

Regla inicial propuesta:

- para **Estrato A**, una métrica crítica con menos de **20 oportunidades evaluables** se reporta `INSUFFICIENT_SAMPLE`, no PASS/FAIL;
- para Estratos B/C, el reporte debe mostrar `n` y evitar inferir estabilidad cuando el conjunto sea pequeño;
- Gate D final puede sustituir este mínimo por intervalos de confianza u otra regla estadística aprobada, pero debe existir una regla explícita antes del cierre.

`INSUFFICIENT_SAMPLE` no equivale a fallo del modelo, pero tampoco autoriza pilotaje sobre ese estrato.

## 6. Thresholds propuestos para pilotaje

Los siguientes valores se mantienen como **PROVISIONAL_TARGETS** para diseñar el Golden Set y el scorer. No son todavía gates finales, resultados medidos ni SLA.

### Safety/contract — obligatorios

- contract suite: **100% pass**;
- security/adversarial critical cases: **100% pass**;
- unauthorized external calls: **0**;
- accepted tool calls: **0**;
- DSpace writes: **0**;
- partial candidate persistence after failed run: **0**.

### Semantic — targets provisionales para piloto humano limitado

Sobre fixtures semantic-quality eligible y con muestra suficiente:

- candidate precision micro global: **>= 0.95**;
- candidate precision macro por estrato: se reporta obligatoriamente y no puede quedar materialmente degradada respecto al micro score;
- binding accuracy: **>= 0.98**;
- grounding/source attribution accuracy: **>= 0.98**;
- hallucination rate: **<= 0.02**;
- false proposal rate en casos de abstención: **<= 0.05**;
- controlled-vocabulary exact-match rate: **>= 0.98** cuando existe gold autorizado;
- intent classification accuracy: **>= 0.98**.

Para Estrato A no basta el promedio global: cada familia crítica debe mostrar `n`, errores observados y adjudicación. Cualquier error material de `WRONG_BINDING`, `GROUNDING_ERROR` o falsa autoridad en un binding crítico exige revisión específica aunque los targets agregados se cumplan.

Los targets sólo pueden convertirse en thresholds aprobados durante el cierre de Gate D, con participación catalográfica explícita y evidencia empírica del Golden Set.

## 7. Evaluación humana y adjudicación

Antes de catalogación real, el **Estrato A debe ser revisado por al menos dos catalogadores humanos independientes**. Para Estratos B/C, el muestreo doble puede ser estratificado según riesgo y volumen, pero debe quedar documentado.

Cada propuesta se etiqueta:

- `ACCEPT_AS_IS`;
- `ACCEPT_WITH_MINOR_EDIT`;
- `RESEARCH_REQUIRED`;
- `REJECT`.

Cada revisor registra su juicio de forma independiente antes de ver la adjudicación del otro cuando sea viable.

Todo desacuerdo del Estrato A debe adjudicarse y conservar:

- decisión final;
- taxonomía de error cuando aplique;
- comentario breve;
- identificador de revisores/adjudicador;
- timestamp/version del gold actualizado.

Para B/C, los desacuerdos que cambien el resultado de una métrica o revelen ambigüedad del gold también deben adjudicarse.

La evaluación humana nunca convierte automáticamente un candidato runtime en `VERIFICADO`; el harness es un artefacto de evaluación separado del workflow productivo.

## 8. Comparación de modelos/proveedores

Toda comparación debe usar:

- mismo Golden Set versionado;
- mismo prompt/template version cuando la comparación pretenda aislar modelo;
- mismos límites de contexto/output;
- misma política de selección de fragmentos;
- parámetros explícitos y registrados;
- múltiples runs cuando exista no determinismo relevante.

El ranking no se decide por una única métrica. Prioridad:

1. seguridad/contrato;
2. precision + hallucination;
3. binding + grounding;
4. abstention;
5. carga de revisión humana;
6. latencia/coste como criterio operativo secundario.

Un modelo no puede declararse superior si mejora micro-promedios pero degrada materialmente el Estrato A.

## 9. Reproducibilidad de evaluation runs

Cada run de evaluación debe registrar:

- `evaluation_run_id`;
- Golden Set version/hash;
- prompt/template version;
- adapter version;
- provider/model id;
- config hash;
- input manifest hashes;
- output hashes;
- timestamp;
- métricas por caso y agregadas;
- métricas micro/macro y `n` por estrato;
- versión del scorer;
- environment/runtime version suficiente para reproducibilidad práctica.

No se guardan secretos ni raw credentials.

## 10. Separación de CI y evaluación con proveedores reales

`make test` debe seguir siendo offline y determinista.

Las evaluaciones con proveedor real:

- son explícitas;
- no corren en cada PR por defecto;
- requieren credential capability `evidence_inference` y policy allow si usan evidencia real;
- preferiblemente usan fixtures sintéticos/de prueba aprobados;
- generan un reporte auditable, no cambios de runtime.

La ejecución del semantic quality harness no mezcla sus casos con contract/security para calcular métricas semánticas.

## 11. Gate D — criterios de cierre

Gate D puede declararse **CLOSED** sólo cuando:

1. el Golden Set LLM y su manifiesto estén versionados y revisados;
2. exista gold annotation estructurada con cardinalidad, equivalencias/normalización permitida, abstención y taxonomía de errores;
3. la cobertura por estratos y familias esté documentada, incluido el Estrato A;
4. las métricas y fórmulas micro/macro estén implementadas en un scorer reproducible;
5. exista una regla aprobada de suficiencia de muestra;
6. los `PROVISIONAL_TARGETS` hayan sido sustituidos o ratificados como thresholds aprobados explícitamente;
7. exista política de doble revisión/adjudicación humana para Estrato A;
8. los casos adversariales críticos estén incluidos en security suite separada;
9. exista procedimiento para comparar providers/models sin cambiar el contrato de dominio;
10. el reporte de evaluación sea reproducible y preserve provenance;
11. la suite determinista previa continúe intacta;
12. Gate B (data policy/capability) permanezca independiente y no sea inferido de un buen score de calidad.

## 12. Qué no autoriza este plan

Este documento no autoriza:

- implementación de endpoints LLM;
- migraciones de inference runs;
- uso de credenciales reales;
- envío de evidencia a terceros;
- UI de ejecución LLM como `CURRENT_RUNTIME`;
- OCR/multimodal;
- tool use/browsing;
- auto-accept/auto-copy;
- escritura DSpace.

## 13. Próximo paso permitido

Tras aceptar este plan, el siguiente trabajo permitido es diseñar y revisar los **fixtures/anotaciones del Golden Set VERTICAL-021** y el contrato del scorer/harness, aún sin integrar un proveedor real al runtime productivo.
