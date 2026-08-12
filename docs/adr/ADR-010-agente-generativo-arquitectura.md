# ADR-010: Agente generativo — proveedor y arquitectura

**Estado:** Aceptada el 12 de agosto de 2026. Ver VERTICAL-015 para el
backlog de implementación, cuya puerta P0 el usuario autorizó el mismo día.

## Contexto

El nombre completo del proyecto es *Agente de Asistencia Catalográfica*. Hasta
ahora se construyó únicamente la capa determinista de evidencia y herramientas
(sincronización, diagnóstico, similitud, perfil, cola de trabajo, vocabularios,
notificaciones) que ADR-006 anticipó como lo único que el futuro agente podrá
consultar. Con esa base ya construida, corresponde definir cómo se conecta un
modelo generativo a esas herramientas sin violar ADR-005 (humano en el
circuito) ni ADR-006 (recuperación restringida y desacoplada del proveedor).

## Decisión propuesta

1. **Proveedor**: Claude API (Anthropic), vía el SDK oficial de Python, para
   el piloto. La integración se aísla en un módulo `cataloging_api/agent/`
   cuyo límite externo es una interfaz simple (enviar historial + herramientas
   disponibles, recibir texto o solicitud de herramienta). Ningún otro módulo
   importa el SDK de Anthropic directamente — así, cambiar de proveedor más
   adelante (ADR-006) toca sólo ese módulo.
2. **Superficie de herramientas**: exclusivamente wrappers de solo lectura
   sobre servicios ya existentes (búsqueda de ítems, detalle, diagnóstico,
   similitud, perfil de colección, cola de trabajo, vocabularios controlados,
   historial de sugerencias). Ninguna herramienta puede crear, aprobar,
   rechazar o modificar hallazgos, borradores, sugerencias, vocabularios o
   datos en DSpace. El agente no tiene acceso a bash, sistema de archivos ni
   ejecución de código — no es un "Managed Agent" con sandbox, es una llamada
   a la Messages API con `tools` definidas en este repositorio.
3. **Sin escritura nunca**: el agente no genera sugerencias ni borradores por
   su cuenta (ADR-005). Puede señalar que existe una sugerencia o un hallazgo
   pendiente y enlazar a la ficha correspondiente para que un humano decida
   allí, usando los mecanismos ya construidos.
4. **Persistencia**: PostgreSQL (ADR-007). Conversaciones y mensajes quedan
   en tablas append-only, igual que las decisiones de revisión y borrador,
   para auditoría y continuidad de sesión.
5. **Modelo**: `claude-sonnet-5` por defecto para el piloto, dado el volumen
   esperado de consultas acotadas sobre una sola colección. Configurable por
   variable de entorno; no requiere una ADR nueva para cambiarlo.
6. **Respuesta en streaming**: la API expone Server-Sent Events para que la
   interfaz muestre la respuesta token a token, coherente con la expectativa
   de un chat.
7. **Autorización de costo**: crear una conversación o enviar un mensaje exige
   `CATALOG_REVIEW_TOKEN` (el mismo mecanismo que ya protege toda escritura en
   este repositorio), porque cada mensaje tiene costo real de API — a
   diferencia de las lecturas HTTP existentes, que son gratuitas y públicas.
8. **Alcance de colección**: igual que el resto del piloto, limitado a
   `DSpace_PILOT_COLLECTION_UUID`. Sin identidad institucional, sin acceso
   multi-colección.

## Consecuencias

Positivas: arquitectura desacoplada del proveedor desde el día uno;
reutiliza toda la evidencia y las reglas ya construidas sin duplicarlas;
mantiene humano-en-el-circuito sin excepciones nuevas; auditable en
PostgreSQL igual que el resto del sistema.

Costos: requiere una clave de API de Anthropic y su gestión como secreto;
introduce costo variable por uso (mitigado por el token de autorización y
límites de mensajes); añade una dependencia externa (latencia y
disponibilidad del proveedor) a una superficie que hasta ahora era
totalmente local.

## Alternativas

- **Managed Agents (Anthropic)**: descartado para el P0 — da sandbox de
  archivos/bash que este caso de uso no necesita; la Messages API con
  herramientas propias ya cubre "consultar herramientas internas de
  búsqueda, reglas y evidencia" (ADR-006) sin esa superficie adicional.
- **Generación de sugerencias por el agente**: descartado — ADR-005 exige
  aceptación, edición o rechazo humano explícito para toda sugerencia; el
  mecanismo de sugerencias ya existente (similitud estructurada) seguirá
  siendo el único generador hasta una ADR posterior que lo autorice.
- **Sin persistencia de conversación**: descartado — rompe la trazabilidad
  que el resto del sistema ya garantiza (ADR-002, revisiones y borradores).

## Condición de revisión

Reevaluar el proveedor si ADR-006 deja de cumplirse en la práctica (el
módulo `agent/` deja de ser el único punto de acoplamiento), o el modelo por
defecto si el costo o la calidad del piloto lo justifican.
