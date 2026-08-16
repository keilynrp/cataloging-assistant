# ADR-016: Secure remote evidence fetch

**Estado:** Propuesta implementada en la rama `feat/secure-remote-evidence-fetch`.

## Contexto

VERTICAL-017 (ADR-014) y VERTICAL-019 (ADR-015) dejaron explícitamente fuera
de alcance el fetch remoto de URLs: el catalogador podía aportar una URL como
*locator* (evidencia de que existe, nunca se descarga), texto pegado a mano o
un PDF subido explícitamente. Esta ADR abre esa última puerta de VERTICAL-017
("Fetch HTTP seguro con allow/deny de red, timeout, tamaño y redirecciones")
de forma acotada, con SSRF como amenaza central de diseño.

## Decisiones

1. **El fetch remoto sólo ocurre por acción explícita del catalogador.** No
   hay crawling, no hay reintento automático, no hay disparo por evento
   DSpace. Cada llamada a `POST /api/evidence-sessions/{id}/sources/remote`
   es una decisión humana puntual sobre una URL concreta.
2. **Sólo `http`/`https`.** Cualquier otro esquema (`file:`, `ftp:`,
   `gopher:`, `data:`, etc.) se rechaza antes de cualquier resolución DNS o
   conexión (`remote_url_invalid`).
3. **HTTPS es la vía esperada; HTTP se permite** porque el runtime de
   `dspace-cataloger` original y muchos repositorios/portales bibliográficos
   de la región siguen sirviendo sólo HTTP. No se fuerza upgrade a HTTPS
   automático (eso reescribiría la URL que el catalogador pidió
   explícitamente). Ambos esquemas pasan por la misma política SSRF y el
   mismo allowlist de MIME; no hay relajación de límites para HTTP.
4. **Sin autenticación remota.** El cliente nunca envía `Authorization`,
   nunca reenvía cookies de sesión, nunca implementa ningún flujo
   OAuth/basic/bearer contra el destino.
5. **Sin cookies.** El cliente HTTP dedicado se construye sin *cookie jar*
   persistente y no acepta `Set-Cookie` entre requests (cada fetch usa un
   `httpx.AsyncClient` nuevo, cerrado al terminar).
6. **Sin credenciales.** No existe ningún mecanismo para que el catalogador
   aporte usuario/contraseña, API key o token para el destino remoto. El
   único campo de entrada es la URL (más el nombre del catalogador para
   trazabilidad, igual que en subida de PDF).
7. **Sin `Authorization` headers.** Nunca se construye ni se reenvía ese
   header, en ninguna dirección.
8. **Sin headers aportados libremente por el usuario.** El request body de
   la API sólo acepta `url` y `author` (ver Fase 8). No existe ningún campo
   `headers` en el contrato; el catalogador no puede inyectar
   `X-Forwarded-For`, `Host` falsificado, ni ningún otro header hacia el
   destino remoto ni hacia esta misma API.
9. **Sin proxies aportados por el usuario.** El cliente HTTP se construye
   con `trust_env=False`: ignora `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` del
   entorno del proceso y cualquier `.netrc`. No hay parámetro de proxy en la
   API ni en la configuración de esta vertical.
10. **Sin crawling.** Un fetch procesa exactamente una URL (más los saltos
    de redirección estrictamente necesarios para resolverla, limitados y
    revalidados — ver Fase 3). Nunca se descubren ni se siguen enlaces
    nuevos a partir del contenido descargado.
11. **Sin ejecución de JavaScript.** El pipeline HTML nunca invoca un motor
    JS. El fetch en sí tampoco ejecuta ningún contenido descargado (ni PDF,
    igual que VERTICAL-019).
12. **Sin navegador/headless browser.** El fetch se hace con un cliente HTTP
    puro (`httpx`); no se levanta Chromium/Playwright/Puppeteer ni ningún
    proceso de renderizado.
