# Agente de Asistencia Catalográfica para DSpace

Primera vertical del MVP para **P'UHREPECHA** (`123456789/4`).

## Alcance actual

- Cliente DSpace 7.6.6 estrictamente de lectura y enumeración mediante Discover.
- HAL+JSON original más metadatos repetibles normalizados en PostgreSQL.
- Sincronización paginada, idempotente, reanudable y auditable.
- API FastAPI para búsqueda, filtros, detalle y estado de sincronización.
- Explorador Next.js con lista y ficha completa.
- Diagnóstico determinista, versionado y reconstruible por ítem.
- Registros similares con puntaje y evidencia estructurada.
- Perfil cuantitativo de cobertura, valores y relaciones observadas.
- Cola operativa con prioridad, filtros y métricas reconciliadas a grano de ítem.
- Revisión humana append-only de hallazgos, almacenada únicamente en PostgreSQL local.
- Borradores lingüísticos locales con revisiones y detección de fuente obsoleta.
- Vocabularios aprobados versionados y validación literal con evidencia de procedencia.
- Agente conversacional de solo lectura sobre las herramientas internas existentes.
- Sin identidad institucional ni escritura en DSpace, ni por humanos ni por el agente.

## Arranque en WSL

```bash
cd /home/keilyn/cat
cp .env.example .env
docker-compose up -d postgres api web
docker-compose run --rm api python -m cataloging_api.sync.cli
docker-compose run --rm api python -m cataloging_api.diagnostics.cli
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000/docs`
- Salud: `http://localhost:8000/health`

No se descarga el contenido de los bitstreams; se conservan únicamente descriptores y enlaces públicos.

## Diagnóstico inicial

Las reglas activas son `CAT-LING-001` (familia sin rama) y `CAT-LING-002`
(rama sin familia). Los campos obligatorios se configuran mediante
`CATALOG_REQUIRED_FIELDS`, como una lista de claves separadas por comas. La
configuración queda vacía hasta que el referente catalográfico confirme P-002.
No se evalúan relaciones controladas ni variantes ortográficas sin vocabularios aprobados.

## Similitud estructurada

`GET /api/items/{uuid}/similar` compara únicamente ítems activos de la misma
colección. El puntaje combina coincidencias lingüísticas y tokens de título;
sirve para ordenar vecinos y no debe interpretarse como confianza catalográfica.
No utiliza embeddings, bitstreams ni fuentes externas.

## Evidencia de colección

`GET /api/catalog-profile` y `http://localhost:3000/catalog-profile` muestran
cobertura, valores frecuentes, patrones de completitud y relaciones observadas.
Todas las métricas usan ítems activos como población y muestran la frescura de
la sincronización. Las observaciones no se consideran vocabularios autorizados.

## Cola de trabajo

`GET /api/work-queue` y `http://localhost:3000/work-queue` priorizan ítems
con hallazgos vigentes o borradores locales. Las tarjetas usan toda la colección
activa; los filtros sólo afectan la lista. Todos los conteos tienen grano de ítem
y la vista declara fuente, denominador y frescura. La clasificación es
determinista y no modifica DSpace.


## Revisión humana local

La ficha permite confirmar, descartar o posponer hallazgos y registrar una nota
auditable. Configure un valor aleatorio largo en `CATALOG_REVIEW_TOKEN`; Next.js
lo usa sólo en el servidor para llamar a la API. El nombre del revisor es
autodeclarado durante el piloto. No existe ninguna operación de escritura hacia
DSpace ni edición de metadatos normalizados.

## Borradores locales

La ficha permite preparar reemplazos para los cuatro campos lingüísticos. Cada
borrador conserva una instantánea normalizada y revisiones append-only. Si cambia
el `source_hash` sincronizado, se bloquean nuevas revisiones; no hay rebase ni
aplicación automática. Los valores proceden del catalogador y no se consideran
vocabulario autorizado. Antes de guardar, el editor muestra una comparación
literal no bloqueante con los vocabularios activos. En cada revisión el servidor
guarda una instantánea de esa evidencia (revisión, fuente, aprobador, valores y
resultado); si no existe vocabulario, queda registrada como «no configurado».

## Vocabularios controlados

