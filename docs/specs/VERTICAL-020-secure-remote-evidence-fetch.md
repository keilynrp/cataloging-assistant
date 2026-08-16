# VERTICAL-020: Secure remote evidence fetch

## Estado

**Implementado en rama `feat/secure-remote-evidence-fetch`; pendiente de
revisión y merge.**

## Objetivo

Cerrar la última puerta que VERTICAL-017 dejó explícitamente abierta: fetch
HTTP(S) controlado de una URL de evidencia aportada explícitamente por el
catalogador, con SSRF como amenaza central de diseño, sin introducir LLM,
OCR, escritura DSpace, crawling ni acceso de red para el agente
conversacional.

## Scope

- Un endpoint nuevo y separado, `POST
  /api/evidence-sessions/{session_id}/sources/remote`, que recibe `{"url",
  "author"}` y realiza el fetch desde el backend (nunca desde el navegador).
- Feature flag `EVIDENCE_REMOTE_FETCH_ENABLED`, `false` por defecto: el
  endpoint responde `403 remote_fetch_disabled` sin tocar red mientras esté
  apagado.
- Política SSRF completa (ver ADR-016, Fase 2/3): sólo `http`/`https`, sin
  `userinfo`, resolución DNS explícita con **todas** las IPs resueltas
  públicas, redirecciones manuales limitadas y revalidadas salto a salto.
- Allowlist de MIME: `text/plain`, `text/html`, `application/xhtml+xml`,
  `application/pdf`, `application/xml`, `text/xml`.
- Streaming con límite de tamaño aplicado incluso si `Content-Length` falta
  o miente; ninguna fuente ni archivo parcial se persiste.
- Reutilización íntegra del pipeline PDF de VERTICAL-019 (magic bytes,
  límite de páginas, timeout, sin OCR) para PDFs remotos.
- Conversión HTML→texto determinista con la librería estándar
  (`html.parser`), sin ejecutar JavaScript, sin seguir imágenes/CSS/
  iframes/enlaces, sin subrequests.
- Cliente HTTP dedicado (`cataloging_api.evidence.remote_fetch`), separado
  del cliente DSpace, sin cookies, sin credenciales, sin proxies del
  entorno (`trust_env=False`), timeouts connect/read/write/pool.
- Cada fetch explícito crea una fuente `CatalogEvidenceSource` nueva
  (`kind="remote"`), append-only; dos fetches de la misma URL producen dos
  snapshots distintos.
- Extracción de candidatos determinista reutilizando `_candidate_rows`
  existente, sin ninguna semántica nueva de inferencia.
- Bloqueo de fetch remoto/extract/copy-to-draft sobre sesiones stale,
  consistente con URL-locator/texto/PDF ya existentes.
- UI en `/evidence/{sessionId}`: formulario "Obtener evidencia desde URL"
  con aviso explícito de que se hará una solicitud HTTP saliente, y
  presentación de URL final, MIME, tamaño, SHA-256, redirecciones y
  timestamp tras el fetch.
- Golden Set: 20 casos nuevos (15–34) sobre los 14 ya existentes (mínimo 34
  totales), y suite de tests unitarios de política de red/IP.

## Out of scope

- LLM/generativo para producir o corregir candidatos.
- OCR de PDFs remotos sin texto extraíble (mismo tratamiento
  `no_extractable_text` que VERTICAL-019, sin reintento automático).
- Cualquier escritura, sincronización o autenticación contra DSpace.
- Crawling: descubrir o seguir enlaces nuevos a partir del contenido
  descargado (HTML o PDF).
- Ejecución de JavaScript o cualquier forma de renderizado
  (navegador/headless browser).
- Ampliar `copy-to-draft` más allá de los campos `runtime_draftable` ya
  definidos por el contrato maestro (VERTICAL-018).
- Dar al agente conversacional (ADR-010) ninguna herramienta de red nueva;
  el fetch remoto sigue siendo un flujo separado iniciado por el
  catalogador desde la UI de evidencia.
- Autenticación nueva: sigue usándose únicamente `CATALOG_REVIEW_TOKEN`.
- Persistir el binario remoto en disco (a diferencia del PDF subido
  localmente); sólo se conservan hashes y, cuando aplica, el texto
  derivado — ver ADR-016, Fase 7.
- Resolver DNS rebinding con *pinning* de conexión TCP a la IP validada:
  limitación residual documentada y aceptada (ADR-016, Fase 3).

## SSRF threat model

