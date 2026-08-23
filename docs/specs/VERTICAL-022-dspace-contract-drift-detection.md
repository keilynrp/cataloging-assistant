# VERTICAL-022: DSpace Contract Drift Detection & Synchronization

## Resultado observable

La aplicación puede verificar periódicamente, de forma read-only, si la estructura
catalográfica efectiva de la instancia DSpace cambió desde el último snapshot aprobado.
El sistema conserva snapshots versionados, calcula un hash canónico, produce un diff
semántico y clasifica el drift antes de permitir cualquier promoción del contrato local.

La detección es automática. La adopción de cambios es siempre humana.

## Objetivo

Evitar que `cataloging-assistant` y `dspace-cataloger` operen contra una fotografía
obsoleta del formulario DSpace.

La sincronización debe detectar como mínimo:

- campos de metadatos añadidos;
- campos eliminados;
- cambios en schema / element / qualifier;
- cambios en labels visibles;
- cambios required/repeatable;
- cambios de tipo de control;
- cambios de orden;
- cambios de binding;
- cambios de vocabulario asociado;
- cambios de valores en vocabularios controlados;
- cambios en submission definitions/sections relevantes.

## Principio de arquitectura

```text
DSpace
  -> collect read-only
  -> preserve raw HAL+JSON
  -> normalize
  -> canonical snapshot
  -> SHA-256
  -> compare with ACTIVE snapshot
  -> classify drift
  -> report / alert
  -> human review
  -> explicit promotion
```

Nunca:

```text
DSpace drift -> automatic contract rewrite -> automatic skill release
```

## Superficies DSpace a observar

El collector debe leer únicamente endpoints GET autorizados y compatibles con la
instancia. Como mínimo debe intentar cubrir:

1. metadata schemas;
2. metadata fields;
3. submission definitions;
4. submission sections;
5. vocabularios/configuración controlada disponible por REST o por el mecanismo
   read-only ya adoptado por VERTICAL-013.

La ausencia de una superficie en REST no autoriza scraping frágil ni escritura.
Debe registrarse como `UNOBSERVABLE_SURFACE` con evidencia y timestamp.

## Extensión de `DSpaceClient`

Añadir métodos read-only explícitos; no introducir un método HTTP genérico público.

Ejemplo conceptual:

```python
get_metadata_schemas()
get_metadata_fields()
get_submission_definitions()
get_submission_sections()
```

Deben conservar retries, timeout, validación HAL/JSON y errores tipados del cliente
actual.

## Preservación obligatoria de evidencia DSpace

Cumpliendo `AGENTS.md`, toda observación que participe en la construcción de un
snapshot debe preservar el **HAL+JSON bruto** recibido desde DSpace, además de la forma
normalizada.

Requisitos:

- cada página/respuesta GET usada por el collector se guarda de forma inmutable;
- cada raw payload conserva endpoint, parámetros, timestamp y hash SHA-256;
- el snapshot normalizado conserva referencias a todos sus raw payloads de origen;
- una respuesta posterior no sobrescribe una respuesta anterior;
- si una página de una colección paginada falta, el run queda incompleto y no puede
  producir un snapshot comparable ni inferir eliminaciones;
- la retención del raw HAL+JSON debe permitir reconstruir y auditar el snapshot aunque
  el endpoint DSpace cambie después.

La provenance sin payload bruto **no es suficiente** para declarar un snapshot completo.

## Snapshot canónico

Entidad propuesta: `DSpaceContractSnapshot`.

Campos mínimos:

- `id`;
- `captured_at`;
- `source_base_url`;
- `dspace_version` cuando sea observable;
- `metadata_field_count`;
- `form_binding_count`;
- `canonical_payload` o referencia inmutable al payload normalizado;
- `raw_source_refs[]` obligatorias;
- `content_hash` SHA-256;
- `status`;
- `previous_snapshot_id`;
- `collector_version`;
- `observation_warnings[]`.

Estados:

- `OBSERVED`;
- `NO_CHANGE`;
- `DIFF_DETECTED`;
- `REVIEW_REQUIRED`;
- `APPROVED`;
- `REJECTED`;
- `ACTIVE`;
- `SUPERSEDED`.

Solo un snapshot puede ser `ACTIVE` por contrato/instancia.

