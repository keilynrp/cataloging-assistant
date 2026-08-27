# VERTICAL-024: Operational Recovery & Restart Hardening

## Resultado observable

Después de un reinicio controlado del daemon Docker —y, cuando sea viable, después de un reinicio del host— el stack de Cataloging Assistant recupera automáticamente su estado operativo esperado sin requerir un `docker compose up`, restart manual de contenedores ni mutación ad hoc de configuración.

La recuperación debe demostrar, en este orden lógico:

```text
container recovery
  -> PostgreSQL healthy
  -> API live
  -> API ready
  -> web internally reachable
  -> public frontend/API reachable
  -> governed production smoke PASS
  -> durable operational evidence
```

La recuperación automática de infraestructura **no** modifica DSpace, VERTICAL-022, semántica catalográfica ni criterios de readiness.

## Objetivo

Cerrar el riesgo residual identificado durante VERTICAL-023-C: los contenedores `api`, `web` y `postgres` tenían `restart=no` y permanecieron detenidos tras un reinicio del daemon Docker, aunque el código desplegado y los servicios eran funcionales una vez restaurados manualmente.

VERTICAL-024 debe convertir la recuperación tras reinicio en una propiedad explícita, versionada, verificable y gobernada del despliegue.

## Motivación inmediata

Durante la aceptación de VERTICAL-023 se observó en producción:

```text
api      restart=no
web      restart=no
postgres restart=no
```

Los tres contenedores terminaron al mismo tiempo que el daemon Docker se reinició y no volvieron a levantarse automáticamente.

Traefik permaneció operativo. Como consecuencia, las rutas públicas dejaron de servir la aplicación hasta que el stack fue restaurado manualmente.

Después de la recuperación manual, VERTICAL-023 pasó completamente:

```text
PASS compose_services
PASS api_liveness
PASS api_readiness
PASS web_internal
PASS public_frontend
PASS public_api
WARN dspace_contract SYNCED
RESULT PASS
SMOKE_EXIT=0
```

Por tanto, el problema no fue de salud de aplicación, readiness ni contrato DSpace. Fue una brecha en la política de recuperación del deployment.

## Relación con VERTICAL-023

VERTICAL-023 sigue siendo la autoridad para:

- semántica de `/health`;
- semántica de `/ready`;
- checks internos/públicos;
- `scripts/production-smoke.sh`;
- clasificación operacional de PASS/WARN/FAIL;
- aceptación basada en evidencia.

VERTICAL-024 no redefine esas superficies. Las utiliza como pruebas posteriores a la recuperación.

Invariante:

> Una política de restart puede reiniciar procesos de infraestructura, pero nunca puede convertir un servicio no-ready en ready ni alterar los criterios de VERTICAL-023 para ocultar un fallo persistente.

## Relación con VERTICAL-022 y DSpace

VERTICAL-022 permanece como única autoridad para:

- snapshots DSpace;
- baseline `ACTIVE`;
- drift;
- resolución de evidencia;
- aprobación/promoción humana.

La recuperación de VERTICAL-024 puede observar el estado DSpace de forma read-only mediante las superficies ya gobernadas.

Nunca puede:

- escribir en DSpace;
- aprobar;
- resolver evidencia;
- promover;
- superseder;
- crear snapshots;
- cambiar el baseline `ACTIVE`.

## Principio de arquitectura

```text
host / docker restart
  -> container restart policy
  -> postgres process start
  -> postgres healthcheck
  -> api process start / migration gate
  -> api readiness
  -> web process start
  -> internal reachability
  -> public routing
  -> production smoke
  -> human acceptance
```

Nunca:

```text
persistent application failure
  -> infinite opaque restart loop
  -> readiness bypass
  -> hidden outage
```

Ni:

```text
infrastructure restart
  -> DSpace mutation
  -> VERTICAL-022 baseline promotion
```

## Superficie de configuración autoritativa

La política efectiva de recuperación debe quedar explícita y versionada en el contrato de despliegue administrado por el repositorio o en una configuración Dokploy equivalente que sea:

- reproducible;
- auditable;
- revisable por PR o evidencia durable equivalente;
- observable en runtime.

La implementación debe determinar cuál de estas alternativas es autoritativa:

1. Compose `restart: unless-stopped`;
2. Compose `restart: always`;
3. una política equivalente administrada por Dokploy;
4. otra estrategia explícita compatible con Docker/Dokploy.

La selección no debe hacerse por conveniencia. Debe documentar semántica, trade-offs y comportamiento ante:

- reinicio del daemon Docker;
- reinicio del host;
- parada manual intencional;
- fallo persistente del proceso;
- dependencia crítica no disponible.

## Política funcional esperada

La implementación elegida debe cumplir estas propiedades:

### PostgreSQL

- debe recuperar automáticamente el proceso tras restart del daemon/host;
- debe conservar el volumen persistente existente;
- debe volver a estado `healthy`;
- no debe inicializar una base vacía por pérdida de volumen;
- su disponibilidad sigue gobernando readiness de API.

### API

