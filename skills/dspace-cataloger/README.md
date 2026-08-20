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
versions/dspace-cataloger-v3.9.skill
audits/dspace-cataloger-v3.8-audit.json
migrations/dspace-cataloger-v3.8-to-v3.9-alignment-report.md
```

## Current repository-preserved version

**None declared yet.**

No version should be marked `CURRENT`, `CANONICAL`, or repository-preserved until the complete artifact has been committed and verified.

## Historical migration candidates

Historical evidence indicates the prior existence of at least the following artifacts outside this repository:

| Version | Historical artifact | GitHub preservation status |
| --- | --- | --- |
| 3.5 | `dspace-cataloger-v3.5.skill` | `PENDING_MIGRATION` |
| 3.6 | `dspace-cataloger-v3.6.skill` | `PENDING_MIGRATION` |
| 3.8 | `dspace-cataloger-v3.8.skill` | `PENDING_MIGRATION` |

These entries are discovery and migration records only. They do not assert that the corresponding bytes are currently preserved in GitHub.

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
