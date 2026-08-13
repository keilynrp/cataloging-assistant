# ADR-011: Gestión de credenciales de proveedores de IA

**Estado:** Aceptada el 12 de agosto de 2026.

## Contexto

ADR-010 dejó la clave del proveedor en una variable de entorno
(`ANTHROPIC_API_KEY`) y aisló la integración en `cataloging_api/agent/`
"para que cambiar de proveedor más adelante toque sólo ese módulo". El
usuario pidió ir más allá: una área de configuración donde se puedan
gestionar credenciales de distintos proveedores de IA sin editar `.env` ni
redesplegar, y que el agente pueda correr con más de un proveedor real
(Anthropic y OpenAI para empezar).

## Decisión propuesta

1. **Almacenamiento**: tabla `provider_credentials` en PostgreSQL
   (ADR-007). La clave se cifra en reposo con Fernet (símetrico,
   `cryptography`), usando una clave raíz nueva en `SETTINGS_ENCRYPTION_KEY`.
   Sin esa variable, los endpoints de escritura de settings responden 503 —
   mismo patrón de apagado explícito que `CATALOG_REVIEW_TOKEN`. La clave
   cifrada nunca se devuelve en ninguna respuesta HTTP; sólo su prefijo
   enmascarado para que el operador la reconozca.
2. **Un proveedor activo a la vez**: como con los vocabularios controlados
   (`catalog_vocabulary_revisions`), sólo puede haber una credencial activa
   globalmente; activar una nueva desactiva la anterior en la misma
   transacción. Es el modelo más simple correcto para un agente de un solo
   piloto; no hay necesidad de enrutar conversaciones distintas a
   proveedores distintos todavía.
3. **Abstracción provider-agnóstica**: `agent/providers/` reemplaza al
   único adaptador de ADR-010. Define un protocolo común
   (`ProviderTurn`/eventos `TextDelta`/`ToolCallEvent`/`TurnFinished`) que
   oculta el formato de wire de cada proveedor — incluida la reconstrucción
   del historial de mensajes con llamadas a herramientas, que difiere
   estructuralmente entre Anthropic y OpenAI. `cataloging_api/agent/service.py`
   sólo conoce estos eventos comunes, nunca el SDK de un proveedor
   específico.
4. **Proveedores P0**: Anthropic (ya existente) y OpenAI, ambos con
   adaptador real. Un proveedor sin adaptador implementado se puede guardar
   como credencial pero no se puede activar — falla con un error explícito,
   nunca en silencio.
5. **Autorización**: mismas reglas que el resto de las mutaciones de este
   repositorio — `CATALOG_REVIEW_TOKEN`. A diferencia de los datos
   catalográficos, aquí también se protege la *lectura* (incluso los
   metadatos enmascarados de qué proveedores están configurados), porque es
   una superficie más sensible que el resto del piloto.
6. **El modelo es configurable, no fijo en código**: cada credencial guarda
   su propio identificador de modelo como texto libre, para no atar este
   repositorio a IDs de modelo que cambian más rápido que el código.

## Consecuencias

Positivas: rotar o cambiar de proveedor ya no exige editar `.env` ni
redesplegar; la abstracción provider-agnóstica queda demostrada con dos
implementaciones reales en vez de una sola (que es la única forma honesta
de validar que el desacoplamiento de ADR-006/010 realmente desacopla);
mismo modelo mental que vocabularios controlados para "activo único".

Costos: una clave raíz más que custodiar (`SETTINGS_ENCRYPTION_KEY`); una
dependencia nueva (`cryptography`) y un segundo SDK (`openai`); dos
adaptadores que mantener sincronizados con la misma superficie de
herramientas; sin esa clave raíz, las credenciales guardadas antes de
perderla quedan indescifrables — el operador debe tratarla con el mismo
cuidado que `CATALOG_REVIEW_TOKEN`.

## Alternativas

- **Seguir en `.env`**: descartado — es exactamente lo que el usuario pidió
  evitar; no permite rotar sin redesplegar ni gestionar más de un
  proveedor a la vez de forma operativa.
- **Un secreto por variable de entorno por proveedor** (`OPENAI_API_KEY`,
  etc.): descartado por la misma razón; además no soporta agregar
  proveedores sin tocar código de configuración.
- **Múltiples credenciales activas simultáneas** (para enrutar por
  conversación): descartado para este alcance — añade una decisión de
  producto (¿qué conversación usa qué proveedor?) que nadie pidió todavía.

## Condición de revisión

Reevaluar "un activo a la vez" si aparece una necesidad real de correr
conversaciones distintas contra proveedores distintos en paralelo.
