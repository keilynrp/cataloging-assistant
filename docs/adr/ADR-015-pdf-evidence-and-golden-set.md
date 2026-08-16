# ADR-015: Ingesta de PDF como evidencia y Golden Set

**Estado:** Propuesta implementada en la rama `feat/golden-set-pdf-evidence`.

## Contexto

VERTICAL-017 (ADR-014) dejó explícitamente fuera de alcance la subida de PDF y
la importación del Golden Set del skill `dspace-cataloger`, para no introducir
una superficie de seguridad excesiva en el primer corte. Con el MVP de
evidencia ya fusionado en `main`, esta ADR abre esa siguiente iteración de
forma acotada.

## Decisiones

1. **El PDF es una fuente de evidencia externa local**, del mismo tipo que URL
   o texto: nunca se trata como fuente de verdad ni se escribe a DSpace.
2. **El binario original conserva su SHA-256** (`content_hash`), calculado
   sobre los bytes recibidos antes de cualquier parseo.
3. **El texto extraído conserva su propio SHA-256** (`extracted_text_hash`),
   distinto del hash del binario, para poder auditar el texto derivado de
   forma independiente del archivo original.
4. **Nunca se ejecuta contenido del PDF.** El pipeline sólo usa `pypdf` para
   leer estructura y flujos de texto (`page.extract_text()`). No se invoca
   ningún visor/renderizador, no se procesan `/OpenAction`, `/Launch`,
   JavaScript embebido, anotaciones con acciones URI, ni se extraen adjuntos
   embebidos (`reader.attachments` nunca se llama). No seguir estos objetos es
   suficiente para que permanezcan inertes: `pypdf` no los ejecuta por sí solo.
5. **Sin OCR en este corte.** Un PDF sin capa de texto extraíble no genera
   candidatos; ver decisión 7.
6. **Sólo PDFs con texto extraíble producen candidatos.**
7. **PDF escaneado/sin texto útil → `extraction_status = "no_extractable_text"`
   y no se generan candidatos.** Esto es un estado de ingestión exitosa (la
   fuente se persiste, queda trazable), no un error HTTP: el catalogador
   puede ver que se intentó y por qué no hay candidatos. La redacción original
   de VERTICAL-017 ("`unsupported`/`requires_ocr`") se resuelve como
   `no_extractable_text` en el enum real, para no crear dos nombres para el
   mismo estado; esta ADR es la referencia canónica de esa equivalencia.
8. **No se hace fetch de URL** en este corte (sigue fuera de alcance, igual
   que VERTICAL-017).
9. **No se toca DSpace.** Ninguna operación de esta vertical escribe,
   sincroniza ni autentica contra DSpace.
10. **No se usa LLM.** La extracción de candidatos desde el texto del PDF
    reutiliza exactamente las mismas reglas deterministas de VERTICAL-017
    (líneas explícitas del contrato, DOI, ISSN, ISBN); no se añade inferencia
    generativa.
11. **Los candidatos producidos por PDF siguen siendo `EXTRAÍDO`**, igual que
    los de URL/texto.
12. **`binding_id` sigue siendo obligatorio para claves ambiguas** (`dc.subject`,
    `dc.format.medium`); el extractor no cambia sus reglas de resolución.
13. **El orden lógico de fuentes y candidatos sigue usando `position`.** Un PDF
    subido después de crear la sesión recibe la siguiente posición disponible
    (`MAX(position) + 1` dentro de la sesión), consistente con el mecanismo ya
    introducido para el bug de orden no determinista corregido en el PR #2.
14. **El Golden Set no modifica el runtime; es un fixture de aceptación.**
    Vive en `tests/golden/evidence/` y se ejecuta con `pytest`, sin tocar
    contrato, servicios ni endpoints en producción.

## Dependencia elegida: `pypdf`

Se inspeccionaron las dependencias actuales (`apps/api/pyproject.toml`): no
había ninguna librería de PDF. Se evaluaron las opciones típicas del
ecosistema Python:

- **`pypdf`** (sucesor mantenido de `PyPDF2`, MIT, puro Python): sólo lee
  estructura y extrae texto; no depende de binarios del sistema, no invoca
  un motor JavaScript, no renderiza páginas. Es la opción más acotada para
  "sólo extraer texto de forma segura".
- `PyMuPDF`/`fitz`: más veloz y con más funciones (incluye renderizado de
  páginas), pero es un binding sobre una librería C (MuPDF) con superficie
  mucho mayor de la necesaria para este corte, y licencia AGPL/comercial.
- `pdfminer.six`: también puro Python y capaz, pero su API de extracción de
  texto es más compleja para obtener offsets por página de forma fiable.

Se elige `pypdf` por ser la superficie más pequeña suficiente para el
requisito ("sólo extraer texto, nunca ejecutar ni renderizar"), pura Python
(sin proceso externo que lanzar), y activamente mantenida.

También se añade `python-multipart`, requerida por FastAPI/Starlette para
parsear `multipart/form-data` (`UploadFile`); sin ella, el endpoint de subida
no puede funcionar.