13. **Sin seguir enlaces encontrados en el contenido descargado.** El
    parser HTML extrae texto visible; nunca resuelve `<a href>`, `<img
    src>`, `<link>`, `<iframe>`, ni hace subrequests para CSS/JS/imágenes.
    El pipeline PDF ya tenía esta garantía desde ADR-015 (nunca se procesan
    anotaciones URI ni `/Launch`) y se mantiene sin cambios.
14. **Sin escritura DSpace.** Igual que toda la vertical de evidencia: DSpace
    sólo se lee (`source_hash` para staleness). Ningún código de esta ADR
    llama a `cataloging_api.dspace`.
15. **Sin LLM.** La extracción de candidatos sobre el texto derivado
    (HTML/texto plano/PDF remoto) reutiliza exactamente el extractor
    determinista existente (`_candidate_rows`), sin ningún proveedor de
    modelos de lenguaje.
16. **Toda descarga conserva provenance y SHA-256.** Ver el contrato de
    provenance en la Fase 7 más abajo: SHA-256 del cuerpo original recibido
    y, cuando aplica, del texto derivado, más URL solicitada/final, cadena
    de redirecciones, IPs validadas, código de estado, tipo de contenido,
    tamaño, marca de tiempo y versión de política.
17. **Toda URL final después de redirects supera las mismas comprobaciones
    SSRF que la URL inicial.** No existe un salto "de confianza": cada
    `Location` se revalida con la misma función de validación de
    esquema/userinfo/DNS/política de IP que la URL original (Fase 3).
18. **DNS se valida antes de la conexión, en la medida que permite `httpx`.**
    Se resuelve explícitamente con `asyncio`/`socket.getaddrinfo` y se
    exige que **todas** las IPs devueltas sean públicas antes de emitir la
    petición HTTP. `httpx`/`httpcore` no exponen un *hook* público para
    fijar la conexión TCP a una IP ya validada preservando `Host`/SNI de
    forma correcta (ver limitación residual en Fase 3); por eso la conexión
    real la resuelve el sistema operativo una segunda vez, milisegundos
    después de la validación.
19. **No se confía únicamente en el hostname textual.** La clasificación de
    "público" siempre opera sobre la(s) IP(s) resuelta(s)
    (`ipaddress.IPv4Address`/`IPv6Address`), nunca sobre patrones de texto
    del hostname (salvo el bloqueo defensivo explícito de `localhost` y de
    formas numéricas que intentan imitar una IP — ver Fase 2).
20. **La aplicación falla cerrada.** Cualquier ambigüedad, error de DNS,
    error de parseo de URL, tipo de contenido no reconocido, timeout o
    error de red se traduce en un rechazo explícito con código estable; no
    hay ningún camino donde una condición no reconocida se trate como
    "permitir por defecto".

## Threat model SSRF (Fase 2)

La política de IP se implementa con `ipaddress` de la librería estándar y
usa como regla base `ip.is_global` (la clasificación más estricta que la
librería puede dar: excluye simultáneamente privado, loopback, link-local,
reservado, multicast y no especificado). Además se mantiene una lista
explícita, redundante a propósito, de las redes pedidas por el threat model,
para que el código de política sea auditable a simple vista sin tener que
confiar en el comportamiento exacto de `is_global` en una versión futura de
Python:

IPv4 bloqueadas explícitamente (además de `not is_global`):
`0.0.0.0/8`, `10.0.0.0/8`, `100.64.0.0/10`, `127.0.0.0/8`, `169.254.0.0/16`,
`172.16.0.0/12`, `192.0.0.0/24`, `192.0.2.0/24`, `192.168.0.0/16`,
`198.18.0.0/15`, `198.51.100.0/24`, `203.0.113.0/24`, `224.0.0.0/4`,
`240.0.0.0/4`.

IPv6 bloqueadas explícitamente: `::/128`, `::1/128`, `fc00::/7`, `fe80::/10`,
`ff00::/8`, `2001:db8::/32` (documentación), `64:ff9b::/96` (NAT64,
defensivo). Una dirección IPv4-mapped-en-IPv6 (`::ffff:a.b.c.d`) se
desenvuelve y se reclasifica con la misma regla IPv4 antes de aceptarla.

