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
8. El orden de los bindings en `FIELDS` sigue el orden real del formulario de envío
   DSpace tal como lo documenta el layout del artefacto `dspace-cataloger v3.6`
   (posiciones 28-35 del formulario: `languageUsage, registeredLanguage,
   linguiscgroup, linguisticFamily, linguisticBranch, linguisticVariant,
   selfDenomination, iso6391`). Este orden es *UI Fidelity* (fiel al formulario
   real) y es una dimensión independiente de la jerarquía semántica CLIN de
   ADR-012 (Familia → Agrupación → Variante), que sigue viviendo únicamente en
   `CLIN_RELATIONSHIPS` y en las reglas de diagnóstico.

## Consecuencias

- Se reduce el riesgo de que Python, UI y skill diverjan silenciosamente.
- Cambiar un campo runtime debe comenzar modificando el contrato y sus pruebas.
- La UI puede degradar explícitamente si el contrato no está disponible; no debe
  reconstruir por su cuenta una lista supuestamente equivalente.
- La disponibilidad de un binding en el contrato no autoriza escritura en DSpace.
- Reordenar `FIELDS` debe verificarse contra el layout del formulario documentado
  por `dspace-cataloger v3.6`, no inferirse de la jerarquía CLIN; ambos órdenes
  pueden divergir legítimamente. La regresión de orden se protege con
  `test_master_contract_preserves_dspace_ui_order` en
  `apps/api/tests/test_cataloging_contract.py`.

## Compatibilidad

Se conserva literalmente `dc.subject.linguiscgroup`, la validación literal de
vocabularios, `source_hash`, revisiones append-only y todos los límites de ADR-005,
ADR-006 y ADR-010.

## Revisión futura

Cuando el contrato pueda generarse directamente desde el artefacto maestro del
skill, sustituir la sincronización manual de versión por una generación reproducible
con checksum y prueba de equivalencia.
