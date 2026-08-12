# VERTICAL-014 — Notificaciones operativas en tiempo real

**Estado:** Backlog P0 (NTF-001 a NTF-007) y P1 (NTF-008 a NTF-011)
implementados el 12 de agosto de 2026, autorizados explícitamente por el
usuario. De P2, sólo se inició "resúmenes" (NTF-012); notificaciones
externas, broker dedicado y múltiples colecciones quedan sin iniciar y
requieren decisión explícita adicional del usuario. Esta vertical nunca
autoriza escrituras en DSpace.

## Resultado observable

Un catalogador autenticado ve una campana en el extremo derecho del encabezado. La campana muestra el número de notificaciones no leídas y abre un panel de eventos operativos. Los avisos persisten en PostgreSQL y se recuperan aunque el navegador estuviera desconectado.

WebSocket sólo comunica que existe estado nuevo. PostgreSQL y la API HTTP son la fuente de verdad del contenido, destinatarios y estados de lectura.

## Alcance inicial

Incluye:

- campana global, contador, panel reciente e historial paginado;
- estados `unread`, `read` y `archived`;
- eventos de sincronización, diagnósticos, borradores, sugerencias y vocabularios;
- WebSocket autenticado, reconexión y recuperación HTTP;
- degradación a sondeo HTTP;
- auditoría de generación y lectura.

No incluye correo, SMS, push móvil, preferencias complejas, difusión no autorizada, datos personales de DSpace, acciones catalográficas automáticas ni escrituras en DSpace.

## Principios

1. PostgreSQL es la fuente de verdad local.
2. WebSocket no transporta el cuerpo: emite un aviso mínimo con cursor monotónico.
3. El cliente recupera contenido autorizado por HTTP.
4. Entrega al menos una vez y deduplicación mediante `notification_id`.
5. Una notificación no es evidencia catalográfica ni cambia hallazgos, borradores o sugerencias.
6. Los eventos se generan sólo al confirmar la transacción local.
7. La pérdida del canal no implica pérdida de notificaciones.
8. Ningún token de DSpace, JWT, CSRF ni secreto interno llega al navegador.

## Eventos P0

| Tipo | Disparador | Destinatario inicial | Severidad | Destino |
| --- | --- | --- | --- | --- |
| `sync.completed` | sincronización finalizada | catalogadores piloto | info | evidencia de sincronización |
| `sync.failed` | sincronización fallida | catalogadores y operador | error | ejecución local |
| `items.changed` | nuevos o modificados | catalogadores piloto | info | cola filtrada |
| `diagnostics.changed` | hallazgos o fingerprints nuevos | catalogadores piloto | warning | cola |
| `draft.stale` | cambia el hash fuente | autor y catalogadores | warning | ficha |
| `review.deferred` | decisión pospuesta confirmada | revisor y catalogadores | info | ficha |
| `suggestion.pending` | sugerencia sin decisión terminal | catalogadores piloto | info | ficha |
| `vocabulary.promoted` | revisión local activada | catalogadores piloto | info | vocabulario |

`review.confirmed`, `review.dismissed` y `draft.created` quedan P1 hasta definir agrupación y evitar ruido.

## Modelo de datos mínimo

### notification_events

Evento inmutable:

- `event_id UUID PK`
- `event_type VARCHAR(100)`
- `aggregate_type VARCHAR(50)`
- `aggregate_id VARCHAR(255)`
- `collection_uuid UUID NULL`
- `severity VARCHAR(20)`
- `title TEXT`
- `summary TEXT`
- `target_path TEXT NULL`, sólo rutas internas
- `payload JSONB`, sin secretos ni datos personales innecesarios
- `deduplication_key VARCHAR(255) UNIQUE`
- `occurred_at TIMESTAMPTZ`
- `created_at TIMESTAMPTZ`
- `expires_at TIMESTAMPTZ NULL`

### notification_deliveries

Estado por destinatario:

- `notification_id UUID PK`
- `event_id UUID FK`
- `recipient_id UUID`
- `state VARCHAR(20)`
- `delivered_at TIMESTAMPTZ`
- `read_at TIMESTAMPTZ NULL`
- `archived_at TIMESTAMPTZ NULL`
- única `(event_id, recipient_id)`

### notification_outbox