## Persistencia

Se extiende `CatalogEvidenceSource` (no se crea una tabla nueva) con cuatro
columnas: `extraction_status`, `extraction_metadata_json`, `extracted_text_hash`
y `page_count`. Se reutilizan las columnas ya existentes `content_hash`
(binario original), `content_text` (texto extraído), `locator` (se deja
`NULL` para PDF) y `media_type` (`application/pdf`).

Se prefiere extender la tabla existente en vez de crear
`catalog_evidence_pdf_artifacts` separada porque:

- el resto del pipeline (`extract`, `get_evidence_session`, `position`,
  staleness) ya opera sobre `CatalogEvidenceSource` de forma genérica por
  `kind`; una tabla nueva forzaría un `UNION`/`JOIN` en cada consulta;
- el volumen de columnas añadidas es pequeño (4) y no introduce redundancia
  con las columnas existentes;
- el orden (`position`) y el ciclo de vida (append-only, snapshot inmutable)
  son idénticos entre URL/texto/PDF; una tabla separada duplicaría esas
  garantías en dos lugares.

El binario del PDF **no se guarda en PostgreSQL**: se escribe en disco local
bajo `EVIDENCE_PDF_STORAGE_DIR` (por defecto `data/evidence-pdfs/`), con el
nombre de archivo derivado exclusivamente de un `source_id` (UUID) generado
por el servidor — nunca del nombre de archivo subido por el catalogador. Esto
hace la path traversal estructuralmente imposible: no existe ninguna ruta en
el código que use el nombre de archivo del cliente para construir una ruta.

## Estados de extracción vs. estados de evidencia

`extraction_status` (`pending` / `extracted` / `no_extractable_text` /
`rejected`) describe el **pipeline de ingestión** de una fuente. Es un
concepto distinto de `EVIDENCE_STATES` (`EXTRAÍDO`, `VERIFICADO`, `INFERIDO`,
`PENDIENTE`, `GENERADO`), que describe el **candidato** ya producido. Un PDF
`rejected` nunca llega a persistirse (ver más abajo) y por tanto nunca
convive con estados QA como `APP_SCHEMA_GAP`, que de todas formas no forman
parte de `EVIDENCE_STATES` desde VERTICAL-018.

## Comportamiento de rechazo (falla cerrada)

Si el PDF es ilegible (no tiene los magic bytes `%PDF-`), está cifrado,
excede `MAX_PDF_PAGES` (300) o `pypdf` no puede parsearlo, la operación
completa falla con `422` **antes** de escribir el archivo a disco o
persistir una fila en `catalog_evidence_sources`. No queda estado parcial.
Esto es distinto del caso "sin texto útil" (decisión 7), que sí es una
ingestión válida y se persiste.

## Límite de tamaño y buffering

FastAPI/Starlette materializa el cuerpo `multipart/form-data` completo en
`UploadFile` (memoria o archivo temporal con spillover) antes de que el
handler de la ruta se ejecute; no hay un punto de control de streaming en el
handler mismo sin leer el `Request` crudo. El límite de 25 MB (`413`) se
aplica en la lógica de la aplicación (se lee `MAX_PDF_BYTES + 1` y se
rechaza si excede), lo que evita gastar CPU en parseo de PDFs grandes, pero
no evita que Starlette reciba y almacene temporalmente el cuerpo antes de esa
verificación. Dado que esta aplicación es una herramienta local para un
catalogador de confianza (sin autenticación de usuario final, token de
revisión ya requerido, sin exposición pública), un límite de tamaño estricto
a nivel de proxy/ASGI queda fuera de alcance de este corte y debe resolverse
si la aplicación se expone alguna vez a más de un operador de confianza.

## Timeout de extracción — ENFORCED

`EVIDENCE_PDF_EXTRACTION_TIMEOUT_SECONDS` (config, default 20s, 1–120s) es
un límite **aplicado**, no reservado para una iteración futura.
`extract_pdf_text()` se mantiene como función síncrona pura (sin `asyncio`
dentro); `add_pdf_evidence_source()` la ejecuta fuera del event loop con
`asyncio.to_thread()` y envuelve esa llamada en
`asyncio.wait_for(..., timeout=get_settings().evidence_pdf_extraction_timeout_seconds)`.
Si el timeout se cumple, se lanza `EvidencePdfTimeoutError` (subclase de
`EvidenceValidationError`) **antes** de calcular la posición, escribir el
archivo a disco o tocar la base de datos — falla cerrada, sin estado
parcial. La ruta HTTP la mapea explícitamente a `422` con un detalle de
código estable: `pdf_extraction_timeout: PDF extraction exceeded the
configured timeout`.

