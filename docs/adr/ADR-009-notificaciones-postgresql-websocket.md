# ADR-009: PostgreSQL y outbox como fuente; WebSocket como señal

**Estado:** Aceptada el 12 de agosto de 2026.

## Contexto

La aplicación necesita avisos operativos sin recarga, con trazabilidad y recuperación tras desconexiones, evitando infraestructura prematura.

## Decisión propuesta

- PostgreSQL conserva eventos, entregas y lectura.
- Productores usan outbox transaccional.
- HTTP sirve contenido, historial y mutaciones.
- WebSocket sólo emite una señal mínima con cursor.
- El worker existente publica durante el piloto.
- No se incorporan Redis, Kafka ni servicios externos inicialmente.
- Las notificaciones no ejecutan acciones catalográficas ni escriben en DSpace.

## Consecuencias

Positivas: no hay pérdida lógica al desconectar, auditoría reconciliable, fallback HTTP y menor complejidad operativa.

Costos: exige identidad local antes del fan-out personal, nuevas tablas y retención, y controles de Origin, sesión, límites y observabilidad.

## Alternativas

- Sólo sondeo HTTP: fallback válido, menos inmediato.
- WebSocket como fuente: descartado por pérdida durante desconexión.
- Redis Pub/Sub: no justificado para una réplica piloto.
- SSE: alternativa válida si no se necesita canal bidireccional.

## Condición de revisión

Reevaluar SSE o broker con más de una réplica de API, fan-out elevado o incumplimiento medido del objetivo de latencia.
