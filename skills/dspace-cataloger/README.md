# dspace-cataloger — Version Registry

Status: **GOVERNED — REPOSITORY SOURCE OF TRUTH**

Canonical root: `skills/dspace-cataloger/`

Governed by: [`docs/governance/PROJECT-GOVERNANCE-CONTRACT-v1.1-SKILL-VERSIONING-AMENDMENT.md`](../../docs/governance/PROJECT-GOVERNANCE-CONTRACT-v1.1-SKILL-VERSIONING-AMENDMENT.md)

## Purpose

This directory is the canonical GitHub location for preserving complete, versioned `dspace-cataloger` skill artifacts and their supporting audit or migration evidence.

A skill version is considered repository-preserved only when its complete artifact, or a complete lossless representation, exists in this directory tree and is traceable through Git history.

## Canonical layout

```text
skills/dspace-cataloger/
  README.md
  versions/
  audits/
  migrations/
```

Expected naming examples:

```text
versions/dspace-cataloger-v3.8.skill
versions/v3.9/
audits/dspace-cataloger-v3.9-audit.json
migrations/dspace-cataloger-v3.8-to-v3.9-alignment-report.md
```

## Current repository-preserved version

**3.9 — CURRENT / CANONICAL / REPOSITORY-PRESERVED**

Canonical preservation representation:

`skills/dspace-cataloger/versions/v3.9/`

Artifact identity:

- canonical artifact name: `dspace-cataloger-v3.9.skill`;
- representation: lossless Base64 multipart;
- original size: `122755` bytes;
- Base64 representation length: `163676` characters;
- SHA-256: `81e20a04162c8d6631eff7f5555e980102a68532d16e052731e015e1e615679e`;
- ZIP integrity: `PASS`;
- JSON validation: `PASS` (`33` JSON members);
- package files: `80`;
- form bindings: `56`;
- Golden Set: `GR01–GR20` present.

Canonical evidence:

- [`versions/v3.9/manifest.json`](versions/v3.9/manifest.json)
- [`versions/v3.9/RECONSTRUCT.md`](versions/v3.9/RECONSTRUCT.md)
- [`audits/dspace-cataloger-v3.9-audit.json`](audits/dspace-cataloger-v3.9-audit.json)

The multipart representation is lossless and reconstructs the original artifact identified by the SHA-256 above. The manifest records the exact reconstruction order and Git blob SHA-1 for every part.

## Historical migration candidates

Historical evidence indicates the prior existence of the following artifacts:

| Version | Historical artifact | GitHub preservation status |
| --- | --- | --- |
| 3.5 | `dspace-cataloger-v3.5.skill` | `PENDING_MIGRATION` |
| 3.6 | `dspace-cataloger-v3.6.skill` | `PENDING_MIGRATION` |
| 3.8 | `dspace-cataloger-v3.8.skill` | `PENDING_MIGRATION` |
| 3.9 | `dspace-cataloger-v3.9.skill` | `CURRENT / CANONICAL / REPOSITORY-PRESERVED` |

The earlier entries are discovery and migration records only. They do not assert that the corresponding complete historical artifacts are currently preserved in GitHub.

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
