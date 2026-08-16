# ADR-014: Ingesta controlada de evidencia externa — MVP

## Estado

Propuesto para revisión con VERTICAL-017.

## Contexto

`dspace-cataloger` puede trabajar fuera de la aplicación con URL, PDF o texto completo, mientras que el runtime de `cataloging-assistant` debe conservar DSpace como fuente de verdad, aprobación humana y ausencia de escritura DSpace.

VERTICAL-017 dejó cinco puertas de diseño abiertas. Para iniciar sin introducir una superficie de seguridad excesiva, este ADR adopta un primer corte deliberadamente estrecho.

## Decisiones

1. **Política de fuentes (P0).** El primer corte acepta URL HTTP(S) como locator y texto UTF-8 aportado explícitamente, con máximo de 250 000 caracteres. La aplicación no obtiene contenido remoto, no sigue autenticación y no procesa archivos binarios todavía.
2. **Extracción (P1).** El MVP es determinista. No se usa LLM para crear candidatos. Se reconocen líneas explícitas `metadataField: valor` pertenecientes al contrato maestro y patrones conservadores de DOI, ISSN e ISBN. La URL aportada produce evidencia para `dc.identifier.url`.
3. **Contrato de evidencia (P2).** Cada candidato conserva fuente, campo, valor, estado `EXTRAÍDO`, fragmento/posición o locator, y snapshot de validación contra vocabulario local activo cuando aplica.
4. **Relación con los 56 bindings (P3).** La extracción puede producir evidencia para cualquiera de los `metadataField` del contrato maestro, pero `copy-to-draft` sólo admite los campos lingüísticos `runtime_draftable` del contrato actual. Los demás candidatos permanecen como evidencia para revisión.
5. **Golden Set (P4).** Este corte añade fixtures unitarios deterministas. La importación completa del Golden Set del skill queda como puerta para el extractor LLM/PDF posterior.

## Persistencia

Se introducen tres entidades:

- `catalog_evidence_sessions`: sesión, contrato usado y `base_source_hash` opcional;
- `catalog_evidence_sources`: snapshots inmutables de locator/texto y SHA-256;
- `catalog_evidence_candidates`: candidatos append-only por sesión.

La primera extracción de una sesión queda congelada. Repetir `/extract` devuelve los candidatos existentes y no los reemplaza.

## Staleness

Cuando una sesión está ligada a un ítem DSpace, captura el `source_hash`. Si el registro sincronizado cambia, la sesión se considera stale y se bloquean extracción y copia a borrador.

## Escrituras

Crear sesión, extraer y copiar a borrador exigen `CATALOG_REVIEW_TOKEN`. Las lecturas son locales. `copy-to-draft` reutiliza el servicio existente de borradores y nunca escribe DSpace.

## Consecuencias

Este MVP valida trazabilidad, persistencia, staleness y puente hacia borradores sin introducir SSRF, descarga remota, parsing de PDF ni decisiones generativas. URL fetch, subida de PDF, extracción de texto y asistencia LLM requieren una iteración posterior con límites y pruebas específicas.
