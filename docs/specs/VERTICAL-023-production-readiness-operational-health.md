# VERTICAL-023: Production Readiness & Operational Health

## Resultado observable

La aplicación puede distinguir de forma reproducible entre:

- proceso vivo;
- servicio listo para recibir tráfico;
- dependencia degradada;
- fallo operacional que requiere intervención humana.

El despliegue expone señales de liveness/readiness seguras, dispone de smoke tests reproducibles para Docker/Dokploy y conserva evidencia suficiente para aceptar o rechazar operacionalmente una release.

La observabilidad puede detectar y clasificar fallos. **Nunca repara automáticamente infraestructura ni modifica gobernanza catalográfica.**

## Objetivo

Cerrar la brecha entre "la aplicación está desplegada" y "la aplicación está operativamente disponible".

VERTICAL-023 debe reducir el tiempo de diagnóstico de fallos como:

- `Bad Gateway` del frontend;
- proceso web vivo pero no alcanzable desde la red Docker;
- API viva pero no ready por dependencia crítica;
- pérdida de conectividad API -> PostgreSQL;
- configuración de runtime incompleta o incoherente;
- fallo del contrato DSpace que debe ser visible sin promover, aprobar ni mutar snapshots.

## Motivación inmediata

El incidente de producción resuelto antes de este vertical mostró una diferencia importante entre estado de contenedor y disponibilidad real:

```text
container web: Up
Next.js: Ready
127.0.0.1:3000: connection refused
api -> web:3000: connection refused
public frontend: Bad Gateway
```

La causa fue un bind del servidor Next.js al hostname efímero del contenedor en lugar de `0.0.0.0:3000`.

VERTICAL-023 no codifica ese incidente como caso especial. Generaliza la capacidad de demostrar que cada servicio está vivo, listo y alcanzable por las rutas que realmente utiliza producción.

## Principio de arquitectura

```text
process state
  -> liveness
  -> dependency checks
  -> readiness
  -> deployment smoke
  -> operational evidence
  -> human acceptance
```

Nunca:

```text
failed readiness
  -> automatic restart/redeploy
  -> automatic config rewrite
  -> automatic DSpace baseline approval
```

## Definiciones normativas

### Liveness

Responde únicamente si el proceso de aplicación está vivo y puede atender una petición mínima.

No debe depender de DSpace ni de servicios externos remotos.

Un fallo de PostgreSQL no debe convertir liveness en una sonda de disponibilidad total.

### Readiness

Responde si el servicio puede realizar su función mínima de producción en ese momento.

Puede depender de componentes críticos internos, pero debe distinguir dependencias esenciales de dependencias degradables.

### Operational health

Vista estructurada y diagnóstica para operadores. Puede exponer estados parciales, timestamps, versión desplegada y salud de dependencias sin revelar secretos.

No debe utilizarse como mecanismo de aprobación ni mutación.

## Superficies mínimas

### API

Definir o normalizar:

- `GET /health` — liveness;
- `GET /ready` — readiness;
- una superficie operativa detallada, preferiblemente bajo namespace administrativo/operacional existente si lo hubiera.

Semántica inicial:

```text
GET /health
200 -> proceso API vivo

GET /ready
200 -> dependencias críticas mínimas disponibles
503 -> proceso vivo pero no listo
```

### Frontend

El smoke test debe demostrar al menos:

- proceso Next.js vivo;
- escucha en interfaz alcanzable por la red Docker;
- `web:3000` accesible desde otro servicio del compose;
- URL pública responde sin `502/503`.

No es obligatorio exponer una API de health propia del frontend si una comprobación HTTP determinista sobre una ruta mínima cumple el contrato.

## Dependencias y criticidad

Clasificación inicial:

### Críticas para readiness de API

- PostgreSQL cuando la operación normal requiere persistencia;
- configuración runtime mínima necesaria para arrancar correctamente.

### Observables pero no necesariamente bloqueantes

- estado del contrato DSpace de VERTICAL-022;
- última verificación DSpace;
- scheduler externo;
- servicios externos cuya caída permita operación degradada segura.

El contrato DSpace puede estar `REVIEW_REQUIRED`, `STALE_CHECK_FAILED` o equivalente sin convertir automáticamente `/health` en fallo de proceso.

La política exacta de readiness debe documentar qué estados bloquean tráfico y cuáles producen degradación visible.

## Modelo de estado

Estados operacionales mínimos:

- `LIVE`;
- `READY`;
- `DEGRADED`;
- `NOT_READY`;
- `UNKNOWN`.

