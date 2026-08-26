# VERTICAL-022 — Live DSpace contract reconciliation

Date: 2026-08-26  
Collection: `e9a8f44f-a8d3-4d22-b02a-cf590285bac6`  
Active definition observed: `traditional`

## Evidence

Authenticated read-only export from the target DSpace instance:

- schemas: 18
- global metadata fields: 292
- configured submission definitions: 12
- configured submission sections: 46
- configured submission forms: 15
- global configured bindings: 179
- export semantic hash: `8260b2023b7b417f3056d3724664869f96cb613371c673517d6b7400af2a0b1c`

The live endpoint for `traditional/sections` returned HTTP 204 No Content. Therefore active section membership/order was not directly observable through that linked REST surface and the exporter correctly marked the full snapshot incomplete.

## Reconciliation against dspace-cataloger v3.9.1

The canonical skill form contract contains 56 bindings.

The live configured form inventory contains:

- `traditionalpageone`: 44 unique bindings
- `traditionalpagetwo`: 12 unique bindings
- total unique contract bindings: 56

The global-section fallback lists `traditionalpagetwo` twice, so the raw fallback produces 68 rows for the two traditional form IDs. Deduplicating by `form_id + row + field + metadata_index + metadata_key` produces exactly 56.

### Binding-level result

| Dimension | Match |
|---|---:|
| binding identity | 56 / 56 |
| metadataField | 56 / 56 |
| uiLabel | 56 / 56 |
| required | 56 / 56 |
| repeatable | 56 / 56 |
| inputType | 56 / 56 |
| controlledVocabulary | 56 / 56 |
| closedVocabulary | 56 / 56 |
| formOrder | 56 / 56 |
| renderOrder | 56 / 56 |

Result: **STRUCTURAL_MATCH_100_PERCENT** for the configured `traditionalpageone` and `traditionalpagetwo` controls.

Normalized live 56-binding comparison SHA-256:
`5b549a16307354b84b9327325532755877a622e323573616e92c8a0dee93ea92`

### Metadata-registry result

The 56 bindings use 54 unique metadata keys because some metadata keys have more than one UI binding, e.g. `dc.format.medium` and `dc.subject`.

All 54 / 54 unique metadata keys exist in the live 292-field metadata registry.

For those 54 fields:

- field ID: 54 / 54 exact
- element/qualifier identity: 54 / 54 exact
- scope note: 54 / 54 exact

Result: **REGISTRY_MATCH_100_PERCENT** for the current 56-binding contract.

## Important limitation

This reconciliation proves that the configured forms named `traditionalpageone` and `traditionalpagetwo` match the v3.9.1 contract exactly.

It does **not** prove, through the current REST linked-sections endpoint, that those two forms are the complete active section membership/order of the collection at the capture instant, because:

`GET /config/submissiondefinitions/traditional/sections` -> HTTP 204 No Content.

Therefore the first ACTIVE baseline must preserve:

`ACTIVE_SUBMISSION_SECTIONS_UNRESOLVED_HTTP_204`

and must not claim 100% observability of collection-to-section membership.

## Consequences for Slice 1C

1. Treat the live 56-binding reconciliation as a verified configured-form fixture.
2. Do not use all 179 global bindings as the collection contract.
3. Never infer active membership from the 46 global sections.
4. HTTP 204 on the linked active-sections endpoint is an explicit `UNOBSERVABLE_SURFACE`, not an empty active form.
5. Suppress destructive drift derived from active-membership absence while that surface is unobservable.
6. Registry and configured-form drift may still be detected independently.
7. Baseline promotion remains human-approved and must retain the observability warning until a stronger collection-to-section source is available.
