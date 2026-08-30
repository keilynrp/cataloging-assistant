# ADR-019: Autorización web acotada para el reporte DSpace

**Estado:** Propuesta.

## Contexto

VERTICAL-025A exige una superficie web mínima para seleccionar un rango y
descargar CSV, XLSX o PDF. ADR-018 permite que el backend use una cuenta DSpace
institucional de solo lectura para observar workspace y workflow, siempre que
las credenciales, cookies y JWT de DSpace permanezcan exclusivamente server-side.

El API FastAPI del reporte ya exige `CATALOG_REVIEW_TOKEN` antes de crear el
cliente DSpace. Sin embargo, la aplicación web no tiene login, identidad ni
sesión de usuario. Un proxy Next.js que inyecte incondicionalmente ese token
anula la frontera FastAPI: cualquier visitante que alcance el web podría hacer
que el servidor se autentique contra DSpace y descargar metadata que DSpace no
entrega anónimamente.

No es correcto resolverlo enviando credenciales DSpace al navegador, dejando el
proxy público, confiando sólo en CORS o suponiendo que la red de despliegue es
privada. Tampoco corresponde introducir en este slice un proveedor de identidad,
roles, usuarios persistentes o autorización general para toda la aplicación.

Esta ADR decide únicamente cómo un operador autorizado desbloquea temporalmente
las descargas web de VERTICAL-025A. No autoriza otras rutas, mutaciones, sesiones
generales ni cambios al lifecycle.

## Decisión

La web puede establecer una autorización efímera y específica del reporte con
un secreto de despliegue nuevo y limitado, `CATALOG_REPORT_ACCESS_TOKEN`. El
mecanismo completo es:

1. La pantalla del reporte muestra inicialmente un formulario de acceso además
   de los controles congelados `from`, `to` y formato.
2. El operador presenta `CATALOG_REPORT_ACCESS_TOKEN` mediante un `POST`
   same-origin sobre TLS a una ruta Next.js dedicada bajo
   `/api/reports/dspace-weekly/access`.
3. La ruta exige un encabezado `Origin` que coincida exactamente con el origen
   web configurado, rechaza cuerpos o tipos inesperados, y compara el valor con
   el secreto server-side usando comparación en tiempo constante. Un fallo
   devuelve un error genérico y no registra el valor recibido.
4. Si la comparación es válida, Next.js emite una cookie de autorización
   firmada y de vida corta. El valor de `CATALOG_REPORT_ACCESS_TOKEN` no se copia
   a la cookie ni a almacenamiento del navegador.
5. Cada proxy de descarga exige Fetch Metadata `Sec-Fetch-Site: same-origin`,
   valida que `Origin` coincida exactamente cuando el navegador lo envía, y
   verifica firma, versión y expiración de la cookie antes de inyectar
   server-side `X-Catalog-Review-Token` hacia FastAPI. Sin todas esas señales
   válidas, no llama a FastAPI ni inicia autenticación DSpace.
6. La cookie y su verificación se aplican sólo a las rutas de VERTICAL-025A. No
   conceden acceso a settings, evidencia, vocabularios, agentes ni otras APIs.

`CATALOG_REPORT_ACCESS_TOKEN` es una capacidad distinta, sólo para desbloquear
VERTICAL-025A. Debe tener al menos 32 bytes aleatorios, no puede ser igual a
`CATALOG_REVIEW_TOKEN`, a una credencial DSpace ni a otro secreto del proyecto, y
no es aceptado por ninguna ruta FastAPI. Puede presentarse transitoriamente para
obtener una sesión de reporte, pero no se expone en bundles, variables
`NEXT_PUBLIC_*`, HTML, URLs, logs, errores, localStorage o sessionStorage.

`CATALOG_REVIEW_TOKEN` permanece exclusivamente server-side. El operador nunca
lo recibe: Next.js sólo lo usa después de validar la cookie para satisfacer el
gate independiente de FastAPI.

## Contrato de la cookie

La cookie debe cumplir simultáneamente:

- `HttpOnly`;
- `SameSite=Strict`;
- `Secure` en producción;
- `Path=/api/reports/dspace-weekly`;
- expiración absoluta máxima de 10 minutos;
- contenido mínimo no sensible: versión, instante de emisión, expiración y nonce;
- firma HMAC-SHA-256 con una clave derivada server-side de
  `CATALOG_REPORT_ACCESS_TOKEN` y una etiqueta de dominio exclusiva de
  VERTICAL-025A;
- validación de firma en tiempo constante antes de interpretar o confiar en el
  contenido;
- rechazo fail-closed de cookie ausente, malformada, expirada o de otra versión.

