# dspace-cataloger — Version Registry

Status: **GOVERNED — REPOSITORY SOURCE OF TRUTH**

`v3.9.2` is the current verified re-derivation. The failed `v3.9.1` package
remains preserved as historical recovery evidence and is not an adoptable binary
parent.

Canonical root: `skills/dspace-cataloger/`

Governed by: [`docs/governance/PROJECT-GOVERNANCE-CONTRACT-v1.1-SKILL-VERSIONING-AMENDMENT.md`](../../docs/governance/PROJECT-GOVERNANCE-CONTRACT-v1.1-SKILL-VERSIONING-AMENDMENT.md)

## Purpose

This directory is the canonical GitHub location for preserving complete, versioned `dspace-cataloger` skill artifacts and their supporting audit or migration evidence.

A skill version is considered repository-preserved only when its complete artifact, or a complete lossless representation, exists in this directory tree and is traceable through Git history.

## Canonical layout

```text
skills/dspace-cataloger/
  README.md
  CURRENT_RELEASE.md
  versions/
  audits/
  migrations/
```

## Current repository-preserved version

**3.9.2 — CURRENT / CANONICAL / REPOSITORY-PRESERVED**

Canonical preservation representation:

`skills/dspace-cataloger/versions/v3.9.2/`

Artifact identity:

- canonical artifact name: `dspace-cataloger-v3.9.2.skill`;
- representation: lossless Base64 multipart;
- decoded size: `118470` bytes;
- Base64 representation length: `157988` characters;
- SHA-256: `b6c435a28f8bb1a8faab237258161edf0233b2ce3608ff4e025a8ae2a11acede`;
- ZIP integrity: `PASS`;
- JSON validation: `PASS` (`36` JSON members);
- package files: `86`;
- form bindings: `56`;
- Golden Set: `GR01–GR23` present.

Canonical evidence:

- [`CURRENT_RELEASE.md`](CURRENT_RELEASE.md)
- [`versions/v3.9.2/manifest.json`](versions/v3.9.2/manifest.json)
- [`versions/v3.9.2/RECONSTRUCT.md`](versions/v3.9.2/RECONSTRUCT.md)
- [`versions/v3.9.2/RELEASE-NOTES.md`](versions/v3.9.2/RELEASE-NOTES.md)
- [`audits/dspace-cataloger-v3.9.2-audit.md`](audits/dspace-cataloger-v3.9.2-audit.md)

v3.9.2 is a verified re-derivation from the user-provided v3.9 artifact
(`76fdc467…e01c06c`). It carries the documented v3.9.1 semantics forward but
does not claim that the v3.9.1 binary is valid. The preservation incident remains
recorded in [`audits/dspace-cataloger-v3.9.1-integrity-recheck-2026-09-09.md`](audits/dspace-cataloger-v3.9.1-integrity-recheck-2026-09-09.md).

## Preserved versions

| Version | Artifact | GitHub preservation status |
| --- | --- | --- |
| 3.5 | `dspace-cataloger-v3.5.skill` | `PENDING_MIGRATION` |
| 3.6 | `dspace-cataloger-v3.6.skill` | `PENDING_MIGRATION` |
| 3.8 | `dspace-cataloger-v3.8.skill` | `PENDING_MIGRATION` |
| 3.9 | `dspace-cataloger-v3.9.skill` | `SUPERSEDED / REPOSITORY-PRESERVED` |
| 3.9.1 | `dspace-cataloger-v3.9.1.skill` | `PRESERVED / INTEGRITY FAILURE / RECOVERY REQUIRED` |
| 3.9.2 | `dspace-cataloger-v3.9.2.skill` | `CURRENT / VERIFIED RE-DERIVATION / REPOSITORY-PRESERVED` |

The v3.9.1 audit records `SOURCE_VARIANCE_RECORDED`: the local v3.9 artifact used as the direct patch base and the repository-preserved v3.9 artifact do not share the same SHA-256. The repository does not claim byte-identical lineage between those two v3.9 artifacts.

## Preservation requirements

When a historical or new version is added, record at minimum:

- version identifier;
- artifact filename;
- provenance/source;
- preservation status;
- checksum when available;
- audit or validation status when available;
- predecessor/successor relationship when relevant;
- whether the artifact is original, reconstructed, or derived.

## Adoption rule

Discussion in ChatGPT, local notes, memory, or temporary files does not constitute adoption of a skill version.

The governed path is:

```text
finding or proposal
    -> versioned skill artifact
    -> GitHub commit / PR
    -> verification
    -> adoption
```

This registry must be updated whenever the repository-preserved current version changes.