## Baseline inicial gobernado

Una instalación nueva no dispone de snapshot `ACTIVE`. El primer slice debe incluir
un camino explícito y auditable para establecer el baseline sin modificar DSpace ni
hacer auto-promoción.

Flujo obligatorio:

```text
first successful complete observation
  -> OBSERVED
  -> BASELINE_REVIEW_REQUIRED
  -> human approval
  -> ACTIVE
```

Reglas:

1. El primer snapshot completo nunca se vuelve `ACTIVE` automáticamente.
2. Debe existir una acción humana autorizada para aprobar el baseline inicial.
3. La aprobación registra `approved_by`, `approved_at`, comentario opcional y hash
   exacto del snapshot aprobado.
4. Si el baseline se rechaza, permanece `REJECTED` y el sistema continúa sin `ACTIVE`.
5. Mientras no exista `ACTIVE`, el estado operativo es `BASELINE_REQUIRED`; no se
   declara `SYNCED` ni `DRIFT_DETECTED`.
6. Una vez activado el baseline, las observaciones siguientes se comparan contra él.
7. La aprobación inicial no cambia `cataloging_contract.py`, no publica una skill y no
   realiza escritura DSpace.

La misma superficie de aprobación puede reutilizarse posteriormente para promover un
snapshot revisado, siempre con autorización y auditoría.

## Canonicalización

Antes de hashear o comparar:

- ordenar objetos por clave estable;
- separar identidad de campo de presentación UI;
- preservar literalmente `dc.subject.linguiscgroup`;
- preservar bindings distintos aunque compartan `metadataField`;
- no inferir jerarquías a partir del orden de vocabularios;
- eliminar del hash solo datos verdaderamente volátiles y no semánticos;
- incluir referencias deterministas a la evidencia raw preservada sin hacer que
  timestamps volátiles alteren el hash semántico.

La canonicalización debe ser determinista: mismo contrato observado -> mismo hash.

## Sincronización incremental y resumable

Cumpliendo `AGENTS.md`, cada colección paginada se recolecta de forma incremental,
idempotente, resumable y auditable.

Entidad/estado conceptual: `DSpaceContractSyncRun`.

Debe conservar como mínimo:

- `run_id`;
- `started_at`, `completed_at`;
- superficie actual (`metadata_fields`, `schemas`, `submission_sections`, etc.);
- página/cursor siguiente por superficie;
- páginas completadas;
- hashes de raw payloads preservados;
- `status`: `RUNNING`, `INTERRUPTED`, `FAILED`, `COMPLETE`;
- error tipado y timestamp del último fallo;
- `collector_version`.

Semántica:

1. Cada página se persiste antes de avanzar el checkpoint.
2. Un retry del mismo page/cursor es idempotente por `run_id + surface + page/cursor`.
3. Si el proceso se interrumpe, una nueva ejecución puede reanudar el run incompleto
   desde el último checkpoint confirmado.
4. No se crea `DSpaceContractSnapshot` comparable hasta que todas las superficies
   requeridas hayan terminado y sus páginas estén completas.
5. Un run incompleto nunca produce `FIELD_REMOVED`, `BINDING_REMOVED` ni
   `VOCABULARY_VALUE_REMOVED`.
6. Reiniciar desde cero sigue siendo posible mediante una opción administrativa
   explícita, pero no es el comportamiento normal de recuperación.
7. Un run `COMPLETE` no se muta; una observación posterior crea un nuevo run.

## Modelo de drift

Entidad propuesta: `DSpaceContractChange`.

Tipos mínimos:

- `FIELD_ADDED`;
- `FIELD_REMOVED`;
- `FIELD_ID_CHANGED`;
- `FIELD_RENAMED`;
- `LABEL_CHANGED`;
- `REQUIRED_CHANGED`;
- `REPEATABLE_CHANGED`;
- `INPUT_TYPE_CHANGED`;
- `ORDER_CHANGED`;
- `BINDING_ADDED`;
- `BINDING_REMOVED`;
- `BINDING_CHANGED`;
- `VOCABULARY_CHANGED`;
- `VOCABULARY_VALUE_ADDED`;
- `VOCABULARY_VALUE_REMOVED`;
- `FORM_STRUCTURE_CHANGED`;
- `UNOBSERVABLE_SURFACE`.