Una IP se acepta **sólo si** pasa ambas comprobaciones: `is_global is True`
**y** no cae en ninguna red de la lista explícita. Blindaje adicional,
independiente de IP:

- Hostname `localhost`/`localhost.` (con o sin punto final) se rechaza sin
  llegar a resolución DNS.
- Un host que, tras fallar como literal IP válido, resulta puramente
  numérico/con puntos (`2130706433`, `017700000001`) o contiene una forma
  hexadecimal (`0x7f000001`) se rechaza como `remote_url_invalid`: ningún
  hostname público real es puramente numérico, así que esta forma sólo
  puede ser un intento de burlar el parseo de IP con una representación que
  `httpx`/el sistema pueda normalizar de otra manera.
- `userinfo` en la URL (`http://user:pass@host/`) se rechaza siempre,
  independientemente del valor.
- Un endpoint de metadata cloud expresado como IP literal
  (`169.254.169.254`, `fd00:ec2::254`, etc.) cae dentro de los rangos
  link-local/ULA bloqueados arriba; no se requiere una regla especial por
  proveedor.

## DNS / redirect safety (Fase 3)

- Se resuelve el hostname con `asyncio.loop.getaddrinfo` (no bloqueante)
  antes de cada conexión, en cada salto.
- **Todas** las IPs devueltas deben ser públicas; si una sola cae en una red
  bloqueada, se rechaza el destino completo (`remote_target_not_public`),
  aunque otras respuestas de esa misma resolución fueran públicas — esto
  cubre DNS que mezcla respuestas públicas y privadas.
- Redirecciones: máximo `EVIDENCE_REMOTE_FETCH_MAX_REDIRECTS` (3 por
  defecto), manejadas manualmente (`follow_redirects=False` en el cliente
  `httpx`, bucle propio). Cada `Location` se resuelve contra la URL actual
  (`urllib.parse.urljoin`) y **vuelve a pasar** por la validación completa:
  esquema, `userinfo`, resolución DNS, política de IP. Si el destino de una
  redirección no es público, la causa exacta es la misma
  (`remote_target_not_public`, `remote_url_invalid`, etc.) que si hubiera
  sido la URL inicial — no existe un código separado "redirect hacia
  privado"; `remote_redirect_blocked` se reserva para el caso de bucle de
  redirecciones detectado (URL ya visitada en esta cadena). Superar el
  máximo de saltos es `remote_redirect_limit`.
- **Limitación residual de DNS rebinding, documentada y aceptada:** la
  validación DNS y la conexión TCP real son dos operaciones separadas en el
  tiempo (la validación usa `getaddrinfo` propio; la conexión la hace
  `httpx`/`httpcore`, que resuelve el hostname una segunda vez a través del
  resolver del sistema operativo). Entre ambas hay una ventana de
  milisegundos en la que, en teoría, un atacante que controle el DNS
  autoritativo del hostname objetivo podría cambiar la respuesta entre la
  primera y la segunda resolución (DNS rebinding clásico). Se evaluó fijar
  la conexión TCP a la IP ya validada preservando `Host`/SNI correctos, y se
  descarta para este corte: `httpx`/`httpcore` 0.28 no exponen un *hook*
  público de resolución de conexión (el `AsyncHTTPTransport` no acepta un
  resolver inyectable sin reimplementar la capa de *connection pooling* de
  `httpcore`), y una implementación casera de ese pinning con verificación
  TLS manual es exactamente el tipo de "TLS mal hecho para resolver
  rebinding" que esta ADR decide no construir. Mitigación parcial ya
  vigente: el TTL de la ventana es del orden de milisegundos (una sola
  petición HTTP, no un proceso de larga duración que reutiliza el mismo
  hostname), y el operador de esta herramienta es un catalogador de
  confianza que aporta URLs deliberadamente, no un flujo expuesto a
  contenido no confiable de terceros anónimos. Si esta herramienta se
  expone alguna vez a más de un operador de confianza, este punto debe
  revisarse antes de ese cambio de superficie.

