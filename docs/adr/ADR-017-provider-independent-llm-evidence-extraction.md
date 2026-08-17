# ADR-017: Provider-independent LLM-assisted evidence extraction

**Estado:** PROPOSED — decisión arquitectónica; no autoriza implementación productiva.

## Contexto

VERTICAL-017, VERTICAL-019 y VERTICAL-020 establecieron un pipeline de evidencia externo controlado, determinista y auditable: sesiones vinculadas a DSpace, snapshots inmutables, texto pegado, PDF local sin OCR, fetch remoto backend-only con controles SSRF, extracción determinista, validación contractual y copia explícita a borrador local. DSpace permanece estrictamente read-only y el agente conversacional mantiene herramientas read-only.

VERTICAL-021, ya incorporado como especificación arquitectónica, propone añadir una capacidad opcional de extracción/sugerencia asistida por LLM sobre evidencia ya congelada. Esta ADR fija las decisiones de arquitectura necesarias para que esa capacidad no debilite las garantías actuales de autoridad, provenance, seguridad, reproducibilidad, human-in-the-loop y rollback.

ADR-010 y ADR-011 ya gobiernan la arquitectura del agente generativo, la abstracción provider-agnostic y el almacenamiento cifrado de credenciales de proveedores. ADR-017 no crea un segundo sistema de secretos: define cómo la capacidad de **evidence inference** reutiliza esa infraestructura sin heredar automáticamente permisos, tool-calling ni autorización de data egress del agente conversacional.

La decisión parte de una premisa: **el modelo no es una fuente de verdad ni una autoridad catalográfica; es un generador de candidatos revisables**.

## Decisión

Adoptar una arquitectura de inferencia LLM **provider-independent, opt-in, append-only, provenance-first y fail-closed**, separada del extractor determinista y del agente conversacional.

El flujo gobernado será conceptualmente:

`SOURCE SNAPSHOT -> DETERMINISTIC EXTRACTION -> OPTIONAL LLM RUN -> CANDIDATES -> BACKEND VALIDATION -> HUMAN REVIEW -> LOCAL DRAFT`

La capacidad queda deshabilitada por defecto y no podrá exponerse como `CURRENT_RUNTIME` hasta cerrar los gates definidos en VERTICAL-021.

## 1. Provider boundary

El dominio de catalogación no dependerá de SDKs ni tipos propietarios de OpenAI, Anthropic u otro proveedor.

Se definirá una interfaz interna provider-neutral equivalente a:

```text
LLMProviderAdapter.generate(request) -> ProviderResponse
```

El adapter concreto será infraestructura sustituible. El dominio seguirá siendo responsable de:

- selección de bindings permitidos;
- resolución canónica `binding_id -> metadata_field`;
- validación de vocabularios;
- draftability/copy eligibility;
- staleness;
- clasificación final de evidence state;
- persistencia y auditoría.

El proveedor no tendrá autoridad para redefinir ninguna de estas decisiones.

### 1.1 Reconciliación con ADR-010 / ADR-011

ADR-011 conserva autoridad sobre almacenamiento, cifrado, rotación y selección operativa de credenciales de proveedores. ADR-017 **reutiliza** esa infraestructura de credenciales, pero introduce una frontera de capacidad adicional.

Una credencial/proveedor configurado debe poder expresar, de forma explícita y server-side, para qué capacidades está autorizado. Conceptualmente:

```text
provider credential
  ├── capability: agent
  └── capability: evidence_inference
```

La representación exacta puede resolverse mediante columnas, tabla de capabilities, policy binding o configuración equivalente, pero debe cumplir estas reglas:

1. Una credencial activa para `agent` **no autoriza automáticamente** `evidence_inference`.
2. `evidence_inference` requiere autorización explícita de capability para esa credencial/proveedor/deployment.
3. La capability es evaluada server-side; el navegador no puede añadirla ni ampliarla.
4. La política de data egress sigue siendo un gate independiente: una credencial autorizada no implica que una evidencia concreta pueda salir del sistema.
5. Si la credencial está activa pero no autorizada para `evidence_inference`, la corrida falla cerrada antes de cualquier llamada externa.
6. La selección/rotación de credenciales continúa bajo ADR-011; ADR-017 no duplica almacenamiento de API keys ni introduce secretos en provenance.

La condición mínima para una llamada externa de evidencia es, conceptualmente:

```text
EVIDENCE_LLM_EXTRACTION_ENABLED = true
AND provider credential has evidence_inference capability
AND data-egress policy = allow
AND explicit authenticated human action
=> provider call may proceed
```

Cualquier `false`, `deny`, `indeterminate` o ausencia de capability produce **cero tráfico de red**.

### 1.2 Separación entre adapters de agente y evidencia