- debe recuperar automáticamente el proceso;
- debe esperar las dependencias necesarias conforme al contrato Compose/runtime existente;
- debe mantener `/health` como liveness;
- debe mantener `/ready` como readiness con PostgreSQL crítico;
- si PostgreSQL no está disponible, debe permanecer observable como no-ready en vez de simular disponibilidad.

### Web

- debe recuperar automáticamente el proceso;
- debe conservar `HOSTNAME=0.0.0.0` y `PORT=3000` mientras ese contrato siga vigente;
- debe volver a ser alcanzable desde la red Docker;
- el routing público debe restablecerse sin intervención manual sobre Traefik.

## Restart policy vs readiness

La política de restart y readiness resuelven problemas distintos.

Restart policy responde:

> ¿Debe Docker intentar volver a ejecutar este contenedor después de un evento de daemon/host o terminación del proceso?

Readiness responde:

> ¿Puede este servicio aceptar tráfico útil ahora mismo?

VERTICAL-024 no puede usar restart policy para sustituir readiness.

Un contenedor puede estar:

```text
running + NOT_READY
```

y eso debe seguir siendo visible.

## Fallos persistentes y restart loops

La implementación debe evitar una arquitectura en la que el restart automático oculte fallos persistentes.

Como mínimo, la aceptación debe comprobar que:

- un servicio que no alcanza readiness sigue siendo detectable;
- el smoke termina en `FAIL` si los checks obligatorios fallan;
- no se reescribe configuración automáticamente;
- no se cambia la política de criticidad para forzar un PASS;
- los reinicios pueden observarse mediante estado/logs normales del runtime.

No se requiere introducir una plataforma de alerting en este vertical.

## Recuperación tras reinicio del daemon Docker

Este es el caso obligatorio de aceptación.

La prueba gobernada debe:

1. partir de una producción sana;
2. registrar commit desplegado;
3. registrar estado inicial de contenedores;
4. ejecutar un reinicio controlado del daemon Docker;
5. no ejecutar `docker compose up`, `docker restart` ni equivalente manual sobre Catalog Assistant después del restart;
6. esperar una ventana acotada de recuperación;
7. comprobar `postgres healthy`;
8. comprobar API `/health`;
9. comprobar API `/ready`;
10. comprobar `web:3000` desde otro contexto de red Compose;
11. comprobar frontend/API públicos;
12. ejecutar `scripts/production-smoke.sh`;
13. registrar `RESULT PASS` y exit `0`;
14. observar VERTICAL-022 read-only;
15. registrar evidencia durable.

## Recuperación tras reinicio del host

Es objetivo secundario pero deseable.

Debe ejecutarse solo si:

- el entorno permite un reboot gobernado;
- existe acceso operacional suficiente para recuperar la sesión;
- no compromete otros servicios compartidos del VPS;
- el riesgo es aceptado explícitamente antes de la prueba.

Si no es viable, la aceptación puede dejarlo como `NOT TESTED` sin bloquear VERTICAL-024, siempre que el reinicio del daemon Docker esté completamente validado.

No debe declararse host-reboot recovery como probada sin evidencia real.

## Tiempo de recuperación

VERTICAL-024 debe usar timeouts acotados.

La especificación no fija aún un SLO estricto de segundos, pero la implementación debe:

- definir una ventana máxima de espera para cada paso;
- evitar loops infinitos;
- producir fallo explícito cuando la recuperación no ocurre;
- registrar tiempos observados cuando sea razonable.

Un SLO formal de disponibilidad/recovery time puede quedar para un vertical posterior.

## Estado operacional esperado durante recuperación

Transiciones válidas:

```text
STOPPED
  -> STARTING
  -> LIVE
  -> NOT_READY
  -> READY
```

o, si dependencias están disponibles rápidamente:

```text
STOPPED
  -> STARTING
  -> READY
```

No se exige exponer estos nombres como nueva API. Son un modelo operacional para la evidencia.

Un fallo persistente debe permanecer detectable como:

```text
NOT_READY
```

o como fallo del smoke, según corresponda.

## Alcance

Incluye:

- política de restart/recovery para `postgres`, `api` y `web`;
- configuración versionada o gobernada equivalente;
- compatibilidad con Dokploy/Compose;
- recuperación automática tras restart del daemon Docker;
- verificación de persistencia PostgreSQL;
- reutilización del smoke de VERTICAL-023;
- documentación de operación;
- tests estáticos/configuracionales cuando apliquen;
- evidencia de aceptación productiva.

## Fuera de alcance

No incluye:

- Kubernetes;
- migración a Swarm como requisito;
- nueva plataforma de orchestration;
- auto-scaling;
- failover multi-host;
- alta disponibilidad PostgreSQL;
- backups/restore;
- Prometheus/Grafana obligatorios;
- alerting complejo;
- auto-redeploy por health check;
- modificación automática de variables Dokploy;
- cambios semánticos a `/health` o `/ready`;
- cambios a `scripts/production-smoke.sh` salvo defecto independiente descubierto;
- DSpace writes;
- mutación VERTICAL-022;
- cambios a los 56 bindings;
- cambios catalográficos;
- refactor amplio de Traefik o dominios.