- `outbox_id UUID PK`
- `event_id UUID UNIQUE FK`
- `available_at TIMESTAMPTZ`
- `attempt_count INTEGER`
- `published_at TIMESTAMPTZ NULL`
- `last_error TEXT NULL`

Índices: deliveries `(recipient_id, state, delivered_at DESC)`; events `(collection_uuid, occurred_at DESC)` y `(event_type, occurred_at DESC)`; outbox parcial por pendientes.

## Identidad y autorización

La entrega personal requiere identidad local estable. Para el primer incremento
se aprueba el destinatario lógico colectivo `pilot-catalogers`. No se inferirá
identidad desde la procedencia pseudonimizada de DSpace.

Antes del fan-out personal deben existir sesión autenticada, `recipient_id`, autorización por colección y revocación de sesiones.

## Contratos HTTP

- `GET /api/notifications?state=&event_type=&cursor=&limit=`
- `GET /api/notifications/unread-count`
- `POST /api/notifications/{id}/read`
- `POST /api/notifications/read-all`
- `POST /api/notifications/{id}/archive`

Listado:

```json
{
  "items": [{
    "notification_id": "uuid",
    "event_type": "draft.stale",
    "severity": "warning",
    "title": "Borrador obsoleto",
    "summary": "La fuente cambió desde la versión base.",
    "target_path": "/items/{uuid}",
    "state": "unread",
    "occurred_at": "ISO-8601"
  }],
  "next_cursor": "opaque",
  "unread_count": 1
}
```

Las mutaciones son idempotentes, exigen sesión local y sólo afectan entregas autorizadas.

## Contrato WebSocket

Ruta propuesta: `GET /ws/notifications`.

Autenticación preferida: cookie de sesión `HttpOnly`, `Secure` fuera de local y validación de `Origin`. Nunca secretos en query string.

Servidor a cliente:

```json
{ "type": "notifications.available", "cursor": 124 }
```

```json
{ "type": "heartbeat", "server_time": "ISO-8601" }
```

Cliente a servidor, únicamente:

```json
{ "type": "resume", "after_cursor": 120 }
```

Contenido, historial y cambios de lectura usan HTTP.

## Flujo y consistencia

1. El caso de uso local inserta evento y outbox en la misma transacción.
2. El publicador reclama filas con `FOR UPDATE SKIP LOCKED`.
3. Crea entregas idempotentes para destinatarios autorizados.
4. Marca la outbox publicada.
5. Señala el cursor nuevo a conexiones WebSocket.
6. El cliente recupera por HTTP desde su cursor.
7. Al reconectar repite la recuperación.

El worker existente puede publicar durante el piloto. No se introducen Redis, Kafka ni otro broker sin métricas que lo justifiquen.

## UX

- Campana a la derecha del encabezado.
- Badge sólo si hay no leídas; máximo visual `99+`.
- Botón con `aria-label` que incluya el contador.
- Panel de hasta 10 avisos, orden descendente.
- Severidad, título, resumen, antigüedad y estado por fila.
- Abrir no marca automáticamente; lectura explícita.
- Acciones: marcar leído, marcar todos, archivar y abrir destino.
- Estados: `Actualizando`, `Sin conexión`, `Reconectando`.
- El panel nunca acepta, corrige, rechaza ni promueve.

## Reconexión y degradación

- backoff con jitter: 1, 2, 5, 10 y 30 segundos;
- heartbeat cada 30 segundos y cierre tras 90 sin actividad;
- recuperación HTTP al recuperar foco o conectividad;
- sondeo HTTP cada 30 segundos si cae el socket;
- menor actividad con pestaña oculta;
- respuesta 410 ante cursor expirado y recarga segura.

## Seguridad, privacidad y retención propuesta

- autorización en cada HTTP y apertura WebSocket;
- validación de Origin, límites por sesión/IP y tamaño;
- rutas internas validadas contra redirección abierta;
- plantillas sin HTML de usuario y escape en UI;
- no registrar cookies, tokens ni cabeceras sensibles;
- no incluir nombres o correos de DSpace;
- retención inicial aprobada y reversible: entregas 90 días, eventos 180 días.

## Observabilidad

Métricas: eventos por tipo, entregas/leídas/archivadas, edad de outbox, reintentos, conexiones y rechazos, reconexiones, latencia evento→visible y divergencia contador/listado.

Logs con `event_id`, `notification_id`, tipo, colección y resultado, sin contenido sensible.