La infraestructura de transporte/proveedor puede compartir componentes bajos de ADR-011 (resolución de credencial, cliente autenticado, normalización de errores), pero el contrato de ejecución de Evidence Workspace debe permanecer separado del contrato conversacional del agente.

En particular:

- `LLMProviderAdapter` de evidencia no expone herramientas;
- no recibe tool definitions;
- no acepta tool calls como output válido;
- no comparte el inventario de herramientas de `agent/providers/`;
- no hereda browsing, retrieval, function calling ni capacidades mutables;
- sólo ejecuta structured extraction bajo schema cerrado.

Si se reutiliza código bajo `agent/providers/`, deberá extraerse o encapsularse una capa común de transporte que no implique semántica conversacional. La dependencia permitida es **infraestructura compartida**, no **capacidad compartida**.

## 2. Feature flag y activación explícita

La capacidad deberá estar controlada por:

`EVIDENCE_LLM_EXTRACTION_ENABLED=false`

por defecto.

Con el flag deshabilitado:

- no se inicializa cliente externo para evidencia;
- no se produce tráfico de red;
- no se crean inference runs;
- la UI no presenta la capacidad como operativa.

Una inferencia sólo podrá iniciarse mediante acción humana explícita y autenticada del Evidence Workspace. No se ejecutará automáticamente al abrir una sesión, añadir evidencia, extraer deterministicamente ni copiar al borrador.

## 3. Inference runs inmutables

Cada ejecución crea un `inference_run` nuevo, append-only e inmutable. Repetir modelo, prompt, fuentes o parámetros no sobrescribe corridas anteriores.

Cada corrida registrará, como mínimo:

- `inference_run_id`;
- `session_id`;
- adapter id/version;
- provider normalizado;
- model id reportado;
- credential/deployment reference no secreta;
- capability evaluada;
- prompt/template version;
- contract version;
- input manifest exacto y ordenado;
- egress policy version/decision no sensible;
- request/config hash;
- response/output hash;
- timestamps;
- status de corrida;
- error code sanitizado;
- usage metadata provider-neutral cuando exista.

No se persistirán secretos ni credenciales del proveedor.

## 4. Exact input manifest y reproducibilidad

La inferencia no se audita sólo con `source_id` o un hash global. Cada corrida congelará un **input manifest canónico y ordenado** con los fragmentos exactos enviados al adapter.

Cada entrada debe registrar, según corresponda:

- `source_id`;
- tipo/media type;
- hash del snapshot;
- `derived_text_sha256`;
- página y offsets PDF;
- rango de caracteres o fragmento lógico;
- posición ordinal en el payload;
- hash del fragmento exacto;
- longitud;
- extractor id/version.

El orden es parte del contrato. Cambiar fuente, rango, fragmento, orden, prompt, contrato, adapter o configuración genera un request hash distinto y una nueva corrida.

El payload no se reconstruirá retrospectivamente desde el estado actual de la UI.

## 5. Candidate intent y evidence state

El modelo **no elegirá directamente** los estados canónicos de evidencia.

El structured output sólo podrá expresar una intención cerrada:

- `INFERRED_VALUE`
- `GENERATED_CONTENT`

El backend deriva:

- `INFERRED_VALUE -> INFERIDO`
- `GENERATED_CONTENT -> GENERADO`

Por esta vertical, un candidato LLM nunca nace:

- `EXTRAÍDO`;
- `VERIFICADO`;
- `PENDIENTE`.

`EXTRAÍDO` queda reservado al pipeline gobernado de extracción directa; `VERIFICADO` requiere autoridad humana o un contrato posterior explícito; `PENDIENTE` no es una salida seleccionable por el proveedor.

## 6. Structured output y autoridad del backend

La respuesta del proveedor deberá ajustarse a un schema cerrado. Como mínimo, cada candidato incluirá:

- `binding_id`;
- valor;
- `candidate_intent`;
- source refs dentro del input manifest;
- excerpt/rationale cuando aplique.

El backend rechazará candidatos que:

- usen bindings inexistentes o fuera de allowlist;
- emitan intents fuera de enum;
- referencien fuentes fuera de la sesión/manifiesto;
- excedan límites;
- no sean parseables;
- incumplan restricciones estructurales;
- presenten grounding inconsistente cuando el contrato exija excerpt verificable;
- incluyan tool calls, tool requests o estructuras conversacionales no permitidas.

`metadata_field`, labels, evidence state, validation y draftability se derivan server-side.

## 7. Vocabularios y validación

Los vocabularios controlados siguen siendo autoridad del backend.

Un proveedor puede sugerir un valor, pero:

- exact-match se ejecuta contra el vocabulario activo;
- fuzzy matching nunca se convierte silenciosamente en autoridad;
- un no-match queda en review-required o inválido según contrato;
- la validación se repite antes de copy-to-draft.