Ver ADR-016 Fase 2 para el detalle completo (redes IPv4/IPv6 bloqueadas,
manejo de IPv4-mapped, formas numéricas de IP, `userinfo`, `localhost`).
Resumen operativo: una IP sólo se acepta si `ipaddress.<Address>.is_global`
es verdadero **y** no cae en ninguna red de la lista explícita redundante
mantenida en `cataloging_api.evidence.net_policy`. La clasificación siempre
opera sobre la IP resuelta, nunca sobre el hostname como texto (salvo
bloqueo defensivo de `localhost`/formas numéricas de IP).

## DNS policy

- Resolución explícita vía `asyncio` (`loop.getaddrinfo`, no bloqueante)
  antes de cada conexión, en cada salto de redirección.
- Si **cualquier** IP resuelta no es pública, se rechaza el destino
  completo (`remote_target_not_public`) — cubre respuestas DNS mixtas
  público+privado.
- Las IPs validadas del salto final quedan en
  `extraction_metadata_json.resolved_ips`; la traza completa por salto
  (inicial + cada redirect) queda en `extraction_metadata_json.resolved_hops`
  (`[{"url", "host", "resolved_ips"}, ...]`) — provenance/API; nunca en la UI
  pública, ver Fase 11.
- Limitación residual de DNS rebinding documentada en ADR-016; no se
  implementa *pinning* de conexión TCP en este corte.

## Redirect policy

- Máximo `EVIDENCE_REMOTE_FETCH_MAX_REDIRECTS` (3 por defecto) saltos,
  manejados manualmente (`follow_redirects=False`), nunca con el
  seguimiento automático ciego de `httpx`.
- Cada `Location` se resuelve contra la URL actual (`urljoin`) y vuelve a
  pasar por validación completa de esquema, `userinfo`, DNS y política de
  IP — el mismo camino de código que la URL inicial, así que un redirect
  hacia `localhost`/privado/link-local produce el mismo código de error
  (`remote_target_not_public`/`remote_url_invalid`) que si esa URL hubiera
  sido la entrada directa.
- Un bucle de redirecciones (URL ya visitada en la misma cadena) se detecta
  y rechaza como `remote_redirect_blocked`. Superar el máximo de saltos es
  `remote_redirect_limit`.
- Sólo el código de estado del salto **final** importa para MIME/tamaño:
  una vez agotados los saltos de redirect soportados, la respuesta debe
  ser `2xx` para procesarse; ver "Aceptación de status HTTP" más abajo.

## Aceptación de status HTTP

Tras resolver los redirects soportados, únicamente `200 <= status_code <
300` se trata como éxito. La comprobación ocurre **antes** de mirar
`Content-Type` o leer el cuerpo. Cualquier otro estado — `4xx`, `5xx`, o un
`3xx` no reconocido como redirect (`304`, `300`) — se rechaza como
`remote_upstream_error` (`502`) sin procesar su cuerpo ni su MIME: una
página de error 404 en HTML nunca se convierte en fuente ni en candidatos.

## MIME policy

Allowlist: `text/plain`, `text/html`, `application/xhtml+xml`,
`application/pdf`, `application/xml`, `text/xml`. `Content-Type` se compara
tras separar parámetros (`;charset=...`) y normalizar a minúsculas; nunca es
la única comprobación para PDF (se exige además `%PDF-` en los bytes reales
del cuerpo). Cualquier otro tipo (ZIP, Office, imágenes, audio/video,
ejecutables, `application/octet-stream`) se rechaza con
`remote_content_type_not_allowed` antes de leer el cuerpo completo.

## Size/time limits

| Límite | Valor por defecto | Aplicación |
|---|---|---|
| `EVIDENCE_REMOTE_FETCH_MAX_BYTES` | 25 MiB | `Content-Length` declarado > máximo → rechazo inmediato (`413`); si falta o miente, el stream se corta al superar el máximo durante la lectura. |
| `EVIDENCE_REMOTE_FETCH_TIMEOUT_SECONDS` | 10 s | `read`/`write`/`pool` de `httpx.Timeout`; `connect` usa `min(5.0, timeout)`. |
| `EVIDENCE_REMOTE_FETCH_MAX_REDIRECTS` | 3 | Saltos de redirección, no peticiones totales (máximo 4 peticiones). |
| Páginas PDF | 300 (reutilizado de VERTICAL-019) | Mismo `MAX_PDF_PAGES`. |
| Caracteres de texto | 250 000 (reutilizado de VERTICAL-017) | Aplica a `text/plain` y al texto derivado de HTML/XML; excederlo se **rechaza** (`remote_content_invalid`), nunca se trunca en silencio. |
| Timeout de extracción PDF | `EVIDENCE_PDF_EXTRACTION_TIMEOUT_SECONDS` (VERTICAL-019, default 20 s) | Compartido vía un helper (`_extract_pdf_text_off_loop`) entre subida local y PDF remoto; el remoto falla cerrado con `remote_pdf_timeout` sin persistir nada. |

