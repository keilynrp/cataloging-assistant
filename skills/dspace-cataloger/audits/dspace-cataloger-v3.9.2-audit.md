# dspace-cataloger v3.9.2 — release audit

Date: 2026-09-09

## Result

**PASS — verified re-derivation.**

The user-provided `dspace-cataloger-v3.9.skill` was verified before use:

- SHA-256: `76fdc4674ef6b58474d224742005fbf6d4e885db80545ab1d9aa7a3e4e01c06c`
- ZIP entries: `83`
- JSON files: `33`, all valid UTF-8 JSON.

The v3.9.2 reconstruction verifies:

- SHA-256: `b6c435a28f8bb1a8faab237258161edf0233b2ce3608ff4e025a8ae2a11acede`
- decoded bytes: `118470`
- ZIP entries: `86`
- JSON files: `36`, all valid UTF-8 JSON
- form bindings: `56`
- Golden Set: `GR01–GR23`

## Lineage

v3.9.2 is derived from the verified v3.9 source. It carries the documented
v3.9.1 semantic changes (GR21/GR22) forward, but does not claim a binary-parent
relationship to v3.9.1, whose preservation integrity failure remains recorded.

## Boundaries

The release adds no DSpace binding, write operation, OCR capability, or agent
mutation. ORCID is an evidence-only identifier type until a governed DSpace
binding is approved.