El proveedor nunca constituye autoridad de vocabulario.

## 8. Data egress fail-closed

Antes de habilitar cualquier adapter real deberá existir una **política de data egress versionada, aprobada y evaluable por runtime**.

La política deberá cubrir, como mínimo:

- categorías de evidencia permitidas y prohibidas;
- proveedores/deployments autorizados;
- capability `evidence_inference` requerida;
- propósito permitido;
- retención;
- uso/no uso para entrenamiento o mejora del proveedor;
- residencia/región;
- logging, telemetry y redaction;
- campos que deben eliminarse antes del envío;
- límites por fragmento/corrida;
- tratamiento de datos personales, sensibles o restringidos;
- opciones on-prem/private endpoint cuando existan;
- versión de política y decisión aplicada.

La evaluación ocurre server-side **antes** de construir/enviar la petición externa.

Resultado:

- `allow` -> puede continuar sólo si feature flag, credential capability y acción humana también son válidos;
- `deny` -> se bloquea;
- `indeterminate` -> se bloquea.

`deny`, `indeterminate`, capability ausente o credencial no autorizada deben producir **cero tráfico de red**. La UI no puede sobrepasar esta política y el adapter no decide qué datos son elegibles.

## 9. Prompt injection y aislamiento

Todo contenido de evidencia se tratará como datos hostiles.

Mitigaciones mínimas:

- separación rígida entre instrucciones del sistema y payload de evidencia;
- schema cerrado de salida;
- allowlist de bindings;
- sin tool-use durante inferencia;
- sin browsing, crawling ni fetch;
- sin ejecución de código;
- sin lectura de secretos;
- límites de contexto/output;
- errores sanitizados;
- fixtures específicos de prompt injection.

Un documento que contenga instrucciones no puede modificar permisos, bindings, herramientas, capability de credencial ni políticas de egress.

## 10. Persistencia atómica

Los candidatos de una corrida se persisten de forma transaccional sólo después de superar schema, allowlist, source-reference checks y validación estructural.

Un fallo de proveedor, timeout, parseo, schema o validación:

- puede dejar un registro de corrida fallida/rechazada sanitizado para auditoría;
- **no deja candidatos parcialmente persistidos**.

## 11. Staleness

Una Evidence Session stale no puede iniciar una nueva corrida LLM.

Si una sesión se vuelve stale después de una corrida:

- la corrida, manifiesto y candidatos permanecen visibles como historia;
- no se regeneran automáticamente;
- nuevas corridas quedan bloqueadas;
- copy-to-draft permanece sujeto al gate stale existente.

La staleness sigue siendo propiedad de la sesión respecto al `source_hash` DSpace, no de URLs o proveedores LLM.

## 12. DSpace boundary

VERTICAL-021 no introduce escritura DSpace.

El modelo:

- no lee DSpace directamente;
- no escribe DSpace;
- no puede afirmar que publicó, actualizó o sincronizó DSpace.

Sólo consume texto derivado de snapshots ya gobernados por la Evidence Session.

## 13. Agent boundary

El agente conversacional no recibe herramientas para:

- iniciar inference runs;
- añadir fuentes;
- subir PDFs;
- hacer fetch remoto;
- aceptar/rechazar candidatos;
- copiar al borrador;
- modificar vocabularios;
- escribir DSpace.

La inferencia LLM pertenece al workflow humano del Evidence Workspace. La implementación deberá incluir un test de inventario/capabilities que falle si accidentalmente se añaden herramientas mutables al agente.

Además, una capability `agent` y una capability `evidence_inference` son independientes. Activar/configurar una no habilita la otra.

## 14. OCR, browsing y tool use

Esta ADR no autoriza:

- OCR;
- visión/multimodal;
- crawling;
- browsing;
- búsqueda web;
- tool use por parte del modelo;
- RAG externo;
- fine-tuning;
- model routing autónomo.

PDF/HTML/texto remoto sólo llegan al modelo después de haber sido procesados por los pipelines ya gobernados.

## 15. UX boundary

La capacidad futura deberá respetar `UX-DECISION-001` y la arquitectura de tres paneles.

Mientras Gate A permanezca abierto, cualquier affordance LLM se clasifica como `FUTURE_CONTRACT`.

Para aparecer como `CURRENT_RUNTIME` será obligatorio completar:

1. `UX-PROMPT-002` ejecutado;
2. `UX-ALIGNMENT-001` completado contra artefacto real;
3. resultado `ACCEPTED_FOR_FREEZE`;
4. UX Contract Freeze registrado.

## 16. Testing y evaluación

La suite funcional principal debe usar un fake adapter determinista y no depender de Internet ni credenciales reales.

Debe cubrir, al menos:

