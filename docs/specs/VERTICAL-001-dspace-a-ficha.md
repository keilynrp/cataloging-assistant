# VERTICAL-001: DSpace a ficha local

## Objetivo

Sincronizar `P'UHREPECHA` desde DSpace a PostgreSQL y consultar un registro completo desde la web.

## Incluido

- Colección, Discover paginado, detalle, metadatos, bundles y descriptores de bitstreams.
- Upsert por UUID, hash de fuente, checkpoint y conciliación segura.
- API de búsqueda, cuatro filtros lingüísticos, detalle y estado del sync.
- Lista y ficha web.

## Excluido

- Descarga masiva, diagnóstico institucional, agente, revisión y cualquier escritura en DSpace.

## Aceptación

1. Reejecutar el mismo fixture no duplica ítems ni metadatos.
2. JSON fuente, orden y multiplicidad se conservan.
3. Un fallo conserva la página siguiente como checkpoint.
4. Sólo un recorrido completo exitoso marca como inactivos los registros no observados.
5. La API y la web muestran UUID, handle, metadatos, bundles y bitstreams.
6. La suite no necesita la instancia DSpace real.