## Provenance contract

Cada fuente `kind="remote"` conserva en `extraction_metadata_json`:

`requested_url`, `final_url`, `redirect_chain`, `resolved_ips`,
`resolved_hops` (traza por salto: `url`/`host`/`resolved_ips` para la URL
inicial y cada redirect), `status_code`, `content_length`, `fetched_at`,
`response_body_sha256`, `derived_text_sha256`, `remote_fetch_policy_version`,
`extractor`, y (para PDF remoto) `page_char_offsets`. `content_hash` (columna existente)
duplica `response_body_sha256` para consistencia con el resto de fuentes;
`locator` (columna existente) guarda `final_url`. No se guardan cabeceras
sensibles ni ninguna cabecera fuera de esta lista.

## Failure taxonomy

| HTTP | Código estable | Causa |
|---|---|---|
| 403 | `remote_fetch_disabled` | `EVIDENCE_REMOTE_FETCH_ENABLED=false`. |
| 422 | `remote_url_invalid` | Esquema no permitido, `userinfo`, host vacío/inválido, puerto inválido, forma numérica sospechosa de IP. |
| 422 | `remote_target_not_public` | La URL (inicial o tras redirect) resuelve a una IP no pública, o es una IP literal no pública. |
| 422 | `remote_dns_resolution_failed` | El hostname no resuelve. |
| 422 | `remote_redirect_blocked` | Bucle de redirecciones detectado. |
| 422 | `remote_redirect_limit` | Se superó `EVIDENCE_REMOTE_FETCH_MAX_REDIRECTS`. |
| 422 | `remote_content_type_not_allowed` | `Content-Type` fuera del allowlist. |
| 422 | `remote_content_invalid` | Cuerpo no decodificable como el tipo declarado (p. ej. `text/plain` no UTF-8), o texto derivado (`text/plain` o HTML/XML) que excede `MAX_TEXT_CHARS`. |
| 422 | `remote_pdf_invalid` | Magic bytes ausentes o `pypdf` rechaza el PDF (cifrado/corrupto/demasiadas páginas). |
| 422 | `remote_pdf_timeout` | La extracción del PDF (local o remoto, mismo helper compartido) excedió `EVIDENCE_PDF_EXTRACTION_TIMEOUT_SECONDS`; distinto de `remote_fetch_timeout` (fase de descarga HTTP, no de parseo). |
| 413 | `remote_content_too_large` | `Content-Length` o el cuerpo en streaming exceden el máximo. |
| 422 | `remote_fetch_timeout` | Se superó `EVIDENCE_REMOTE_FETCH_TIMEOUT_SECONDS` durante la descarga HTTP (ver ADR-016 sobre por qué `422` y no `504`). |
| 502 | `remote_upstream_error` | Error de red/conexión, `5xx` del servidor remoto, o cualquier estado final que no sea `2xx` ni un redirect soportado (`4xx`, `304`, etc.) — el cuerpo/MIME de una respuesta así nunca se procesa como evidencia. |
| 409 | *(sin código de detalle nuevo)* | Sesión stale, mismo gate que URL/texto/PDF. |

Ningún mensaje de error incluye stack trace ni IP interna; el `detail` de
la respuesta HTTP es siempre uno de los códigos estables de la tabla.

## Rollback

- No hay migración de base de datos que revertir: esta vertical reutiliza
  `CatalogEvidenceSource` sin columnas nuevas (`kind="remote"` es un valor
  más del `String(30)` existente).
- El endpoint nuevo es aislado (`POST .../sources/remote`); revertir el
  commit que lo introduce no afecta `url`/`text`/`pdf` existentes.
- Con `EVIDENCE_REMOTE_FETCH_ENABLED=false` (el default), la superficie de
  red nueva queda completamente inerte incluso sin revertir código.
- No hay archivos en disco que limpiar: el binario remoto nunca se
  persiste fuera de PostgreSQL (a diferencia de `data/evidence-pdfs/`).

## No DSpace write

Ninguna función de esta vertical llama a `cataloging_api.dspace`. DSpace
sigue siendo exclusivamente fuente de lectura para `source_hash`/staleness.

## No LLM

La extracción de candidatos sobre texto remoto (HTML/texto plano/PDF)
reutiliza únicamente `_candidate_rows`, el mismo extractor determinista de
VERTICAL-017/019. No se invoca ningún proveedor de modelos de lenguaje.

## No OCR

