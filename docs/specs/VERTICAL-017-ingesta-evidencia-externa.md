# VERTICAL-017: Ingesta controlada de evidencia externa

## Estado

**MVP determinista implementado en rama; pendiente de revisión y merge.**

## Objetivo

Llevar a la aplicación el flujo que hoy ejecuta `dspace-cataloger cataloga:` fuera del runtime: recibir evidencia aportada por el catalogador, conservar su trazabilidad y producir candidatos catalográficos revisables, nunca una escritura DSpace.

## Alcance del MVP

Este primer corte acepta:

- una URL HTTP(S) como locator de evidencia;
- texto UTF-8 aportado explícitamente, hasta 250 000 caracteres;
- asociación opcional a un ítem DSpace sincronizado.

Deliberadamente **no** descarga la URL, no procesa PDF/binarios, no sigue autenticación externa y no usa LLM para generar candidatos. Esas capacidades quedan para una iteración posterior.

## Principios

1. DSpace continúa como fuente de verdad para registros ya sincronizados.
2. Una URL o texto aportado es **fuente de evidencia externa**, no fuente de verdad del repositorio.
3. Cada fuente se captura como snapshot local con SHA-256.
4. Cada candidato conserva fuente, campo, valor, estado y fragmento/locator de evidencia.
5. El MVP sólo crea candidatos `EXTRAÍDO`; no eleva automáticamente valores a `VERIFICADO` ni convierte inferencias en hechos.
6. Los vocabularios activos de la aplicación gobiernan la validación literal cuando un campo tiene vocabulario.
7. Ninguna salida se aplica a DSpace automáticamente.
8. El agente conversacional read-only de ADR-010 no recibe nuevas herramientas de escritura. La ingesta es un flujo separado iniciado por el catalogador.

## Flujo implementado

1. Crear una sesión local de evidencia con URL y/o texto desde la UI Next.js.
2. Si se vincula un ítem, capturar su `source_hash`.
3. Persistir snapshots inmutables de las fuentes.
4. Ejecutar extracción determinista una sola vez por sesión.
5. Conservar candidatos append-only con evidencia y snapshot de validación.
6. Consultar y revisar sesión/candidatos por API y UI.
7. Permitir copiar candidatos seleccionados sólo hacia los campos `runtime_draftable` del contrato maestro.
8. Si el registro DSpace cambia, marcar la sesión como stale y bloquear extracción/copia.

## Extracción determinista

El MVP reconoce:

- URL aportada → `dc.identifier.url`;
- líneas explícitas `metadataField: valor` si `metadataField` pertenece a los 56 bindings del contrato maestro;
- DOI;
- ISSN;
- ISBN.

No intenta inferir título, autores, lengua, agrupación o variante a partir de prosa libre.

## Persistencia

Entidades implementadas:

- `catalog_evidence_sessions`;
- `catalog_evidence_sources`;
- `catalog_evidence_candidates`.

No se añadió `catalog_evidence_candidate_values`: el MVP usa un candidato por campo/valor para mantener una estructura simple y trazable.

## API implementada

- `POST /api/evidence-sessions`
- `GET /api/evidence-sessions/{id}`
- `POST /api/evidence-sessions/{id}/extract`
- `GET /api/evidence-sessions/{id}/candidates`
- `POST /api/evidence-sessions/{id}/copy-to-draft`

Las operaciones mutables exigen `CATALOG_REVIEW_TOKEN`. `copy-to-draft` reutiliza el servicio local de borradores y nunca escribe DSpace.

## UI implementada

- `/evidence`: crea sesiones con catalogador, UUID opcional de ítem, URL y/o texto.
- `/evidence/{sessionId}`: muestra hashes de fuentes, estado stale, candidatos, evidencia localizada, validación y selección copiable.
- La portada enlaza al flujo de evidencia externa.
- El `CATALOG_REVIEW_TOKEN` permanece del lado servidor mediante Server Actions.

## Reconciliación y copy-to-draft

La extracción puede producir evidencia para cualquier `metadataField` conocido por el contrato maestro. Sin embargo, el borrador local actual sólo admite los campos lingüísticos `runtime_draftable`.

Por tanto:

- candidatos bibliográficos como DOI/ISSN/ISBN/URL permanecen como evidencia revisable;
- sólo candidatos lingüísticos explícitos pueden copiarse al borrador actual;
- al copiar, se vuelve a consultar el vocabulario activo vigente; si existe y el candidato no coincide literalmente, la copia queda bloqueada;
- si no existe vocabulario activo, el candidato se conserva como no configurado y requiere revisión humana posterior.

## Seguridad y límites

- No ejecutar código aportado.
- No realizar fetch remoto en este corte; evita SSRF y redirecciones no gobernadas.
- No seguir autenticaciones ni sesiones externas.
- No descargar bitstreams DSpace automáticamente.
- No afirmar equivalencia entre términos fuente y autoridad si no existe correspondencia aprobada.
- Repetir `/extract` no sustituye candidatos: devuelve el snapshot existente.
- Los estados de evidencia canónicos son `EXTRAÍDO`, `VERIFICADO`, `INFERIDO`, `PENDIENTE` y `GENERADO`; estados QA como `APP_SCHEMA_GAP` no son estados de evidencia.

## Puertas resueltas

- **P0:** política inicial = URL locator + texto, sin fetch/binarios; límite 250 000 caracteres.
- **P1:** extracción inicial determinista.
- **P2:** contrato por candidato con campo, valor, estado, source_id y evidencia localizada.
- **P3:** 56 bindings para extracción; `runtime_draftable` para copia.
- **P4:** se añaden fixtures unitarios e integración para el extractor determinista; el Golden Set completo queda para PDF/LLM.

## Criterios de aceptación del MVP

- una sesión conserva hashes y versión del contrato;
- una sesión asociada a ítem se vuelve stale si cambia `source_hash`;
- URL no provoca fetch remoto;
- texto fuera del límite es rechazado;
- sólo claves del contrato maestro se extraen desde líneas explícitas;
- DOI/ISSN/ISBN conservan contexto de evidencia;
- una segunda extracción no reemplaza el snapshot de candidatos;
- copy-to-draft rechaza campos no `runtime_draftable` y revalida contra el vocabulario activo actual;
- el flujo UI no expone `CATALOG_REVIEW_TOKEN` al navegador;
- ninguna operación escribe DSpace.

## Siguiente iteración

1. Incorporar el Golden Set compartido con `dspace-cataloger` como aceptación end-to-end.
2. Upload controlado de PDF con límites MIME/tamaño y extracción de texto en sandbox.
3. Fetch HTTP seguro con allow/deny de red, timeout, tamaño y redirecciones.
4. Capa LLM provider-independent para candidatos no deterministas, siempre marcada `INFERIDO` o `GENERADO` hasta verificación.
5. Extender el contrato de borrador más allá de los campos lingüísticos mediante una vertical/ADR independiente, sin escritura DSpace.
