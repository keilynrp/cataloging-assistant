# dspace-cataloger v3.9.1 — Release Notes

Fecha: 2026-08-23  
Tipo: patch semántico aditivo sobre v3.9

## Motivo

El caso Balajú 2716 mostró que un recurso panorámico puede mencionar numerosas lenguas
sin que todas deban convertirse en valores de `dc.subject.linguiscgroup`.

## Cambios

- GR21 — Relevancia lingüística para indexación.
- GR22 — No propagación genealógica desde menciones secundarias.
- Roles internos: `PRIMARY_SUBJECT_LANGUAGE`, `SECONDARY_LANGUAGE_MENTION`,
  `VARIANT_EVIDENCE`.
- QA: `CAT-LING-REL-001` … `CAT-LING-REL-004`.
- Golden Set: 20 → 22 fixtures.

## Compatibilidad

- 56 bindings preservados.
- `dc.subject.linguiscgroup` preservado literalmente.
- GR01–GR20 preservados byte-for-byte.
- estados `EXTRAÍDO`, `VERIFICADO`, `INFERIDO`, `PENDIENTE`, `GENERADO` preservados.
- runtime read-only preservado; sin OCR, sin escritura DSpace, sin mutaciones del agente.

## Artefacto

SHA-256: `b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9`