Severidades iniciales:

- `INFO`: adiciones compatibles, cambios de orden no semánticos;
- `LOW`: label-only;
- `MEDIUM`: binding o vocabulario añadido;
- `HIGH`: required/repeatable/input/vocabulary removal;
- `CRITICAL`: field removal, rename incompatible, binding removal o contrato imposible
  de resolver.

La severidad debe ser revisable por gobernanza; no se codifica como verdad eterna.

## Reglas de bloqueo

`NO_CHANGE` no altera el contrato activo.

Drift `INFO/LOW` puede permitir que la catalogación continúe mostrando warning.

Drift `HIGH/CRITICAL` debe marcar el contrato como `REVIEW_REQUIRED` para operaciones
que dependan del campo afectado. No debe causar auto-rewrite del contrato ni publicar
una nueva skill.

Si el collector falla completamente, conservar el último snapshot `ACTIVE` y marcar
estado operativo `STALE_CHECK_FAILED`; no sustituirlo por un snapshot vacío.

Si todavía no existe baseline activo y el collector falla, conservar
`BASELINE_REQUIRED` + estado de fallo; nunca crear un baseline vacío.

## Relación con VERTICAL-018

VERTICAL-018 sigue siendo el contrato maestro runtime.

VERTICAL-022 añade evidencia de procedencia y drift:

- `contract_version` sigue siendo versión gobernada de aplicación;
- `dspace_contract_hash` identifica el snapshot DSpace aprobado;
- `dspace_contract_verified_at` indica última verificación exitosa;
- `dspace_contract_status` expone `BASELINE_REQUIRED`, `SYNCED`, `DRIFT_DETECTED`,
  `REVIEW_REQUIRED` o `STALE_CHECK_FAILED`;
- `field_count == 56` deja de ser una afirmación de eternidad y pasa a ser una
  invariante del snapshot actualmente aprobado, comprobada contra DSpace.

## Provenance en fichas y borradores

Todo borrador/ficha creado bajo un contrato activo debe poder conservar:

- `dspace_contract_snapshot_id`;
- `dspace_contract_hash`;
- `cataloging_contract_version`.

Esto permite reproducir contra qué estructura de DSpace fue tomada una decisión
catalográfica.

## Scheduler

El job no debe vivir como loop permanente dentro del proceso FastAPI.

Ejecución preferida en producción:

```text
external scheduler / Dokploy cron
  -> python -m cataloging_api.dspace.contract_sync
```

Cadencia inicial recomendada: diaria.

Ejemplo:

```cron
0 3 * * *
```

La hora real queda en configuración de despliegue y debe documentar timezone.

El comando debe ser idempotente y seguro para ejecución manual. Si existe un run
`INTERRUPTED` compatible con la versión del collector, debe reanudarlo por defecto.

## API propuesta

Lectura:

- `GET /api/dspace-contract/status`
- `GET /api/dspace-contract/snapshots`
- `GET /api/dspace-contract/snapshots/{id}`
- `GET /api/dspace-contract/changes?status=...`
- `GET /api/dspace-contract/sync-runs/{id}`

Mutación local gobernada, sin escritura DSpace:

- acción/endpoint autorizado para `approve-baseline` / `promote-snapshot`.

La mutación debe requerir autorización humana y registrar auditoría. El primer slice
**sí debe incluir al menos la aprobación del baseline inicial**, porque sin ella una
instalación nueva no puede alcanzar un estado operativo válido.

## Contract Health

La UI debe poder mostrar al menos:

```text
DSpace Contract: BASELINE REQUIRED | SYNCED
Last verified: <timestamp>
Metadata fields: <count>
Form bindings: <count>
Hash: <short hash>
Drift: none
```

Y ante drift:

```text
DSpace Contract: REVIEW REQUIRED
Added: N
Removed: N
Modified: N
Highest severity: HIGH|CRITICAL
```

No exponer credenciales ni payloads raw en superficies públicas.

## Notificaciones

VERTICAL-014 puede reutilizarse para notificar únicamente cuando:

- aparece un drift nuevo;
- aumenta la severidad;
- un check programado falla repetidamente;
- se requiere baseline inicial;
- se aprueba/promueve un nuevo snapshot.