## HTTP client (Fase 4)

`httpx>=0.28,<1` ya es una dependencia de `apps/api` (usada por
`cataloging_api.dspace.client.DSpaceClient`); no se añade ninguna librería
nueva. Se crea un cliente **dedicado** para evidencia remota
(`cataloging_api.evidence.remote_fetch`), separado del cliente DSpace: mezclar
ambos mezclaría políticas de timeout, reintento, cabeceras y, sobre todo,
superficie de confianza (DSpace es un backend interno conocido; el fetch de
evidencia apunta a cualquier URL pública que el catalogador escriba).

Config mínima (`cataloging_api.config.Settings`):

| Variable | Default | Notas |
|---|---|---|
| `EVIDENCE_REMOTE_FETCH_ENABLED` | `false` | Apagado por defecto; sin esto en `true`, el endpoint rechaza con `403 remote_fetch_disabled` antes de tocar red. |
| `EVIDENCE_REMOTE_FETCH_TIMEOUT_SECONDS` | `10` | Usado como `read`/`write`/`pool` de `httpx.Timeout`. |
| `EVIDENCE_REMOTE_FETCH_MAX_BYTES` | `25 MiB` (26214400) | Mismo orden de magnitud que `MAX_PDF_BYTES` (VERTICAL-019). |
| `EVIDENCE_REMOTE_FETCH_MAX_REDIRECTS` | `3` | Saltos de redirección, no peticiones totales. |
| `EVIDENCE_REMOTE_FETCH_USER_AGENT` | `CatalogingAssistantEvidenceFetcher/1.0` | Identifica el fetch ante el servidor remoto; no se falsea. |

`connect` se fija a `min(5.0, timeout_seconds)`: una conexión TCP/TLS lenta o
colgada no debe consumir todo el presupuesto de tiempo pensado para
recibir el cuerpo de la respuesta. No se añaden variables de entorno nuevas
más allá de las cinco de la tabla para mantener la superficie de
configuración mínima pedida.

## Content policy (Fase 5)

Allowlist de MIME (comparado tras separar parámetros como `;charset=`):
`text/plain`, `text/html`, `application/xhtml+xml`, `application/pdf`,
`application/xml`, `text/xml`. Cualquier otro valor (ZIP, Office, imágenes,
audio/video, ejecutables, `application/octet-stream` genérico) se rechaza
con `remote_content_type_not_allowed` **antes** de leer el cuerpo completo.

No se confía sólo en `Content-Type`:

- **PDF:** se exige `%PDF-` en los primeros bytes del cuerpo ya descargado
  (`pdf_extraction.looks_like_pdf`, reutilizado sin cambios de VERTICAL-019)
  y se reutiliza `extract_pdf_text` íntegro: mismos límites de páginas (300),
  mismo timeout de extracción, sin OCR. Un PDF remoto que pypdf rechaza
  (cifrado, corrupto, demasiadas páginas) da `remote_pdf_invalid`.
- **HTML/XHTML/XML:** nunca se ejecuta JS. Se decodifica con
  `errors="replace"` (una página HTML real casi nunca es UTF-8 estricto al
  100 %; sustituir bytes inválidos por U+FFFD es el mismo comportamiento
  tolerante que un navegador) y se convierte a texto con un parser propio
  basado en `html.parser.HTMLParser` de la librería estándar — no se añade
  ninguna librería de parsing HTML nueva. Se eliminan `script`, `style`,
  `noscript` y `template` (y todo su contenido) antes de recolectar texto
  visible; no se resuelven `<img>`, `<link>`, `<iframe>`, `<a href>` ni se
  hacen subrequests de ningún tipo. Se conserva el SHA-256 del cuerpo
  original y del texto derivado por separado (mismo patrón que PDF).