Para cada check estructurado conservar:

- `name`;
- `status`;
- `checked_at`;
- `latency_ms` cuando sea útil;
- `detail_code` estable y no secreto;
- mensaje breve apto para operadores.

No retornar:

- passwords;
- tokens;
- connection strings completas;
- `CATALOG_REVIEW_TOKEN`;
- `DSpace_READ_PASSWORD`;
- payloads raw sensibles;
- stack traces completos en endpoint público.

## Detail codes iniciales

Como mínimo:

- `PROCESS_OK`;
- `DATABASE_OK`;
- `DATABASE_UNREACHABLE`;
- `WEB_INTERNAL_OK`;
- `WEB_INTERNAL_UNREACHABLE`;
- `PUBLIC_FRONTEND_OK`;
- `PUBLIC_FRONTEND_BAD_GATEWAY`;
- `PUBLIC_API_OK`;
- `RUNTIME_CONFIG_INVALID`;
- `DSPACE_CONTRACT_SYNCED`;
- `DSPACE_CONTRACT_DEGRADED`.

Los códigos son contrato operativo, no texto libre para lógica de negocio.

## Relación con VERTICAL-022

VERTICAL-022 sigue siendo la única autoridad para:

- snapshots del contrato DSpace;
- baseline `ACTIVE`;
- resolución de evidencia;
- drift;
- aprobación/promoción humana.

VERTICAL-023 solo **lee** el estado operacional expuesto por VERTICAL-022.

Invariante fuerte:

> Ningún health check, readiness check, smoke test ni scheduler de VERTICAL-023 puede aprobar, resolver, promover, superseder o crear un baseline DSpace.

Un fallo de readiness tampoco puede reinterpretarse como drift ni como eliminación de campos.

## Relación con Dokploy/Traefik

El contrato de despliegue debe comprobar la ruta efectiva de red, no solo el estado `Up` del contenedor.

Para el frontend actual:

```text
Traefik/Dokploy -> web:3000
```

Por ello la configuración de producción debe conservar explícitamente:

```text
HOSTNAME=0.0.0.0
PORT=3000
```

mientras Next.js standalone dependa de esas variables para escuchar en todas las interfaces del contenedor.

Un cambio futuro de runtime puede sustituir esta implementación, pero no puede eliminar la invariante de alcanzabilidad desde la red Docker.

## Smoke test reproducible

Debe existir un script versionado en el repositorio, sin secretos embebidos, que pueda ejecutarse manualmente después de un deploy.

Nombre propuesto:

```text
scripts/production-smoke.sh
```

Debe validar, en orden y con timeouts explícitos:

1. compose services esperados activos;
2. API liveness;
3. API readiness;
4. frontend alcanzable en `web:3000` desde una ruta externa al propio proceso web;
5. frontend público;
6. API pública;
7. estado del contrato DSpace como observación read-only.

Debe terminar con exit code no cero ante fallo de criterio obligatorio.

La salida debe ser apta para conservarse como evidencia:

```text
PASS api_liveness
PASS api_readiness
PASS web_internal
PASS public_frontend
PASS public_api
WARN dspace_contract <status>
RESULT PASS
```

No imprimir secretos ni `.env` completo.

## Alcance

Incluye:

- semántica liveness/readiness;
- checks de dependencias críticas;
- smoke test versionado;
- timeouts y códigos de salida estables;
- documentación Dokploy;
- evidencia de aceptación operacional;
- tests automatizados del modelo de health;
- comportamiento fail-closed para readiness cuando una dependencia crítica no está disponible.

## Fuera de alcance

No incluye:

- auto-healing;
- auto-redeploy;
- reinicio automático de contenedores desde la aplicación;
- modificación automática de variables Dokploy;
- escritura en DSpace;
- promoción automática de snapshots;
- nueva plataforma general de observabilidad;
- Prometheus/Grafana obligatorios;
- alerting complejo;
- cambios semánticos de catalogación;
- cambios al contrato maestro de 56 bindings salvo que otro vertical gobernado lo apruebe.

## Invariantes de seguridad y gobernanza

