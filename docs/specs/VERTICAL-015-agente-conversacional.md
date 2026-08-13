# VERTICAL-015 — Agente conversacional de asistencia catalográfica

**Estado:** ADR-010 aceptada; backlog P0 (AGT-001 a AGT-006) y P1
(AGT-007 a AGT-009) autorizados e implementados el 12 de agosto de 2026.

## Resultado observable

Un catalogador autenticado abre una interfaz de chat y pregunta, en lenguaje
natural, sobre la colección piloto ("¿qué ítems tienen hallazgos de vocabulario
sin resolver en la rama Tarasca?", "¿hay sugerencias pendientes para el ítem
X?", "¿cuál es la cobertura de `dc.description.registeredLanguage`?"). El
agente responde citando evidencia obtenida exclusivamente mediante las
herramientas internas ya construidas (búsqueda, diagnóstico, similitud,
perfil, cola de trabajo, vocabularios, sugerencias), con enlaces a las fichas
correspondientes. La conversación persiste en PostgreSQL y puede retomarse.

## Alcance inicial

Incluye:

- chat de una sola colección (la piloto), con historial persistente;
- herramientas de solo lectura sobre servicios ya existentes (ver catálogo);
- citas de evidencia verificables (enlaces a `/items/{uuid}`, `/work-queue`,
  `/catalog-profile`, `/controlled-terms`) en cada respuesta;
- streaming de la respuesta (Server-Sent Events);
- límites de costo: token de autorización, tope de mensajes por conversación,
  tope de llamadas a herramientas por turno.

No incluye:

- ninguna escritura en DSpace, bajo ninguna circunstancia;
- generación de sugerencias, borradores o decisiones de revisión por el
  agente — sigue exigiéndose acción humana explícita en los mecanismos ya
  construidos (ADR-005);
- identidad institucional, múltiples colecciones, memoria entre
  conversaciones distintas, ejecución de código o acceso a archivos/bash;
- voz, canales externos (correo, Slack) o notificaciones proactivas del
  agente — reutiliza el canal de notificaciones existente (VERTICAL-014) sólo
  si una futura vertical lo conecta explícitamente, no en este alcance.

## Principios

1. El agente sólo puede leer; nunca escribe en DSpace ni en los datos
   normalizados de este repositorio (ADR-002, ADR-005).
2. Toda afirmación factual debe originarse en un resultado de herramienta
   dentro del mismo turno — no en conocimiento previo del modelo sobre la
   colección.
3. La integración con el proveedor del modelo vive aislada en
   `cataloging_api/agent/`; ningún otro módulo importa el SDK del proveedor
   (ADR-006, ADR-010).
4. Una sugerencia, hallazgo o borrador mencionado por el agente se resuelve
   por un humano en la ficha correspondiente — el agente enlaza, no decide.
5. Cada mensaje del agente conserva las llamadas a herramientas que lo
   sustentan, para auditoría y para que el catalogador pueda verificar la
   evidencia.
6. Sin datos personales de DSpace más allá de lo que ya exponen las
   herramientas existentes; sin secretos (tokens, claves) en el historial de
   conversación.

## Catálogo de herramientas P0

Todas son envoltorios de servicios ya implementados; ninguna requiere lógica
de dominio nueva.

| Herramienta | Envuelve | Uso típico |
| --- | --- | --- |
| `search_items` | `GET /api/items` | Buscar ítems por texto o campos lingüísticos |
| `get_item` | `GET /api/items/{uuid}` | Detalle, metadatos, diagnóstico y borradores de un ítem |
| `get_similar_items` | `GET /api/items/{uuid}/similar` | Vecinos estructuralmente similares |
| `get_item_metadata_validation` | `GET /api/items/{uuid}/metadata-validation` | Validación literal contra vocabularios activos |
| `get_suggestion_history` | `GET /api/items/{uuid}/suggestion-history` | Sugerencias e historial de decisiones de un ítem |
| `get_work_queue` | `GET /api/work-queue` | Priorización operativa con filtros |
| `get_catalog_profile` | `GET /api/catalog-profile` | Cobertura, valores frecuentes, relaciones |
| `get_controlled_vocabularies` | `GET /api/controlled-vocabularies` | Vocabularios locales activos (e historial) |
| `get_sync_status` | `GET /api/sync-runs/latest` | Frescura de la última sincronización |

Cada herramienta reutiliza la función de servicio existente directamente
(sin pasar por HTTP interno) para evitar una vuelta de red redundante dentro
del mismo proceso.

## Modelo de datos mínimo

### agent_conversations

- `conversation_id UUID PK`
- `collection_uuid UUID`
- `started_by VARCHAR(120)`, autodeclarado como en revisión humana
- `started_at TIMESTAMPTZ`
- `status VARCHAR(20)`, `open` | `archived`

### agent_messages

Append-only, igual que las decisiones de revisión y borrador:

- `message_id UUID PK`
- `conversation_id UUID FK`
- `role VARCHAR(20)`, `user` | `assistant`
- `content TEXT`
- `tool_calls JSONB`, lista de `{tool, input, summary}` que sustentan la
  respuesta cuando `role = assistant`
- `citations JSONB`, lista de `{label, target_path}` derivada de `tool_calls`
- `model VARCHAR(64)` NULL para mensajes de usuario
- `usage JSONB` NULL para mensajes de usuario — tokens de entrada/salida
- `created_at TIMESTAMPTZ`

## Identidad y autorización

Igual que el resto de las mutaciones de este repositorio: crear una
conversación o enviar un mensaje exige `CATALOG_REVIEW_TOKEN`, porque cada
mensaje tiene costo real de API (a diferencia de las lecturas HTTP
existentes). `started_by` es autodeclarado, como el revisor humano en
hallazgos y borradores. No hay sesión de usuario distinta — mismo modelo que
el resto del piloto.

## Contratos HTTP

- `POST /api/agent/conversations` — `{started_by}` → conversación vacía.
- `GET /api/agent/conversations/{id}` — conversación con su historial de
  mensajes, para recargar o continuar.
- `POST /api/agent/conversations/{id}/messages` — `{content}`, exige el
  token; responde con un flujo SSE.

Eventos SSE, en orden dentro de un turno:

```
event: tool_call
data: {"tool": "get_work_queue", "input": {"severity": "warning"}}

event: text_delta
data: {"text": "Hay 4 ítems con hallazgos de vocabulario sin resolver"}

event: done
data: {"message_id": "uuid", "citations": [{"label": "Ítem X", "target_path": "/items/{uuid}"}]}
```

`error` reemplaza a `done` si la llamada al proveedor falla; el mensaje de
usuario ya quedó guardado, así que la conversación no se pierde.

## Flujo y consistencia

1. El mensaje del usuario se guarda antes de llamar al proveedor.
2. El bucle de herramientas corre dentro de `cataloging_api/agent/`: el
   modelo pide una herramienta, el módulo la ejecuta contra el servicio
   correspondiente, el resultado vuelve al modelo — sin bash, sin archivos,
   sin acceso a red fuera de las herramientas declaradas.
3. Tope de llamadas a herramientas por turno (a definir en la
   implementación, orientativamente 6) para acotar costo y evitar bucles.
4. Al terminar, el mensaje del agente se guarda con sus `tool_calls` y
   `citations` en la misma transacción que cierra el turno.
5. Un fallo del proveedor tras el guardado del mensaje de usuario dueño dejar
   la conversación reanudable — no hay estado a medio camino que corregir.

## UX

- Página de chat con historial de la conversación activa.
- Cada respuesta del agente muestra sus citas como enlaces a la ficha,
  cola de trabajo, perfil o vocabularios correspondientes.
- Indicador de "consultando herramienta" mientras el turno está en curso
  (aprovecha el evento `tool_call` del flujo).
- El agente nunca ofrece botones de aprobar/rechazar/aplicar — toda acción
  humana ocurre en las páginas ya existentes, a las que el agente enlaza.

## Seguridad, privacidad y retención propuesta

- Autorización con `CATALOG_REVIEW_TOKEN` en cada creación de conversación y
  envío de mensaje.
- La clave de API del proveedor vive sólo en el proceso de la API, nunca
  llega al navegador ni a `NEXT_PUBLIC_*`.
- El historial de conversación no contiene tokens, credenciales de DSpace ni
  secretos — validar antes de persistir.
- Tope de mensajes por conversación y de llamadas a herramientas por turno,
  para acotar costo y superficie de abuso.
- Retención alineada con las entregas de notificaciones (90 días) salvo que
  el referente catalográfico pida otra cosa — a confirmar en la
  implementación.

## Observabilidad

Métricas: mensajes por conversación, llamadas a herramientas por tipo,
tokens de entrada/salida acumulados, latencia de la primera porción de
respuesta, tasa de error del proveedor. Registrar `conversation_id`,
`message_id` y las herramientas invocadas, sin contenido sensible en logs
estructurados.

## Pruebas

- unitarias del módulo `agent/`: construcción de herramientas, límite de
  llamadas por turno, mapeo de resultados a citas;
- integración: cada herramienta contra su servicio real con fixtures,
  persistencia de conversación y mensajes, idempotencia de guardado tras
  fallo del proveedor;
- contrato HTTP y del flujo SSE (orden de eventos, `error` sin `done`);
- autorización (mensaje sin token, mensaje con token inválido);
- ausencia explícita de cualquier llamada de escritura a DSpace o a los
  endpoints de mutación de este repositorio.

La suite no dependerá de una clave de API real del proveedor — las pruebas
de herramientas usan los servicios directamente; sólo un smoke test manual,
fuera de CI, ejercita el proveedor real.

## Criterios de aceptación

1. Toda afirmación factual en una respuesta del agente tiene una llamada a
   herramienta que la sustenta, visible en `tool_calls`.
2. El agente nunca invoca un endpoint de escritura, directa ni
   indirectamente.
3. Una conversación sobrevive un fallo del proveedor sin perder el mensaje
   del usuario.
4. Enviar un mensaje sin `CATALOG_REVIEW_TOKEN` válido falla con 401/503,
   igual que el resto de las mutaciones.
5. El módulo `agent/` es el único punto del repositorio que importa el SDK
   del proveedor.

## Backlog

### P0

- AGT-001 (S): ADR-010 aprobada, catálogo de herramientas aprobado.
- AGT-002 (M): migración de `agent_conversations` y `agent_messages`.
- AGT-003 (M): módulo `agent/` — envoltorios de herramientas, bucle con tope
  de llamadas, construcción de citas.
- AGT-004 (M): contratos HTTP y flujo SSE.
- AGT-005 (M): interfaz de chat en Next.js.
- AGT-006 (M): pruebas, seguridad, límites de costo y verificación
  end-to-end.

### P1

- AGT-007 (S): listar y retomar conversaciones anteriores.
- AGT-008 (S): métricas operativas del agente (tokens, latencia, errores).
- AGT-009 (M): citar evidencia de perfil/relaciones con más detalle
  (fragmentos de la tabla, no sólo el enlace).

### P2

Generación de sugerencias asistida por el agente (requeriría una ADR que
supere ADR-005 en sus condiciones, no en su principio), múltiples
colecciones, memoria entre conversaciones.

## Puerta de implementación

El usuario aprobó ADR-010 y autorizó iniciar el backlog P0 el 12 de agosto
de 2026.

El backlog P0 (AGT-001 a AGT-006) quedó implementado el mismo día: migración
`0015_agent_conversations`, módulo `cataloging_api/agent/` (9 herramientas
sobre servicios existentes, bucle manual de tool-use con tope de llamadas,
`AgentProvider` como único punto que importa el SDK del proveedor),
contratos HTTP y SSE, y la interfaz de chat en `/asistente`. Verificado en
vivo contra la API real: creación de conversación, detalle y degradación a
`503` en el envío de mensajes cuando `ANTHROPIC_API_KEY` no está configurada
(no hay clave real en este entorno). El bucle de herramientas y la
supervivencia ante fallos del proveedor están cubiertos por pruebas de
integración con un proveedor simulado, sin depender de una clave real.

El mismo día, ADR-011 reemplazó `ANTHROPIC_API_KEY` por credenciales
cifradas gestionables en `/settings`, con `AgentProvider` sustituido por el
contrato `agent/providers/` (Anthropic y OpenAI reales detrás de la misma
interfaz).

El usuario autorizó el backlog P1 (AGT-007 a AGT-009) el 12 de agosto de
2026, aclarando explícitamente que la verificación en vivo contra un
proveedor real queda pendiente hasta contar con una API key — se aceptó ese
riesgo residual conscientemente. P1 quedó implementado el mismo día:

- AGT-007: `GET /api/agent/conversations` (con conteo de mensajes y última
  actividad, vía `list_conversations`) y una sección de "Conversaciones
  recientes" en `/asistente` para retomarlas.
- AGT-008: migración `0017_agent_turn_observability` — `latency_ms` en
  `agent_messages` (tiempo hasta el primer fragmento del proveedor) y la
  tabla append-only `agent_turn_errors` (un turno fallido nunca se convierte
  en `AgentMessage`, así que necesita su propio registro). `agent/metrics.py`
  agrega mensajes por conversación, llamadas a herramientas por tipo,
  tokens acumulados, latencia promedio y tasa de error, expuesto en
  `GET /api/agent/metrics` y en un panel de `/asistente`.
- AGT-009: `_profile_citations` en `agent/tools.py` enriquece las citas de
  `get_catalog_profile` con fragmentos de datos (cobertura, valor más
  frecuente, par principal de una relación), no sólo el enlace a
  `/catalog-profile`.

Verificado con 91 pruebas backend (unitarias e integración, incluyendo las
nuevas de latencia, persistencia de errores de turno, orden de
conversaciones recientes, agregación de métricas y enriquecimiento de
citas), `ruff` limpio, build de Next.js sin errores de tipos, y smoke test
en vivo contra la API real (creación de conversación, listado, métricas,
limpieza de los datos de prueba) — todo sin depender de una clave de
proveedor real, como en P0.