- **`text/plain`:** decodificación estricta UTF-8 (`errors="strict"`); un
  cuerpo que no es UTF-8 válido se rechaza con `remote_content_invalid` en
  vez de sustituir bytes silenciosamente, porque aquí el texto se trata como
  contenido literal citable, no como marcado tolerante a errores como HTML.
  Se aplica el mismo límite de 250 000 caracteres (`MAX_TEXT_CHARS`) que el
  texto pegado a mano de VERTICAL-017.

## Streaming y tamaño (Fase 6)

El cuerpo se lee con `response.aiter_bytes()` sobre un `client.stream(...)`,
nunca con `response.content`/`response.read()` de una vez. Si
`Content-Length` está presente y excede `EVIDENCE_REMOTE_FETCH_MAX_BYTES`, se
rechaza (`remote_content_too_large`, `413`) sin leer ni un byte del cuerpo.
Si `Content-Length` falta o miente, el bucle de lectura corta el stream tan
pronto el acumulado supera el máximo configurado, cierra la conexión (vía el
`async with` de `httpx`) y lanza el mismo error — nunca se persiste un
cuerpo parcial ni se crea una fuente a medias: la excepción se lanza antes
de que `add_remote_evidence_source` llegue a construir el
`CatalogEvidenceSource`.

## Modelo de evidencia (Fase 7)

Se reutiliza `CatalogEvidenceSource` (VERTICAL-017/019) sin ninguna
migración nueva. Se decide **no** proliferar `kind` con
`remote_text`/`remote_html`/`remote_pdf`: se añade un único `kind="remote"`
nuevo y la distinción de contenido vive en las columnas ya existentes
`media_type` (`text/plain`/`text/html`/`application/xhtml+xml`/
`application/pdf`/`application/xml`/`text/xml`) y `extraction_metadata_json`
(JSONB, ya existente desde la migración `0019`). Esto evita un `if kind ==
"remote_html" or kind == "remote_pdf" or ...` repetido por todo el pipeline;
el código que ya distingue comportamiento por tipo de contenido (extracción
de candidatos, offsets de página) sigue distinguiendo por `media_type`
exactamente igual que ya distinguía `kind == "pdf"` — el añadido es mínimo
(ver `_candidate_rows` en `evidence/service.py`).

**No se persiste el binario remoto en disco.** A diferencia del PDF subido
localmente (que sí se guarda en `EVIDENCE_PDF_STORAGE_DIR` porque el
catalogador entregó el archivo directamente y puede querer volver a verlo),
el binario de un fetch remoto no se escribe a `data/evidence-pdfs/` ni a
ningún otro directorio: sólo se conservan su SHA-256 y, cuando aplica, el
texto derivado. La fuente de verdad para "volver a obtener el contenido" es
la propia URL remota; un nuevo fetch explícito crea un nuevo snapshot (ver
Fase 9). Esto además evita reintroducir la clase de problema de limpieza de
archivos huérfanos que motivó el fix de PR #4 sobre `add_pdf_evidence_source`
para un tipo de fuente que no lo necesita.

`locator` almacena la **URL final** (`final_url`, después de redirecciones);
`content_hash` almacena el SHA-256 del cuerpo original recibido
(`response_body_sha256`); `extracted_text_hash` almacena el SHA-256 del
texto derivado cuando existe. `extraction_metadata_json` añade:

```json
{
  "requested_url": "...",
  "final_url": "...",
  "redirect_chain": ["..."],
  "resolved_ips": ["..."],
  "status_code": 200,
  "content_length": 1234,
  "fetched_at": "2026-08-16T12:00:00+00:00",
  "response_body_sha256": "...",
  "derived_text_sha256": "...",
  "remote_fetch_policy_version": "2026-08-16",
  "extractor": "pypdf" | "html_stdlib_parser" | "utf8_decode",
  "page_char_offsets": [...]
}
```

No se guardan cabeceras sensibles de la respuesta (ni siquiera todas las no
sensibles): sólo los campos de la tabla de arriba.

## Fase 8 — API