Las rutas browser-facing de Next.js quedan obligatoriamente bajo ese path y usan
segmentos: `/api/reports/dspace-weekly/access`, `/csv`, `/xlsx` y `/pdf`. Las
rutas FastAPI con sufijo (`/api/reports/dspace-weekly.csv`, `.xlsx`, `.pdf`) son
upstreams server-to-server y nunca son el destino directo del navegador. Por
tanto, el `Path` de la cookie cubre todos los exports web sin ampliarse a otros
reportes.

La cookie es una capacidad temporal de descarga, no una identidad. No contiene
nombre de catalogador, rol, token DSpace, CSRF DSpace, JWT DSpace,
`CATALOG_REPORT_ACCESS_TOKEN` ni `CATALOG_REVIEW_TOKEN`. No se persiste en
PostgreSQL y no introduce una nueva arquitectura de sesiones.

La ruta de acceso y las respuestas de descarga usan `Cache-Control: no-store`.
El formulario usa un campo de tipo `password`, no repuebla el valor después del
submit y no lo conserva en estado durable. El secreto sólo existe durante el
request de acceso y en la configuración server-side ya existente.

## Fronteras de confianza

Después de esta decisión existen tres verificaciones independientes:

1. **Contexto del navegador:** cada descarga debe provenir de una navegación
   same-origin demostrada mediante Fetch Metadata; un origen cross-origin o
   same-site se rechaza incluso si logra provocar el envío de la cookie.
2. **Next.js:** verifica que el caller posee una capacidad web efímera válida
   antes de reenviar la solicitud.
3. **FastAPI:** sigue exigiendo `X-Catalog-Review-Token` antes de crear el cliente
   DSpace.

La cookie nunca sustituye Fetch Metadata ni el gate FastAPI. Next.js es el único
componente que convierte una cookie válida en el header interno; el navegador no
recibe ese header ni llama directamente a DSpace. CORS no se considera una
autorización. Las respuestas incluyen `Vary: Sec-Fetch-Site, Origin` además de
`Cache-Control: no-store`.

Las credenciales `DSPACE_READ_USERNAME` y `DSPACE_READ_PASSWORD`, así como CSRF,
JWT y cookies de DSpace, permanecen server-side conforme a ADR-018. Esta ADR no
amplía la secuencia DSpace autorizada y no permite ninguna operación
catalográfica `POST`, `PUT`, `PATCH` o `DELETE`.

## Alcance y exclusiones

Esta decisión autoriza únicamente:

- el secreto de despliegue `CATALOG_REPORT_ACCESS_TOKEN`;
- el `POST` same-origin que valida ese secreto y emite la cookie;
- Fetch Metadata y la verificación de cookie en las descargas CSV/XLSX/PDF de
  VERTICAL-025A;
- un estado visual mínimo de acceso requerido, acceso inválido y sesión expirada.

Quedan fuera de alcance:

- usuarios, contraseñas o roles persistidos;
- OAuth, OIDC, SAML, LDAP o integración con un IdP;
- autorización por catalogador o generalización multi-catalogador;
- reutilizar la cookie en otras rutas;
- refresh tokens o renovación automática;
- scheduling, dashboards, métricas, LLM o cambios de lifecycle;
- cualquier escritura DSpace.

Si la aplicación deja de ser un piloto de un solo operador de confianza,
`CATALOG_REPORT_ACCESS_TOKEN` debe sustituirse por identidad y autorización
individual antes de ampliar acceso. Esta ADR no sirve como fundamento para esa
evolución.

## Manejo de errores y abuso

- Se exige que `CATALOG_REPORT_ACCESS_TOKEN` tenga al menos 32 bytes aleatorios y
  sea distinto de los demás secretos; también se exige el
  `CATALOG_REVIEW_TOKEN` interno. Una configuración ausente, débil o reutilizada
  hace que la ruta de acceso y el proxy fallen con 503 antes de DSpace.
- Cada descarga exige `Sec-Fetch-Site: same-origin`; `same-site`, `cross-site`,
  `none` o ausencia del encabezado fallan cerrados. Si `Origin` está presente,
  también debe coincidir exactamente con el origen configurado.
- Token incorrecto, cookie inválida y cookie expirada usan respuestas estables y
  no revelan qué parte falló.
- Una solicitud no autorizada nunca llama a FastAPI, nunca abre una sesión DSpace
  y nunca crea una corrida de evidencia raw.
- El cliente no recibe cuerpos de error upstream que puedan contener secretos.
- No se registra el formulario, la cookie completa ni encabezados sensibles.
- Los controles operativos de despliegue pueden limitar frecuencia, pero no se
  sustituyen las verificaciones criptográficas por rate limiting o CORS.

## Evidencia y privacidad

