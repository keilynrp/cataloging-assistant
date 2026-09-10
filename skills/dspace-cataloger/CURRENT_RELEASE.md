# Current repository-preserved release

## `dspace-cataloger v3.9.2`

Status: **CURRENT / REPOSITORY-PRESERVED / VERIFIED RE-DERIVATION**

This release is derived from the user-provided, checksum-verified v3.9 artifact
after the v3.9.1 preservation incident. It carries v3.9.1's documented semantic
rules forward without claiming v3.9.1 binary lineage, and adds the ORCID
identifier-classification guardrail.

Canonical release directory:

`skills/dspace-cataloger/versions/v3.9.2/`

Artifact identity:

- SHA-256: `b6c435a28f8bb1a8faab237258161edf0233b2ce3608ff4e025a8ae2a11acede`
- Decoded size: `118470` bytes
- ZIP integrity: `PASS`
- JSON validation: `PASS` (`36` JSON files)
- Package files: `86`
- DSpace form bindings: `56`
- Golden Set: `GR01–GR23`

Semantic additions:

- GR21/GR22 — carried-forward linguistic relevance and no-propagation rules.
- GR23 — ORCID is evidence-only; its fragments cannot become ISSN candidates.
- Identifier types: `doi`, `issn`, `isbn`, `orcid`.

See `versions/v3.9.2/manifest.json`, `versions/v3.9.2/RECONSTRUCT.md`, and
`audits/dspace-cataloger-v3.9.2-audit.md` for reproducibility and lineage
evidence.

### v3.9.1 preservation incident

`v3.9.1` remains historical recovery evidence and is not an adoptable binary
parent. See [`dspace-cataloger-v3.9.1-integrity-recheck-2026-09-09.md`](audits/dspace-cataloger-v3.9.1-integrity-recheck-2026-09-09.md).