Objetivo inicial: p95 visible menor de 5 segundos en local, cero pérdidas tras reconexión y contador exactamente reconciliable con PostgreSQL.

## Pruebas

- unitarias de deduplicación, destinatarios y transiciones;
- integración de outbox, reintento e idempotencia;
- autorización y aislamiento;
- contratos HTTP y cursor;
- WebSocket: sesión, Origin, heartbeat, reconexión e inválidos;
- recuperación tras desconexión y fallback HTTP;
- concurrencia de lectura/archivo;
- XSS, redirección abierta, límites y rate limiting;
- accesibilidad de campana, foco, teclado y lector;
- E2E evento→badge→panel→lectura→contador;
- ausencia explícita de llamadas de escritura a DSpace.

La suite no dependerá de DSpace real.

## Criterios de aceptación

1. Un evento confirmado aparece sin recarga.
2. La reconexión recupera todos los avisos autorizados.
3. El contador coincide con PostgreSQL.
4. Leer y archivar son idempotentes y auditables.
5. `deferred` genera aviso pero sigue pendiente en la cola.
6. WebSocket no contiene cuerpos ni secretos.
7. HTTP conserva funcionalidad si falla WebSocket.
8. Campana y panel son accesibles.
9. Notificaciones no cambian el dominio catalográfico ni DSpace.
10. La misma clave no duplica entregas.

## Backlog

### P0

- NTF-001 (S): aprobar ADR, identidad y catálogo.
- NTF-002 (M): migraciones de eventos, entregas y outbox.
- NTF-003 (M): productor idempotente y publicador.
- NTF-004 (M): listado, contador y lectura HTTP.
- NTF-005 (M): WebSocket mínimo con cursor.
- NTF-006 (M): campana, panel y fallback.
- NTF-007 (M): contrato, seguridad, integración y E2E.

### P1

- NTF-008 (S): preferencias simples.
- NTF-009 (S): agrupación de sincronización.
- NTF-010 (M): historial y archivo.
- NTF-011 (S): métricas operativas.

### P2

Notificaciones externas, resúmenes, broker dedicado y múltiples colecciones.

## Decisiones aprobadas

1. Identidad inicial: destinatario colectivo `pilot-catalogers`.
2. Catálogo de eventos P0: aprobado como aparece en este documento.
3. Retención: entregas 90 días y eventos 180 días.
4. ADR-009: aceptado.
5. Abrir el panel no marca avisos como leídos; la lectura es explícita.

## Puerta de implementación

Las decisiones de diseño están aprobadas. No crear migraciones ni componentes
hasta que el usuario autorice explícitamente iniciar el backlog P0.

El usuario autorizó el inicio del backlog P0 el 12 de agosto de 2026. La
migración `0013_notifications`, el productor/publicador (outbox con
`FOR UPDATE SKIP LOCKED`), los contratos HTTP, el WebSocket `/ws/notifications`
y la campana en Next.js quedaron implementados; ver `README.md` para el
resumen operativo.

El usuario autorizó el inicio del backlog P1 el mismo día. NTF-009 agrupa
`diagnostics.changed` por corrida de sincronización o por reconstrucción en
vez de emitir un evento por ítem (`replace_item_findings` ya no genera
notificaciones; el emisor agregado vive en `SyncService` y
`DiagnosticsService`). NTF-008 añade `notification_mute_rules`
(migración `0014`) y `GET`/`PUT /api/notifications/preferences`: silenciar un
tipo de evento no impide que el evento se registre, sólo omite la entrega.
NTF-010 añade la página `/notifications` con filtros e historial paginado por
cursor. NTF-011 añade `GET /api/notifications/metrics` (eventos por tipo,
entregas por estado, backlog/edad/reintentos de la outbox y conexiones
WebSocket aceptadas/rechazadas en memoria).

El usuario eligió "resúmenes" como único punto de P2 a iniciar el mismo día
(NTF-012); notificaciones externas, broker dedicado y múltiples colecciones
quedaron explícitamente sin autorizar. `notifications/digest_cli.py` agrega
un nuevo evento `digest.summary` con el conteo de actividad desde el último
resumen (o de las últimas 24 horas si nunca corrió) y lo emite por el mismo
canal existente (outbox → publicador → WebSocket/HTTP), sin mecanismo de
entrega nuevo. Se opera igual que `sync`/`diagnose`: es un comando disparado
por el operador (`make digest`), no un programador dentro de la API.
