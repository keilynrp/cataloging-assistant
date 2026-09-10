# Current repository-preserved release

## `dspace-cataloger v3.9.1`

Status: **PRESERVATION INTEGRITY FAILURE / RECOVERY REQUIRED**

The version directory remains preserved as historical evidence, but its Base64
reconstruction no longer matches the SHA-256 recorded in its manifest. It must not
be treated as the adopted canonical skill until a complete source artifact is
recovered and independently verified. See
[`dspace-cataloger-v3.9.1-integrity-recheck-2026-09-09.md`](audits/dspace-cataloger-v3.9.1-integrity-recheck-2026-09-09.md).

Preserved artifact directory under recovery:

`skills/dspace-cataloger/versions/v3.9.1/`

Artifact identity:

- SHA-256: `b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9`
- Decoded size: `130657` bytes
- ZIP integrity: `PASS`
- JSON validation: `PASS` (`35` JSON files)
- Package files: `82`
- DSpace form bindings: `56`
- Golden Set: `GR01–GR22`

Semantic patch additions:

- `GR21` — linguistic relevance for indexing.
- `GR22` — no genealogical propagation from secondary language mentions.
- Evidence roles: `PRIMARY_SUBJECT_LANGUAGE`, `SECONDARY_LANGUAGE_MENTION`, `VARIANT_EVIDENCE`.
- QA rules: `CAT-LING-REL-001` through `CAT-LING-REL-004`.

See `versions/v3.9.1/manifest.json`, `versions/v3.9.1/RECONSTRUCT.md`, and `audits/dspace-cataloger-v3.9.1-audit.json` for reproducibility and lineage evidence.

### Lineage disclosure

The direct local v3.9 patch base (`76fdc467…e01c06c`) is not byte-identical to the repository-preserved v3.9 artifact (`81e20a04…15679e`). This variance is explicitly recorded; no false byte-identical predecessor claim is made.
