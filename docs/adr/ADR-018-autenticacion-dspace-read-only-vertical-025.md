# ADR-018: Autenticación DSpace read-only para VERTICAL-025

**Estado:** Propuesta el 28 de agosto de 2026. Debe cambiarse a Aceptada en un
commit revisado antes de habilitar la implementación dependiente.

## Contexto

VERTICAL-025 necesita producir, bajo demanda, un reporte operacional que combine
ítems archivados, workspace items y workflow items. Las dos últimas superficies
pueden no estar disponibles para clientes anónimos en DSpace 7.6.6. La
specification permite reutilizar la autenticación protegida existente y distingue
el login de una escritura catalográfica, pero `AGENTS.md` exige una ADR aprobada
antes de añadir cualquier nueva operación de autenticación DSpace.

El proyecto ya dispone de `ReadAuthenticatedDSpaceClient`, que obtiene CSRF,
ejecuta `POST /api/authn/login`, confirma el JWT y no expone una operación HTTP
genérica ni métodos de escritura. Reutilizar esa abstracción desde el reporte crea,
sin embargo, una nueva ruta de ejecución autenticada y requiere autorización
arquitectónica explícita.

Esta decisión se limita al primer slice de VERTICAL-025A. No autoriza escritura,
scheduling, administración, procesamiento de workflow, edición, publicación ni
autenticación para otras capacidades.

## Decisión

Una vez aceptada esta ADR, el backend puede autenticar una consulta de
VERTICAL-025A con una cuenta DSpace institucional de solo lectura, usando
exclusivamente esta secuencia:

1. `GET /api/authn/status` para obtener el token CSRF;
2. `POST /api/authn/login` con las credenciales server-side ya configuradas;
3. validación obligatoria de la respuesta, del encabezado `Authorization` y de un
   segundo `GET /api/authn/status` que confirme `authenticated == true`;
4. consultas GET limitadas a las superficies read-only necesarias para el reporte:
   - `/api/core/items`;
   - `/api/submission/workspaceitems`;
   - `/api/workflow/workflowitems`;
   - `/api/submission/workspaceitems/{id}/item`;
   - `/api/workflow/workflowitems/{id}/item`.

La autorización es estrecha:

- aplica únicamente a una generación de reporte solicitada bajo demanda;
- reutiliza `DSPACE_READ_USERNAME` y `DSPACE_READ_PASSWORD`; no crea un segundo
  almacén de secretos ni acepta credenciales desde navegador o parámetros HTTP;
- exige que la cuenta DSpace tenga únicamente los privilegios de lectura mínimos
  sobre las superficies requeridas y carezca de permisos para ejecutar o modificar
  submission, workflow, administración o contenido catalográfico;
- mantiene JWT y cookies sólo en memoria durante la vida del cliente efímero; la
  contraseña permanece como secreto server-side de despliegue y sólo se entrega al
  cuerpo del login, sin copiarse al reporte ni a persistencia de aplicación;
- no registra ni persiste contraseña, CSRF, cookies, JWT ni encabezados de
  autorización;
- no permite construir destinos DSpace desde entrada del usuario;
- no añade métodos DSpace `POST`, `PUT`, `PATCH` o `DELETE` distintos del login
  exacto anterior;
- conserva una API de cliente con métodos GET explícitos y sin transporte genérico
  accesible a la capa del reporte.

El login autentica la lectura; no constituye autorización para mutar un recurso
catalográfico. Si la instancia exigiera una operación de submission, workflow,
administración o escritura para obtener el reporte, la implementación debe fallar
cerrada y requerir otra decisión gobernada.

## Integridad, errores y evidencia raw

DSpace continúa siendo la fuente de verdad. Toda respuesta HAL+JSON utilizada para
producir una fila debe persistirse de forma inmutable antes de normalizarla, con
referencias suficientes para reconstruir la fila, sin material de autenticación.

La resolución del Item asociado adopta estas reglas:

- un 404 del enlace de Item puede activar únicamente el fallback de metadata que
  VERTICAL-025 permite y que esté presente en el payload raw del contenedor;
- timeout, 401, 403, 429, 5xx, red, JSON inválido, HAL inválido o cualquier otro
  error interrumpe la generación completa;
- una generación interrumpida no entrega CSV, XLSX ni PDF y no puede marcar su run
  de evidencia como completo;
- los errores externos se devuelven con códigos estables y sin incluir secretos ni
  cuerpos sensibles.

Estas reglas impiden que una indisponibilidad o fallo de integridad se convierta en
un reporte exitoso pero incompleto.

## Frontera con sincronización y lifecycle

