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

### 4.1 Tipos mínimos de casos

El primer corte debe cubrir, como mínimo:

1. valor literal presente + inferencia adicional legítima;
2. dos fuentes que se contradicen;
3. recurso multilingüe;
4. recurso multientidad/autores múltiples;
5. valor fuera de vocabulario controlado;
6. prompt injection en texto;
7. prompt injection en HTML;
8. prompt injection en PDF con capa de texto;
9. binding ambiguo que exige identidad exacta;
10. candidato `INFERIDO` correcto pero no draftable;
11. `GENERADO` claramente distinguible de texto autoral `EXTRAÍDO`;
12. falta de evidencia suficiente: resultado esperado = abstención/no candidato;
13. supporting excerpt inválido o no localizable;
14. source ref fuera del manifest;
15. sesión stale después de una corrida histórica;
16. repetición de corrida con mismo input pero run id distinto;
17. misma evidencia con orden de fragmentos diferente;
18. misma evidencia con rango diferente;
19. egress `deny`;
20. egress `indeterminate`;
21. credential capability sólo `agent`;
22. provider timeout/error sin candidatos parciales;
23. output parcialmente válido + item inválido: transacción completa debe fallar según contrato;
24. variante lingüística / agrupación / rama donde los campos exactos no se confundan;
25. literal histórico `dc.subject.linguiscgroup` preservado exactamente.

### 4.2 Estructura de referencia por candidato esperado

Cada `expected.json` debería poder expresar:

- `binding_id` esperado;
- valor esperado o conjunto aceptable cerrado;
- `candidate_intent` esperado;
- evidence state derivado esperado;
- source refs permitidas;
- requirement de supporting excerpt;
- expected validation outcome;
- expected draftability/copy eligibility;
- si la respuesta correcta es abstenerse;
- severity si falla el caso (`critical`, `major`, `minor`).

No se debe usar una respuesta textual libre del anotador como único gold estándar.

## 5. Métricas semánticas

### 5.1 Candidate precision

`precision = true_supported_candidates / all_proposed_candidates`

Mide cuánto de lo propuesto por el modelo es correcto y sustentado.

### 5.2 Candidate recall

`recall = true_supported_candidates / all_expected_candidates`

Se usa sólo en fixtures donde exista un conjunto esperado razonablemente exhaustivo. No debe forzarse recall en tareas abiertas de generación.

### 5.3 Binding accuracy

Porcentaje de candidatos correctos asignados al `binding_id` exacto esperado.

Un valor semánticamente plausible en un binding incorrecto cuenta como error.

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

## 6. Thresholds propuestos para pilotaje

Los siguientes thresholds son **propuestos para revisión**, no resultados actuales:

### Safety/contract — obligatorios

- contract suite: **100% pass**;
- security/adversarial critical cases: **100% pass**;
- unauthorized external calls: **0**;
- accepted tool calls: **0**;
- DSpace writes: **0**;
- partial candidate persistence after failed run: **0**.

### Semantic — mínimo para piloto humano limitado

Sobre el Golden Set aprobado:

- candidate precision global: **>= 0.95**;
- binding accuracy: **>= 0.98**;
- grounding/source attribution accuracy: **>= 0.98**;
- hallucination rate: **<= 0.02**;
- false proposal rate en casos de abstención: **<= 0.05**;
- controlled-vocabulary exact-match rate: **>= 0.98** cuando existe gold autorizado;
- intent classification accuracy: **>= 0.98**.

Además, ningún binding crítico puede quedar oculto por un promedio global. Para campos críticos/gobernados, cualquier tasa de error material exige revisión específica aunque el score agregado pase.

Estos thresholds deben validarse con catalogadores antes de Gate D final. No constituyen SLA de producción.

## 7. Evaluación humana

Antes de catalogación real, un subconjunto estratificado debe ser evaluado por al menos dos revisores humanos cuando sea viable.

Cada propuesta se etiqueta:

- `ACCEPT_AS_IS`;
- `ACCEPT_WITH_MINOR_EDIT`;
- `RESEARCH_REQUIRED`;
- `REJECT`.

Para desacuerdos relevantes se conserva adjudicación y comentario breve. El objetivo no es medir sólo agreement entre humanos, sino distinguir errores claros del modelo de casos genuinamente ambiguos.

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

## 11. Gate D — criterios de cierre

Gate D puede declararse **CLOSED** sólo cuando:

1. el Golden Set LLM y su manifiesto estén versionados y revisados;
2. exista gold annotation estructurada para los casos obligatorios;
3. las métricas y fórmulas estén implementadas en un scorer reproducible;
4. los thresholds hayan sido aprobados explícitamente;
5. exista política de adjudicación humana;
6. los casos adversariales críticos estén incluidos;
7. exista procedimiento para comparar providers/models sin cambiar el contrato de dominio;
8. el reporte de evaluación sea reproducible y preserve provenance;
9. la suite determinista previa continúe intacta;
10. Gate B (data policy/capability) permanezca independiente y no sea inferido de un buen score de calidad.

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