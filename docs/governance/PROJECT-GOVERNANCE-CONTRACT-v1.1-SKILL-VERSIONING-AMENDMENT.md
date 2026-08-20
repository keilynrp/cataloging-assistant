# Project Governance Contract — v1.1 Skill Versioning Amendment

Status: **NORMATIVE — PROJECT LEVEL**

Project: **Cataloging Assistant**

Amends: [`PROJECT-GOVERNANCE-CONTRACT.md`](PROJECT-GOVERNANCE-CONTRACT.md) version 1.0

Effective governance version: **1.1**

License: **Apache License 2.0**

## 1. Purpose

This amendment establishes repository-level preservation and version-control rules for project skills, with `dspace-cataloger` as the first governed skill.

It exists to prevent operational knowledge, cataloging rules, prompt logic, bindings, validation behavior, or other skill contracts from depending on conversational memory, temporary notes, local-only files, or reconstructed history.

## 2. Source-of-truth rule

GitHub is the canonical source of truth for governed project skills.

A skill version is considered preserved only when its complete versioned artifact, or a complete lossless representation of that artifact, is committed to this repository and traceable through Git history.

Conversation history, assistant memory, local notes, chat exports, temporary attachments, and external working folders are not authoritative skill repositories.

They may provide recovery evidence, but they do not replace repository preservation.

## 3. Version preservation contract

For every governed skill:

1. each adopted version must be preserved in GitHub;
2. previously preserved versions must remain recoverable from repository history;
3. a new version must not silently overwrite the previous version;
4. version changes must be associated with a scoped commit or pull request;
5. the currently adopted version must be explicitly identifiable;
6. the relationship between consecutive versions should be documented when behavior or contract changes materially;
7. incomplete reconstructions must be labeled as reconstructed and must not be represented as canonical historical artifacts;
8. a version must not be declared preserved merely because its version number or summary appears in documentation.

## 4. Canonical repository structure

The canonical root for project skills is:

```text
skills/
  <skill-name>/
    README.md
    versions/
      <versioned-artifacts>
    audits/
      <optional-audit-artifacts>
    migrations/
      <optional-version-alignment-reports>
```

For `dspace-cataloger`, the canonical root is:

```text
skills/dspace-cataloger/
```

Version filenames should preserve the skill's explicit version identifier, for example:

```text
dspace-cataloger-v3.8.skill
dspace-cataloger-v3.9.skill
```

Supporting evidence may use names such as:

```text
dspace-cataloger-v3.8-audit.json
dspace-cataloger-v3.8-to-v3.9-alignment-report.md
```

The exact packaging format may evolve, but the version identifier and traceability requirement are normative.

## 5. Current-version rule

The skill root `README.md` must identify the latest version that is actually preserved in GitHub.

A version that exists only externally or is known only from prior conversations must not be declared `CURRENT` or `CANONICAL` in the repository.

If the application runtime references a skill contract version, that runtime reference and the repository-preserved skill version should be reconciled explicitly rather than assumed to match.

## 6. Historical recovery and migration

Historical skill artifacts discovered outside GitHub should be migrated into the canonical repository structure when their complete bytes or complete source representation are available and provenance can be established.

Migration must preserve, when available:

- original filename;
- version identifier;
- source or provenance;
- checksum;
- audit result;
- relationship to preceding/following versions;
- whether the artifact is original, reconstructed, or derived.

A migrated historical artifact must not be silently modified to match a newer contract. Corrections or normalization should be represented as a new artifact or documented transformation.

## 7. Known historical state at adoption

At adoption of this amendment, historical evidence indicates that versions of `dspace-cataloger` existed outside this GitHub repository, including at least:

- `dspace-cataloger-v3.5.skill`;
- `dspace-cataloger-v3.6.skill`;
- `dspace-cataloger-v3.8.skill`.

Those references are recorded only as **historical migration candidates**.

Their mention in this amendment does **not** mean their complete artifacts are currently preserved in GitHub.

No `dspace-cataloger` version is to be declared repository-canonical until the complete artifact has been committed and verified.

## 8. Change classification

Changes to a governed skill are project-significant when they alter, among other things:

- cataloging rules;
- metadata-field mappings or bindings;
- controlled-vocabulary behavior;
- evidence or provenance behavior;
- validation logic;
- DSpace interaction assumptions;
- inference or generation rules;
- review requirements;
- output schema or interoperability contract.

Such changes should include an alignment report, specification update, ADR, or other governed evidence when appropriate.

## 9. Release relationship

Skill versioning and product release versioning are related but independent.

A skill version such as `dspace-cataloger v3.9` does not imply a product release `v3.9.0`, and a product release does not automatically create a new skill version.

Release notes should identify the skill version used by a product baseline when that relationship is operationally relevant.

## 10. Prohibition on memory-only adoption

A skill change discussed or approved in conversation is not adopted solely by virtue of that discussion.

The normative transition is:

```text
proposal or finding
    -> skill change artifact
    -> versioned repository preservation
    -> review / verification
    -> adoption
```

not:

```text
conversation
    -> remembered behavior
```

## 11. Governance precedence

This amendment forms part of the Project Governance Contract and has the same project-level normative authority for skill preservation and versioning matters.

If the base v1.0 contract and this amendment are read together, the effective governance version is **1.1**.

Future consolidated revisions may incorporate this amendment into a single canonical contract document, but doing so must preserve this amendment's Git history and normative intent.

## 12. Normative summary

1. GitHub is the source of truth for project skills.
2. Every adopted skill version must be preserved completely and traceably.
3. Conversation memory and loose notes are recovery aids, not authoritative storage.
4. Versions must not be silently overwritten.
5. Historical artifacts must be migrated with provenance rather than reconstructed without labeling.
6. The current repository skill version must be explicitly identifiable.
7. Skill version numbers are independent from product SemVer release numbers.
8. `skills/dspace-cataloger/` is the canonical repository location for `dspace-cataloger`.
