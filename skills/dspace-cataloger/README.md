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
  CURRENT_RELEASE.md
  versions/
  audits/
  migrations/
```

## Current repository-preserved version

**3.9.1 — CURRENT / CANONICAL / REPOSITORY-PRESERVED**

Canonical preservation representation:

`skills/dspace-cataloger/versions/v3.9.1/`

Artifact identity:

- canonical artifact name: `dspace-cataloger-v3.9.1.skill`;
- representation: lossless Base64 multipart with repaired explicit continuations;
- original size: `130657` bytes;
- Base64 representation length: `174212` characters;
- SHA-256: `b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9`;
- ZIP integrity: `PASS`;
- JSON validation: `PASS` (`35` JSON members);
- package files: `82`;
- form bindings: `56`;
- Golden Set: `GR01–GR22` present.

Canonical evidence:

- [`CURRENT_RELEASE.md`](CURRENT_RELEASE.md)
- [`versions/v3.9.1/manifest.json`](versions/v3.9.1/manifest.json)
- [`versions/v3.9.1/RECONSTRUCT.md`](versions/v3.9.1/RECONSTRUCT.md)
- [`versions/v3.9.1/RELEASE-NOTES.md`](versions/v3.9.1/RELEASE-NOTES.md)
- [`audits/dspace-cataloger-v3.9.1-audit.json`](audits/dspace-cataloger-v3.9.1-audit.json)

The v3.9.1 repository representation reconstructs the artifact identified by the SHA-256 above. The manifest defines the canonical reconstruction order, including two explicit continuation segments that restore `7097` Base64 characters lost during the original connector upload. GitHub-observed segment sizes total exactly `174212` characters.

## Preserved versions

| Version | Artifact | GitHub preservation status |
| --- | --- | --- |
| 3.5 | `dspace-cataloger-v3.5.skill` | `PENDING_MIGRATION` |
| 3.6 | `dspace-cataloger-v3.6.skill` | `PENDING_MIGRATION` |
| 3.8 | `dspace-cataloger-v3.8.skill` | `PENDING_MIGRATION` |
| 3.9 | `dspace-cataloger-v3.9.skill` | `SUPERSEDED / REPOSITORY-PRESERVED` |
| 3.9.1 | `dspace-cataloger-v3.9.1.skill` | `CURRENT / CANONICAL / REPOSITORY-PRESERVED` |

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