Un PDF remoto sin capa de texto extraíble se persiste con
`extraction_status = "no_extractable_text"` y no genera candidatos, igual
que un PDF subido localmente (VERTICAL-019). Un HTML sin texto visible
recibe el mismo tratamiento.

## Acceptance criteria

1. Con `EVIDENCE_REMOTE_FETCH_ENABLED=false`, el endpoint responde `403
   remote_fetch_disabled` sin abrir ninguna conexión de red.
2. Una URL con esquema distinto de `http`/`https` es rechazada con
   `remote_url_invalid` antes de cualquier resolución DNS.
3. Una URL con `userinfo` (`http://user:pass@host/`) es rechazada con
   `remote_url_invalid`.
4. Un hostname que resuelve a `127.0.0.1`, `::1`, `169.254.169.254`, o
   cualquier red RFC1918/link-local/reservada es rechazado con
   `remote_target_not_public`, tanto si es una IP literal como si es el
   resultado de resolución DNS.
5. Una resolución DNS que devuelve una mezcla de IPs públicas y privadas
   rechaza el destino completo.
6. Una redirección hacia un destino privado/`localhost`/link-local es
   rechazada con la misma comprobación que la URL inicial.
7. Un bucle de redirecciones se detecta y rechaza
   (`remote_redirect_blocked`); superar `EVIDENCE_REMOTE_FETCH_MAX_REDIRECTS`
   se rechaza como `remote_redirect_limit`.
8. Un `Content-Type` fuera del allowlist se rechaza antes de leer el cuerpo.
9. Un cuerpo cuyo `Content-Length` declarado excede el máximo se rechaza
   con `413` sin leerlo; un cuerpo que excede el máximo en streaming sin
   `Content-Length` fiable se corta y rechaza igual, sin persistir nada
   parcial.
10. Un PDF remoto válido reutiliza el pipeline de VERTICAL-019 (magic
    bytes, límite de páginas, timeout, sin OCR) y produce los mismos
    candidatos deterministas que un PDF subido localmente con el mismo
    texto.
11. Un HTML remoto válido produce texto derivado sin restos de
    `script`/`style`/`noscript`/`template`, con su propio SHA-256, y
    candidatos deterministas (DOI/ISSN/ISBN/líneas explícitas) igual que
    texto plano.
12. Dos fetches explícitos de la misma URL crean dos fuentes `remote`
    distintas, append-only, cada una con su propia `position`.
13. Una sesión `stale` bloquea un nuevo fetch remoto, igual que bloquea
    `/extract`, `copy-to-draft` y subida de PDF.
14. `pytest tests/golden -q` pasa con un mínimo de 34 casos (14 previos +
    20 de esta vertical; 39 tras la revisión pre-Ready del PR #5, que añadió
    5 casos más: rechazo de `4xx`/`401`/`403`, rechazo por truncamiento de
    HTML, y provenance DNS por salto).
15. Ninguna prueba de esta vertical realiza una llamada HTTP real ni
    resolución DNS real: todo el tráfico se intercepta a nivel de
    transporte (`respx`) y toda resolución DNS por hostname (no IP literal)
    usa un resolutor inyectado de prueba, sin debilitar la política SSRF
    real (`net_policy` se ejecuta sin modificar en todos los casos).
16. Ninguna operación de esta vertical llama a la capa DSpace ni añade
    herramientas de red al agente conversacional.
17. Un `4xx` o cualquier estado final que no sea `2xx` ni un redirect
    soportado (incluidos `401`, `403`, `404`, `304`) nunca crea una fuente
    ni candidatos; se rechaza como `remote_upstream_error` antes de mirar
    `Content-Type` o leer el cuerpo.
18. Un texto derivado (HTML/XML o `text/plain`) que excede `MAX_TEXT_CHARS`
    se rechaza (`remote_content_invalid`); ninguna fuente queda persistida
    con `extraction_status = "extracted"` y texto truncado en silencio.
19. La extracción de un PDF remoto usa el mismo helper de timeout que la
    subida local (`_extract_pdf_text_off_loop`, fuera del event loop vía
    `asyncio.to_thread`); si excede `EVIDENCE_PDF_EXTRACTION_TIMEOUT_SECONDS`,
    falla cerrado con `remote_pdf_timeout` sin persistir nada.
20. `extraction_metadata_json.resolved_hops` conserva la traza DNS validada
    de cada salto (URL inicial y cada redirect), no sólo del último.

## Relación con VERTICAL-017/019

Este documento no reescribe VERTICAL-017 ni VERTICAL-019; los continúa.
Ambos quedan marcados como implementados/fusionados en `main`, con su
"Siguiente iteración" apuntando aquí y a ADR-016.