Limitación conocida y aceptada: `asyncio.to_thread` no puede matar el hilo
en ejecución cuando el `wait_for` expira; el hilo de `pypdf` sigue corriendo
en segundo plano hasta que termina por su cuenta (liberando eventualmente
sus recursos), aunque la petición HTTP ya recibió su error 422. Para esta
herramienta de operador único de confianza y con el límite de 300 páginas
ya vigente, esto es un techo aceptable de trabajo desperdiciado, no un
problema de disponibilidad.

## Consistencia filesystem/DB

`_write_pdf_bytes()` escribe el binario a disco **antes** de
`session.flush()`. Si el `flush()` falla por cualquier motivo — incluida
una colisión de `UNIQUE(session_id, position)` — el archivo ya escrito
quedaría huérfano. `add_pdf_evidence_source()` envuelve el `flush()` en un
`try/except` que ejecuta `Path.unlink(missing_ok=True)` sobre el archivo
recién escrito antes de relanzar la excepción original, de modo que
cualquier fallo de persistencia posterior a la escritura del archivo deja
el storage exactamente como estaba.

## Concurrencia en la asignación de `position`

`_next_source_position()` calcula `MAX(position) + 1` para la sesión. Sin
control adicional, dos subidas concurrentes a la misma sesión podrían leer
el mismo `MAX` y competir por la misma posición, con `UNIQUE(session_id,
position)` rechazando a la segunda con `IntegrityError` — y, sin la
limpieza descrita arriba, dejando su archivo huérfano.

Se elige serializar mediante bloqueo de fila (`SELECT ... FOR UPDATE` sobre
`catalog_evidence_sessions.session_id`), el mismo patrón ya usado en
`vocabularies/service.replace_active_vocabulary` para el mismo tipo de
carrera. `add_pdf_evidence_source()` adquiere ese lock antes de calcular
`_next_source_position()`; una segunda transacción concurrente sobre la
misma sesión queda bloqueada hasta que la primera confirma o revierte, y
entonces lee un `MAX` ya actualizado. No se eliminó
`UNIQUE(session_id, position)`: el lock evita la carrera en el camino feliz,
la restricción sigue siendo la garantía de última instancia a nivel de base
de datos. Se prefirió el lock sobre un retry-after-failure porque evita por
completo la ventana de colisión (y por tanto el propio riesgo de archivo
huérfano) en vez de sólo recuperarse de ella.

## Sesiones sin fuentes (PDF-only real)

VERTICAL-017 exigía URL o texto para crear una sesión
(`_normalized_source_payload` lanzaba `EvidenceValidationError` si ambos
eran `None`). Esa restricción hacía que un flujo "sólo PDF" necesitara un
texto ancla artificial como primera fuente. Se elimina esa restricción: una
`CatalogEvidenceSession` puede existir con cero fuentes; un PDF subido
después queda como primera fuente en `position=0`; `POST /extract` sobre una
sesión sin fuentes no inventa nada y devuelve una lista vacía de candidatos
de forma determinista (el bucle de extracción simplemente no itera nada).
La API sigue aceptando exactamente las mismas peticiones que antes
(`url`/`text` con valor siguen funcionando igual); sólo se volvió más
permisiva al aceptar también la ausencia de ambos, por lo que no hay cambio
incompatible para quien ya envía `url` o `text`. El formulario web de
creación de sesión refleja lo mismo: ya no exige ninguno de los dos campos.

## Golden Set

`tests/golden/evidence/` contiene un manifiesto (`manifest.json`) y casos
individuales bajo `cases/<case-id>/`, cada uno describiendo entradas y
resultados esperados (fuentes, candidatos, `binding_id`, campos, valores,
estado de evidencia, orden, estado de validación). Es un fixture de
aceptación de extremo a extremo ejecutado por `pytest tests/golden -q` e
incluido en `make test`; no reemplaza ni modifica ningún servicio en
producción.

## Consecuencias

- `CatalogEvidenceSource` gana un tercer `kind` (`pdf`), con cuatro columnas
  nuevas y una migración (`0019`).
- El extractor determinista existente (`_candidate_rows`) se reutiliza
  íntegramente para el texto derivado del PDF; sólo se le añade metadata de
  trazabilidad (página, offsets, hash del texto) cuando la fuente es PDF, sin
  alterar el comportamiento para URL/texto.
- La UI de evidencia gana un formulario de subida de PDF, con el mismo patrón
  de token server-side ya usado por el resto de las Server Actions, y ya no
  exige URL o texto para crear una sesión.
- `add_pdf_evidence_source` ahora: aplica el timeout de extracción de forma
  real (`EvidencePdfTimeoutError` → `422`), serializa la asignación de
  `position` por sesión con un lock de fila, y limpia el archivo escrito en
  disco si la persistencia posterior falla por cualquier motivo.
- VERTICAL-017 pasa a estado "Implementado / merged en main"; su "Siguiente
  iteración" apunta a esta ADR y a VERTICAL-019.

## Compatibilidad

Se preservan ADR-002, ADR-005, ADR-006, ADR-010 y ADR-014: DSpace de sólo
lectura, aprobación humana, agente conversacional sin herramientas de
escritura, y ausencia de fetch remoto.