Ver contrato completo en VERTICAL-020. Resumen: `POST
/api/evidence-sessions/{session_id}/sources/remote` con `{"url", "author"}`
en el cuerpo, exige `X-Catalog-Review-Token`, devuelve el mismo
`EvidenceSessionOut` que el resto de endpoints mutables. Taxonomía de error
estable con un código por causa (`remote_fetch_disabled`,
`remote_url_invalid`, `remote_target_not_public`,
`remote_dns_resolution_failed`, `remote_redirect_blocked`,
`remote_redirect_limit`, `remote_content_type_not_allowed`,
`remote_content_invalid`, `remote_pdf_invalid`, `remote_content_too_large`,
`remote_fetch_timeout`, `remote_upstream_error`), nunca un mensaje libre que
pueda filtrar una IP interna o un stack trace.

`remote_fetch_timeout` se mapea a `422`, no `504`: este backend no actúa
como gateway/proxy genérico de terceros (no hay ningún cliente esperando un
504 de nivel de infraestructura); se mantiene la misma convención que
`pdf_extraction_timeout` de VERTICAL-019 (también `422`), para que el
catalogador vea un único vocabulario de error en toda la vertical de
evidencia. `remote_upstream_error` (fallo de red/conexión o `5xx` del
servidor remoto) se mapea a `502`, reflejando que la causa es el destino
externo, no una entrada inválida del catalogador.

## Fase 9 — Idempotencia / snapshot

Cada `POST .../sources/remote` crea una fuente **nueva**, en la siguiente
`position` disponible de la sesión (mismo lock de fila que PDF, mismo
`_next_source_position`). Nunca sobreescribe una fuente existente. Repetir
el fetch de la misma URL produce dos snapshots independientes — con hashes
distintos si el contenido remoto cambió entre llamadas, o hashes idénticos
si no cambió, pero siempre como dos filas separadas, append-only. La
extracción de candidatos reutiliza `_candidate_rows`/`extract_evidence_candidates`
sin ninguna rama de código nueva de inferencia: un candidato de fuente
`remote` sigue naciendo `EXTRAÍDO`, exactamente igual que uno de PDF o texto.

## Fase 10 — Staleness

`upload_remote_source` (ruta) comprueba `stale` **antes** de llamar al
servicio, exactamente igual que `extract_session`, `copy_to_draft` y
`upload_pdf_source`: una sesión stale bloquea fetch remoto nuevo, `/extract`
y `copy-to-draft` con `409`.

## Compatibilidad

Se preservan ADR-002 (DSpace fuente de verdad), ADR-005 (humano en el
circuito), ADR-006 (recuperación restringida), ADR-010 (agente
conversacional sin herramientas de escritura ni de red — el agente
conversacional no obtiene ninguna herramienta nueva en esta ADR; el fetch
remoto es un flujo HTTP separado iniciado explícitamente por el catalogador
desde `/evidence/{sessionId}`, nunca desde el agente), ADR-014 y ADR-015.

## Consecuencias

- Nueva superficie de red saliente controlada, apagada por defecto
  (`EVIDENCE_REMOTE_FETCH_ENABLED=false`).
- Tres módulos nuevos en `cataloging_api.evidence`: `net_policy` (SSRF/IP/DNS),
  `remote_fetch` (cliente HTTP dedicado, streaming, redirecciones),
  `html_extraction` (HTML→texto determinista, stdlib).
- `CatalogEvidenceSource` gana un tercer `kind` (`"remote"`) sin ninguna
  migración: reutiliza columnas y JSONB existentes.
- `_candidate_rows` gana un caso adicional mínimo para tratar `kind ==
  "remote"` con `media_type == "application/pdf"` igual que `kind == "pdf"`
  para offsets de página; el resto del pipeline no cambia.
- UI de evidencia gana un formulario "Obtener evidencia desde URL" en
  `/evidence/{sessionId}`, con el mismo patrón de token server-side ya usado
  por el resto de mutaciones.
- Golden Set crece de 14 a 34 casos mínimos, cubriendo el threat model SSRF
  completo con mocks de transporte HTTP (nunca red real).