1. Health/readiness son read-only.
2. Ningún endpoint operacional muta DSpace.
3. Ningún endpoint operacional muta baseline, snapshot o resolución VERTICAL-022.
4. No se exponen secretos.
5. Liveness no depende de DSpace remoto.
6. Readiness diferencia fallo crítico de degradación no bloqueante.
7. `503` significa proceso vivo pero no listo; no equivale a crash.
8. Un `502 Bad Gateway` público debe poder distinguirse de un proceso web caído mediante checks internos.
9. El smoke test no corrige configuración automáticamente.
10. La aceptación de producción es humana y basada en evidencia.
11. La evidencia se registra con timestamp y commit/release identificable cuando esté disponible.
12. Cambios futuros a la política de criticidad requieren revisión explícita.

## Slice 023-A — Health model

### Backend

- normalizar `GET /health`;
- añadir `GET /ready`;
- check mínimo de PostgreSQL con timeout corto;
- modelo estructurado de componentes;
- códigos estables;
- no incluir DSpace como dependencia de liveness;
- exponer DSpace contract health solo como componente operacional read-only.

### Tests

- proceso vivo + DB disponible -> `/health=200`, `/ready=200`;
- proceso vivo + DB caída -> `/health=200`, `/ready=503`;
- DSpace no accesible -> liveness permanece `200`;
- estado DSpace degradado no provoca ninguna mutación;
- respuestas no contienen secretos conocidos;
- timeout de dependencia produce código estable y no bloqueo indefinido.

### Acceptance 023-A

1. Liveness y readiness tienen semántica distinta y testeada.
2. PostgreSQL crítico bloquea readiness cuando no está disponible.
3. DSpace no bloquea liveness.
4. No existe path de mutación desde health/readiness.

## Slice 023-B — Deployment smoke

### Implementación

- añadir `scripts/production-smoke.sh`;
- timeouts explícitos;
- checks internos y públicos;
- salida PASS/WARN/FAIL estable;
- exit code determinista;
- documentación de uso en Dokploy;
- posibilidad de sobrescribir URLs por variables no secretas para staging/producción.

### Checks mínimos

```text
api /health                mandatory
api /ready                 mandatory
api -> postgres            represented by readiness
network -> web:3000        mandatory
public frontend            mandatory
public api health          mandatory
DSpace contract status     observational/warn unless policy says otherwise
```

### Acceptance 023-B

1. El script detecta frontend interno no alcanzable aunque el contenedor esté `Up`.
2. El script detecta `502/503` públicos.
3. El script devuelve `0` solo cuando los checks obligatorios pasan.
4. Ningún output contiene secretos.
5. Puede ejecutarse manualmente después de un redeploy sin cambiar estado de negocio.

## Slice 023-C — Operational acceptance

Crear evidencia durable, propuesta:

```text
docs/vertical-023-operational-acceptance.md
```

Debe registrar:

- fecha de aceptación;
- commit desplegado;
- URLs verificadas;
- resultado de smoke;
- health/readiness observados;
- conectividad interna relevante;
- estado VERTICAL-022 observado;
- excepciones/warnings aceptados;
- operador/revisor cuando corresponda;
- confirmación de que no hubo mutaciones DSpace ni de gobernanza.

Solo después de esta evidencia el índice canónico puede marcar VERTICAL-023 como `Accepted / Operationalized`.

## Criterios de aceptación global

1. `/health` demuestra vida del proceso y no disponibilidad total del ecosistema.
2. `/ready` falla con `503` cuando una dependencia crítica mínima no está disponible.
3. El frontend es verificable desde la red Docker y desde su URL pública.
4. La API es verificable desde su URL pública.
5. El smoke test es reproducible, versionado, con timeouts y exit codes estables.
6. Un caso equivalente a servidor web vivo pero no alcanzable por `web:3000` produce fallo explícito.
7. Un `Bad Gateway` público se clasifica sin asumir que la aplicación está caída.
8. VERTICAL-022 permanece read-only desde esta superficie.
9. Ningún check imprime secretos.
10. La aceptación operacional queda documentada con evidencia de producción.

## Stop conditions

La implementación debe detenerse y requerir revisión si para cumplir el vertical fuese necesario:

- habilitar escritura DSpace;
- cambiar la política de aprobación VERTICAL-022;
- exponer credenciales;
- añadir auto-repair o auto-redeploy;
- convertir health en una operación con efectos laterales;
- cambiar el contrato catalográfico maestro fuera de un vertical específico;
- aceptar como sano un smoke con checks obligatorios fallidos.

## Definition of Done

VERTICAL-023 está implementado cuando 023-A, 023-B y 023-C cumplen sus criterios, existe evidencia durable de producción y el índice canónico se actualiza explícitamente.

La mera existencia de endpoints de health o de un script de smoke **no** equivale a aceptación operacional.