No emitir ruido diario cuando el hash no cambia.

## Invariantes de seguridad y gobernanza

1. DSpace sigue siendo fuente de verdad externa.
2. Collector estrictamente read-only.
3. `dspace_write_enabled == false`.
4. No auto-promoción.
5. No auto-modificación de `cataloging_contract.py`.
6. No auto-release de `dspace-cataloger`.
7. Aprobación humana obligatoria para baseline y adopción de drift.
8. Snapshots append-only; no reescribir historia.
9. Hash canónico reproducible.
10. Los fallos de observación no se interpretan como eliminaciones de campos.
11. `dc.subject.linguiscgroup` permanece literal.
12. Bindings compartidos por metadata field permanecen entidades distintas.
13. Raw DSpace HAL+JSON se preserva junto a la forma normalizada.
14. Toda sincronización es incremental, idempotente, resumable y auditable.

## Primer slice implementable

### Backend

- ampliar `DSpaceClient` con las lecturas necesarias;
- persistencia inmutable de raw HAL+JSON;
- modelo/checkpoint `DSpaceContractSyncRun` resumable;
- normalizador canónico del contrato observado;
- modelos DB `DSpaceContractSnapshot` y `DSpaceContractChange`;
- comando `contract_sync` incremental, idempotente y resumable;
- diff semántico;
- endpoint `GET /api/dspace-contract/status`;
- endpoint para inspección de changes;
- acción gobernada de aprobación del baseline inicial.

### Tests

- same input -> same hash;
- reordenamiento irrelevante -> no drift;
- raw HAL+JSON queda preservado y referenciado;
- baseline inicial requiere aprobación humana;
- sin `ACTIVE` -> `BASELINE_REQUIRED`;
- field added -> `FIELD_ADDED`;
- field removed -> `FIELD_REMOVED/CRITICAL`;
- required changed -> `REQUIRED_CHANGED/HIGH`;
- vocabulary value removed -> `VOCABULARY_VALUE_REMOVED/HIGH`;
- shared metadata field bindings remain distinct;
- failed fetch does not create false removals;
- interrupción después de N páginas -> run `INTERRUPTED` con checkpoint;
- resume continúa desde el checkpoint sin duplicar páginas/raw payloads;
- run incompleto no produce snapshot ni removals;
- second identical complete run is idempotent;
- no DSpace mutation path exists.

### Deploy

- documentar comando manual;
- configurar cron externo diario;
- registrar `last_success_at`, `last_failure_at`, `consecutive_failures`;
- documentar recuperación/reanudación de runs interrumpidos.

## Acceptance criteria

1. Una ejecución completa produce snapshot hashable y auditable con referencias a raw
   HAL+JSON preservado.
2. Dos ejecuciones idénticas no generan cambios duplicados.
3. Una adición/eliminación/modificación simulada se clasifica correctamente.
4. El sistema nunca cambia automáticamente el contrato runtime activo.
5. El último snapshot aprobado permanece utilizable ante una caída de DSpace.
6. Existe evidencia de cuándo se verificó por última vez la estructura.
7. Una instalación nueva puede establecer un baseline `ACTIVE` mediante aprobación
   humana auditada, sin edición directa de base de datos.
8. La app puede indicar `SYNCED` o `DRIFT_DETECTED` solo después de existir baseline.
9. Las fichas/borradores pueden quedar trazadas al hash del contrato DSpace.
10. La implementación conserva VERTICAL-018, VERTICAL-013 y las restricciones
    read-only del agente.
11. El cron es externo al proceso FastAPI y el comando es idempotente.
12. Una sincronización paginada interrumpida es reanudable desde un checkpoint auditado.
13. Un run incompleto no puede producir falsos eventos de eliminación.
14. El raw HAL+JSON permite reconstruir/auditar el snapshot normalizado original.

## Fuera de alcance

- escritura en DSpace;
- auto-migraciones destructivas;
- auto-edición de la skill;
- auto-publicación de releases;
- reconciliación semántica LLM de cambios de schema;
- scraping de UI como fuente primaria;
- sustitución automática de vocabularios aprobados;
- asumir que ausencia temporal de endpoint equivale a eliminación de un campo.