## Invariantes de seguridad y gobernanza

1. Recovery policy no escribe en DSpace.
2. Recovery policy no muta VERTICAL-022.
3. Readiness conserva la semántica aceptada en VERTICAL-023.
4. Liveness conserva la semántica aceptada en VERTICAL-023.
5. PostgreSQL conserva su volumen persistente.
6. Ninguna prueba imprime secretos.
7. TLS permanece verificado.
8. No se ejecuta auto-repair de configuración.
9. Un servicio persistemente no-ready no se clasifica como sano.
10. El smoke sigue siendo la verificación final de disponibilidad.
11. La aceptación requiere evidencia de producción real.
12. Una parada manual intencional no debe convertirse en un comportamiento sorprendente sin documentar la semántica exacta de la política elegida.

## Evidencia mínima de implementación

Antes de producción, el PR de implementación debe demostrar:

- política efectiva configurada para cada servicio;
- diff limitado;
- validación sintáctica del Compose/configuración;
- tests automatizados o assertions estructurales que eviten regresar a `restart=no`;
- ausencia de cambios en health/readiness, DSpace y semántica catalográfica;
- explicación de comportamiento ante parada manual y restart de daemon.

## Slice 024-A — Recovery policy contract

Objetivo:

- seleccionar la política exacta;
- documentar semántica;
- definir archivos autoritativos;
- definir interacción con Dokploy;
- definir cómo se valida sin producción.

Acceptance 024-A:

1. política elegida y justificada;
2. alcance por servicio explícito;
3. comportamiento ante daemon restart documentado;
4. comportamiento ante parada manual documentado;
5. no se modifica runtime de aplicación.

## Slice 024-B — Deployment hardening

Implementación esperada:

- aplicar la política aprobada;
- añadir tests/config assertions;
- no alterar checks VERTICAL-023;
- no modificar DSpace;
- no introducir auto-repair.

Acceptance 024-B:

1. diff limitado al deployment hardening y tests/documentación necesarios;
2. configuración válida;
3. tests pasan;
4. no hay scope creep;
5. política efectiva observable en los contenedores desplegados.

## Slice 024-C — Recovery acceptance

Crear evidencia durable, propuesta:

`docs/vertical-024-operational-acceptance.md`

Debe registrar:

- fecha/hora/timezone;
- commit desplegado;
- política efectiva observada;
- estado pre-restart;
- evento controlado de Docker restart;
- estado post-restart;
- evidencia de `postgres healthy`;
- `/health`;
- `/ready`;
- web interno;
- frontend/API públicos;
- smoke completo;
- exit code;
- VERTICAL-022 observado;
- confirmación de no mutación;
- confirmación de no intervención manual para levantar el stack;
- incidentes/warnings;
- host reboot probado o `NOT TESTED`;
- decisión humana.

Solo después de esa evidencia puede el índice marcar VERTICAL-024 como `Accepted / Operationalized`.

## Criterios de aceptación global

1. La política de restart es explícita y versionada/gobernada.
2. `postgres`, `api` y `web` recuperan automáticamente después de un restart controlado del daemon Docker.
3. No se requiere `docker compose up`, `docker restart` ni intervención equivalente después del evento.
4. PostgreSQL recupera `healthy` conservando datos/volumen.
5. `/health` devuelve `200 LIVE` tras recuperación.
6. `/ready` devuelve `200 READY` con `DATABASE_OK`.
7. El frontend es alcanzable desde la red Compose.
8. Frontend y API públicos pasan.
9. El smoke devuelve `RESULT PASS` y exit `0`.
10. VERTICAL-022 se observa read-only.
11. No hay writes DSpace ni mutación de gobernanza.
12. La evidencia queda durable en el repositorio.

## Stop conditions

Detener implementación o aceptación si:

- para recuperar el stack se requiere modificar health/readiness;
- se requiere escribir en DSpace;
- se requiere mutar VERTICAL-022;
- se pierde o sustituye el volumen PostgreSQL;
- aparecen restart loops que ocultan un fallo persistente;
- se necesita una refactorización amplia de deployment no prevista;
- el smoke obligatorio falla;
- la recuperación requiere intervención manual después del evento de aceptación;
- se exponen secretos;
- TLS tendría que deshabilitarse;
- el commit desplegado no puede identificarse;
- la evidencia de producción es incompleta.

## Definition of Done

VERTICAL-024 está implementado cuando:

1. 024-A define y aprueba la política;
2. 024-B aplica el hardening con tests;
3. 024-C demuestra recuperación real tras restart de Docker;
4. el stack vuelve a estado READY y públicamente alcanzable sin intervención manual;
5. el smoke gobernado pasa;
6. no hay mutaciones DSpace/VERTICAL-022;
7. existe evidencia durable;
8. el índice canónico cambia explícitamente a `Accepted / Operationalized`.

La existencia de una directiva `restart:` por sí sola **no** equivale a aceptación operacional.