La autorización web no se guarda junto con la evidencia HAL+JSON. Las corridas de
evidencia conservan únicamente los payloads DSpace ya autorizados por ADR-018 y
sus referencias auditables. Cookies, token local, credenciales DSpace, CSRF y JWT
se excluyen explícitamente de raw evidence, reportes y logs.

## Alternativas consideradas

### Proxy Next.js público que inyecta el token

Descartada: convierte una credencial server-side en una capacidad pública y
anula el gate FastAPI.

### Enviar el token en cada descarga desde JavaScript

Descartada: mantiene el secreto en memoria cliente durante toda la interacción,
facilita su reutilización accidental y contradice el patrón server-side existente.

### Conectar el navegador directamente a DSpace

Descartada por ADR-001 y ADR-018: expondría credenciales/protocolo DSpace y
saltaría FastAPI y la preservación raw gobernada.

### Confiar en CORS o en una red supuestamente privada

Descartada: CORS no protege llamadas HTTP directas y la topología de despliegue no
es una identidad verificable por la aplicación.

### Incorporar un proveedor de identidad completo

Descartada para VERTICAL-025A: es una arquitectura transversal de usuarios,
sesiones y roles que excede el reporte semanal. Debe evaluarse mediante otra ADR
si el piloto crece.

### Eliminar la superficie web y conservar sólo FastAPI

Descartada: incumple el contrato funcional congelado de #81.

## Consecuencias

### Positivas

- el proxy deja de ser una vía pública hacia metadata DSpace protegida;
- DSpace y el review token permanecen fuera de bundles y almacenamiento durable
  del navegador;
- no se añaden tablas, dependencias ni un sistema general de identidad;
- la doble frontera Next.js/FastAPI falla cerrada;
- la sesión expira rápidamente y está limitada por path.

### Costos y riesgos

- el operador debe poseer el secreto acotado del reporte;
- durante el `POST` de acceso el secreto transita por el navegador y exige TLS;
- un token compartido no da atribución individual ni revocación por usuario;
- se añade un secreto de despliegue que debe generarse, distribuirse y rotarse;
- comprometer `CATALOG_REPORT_ACCESS_TOKEN` obliga a rotarlo y expira
  implícitamente todas las cookies firmadas con la clave anterior, pero no concede
  acceso a otras APIs protegidas por `CATALOG_REVIEW_TOKEN`;
- esta solución no debe generalizarse a otras capacidades.

## Relación con decisiones existentes

Esta ADR complementa ADR-018 y sustituye, sólo para el formulario de acceso de
VERTICAL-025A, la prohibición general de introducir una credencial nueva en
frontend. Esa credencial queda limitada al reporte y no permite enviar ni aceptar
credenciales DSpace o `CATALOG_REVIEW_TOKEN` desde cliente.

Se preservan:

- ADR-001: el navegador consume la aplicación y nunca DSpace directamente;
- ADR-002: DSpace sigue siendo fuente de verdad;
- ADR-005 y ADR-006: no se añaden acciones catalográficas ni recuperación
  mutable;
- ADR-018: login DSpace efímero, backend-only y estrictamente read-only;
- el contrato visible de siete columnas y todas las reglas de VERTICAL-025.

## Gates de implementación y validación

Ningún código dependiente de esta decisión puede considerarse habilitado hasta
que la ADR figure como Aceptada en `main`.

La implementación debe demostrar mediante tests:

1. `CATALOG_REPORT_ACCESS_TOKEN` ausente, débil, reutilizado o incorrecto no emite
   cookie;
2. comparación del token y de firmas no usa igualdad ingenua;
3. `Origin` ausente o distinto se rechaza al emitir la cookie;
4. cada descarga rechaza Fetch Metadata ausente, `same-site` o `cross-site`, y
   rechaza un `Origin` presente que no coincida;
5. cookie válida contiene sólo claims no sensibles y atributos obligatorios;
6. cookie expirada, alterada, malformada o de versión desconocida se rechaza;
7. una descarga sin autorización no llama a FastAPI ni autentica DSpace;
8. una descarga autorizada inyecta `CATALOG_REVIEW_TOKEN` sólo server-side;
9. CSV, XLSX y PDF usan exactamente el mismo gate;
10. ambos tokens y la cookie no aparecen en HTML, bundles, URLs, logs, outputs ni
    evidencia;
11. el token de acceso al reporte no autoriza ninguna ruta FastAPI y FastAPI
    conserva su gate independiente;
12. no existe tráfico DSpace de escritura y el único POST DSpace continúa siendo
    `/api/authn/login` conforme a ADR-018.

El PR funcional debe rebasarse sobre el commit que acepte esta ADR, resolver el
hallazgo P1 de autorización web y volver a solicitar revisión antes de aprobación
final.