La captura de VERTICAL-025A es una observación inmutable, acotada a una solicitud
de reporte. No actualiza el índice canónico, no materializa snapshots de contrato,
no promueve estados de lifecycle y no sustituye las sincronizaciones gobernadas
por VERTICAL-001 o VERTICAL-022.

Una solicitud completa crea una sola corrida de evidencia. Si falla después de
persistir una o más páginas:

- la corrida conserva estado `INTERRUPTED` o `FAILED` para auditoría;
- no produce un archivo parcial;
- un reintento explícito crea una observación nueva desde la primera página;
- páginas de corridas distintas no se mezclan, porque representarían instantes de
  observación distintos;
- la corrida parcial nunca se reutiliza como fuente de una descarga exitosa.

Por tanto, esta ADR no modifica la semántica incremental, idempotente y resumable
de los jobs de sincronización. Tampoco introduce resumibilidad, scheduling ni un
nuevo estado de lifecycle para el reporte.

## Relación con decisiones existentes

Esta ADR sustituye la prohibición general de `AGENTS.md` **sólo** para el
`POST /api/authn/login` efímero y server-side descrito aquí, ejecutado como parte de
VERTICAL-025A después de su aceptación.

Se preservan:

- ADR-001: el navegador consume FastAPI y nunca se conecta directamente a DSpace;
- ADR-002: DSpace sigue siendo fuente de verdad y PostgreSQL continúa siendo
  derivado y reconstruible;
- ADR-004: no cambia la sincronización canónica mediante Discover;
- ADR-005 y ADR-006: no se añaden acciones catalográficas ni herramientas mutables;
- ADR-012 y ADR-013: no se alteran bindings, reglas catalográficas ni el contrato
  maestro;
- VERTICAL-022, VERTICAL-023 y VERTICAL-024: no se aprueban snapshots ni se cambia
  readiness, recovery o auto-healing.

La decisión no autoriza autenticación DSpace para ninguna otra ruta, worker,
agente, script o integración.

## Consecuencias

### Positivas

- el reporte puede observar workspace y workflow sin exponer credenciales al
  frontend;
- la superficie mutable queda reducida al protocolo de login requerido por
  DSpace;
- los fallos de disponibilidad o integridad producen fallo cerrado;
- la evidencia raw permanece auditable sin guardar secretos;
- los límites entre reporte, sincronización e índice canónico quedan explícitos.

### Costos y riesgos

- cada descarga abre una sesión autenticada efímera contra DSpace;
- la operación depende de la disponibilidad del servicio de autenticación;
- el despliegue debe administrar y revisar periódicamente una cuenta de mínimo
  privilegio;
- cambios futuros del protocolo CSRF/JWT requerirán revisión y pruebas;
- un endpoint bajo demanda puede ser invocado repetidamente, por lo que los
  controles operativos de FastAPI deben evitar abuso sin convertirlo en scheduler.

## Alternativas consideradas

### Consultar únicamente superficies públicas

Descartada: no garantiza workspace/workflow y puede producir un reporte incompleto
que aparenta éxito.

### Leer sólo el índice local existente

Descartada para VERTICAL-025A: el índice canónico actual no garantiza una
observación contemporánea de todas las superficies requeridas. Esta alternativa
podrá reconsiderarse si una sincronización aprobada incorpora esas superficies y
sus referencias raw.

### Autorizar un cliente DSpace autenticado genérico

Descartada: ampliaría innecesariamente la superficie de confianza y permitiría que
otras capacidades heredaran autenticación sin decisión propia.

### Reanudar y combinar corridas parciales

Descartada en este slice: mezcla instantes de observación y exige semántica nueva de
lifecycle. El reporte falla cerrado y un reintento crea una corrida independiente.

## Gates de implementación y validación

Ningún código dependiente de esta decisión puede considerarse habilitado hasta que
la ADR figure como Aceptada en `main`.

La implementación posterior debe demostrar mediante tests sin acceso a la instancia
real:

1. secuencia CSRF/login/confirmación y ausencia de cualquier otra mutación;
2. cero tráfico de autenticación cuando faltan credenciales;
3. fallo cerrado ante autenticación incompleta o rechazada;
4. fallback únicamente ante 404 del Item asociado;
5. propagación de errores no-404 y ausencia de archivos parciales;
6. persistencia raw antes de normalizar y exclusión de secretos;
7. misma salida determinista para el mismo conjunto de fixtures y periodo;
8. inventario explícito de métodos DSpace read-only usados por el reporte.

El PR de implementación debe rebasarse sobre el commit que acepte esta ADR, citarlo
y resolver los hallazgos de revisión antes de solicitar aprobación final.
