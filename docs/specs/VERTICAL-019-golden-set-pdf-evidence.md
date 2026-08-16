# VERTICAL-019: Golden Set end-to-end + ingestión PDF controlada

## Estado

**Implementado / merged en main** (PR #4). Ver "Siguiente iteración" al
final de este documento.

## Objetivo

Extender la ingesta de evidencia externa (VERTICAL-017) con una segunda
fuente determinista — PDF con texto extraíble, subido explícitamente por el
catalogador — y validar todo el pipeline de evidencia (URL, texto, PDF)
contra un Golden Set de aceptación end-to-end.

## Scope

- Subida explícita de un único PDF por request a una sesión de evidencia
  existente (`POST /api/evidence-sessions/{session_id}/sources/pdf`).
- Validación de MIME, extensión, tamaño (≤ 25 MB), magic bytes (`%PDF-`) y
  número de páginas (≤ 300) antes de aceptar el archivo.
- Extracción determinista de texto vía `pypdf` (sin OCR), reutilizando
  exactamente las reglas de extracción de VERTICAL-017 (líneas explícitas del
  contrato, DOI, ISSN, ISBN) sobre el texto derivado.
- Persistencia de metadata segura: SHA-256 del binario, SHA-256 del texto
  extraído, número de páginas, estado de extracción — nunca la ruta interna
  del archivo en disco.
- Trazabilidad enriquecida para candidatos derivados de PDF: página (cuando
  es determinable de forma fiable), offsets de caracteres, extractor, hash
  del texto extraído.
- Orden estable (`position`) para fuentes y candidatos, incluyendo PDF
  intercalado con URL/texto en la misma sesión, y PDF como primera y única
  fuente (`position=0`) de una sesión creada sin URL ni texto.
- Timeout de extracción realmente aplicado (`asyncio.wait_for` sobre
  `asyncio.to_thread`), no sólo configurado; falla cerrada con `422`.
- Limpieza del archivo PDF en disco si la persistencia posterior a la
  escritura falla por cualquier motivo (incluida una colisión de
  `position` bajo concurrencia).
- Asignación de `position` serializada por sesión mediante un lock de fila,
  para que dos subidas concurrentes a la misma sesión no compitan por el
  mismo valor.
- Golden Set de aceptación end-to-end (`tests/golden/evidence/`) ejecutable
  con `pytest tests/golden -q` e incluido en `make test`.
- Actualización de UI (`/evidence/{sessionId}`) para subir un PDF y ver su
  estado de extracción.

## Out of scope

- OCR o reconocimiento de imágenes escaneadas.
- Fetch remoto de URLs (sigue fuera de alcance; ver VERTICAL-017).
- Cualquier escritura, sincronización o autenticación contra DSpace.
- Asistencia LLM/generativa para producir o corregir candidatos.
- Extracción de archivos embebidos, ejecución de JavaScript, acciones de
  lanzamiento (`/Launch`) o seguimiento de enlaces internos/externos del PDF.
- Ampliar el contrato de borradores (`copy-to-draft`) más allá de los campos
  `runtime_draftable` ya definidos por el contrato maestro.
- Autenticación nueva: sigue usándose únicamente `CATALOG_REVIEW_TOKEN`.
- Cola de trabajo asíncrona para extracción (la extracción PDF es síncrona
  dentro del propio request, dentro del límite de 300 páginas).
- OCR de PDFs "sin texto útil": esos quedan marcados `no_extractable_text`
  para revisión humana posterior, no se reintenta automáticamente.

## Threat model básico

| Vector | Mitigación |
|---|---|
| Contenido ejecutable dentro del PDF (JS, `/OpenAction`, `/Launch`) | Nunca se invoca un motor JS ni se procesan esos objetos; `pypdf` sólo lee estructura y extrae texto de páginas. |
| Archivos embebidos dentro del PDF | Nunca se llama a la API de adjuntos de `pypdf`; no se extraen. |
| Enlaces internos/externos del PDF | No se procesan anotaciones ni acciones URI; no hay fetch de red en ningún punto de esta vertical. |
| Path traversal vía nombre de archivo | El nombre subido se sanea (`os.path.basename`, sin nulos, longitud acotada) y sólo se usa para mostrar/auditar; la ruta real en disco se deriva exclusivamente de un UUID generado por el servidor. |
| Content-Type falsificado | Se exige `application/pdf` y extensión `.pdf`, pero además se verifican los magic bytes (`%PDF-`) antes de aceptar el archivo como PDF real; un archivo que finja ser PDF sin serlo se rechaza con `422`. |
| PDF corrupto/cifrado/con demasiadas páginas | Se rechaza con `422` **antes** de escribir a disco o persistir en base de datos; no queda estado parcial. |
| Denegación de servicio por archivo muy grande | Límite de 25 MB aplicado en lógica de aplicación (`413`); ver ADR-015 sobre la limitación conocida de buffering de Starlette para este MVP de operador único de confianza. |
| Denegación de servicio por PDF patológicamente lento de parsear | Timeout aplicado (`EVIDENCE_PDF_EXTRACTION_TIMEOUT_SECONDS`, default 20s) vía `asyncio.wait_for` sobre `asyncio.to_thread`; falla cerrada con `422` sin tocar disco ni base de datos. El hilo de extracción puede seguir corriendo hasta terminar por su cuenta (limitación conocida, ver ADR-015), pero la petición ya no espera. |
| Archivo huérfano en disco tras un fallo de persistencia (incluida una colisión de `position` bajo concurrencia) | `add_pdf_evidence_source` limpia (`Path.unlink`) el archivo recién escrito si `session.flush()` falla por cualquier motivo, antes de relanzar el error. |
| Fuga de rutas internas del filesystem | La API y la UI nunca serializan una ruta de disco; sólo `source_id`, hash, nombre saneado, página y estado. |
| Escritura accidental a DSpace | Ningún código de esta vertical llama a la capa de sincronización/escritura DSpace; sigue sin existir tal capa en el runtime. |
| Token de revisión expuesto al navegador | El upload se realiza desde una Server Action de Next.js; el token permanece server-side, igual que el resto de mutaciones de evidencia. |

## Acceptance criteria

1. Un PDF válido con texto se sube, se persiste con `extraction_status =
   "extracted"`, `page_count` correcto y `extracted_text_hash` no nulo.
2. Un PDF válido sin capa de texto (por ejemplo, escaneado) se persiste con
   `extraction_status = "no_extractable_text"` y **no** genera candidatos al
   ejecutar `/extract`.
3. Un archivo que no supere el límite de tamaño pero no tenga los magic
   bytes `%PDF-` es rechazado con `422` y no deja ningún registro persistido
   ni archivo en disco.
4. Un archivo mayor a 25 MB es rechazado con `413`.
5. Un archivo con `Content-Type` o extensión distintos de PDF es rechazado
   con `415`, sin siquiera intentar parsear el contenido.
6. Un nombre de archivo como `../../evil.pdf` nunca resulta en escritura
   fuera del directorio de almacenamiento configurado; el nombre saneado se
   usa sólo para mostrar.
7. `binding_id` sigue siendo obligatorio para `dc.subject` y
   `dc.format.medium`; un candidato derivado de PDF con esas claves
   ambiguas por `metadataField` no se genera sin `binding_id` explícito.
8. `position` es estable y consecutivo por sesión entre fuentes URL, texto y
   PDF combinadas, y entre candidatos, incluso tras reconsultar la sesión.
9. Una sesión `stale` bloquea tanto la subida de un nuevo PDF como
   `/extract` y `copy-to-draft`, igual que en VERTICAL-017.
10. `copy-to-draft` revalida contra el vocabulario activo vigente igual que
    para candidatos de URL/texto; ningún candidato de PDF recibe trato
    especial ahí.
11. `pytest tests/golden -q` pasa con los 14 casos mínimos del Golden Set.
12. Ninguna prueba de esta vertical realiza una llamada HTTP saliente ni
    escribe en DSpace.
13. Una sesión puede crearse sin URL ni texto; `POST /extract` sobre ella
    devuelve una lista vacía de candidatos sin inventar nada. Un PDF subido
    después queda como única fuente en `position=0`.
14. Una extracción que excede el timeout configurado falla con `422`
    (código estable `pdf_extraction_timeout`) sin escribir el archivo a
    disco ni persistir ninguna fuente.
15. Si la persistencia de una fuente PDF falla después de escribir el
    archivo a disco, no queda archivo huérfano en
    `EVIDENCE_PDF_STORAGE_DIR` ni fila persistida.
16. Dos subidas de PDF concurrentes a la misma sesión obtienen posiciones
    distintas y consecutivas, sin violar `UNIQUE(session_id, position)`.

## Rollback

- La migración `0019` es aditiva (cuatro columnas nuevas, todas con
  `server_default`/nulables); `alembic downgrade -1` las elimina sin pérdida
  de datos en `catalog_evidence_sessions`/`catalog_evidence_candidates`, y
  sin afectar fuentes `kind="url"`/`"text"` ya existentes.
- El endpoint nuevo (`POST .../sources/pdf`) es aislado: revertir el commit
  que lo introduce no afecta ningún endpoint existente de VERTICAL-017.
- Los archivos PDF ya escritos en `EVIDENCE_PDF_STORAGE_DIR` quedan
  huérfanos tras un rollback de código (no se borran automáticamente); es un
  directorio local de datos, no una migración, y su limpieza es manual si se
  revierte la funcionalidad.
- El Golden Set (`tests/golden/`) no toca runtime; eliminarlo no requiere
  ninguna migración ni cambio de código de producción.

## No DSpace write

Ninguna función de esta vertical llama a la capa DSpace. DSpace continúa
siendo exclusivamente fuente de lectura para `source_hash`/staleness
(idéntico a VERTICAL-017).

## No LLM

La extracción de candidatos desde texto de PDF reutiliza únicamente las
reglas deterministas ya existentes (líneas explícitas, DOI, ISSN, ISBN). No
se invoca ningún proveedor de modelos de lenguaje en esta vertical.

## No remote fetch

La ingesta de PDF es enteramente local: recibe bytes ya subidos por el
catalogador vía `multipart/form-data`. Ningún código de esta vertical abre
una conexión de red saliente.

## Relación con VERTICAL-017

Este documento no reescribe VERTICAL-017; lo continúa. VERTICAL-017 queda
marcado como implementado/fusionado en `main`, con su "Siguiente iteración"
apuntando aquí y a ADR-015.

## Siguiente iteración

Ver **VERTICAL-020** (`docs/specs/VERTICAL-020-secure-remote-evidence-fetch.md`)
y **ADR-016** (`docs/adr/ADR-016-secure-remote-evidence-fetch.md`): fetch
HTTP(S) seguro de una URL de evidencia, con SSRF como amenaza central de
diseño (allowlist de IP pública, validación de redirecciones salto a salto,
límites de tamaño en streaming), cerrando el punto 3 pendiente de la
"Siguiente iteración" de VERTICAL-017. No reescribe nada de este documento;
sólo añade un cuarto tipo de fuente (`kind="remote"`) junto a `url`/`text`/`pdf`.
