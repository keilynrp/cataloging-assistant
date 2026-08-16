# ADR-013: Contrato maestro de catalogación

**Estado:** Propuesta implementada en la rama `feat/skill-v3-6-alignment`.

## Contexto

La aplicación repetía listas de campos lingüísticos en diagnóstico, borradores,
vocabularios, perfil y acciones de Next.js. `dspace-cataloger` v3.6 mantiene además
un contrato de 56 bindings DSpace, estados de evidencia y reglas de gobernanza.
Mantener esos contratos por separado crea riesgo de *schema drift*.

## Decisión

1. `cataloging_api.cataloging_contract` es la representación canónica ejecutable
   del contrato `dspace-cataloger-v3.6` dentro de la aplicación.
2. El contrato conserva los **56 bindings observados** de DSpace, incluyendo
   bindings distintos que comparten `metadata_field` (`dc.format.medium` y
   `dc.subject`).
3. Cada binding conserva `binding_id`, `metadata_field`, `ui_label`,
   `assistant_label`, repetibilidad, obligatoriedad, vocabulario y capacidades
   runtime.
4. Los subconjuntos operativos (draftable, controlled, profiled) se derivan del
   contrato; los servicios no deben mantener listas paralelas.
5. `GET /api/cataloging-contract` publica una vista de solo lectura para clientes
   de la aplicación. Next.js puede consumirla sin convertirla en fuente de verdad
   independiente.
6. El contrato declara de forma explícita:
   - CLIN: Familia → Agrupación → Variante;
   - Rama: enriquecimiento genealógico opcional;
   - Lengua de registro: eje documental independiente;
   - DSpace write: deshabilitado;
   - aprobación humana: obligatoria.
7. Los estados de evidencia del skill se exponen como parte del contrato para la
   futura VERTICAL-017 de ingesta externa.

## Consecuencias

- Se reduce el riesgo de que Python, UI y skill diverjan silenciosamente.
- Cambiar un campo runtime debe comenzar modificando el contrato y sus pruebas.
- La UI puede degradar explícitamente si el contrato no está disponible; no debe
  reconstruir por su cuenta una lista supuestamente equivalente.
- La disponibilidad de un binding en el contrato no autoriza escritura en DSpace.

## Compatibilidad

Se conserva literalmente `dc.subject.linguiscgroup`, la validación literal de
vocabularios, `source_hash`, revisiones append-only y todos los límites de ADR-005,
ADR-006 y ADR-010.

## Revisión futura

Cuando el contrato pueda generarse directamente desde el artefacto maestro del
skill, sustituir la sincronización manual de versión por una generación reproducible
con checksum y prueba de equivalencia.
