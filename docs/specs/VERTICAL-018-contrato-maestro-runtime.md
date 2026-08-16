# VERTICAL-018: Contrato maestro runtime

## Resultado observable

La aplicación dispone de un contrato único, versionado y consultable que describe
los bindings catalográficos y los subconjuntos operativos usados por el runtime.
Los servicios backend derivan sus listas de campos desde ese contrato; Next.js lo
consulta mediante una API read-only y el agente dispone de una herramienta de
solo lectura para consultar su semántica.

## Contrato HTTP

`GET /api/cataloging-contract`

La respuesta incluye:

- `contract_version`;
- `dspace_version`;
- `field_count`;
- `fields[]` con binding, clave de metadato, etiquetas y propiedades;
- `runtime.draftable_fields`;
- `runtime.controlled_fields`;
- `runtime.profile_fields`;
- `runtime.profile_relationships`;
- `runtime.clin_relationships`;
- banderas de gobernanza;
- `evidence_states`;
- `qa_rules`.

## Consumo runtime

- `drafts.service` deriva los campos editables desde el contrato.
- `vocabularies.service` deriva los campos gobernables desde el contrato.
- `profile.metrics` deriva campos y relaciones desde el contrato.
- `diagnostics.engine` reutiliza las claves canónicas del contrato.
- las Server Actions de Next.js consultan el contrato antes de preparar mutaciones locales;
- el editor de borradores carga los campos runtime desde el endpoint público de lectura;
- la página de vocabularios construye etiquetas y opciones a partir del contrato;
- el agente expone `get_cataloging_contract`, siempre read-only.

## Invariantes

1. `field_count == 56`.
2. `dc.subject.linguiscgroup` se conserva literalmente.
3. Dos bindings de `dc.format.medium` permanecen separados.
4. Dos bindings de `dc.subject` permanecen separados.
5. Variante lingüística pertenece a draft, validación y perfil runtime.
6. Variante puede ser vocabulario local controlado sin presumir que DSpace expone una lista promocionable específica.
7. Lengua de registro no aparece en `clin_relationships`.
8. Rama no es obligatoria para que una familia sea válida.
9. `dspace_write_enabled == false`.
10. `human_approval_required == true`.

## Degradación

Si Next.js no puede recuperar el contrato en una operación que depende de él, la
operación se bloquea o se presenta como no disponible. No se reconstruye una lista
hardcodeada de fallback para acciones catalográficas.

## Pruebas mínimas

- conservación de 56 bindings;
- conservación de claves compartidas como bindings distintos;
- inclusión de los cinco campos lingüísticos runtime;
- variante controlada sin vocabulario DSpace presumido;
- jerarquía CLIN correcta;
- serialización del payload;
- herramienta read-only disponible para el agente;
- endpoint disponible en modo read-only.

## Fuera de alcance

- generación automática del contrato desde el archivo `.skill`;
- escritura DSpace;
- ingesta URL/PDF;
- reconciliación automática CLIN;
- relaciones multientidad persistidas como grafo.