- feature flag OFF sin red;
- credencial activa sólo para `agent` no autoriza evidencia y produce cero red;
- credencial sin `evidence_inference` produce cero red;
- `evidence_inference` autorizada pero egress deny/indeterminate produce cero red;
- acción humana ausente/inválida produce cero red;
- adapter de evidencia no expone ni acepta tool-calling;
- input manifest exacto y ordenado;
- request hash sensible a rangos/orden/config;
- derivación `INFERRED_VALUE -> INFERIDO`;
- derivación `GENERATED_CONTENT -> GENERADO`;
- rechazo de bindings/intents/source refs inválidos;
- validación exact-match de vocabularios;
- prompt-injection fixtures;
- atomicidad sin candidatos parciales;
- stale session gate;
- DSpace read-only;
- agent tool inventory read-only.

La evaluación semántica del modelo se mantiene en un harness separado de tests funcionales y de seguridad, con métricas como precision, recall, hallucination rate, binding accuracy, grounding y tasa de revisión humana.

## 17. Rollback

El diseño debe permitir rollback limpio:

- feature flag OFF deja la capacidad completamente inerte;
- adapters permanecen aislados del dominio;
- capacidades de credencial pueden revocarse sin borrar secretos ni corridas históricas;
- extracción determinista sigue operativa;
- corridas históricas pueden quedar legibles/inertes sin romper sesiones;
- no hay datos DSpace que revertir.

## Alternativas consideradas

### A. Integrar directamente un SDK de proveedor en el dominio

Rechazada. Acopla semántica y persistencia a un proveedor específico y dificulta pruebas, migración y rollback.

### B. Permitir que el modelo devuelva `metadata_field` y evidence state finales

Rechazada. Cede autoridad catalográfica al proveedor y rompe el contrato runtime.

### C. Ejecutar LLM automáticamente después de ingestión/extracción

Rechazada. Introduce coste, egress y cambios de estado implícitos incompatibles con el modelo human-in-the-loop.

### D. Permitir egress salvo lista de bloqueo

Rechazada. La política debe ser allow/deny explícita y fail-closed, especialmente para contenido sensible/restringido.

### E. Reemplazar el extractor determinista por LLM

Rechazada. El determinismo actual sigue siendo baseline auditable y debe poder funcionar sin proveedor externo.

### F. Considerar una credencial activa del agente como autorización implícita para evidencia

Rechazada. Mezcla dos superficies de riesgo diferentes. La conversación del agente puede usar el proveedor sin que ello autorice a enviar snapshots de evidencia catalográfica. `agent` y `evidence_inference` deben ser capabilities explícitas e independientes.

### G. Reutilizar directamente el adapter conversacional del agente con tool-calling desactivado por prompt

Rechazada. Un prompt no es una frontera de seguridad suficiente. Evidence Workspace requiere un contrato de adapter distinto, sin tools en su interfaz ni aceptación de tool-call outputs.

## Consecuencias

### Positivas

- mantiene provider portability;
- reutiliza la infraestructura de credenciales de ADR-011 sin duplicar secretos;
- separa autorización de proveedor de autorización de data egress;
- protege la autoridad del contrato catalográfico;
- mejora auditabilidad y reproducibilidad;
- reduce riesgo de prompt injection y data leakage;
- impide que Evidence Workspace herede tool-calling del agente;
- permite rollback limpio;
- mantiene separación entre agente, evidencia y DSpace;
- permite comparar determinismo vs inferencia sin sustituir el baseline.

### Costes

- requiere modelar/enforcear capabilities de credencial;
- aumenta persistencia/provenance requerida;
- exige política institucional de data egress;
- obliga a diseñar manifests y hashes reproducibles;
- requiere harness separado de evaluación de calidad;
- añade controles de seguridad y atomicidad antes de cualquier valor UX visible.

## Gates antes de implementación

La implementación productiva no debe comenzar hasta cerrar explícitamente:

- **Gate A — UX:** `UX-PROMPT-002` + `UX-ALIGNMENT-001` + `ACCEPTED_FOR_FREEZE` + UX Contract Freeze.
- **Gate B — Data policy:** política de egress aprobada/versionada y modelo de capability `evidence_inference` definido y enforceable sobre la infraestructura de credenciales de ADR-011.
- **Gate C — Arquitectura:** esta ADR aceptada.
- **Gate D — Evaluation:** fixtures/métricas aprobados para calidad semántica.

## Resultado

ADR-017 fija el límite arquitectónico para cualquier implementación futura de VERTICAL-021. Reutiliza la infraestructura de proveedores/credenciales de ADR-011, pero no hereda autorización de agente, tool-calling ni permiso de egress. No habilita proveedor, endpoint, migración, UI, OCR, tool use, escritura DSpace ni nuevas capacidades mutables del agente.