`GET /api/controlled-vocabularies`, `GET /api/items/{uuid}/metadata-validation`
y `http://localhost:3000/controlled-terms` exponen revisiones locales aprobadas.
Cada revisión conserva fuente, versión, aprobador e historial. La comparación es
literal; sin una fuente aprobada el estado permanece «no configurado». El alta
local requiere `CATALOG_REVIEW_TOKEN` y nunca escribe en DSpace.
Al reconstruir diagnósticos, un valor fuera de una revisión activa genera
`CAT-VOCAB-001`. La revisión forma parte del perfil y del fingerprint de
evidencia; reemplazarla marca resultados anteriores como obsoletos y evita
reutilizar decisiones humanas sobre evidencia diferente.

## Notificaciones en tiempo real

La campana en el encabezado muestra avisos operativos (sincronización,
diagnósticos, borradores obsoletos, revisiones pospuestas, sugerencias
pendientes y vocabularios promovidos) para el destinatario colectivo piloto
`pilot-catalogers`. PostgreSQL es la fuente de verdad: cada caso de uso local
inserta el evento y su fila de outbox en la misma transacción; un publicador en
segundo plano dentro del proceso de la API reclama la outbox con
`FOR UPDATE SKIP LOCKED`, crea entregas idempotentes y señala a los sockets
abiertos únicamente un cursor monotónico (`GET /ws/notifications`, sin cuerpo
ni secretos). El contenido, el conteo de no leídas y las transiciones de
lectura/archivado se sirven siempre por HTTP
(`GET /api/notifications`, `GET /api/notifications/unread-count`,
`POST /api/notifications/{id}/read`, `POST /api/notifications/read-all`,
`POST /api/notifications/{id}/archive`), con reconexión con backoff,
sondeo de respaldo cada 30 segundos y recuperación tras foco/reconexión.
Las mutaciones exigen `CATALOG_REVIEW_TOKEN`, adjuntado únicamente por rutas
proxy de Next.js para que el token nunca llegue al navegador. Una notificación
no es evidencia catalográfica ni cambia hallazgos, borradores, sugerencias o
DSpace.

Los hallazgos de diagnóstico nuevos se agregan por corrida de sincronización o
por reconstrucción (`GET /api/notifications` recibe un aviso por lote, no uno
por ítem). `GET`/`PUT /api/notifications/preferences` permite silenciar un
tipo de evento: el evento se sigue registrando en PostgreSQL, sólo se omite su
entrega. `http://localhost:3000/notifications` ofrece el historial completo
con filtros por estado y tipo, paginado por cursor. `GET
/api/notifications/metrics` expone eventos por tipo, entregas por estado,
backlog/edad/reintentos de la cola de salida y conexiones WebSocket aceptadas
o rechazadas.

```bash
docker-compose run --rm api python -m cataloging_api.notifications.digest_cli
```

Genera un aviso `digest.summary` con el conteo de actividad desde el resumen
anterior (o de las últimas 24 horas si nunca corrió), reutilizando el mismo
canal que el resto de las notificaciones; no emite nada si no hubo actividad.
Se opera igual que `sync`/`diagnose` (`make digest`); este repositorio no
incluye un programador propio, así que debe invocarse periódicamente desde el
host (por ejemplo con `cron`).

## Reanudación

`GET /api/sync-runs/latest` muestra el checkpoint. Para reanudar:

```bash
docker-compose run --rm api python -m cataloging_api.sync.cli --resume-page 3
```

Una reanudación no marca ausentes como eliminados. La conciliación sólo ocurre tras un recorrido completo exitoso desde la página cero.

## Asistente conversacional

`http://localhost:3000/asistente` abre un chat que responde preguntas sobre
la colección piloto usando exclusivamente herramientas internas de solo
lectura (búsqueda, ítem, similares, validación, sugerencias, cola de
trabajo, perfil, vocabularios, estado de sincronización). Nunca escribe en
DSpace ni genera hallazgos, borradores o sugerencias por su cuenta — sólo
enlaza a la ficha correspondiente para que un humano decida allí. La
integración con el proveedor del modelo vive aislada en
`cataloging_api/agent/`, el único módulo que importa su SDK (ADR-010).

Requiere `ANTHROPIC_API_KEY` en `.env`; sin ella, crear una conversación
funciona pero enviar mensajes responde `503`. Igual que el resto de las
mutaciones, iniciar una conversación y enviar mensajes exige
`CATALOG_REVIEW_TOKEN`, porque cada mensaje tiene costo real de API. El
historial de la conversación persiste en PostgreSQL (`agent_conversations`,
`agent_messages`, append-only).

## Verificación

```bash
make test
make lint
docker-compose build web
```

La suite usa fixtures HAL+JSON y PostgreSQL local; DSpace real no es una dependencia obligatoria.
