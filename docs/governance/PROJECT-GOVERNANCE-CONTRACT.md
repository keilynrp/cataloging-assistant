# Project Governance Contract

Status: **NORMATIVE — PROJECT LEVEL**

Project: **Cataloging Assistant**

Version: **1.0**

License: **Apache License 2.0**

## 1. Purpose

This document defines the project-level governance contract for Cataloging Assistant.

It establishes the rules used to govern source integration, documentation, release management, versioning, tags, experimental work, architectural decisions, UX evidence, privacy, licensing, and changes that affect cataloging semantics or DSpace behavior.

This contract is intended to keep the project auditable, reproducible, and safe to evolve while preserving the distinction between experimentation, validated runtime behavior, and released product baselines.

## 2. Scope

This contract applies to the entire repository, including:

- application code;
- APIs and services;
- persistence and database changes;
- DSpace integrations;
- agent capabilities;
- metadata models and cataloging semantics;
- controlled vocabularies;
- UX prototypes and UX evidence;
- architecture decisions;
- functional and technical specifications;
- evaluation artifacts;
- documentation;
- release artifacts and Git tags.

Specialized governance documents may define stricter rules for a specific area. They must not silently weaken this project-level contract.

## 3. Governance hierarchy

When two artifacts appear to conflict, use the following order of authority:

1. this project-level governance contract;
2. approved Architecture Decision Records (`docs/adr`);
3. approved functional or technical specifications (`docs/specs`);
4. specialized governance contracts, including UX governance under `docs/ux`;
5. accepted implementation evidence and evaluation artifacts;
6. implementation code and tests;
7. experimental prompts, prototypes, notes, and drafts.

A lower-level artifact must not redefine a higher-level contract implicitly.

If behavior and documentation diverge, the discrepancy must be treated as a governance defect and resolved explicitly.

## 4. Core project principles

Cataloging Assistant is governed by the following principles:

- **Human-in-the-loop:** cataloging decisions remain subject to human review.
- **Evidence traceability:** extracted, inferred, validated, selected, and persisted information must remain distinguishable where relevant.
- **DSpace as source of truth:** the current product contract treats DSpace as the authoritative source system.
- **Read-only DSpace integration by default:** no write capability may be introduced without an explicit approved architectural and functional decision.
- **No silent semantic mutation:** metadata semantics, controlled vocabularies, provenance, validation states, or review states must not change implicitly.
- **Auditable change:** significant product behavior must be traceable to a PR, specification, ADR, evaluation artifact, or accepted evidence.
- **Experimentation is not runtime:** prototypes, UX exploration, prompts, and presentation-only interactions do not become product behavior merely because they exist.
- **Release is not synonymous with merge:** `main` represents the latest integrated state, while releases represent deliberate validated baselines.

## 5. Branch and pull request policy

Changes should be developed on focused branches and integrated through pull requests.

Each pull request should:

- have a clear and bounded purpose;
- avoid unrelated refactors;
- identify architectural, semantic, persistence, DSpace, security, or UX-contract implications when present;
- include or update the required ADR, specification, evidence, or documentation;
- pass the relevant verification before merge.

Documentation-only changes do not require a product release unless they alter a normative contract in a way that changes how existing runtime behavior must be interpreted.

## 6. Main branch contract

`main` is the canonical integrated branch.

The presence of a commit in `main` means that the change has been accepted for the integrated project history. It does **not** necessarily mean that the commit belongs to a published product release.

Therefore:

`commit != release`

A release is created only when a coherent baseline satisfies the release gate defined below.

## 7. Versioning policy

Cataloging Assistant follows **Semantic Versioning (SemVer)** using the form:

`MAJOR.MINOR.PATCH`

Git release tags must use a leading `v`:

`vMAJOR.MINOR.PATCH`

Examples:

- `v0.1.0`
- `v0.2.0`
- `v0.2.1`
- `v0.3.0-rc.1`
- `v0.3.0`

### 7.1 MVP phase

While the project remains in the MVP phase, official releases remain in the `0.x` series.

During this phase:

- **MINOR** versions represent coherent, validated capability increments;
- **PATCH** versions represent backward-compatible fixes or corrections;
- pre-release identifiers may be used for release candidates;
- documentation-only and experimental UX changes do not independently trigger a product release.

Because `0.x` indicates a still-evolving public contract, MINOR changes may include substantial compatible evolution and must be reviewed carefully for semantic or architectural impact.

### 7.2 Release candidates

Release candidates use:

`v0.X.0-rc.N`

Examples:

- `v0.4.0-rc.1`
- `v0.4.0-rc.2`

A release candidate is recommended when a release includes significant changes to one or more of the following:

- persistence;
- review workflows;
- agent behavior;
- metadata semantics;
- controlled vocabularies;
- DSpace integration;
- authentication or security;
- externally consumed API behavior;
- UX changes that alter runtime behavior rather than presentation only.

### 7.3 Stable 1.0

`v1.0.0` is reserved for a mature product contract.

The project should not declare `1.0.0` solely because the MVP is functional.

Before `1.0.0`, the project should have stable and documented contracts for at least:

- architecture;
- data model;
- DSpace synchronization;
- evidence semantics;
- human review;
- controlled vocabularies;
- persistence;
- agent behavior;
- security;
- APIs;
- upgrade expectations.

A key maturity criterion is that a `1.x` installation can be upgraded without silently reinterpreting previously recorded cataloging decisions.

## 8. Release significance

The following changes are normally release-significant:

- new runtime capabilities;
- new compatible API endpoints;
- persistence-model changes;
- changes to review or draft workflows;
- changes to controlled-vocabulary behavior;
- changes to DSpace integration behavior;
- changes to metadata semantics;
- changes to evidence-state semantics;
- changes to staleness behavior;
- changes to `metadataField` or `bindingId` contracts;
- security model changes;
- agent capabilities that change runtime behavior.

The following do not normally require an independent product release:

- typo fixes;
- README cleanup;
- documentation restructuring;
- UX prompts that remain experimental;
- presentation-only prototype changes;
- evidence capture for an already accepted prototype;
- non-runtime editorial changes.

## 9. Release gate

A product release may be published only when all applicable conditions are satisfied:

1. `main` is in a known stable state.
2. Relevant tests pass.
3. Relevant lint checks pass.
4. Relevant application builds succeed.
5. Required ADRs are current.
6. Required specifications are current.
7. Cataloging-semantic changes are explicitly documented.
8. DSpace interaction behavior is explicitly documented.
9. Persistence changes are documented and migration implications are known.
10. Experimental or `PRESENTATION_ONLY` behavior is not represented as productive runtime behavior.
11. Known limitations are recorded.
12. The release notes accurately describe the baseline.

A release must not be created merely to mark project activity.

## 10. Release notes contract

GitHub Releases should use a consistent structure:

```markdown
## Cataloging Assistant vX.Y.Z

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Documentation
- ...

### Architecture
- ...

### Known limitations
- ...

### DSpace contract
Read-only unless an approved governance change explicitly states otherwise.

### Verification
- tests: passed / not applicable
- lint: passed / not applicable
- web build: passed / not applicable
```

Release notes must not imply capabilities that are only experimental, future-contract, or presentation-only.

## 11. Git tag policy

Official release tags must follow SemVer-compatible names with a leading `v`.

Allowed examples:

- `v0.1.0`
- `v0.2.1`
- `v0.3.0-rc.1`
- `v1.0.0`

Avoid ambiguous tags such as:

- `final`
- `latest`
- `stable2`
- `working`
- `version-final`

A Git tag is an immutable reference to a release baseline. If a release is incorrect, publish a corrective version rather than moving an existing release tag silently.

## 12. GitHub Topics policy

GitHub Topics are descriptive discovery metadata and are independent from release tags.

Recommended project topics include:

- `dspace`
- `cataloging`
- `metadata`
- `digital-libraries`
- `human-in-the-loop`
- `metadata-validation`
- `controlled-vocabularies`
- `ai-assistant`

Topics should describe stable aspects of the project rather than temporary experiments or a specific pilot collection.

Do not use release version numbers as GitHub Topics.

## 13. ADR and specification policy

A change requires an ADR when it introduces or materially alters a significant architectural decision, including but not limited to:

- persistence strategy;
- authentication or authorization model;
- external-service integration;
- DSpace write capability;
- data ownership boundaries;
- eventing or messaging architecture;
- security-sensitive architecture;
- fundamental agent architecture.

A specification should be updated when a change alters functional behavior, technical contracts, or cataloging semantics that downstream implementation or validation depends on.

## 14. Cataloging-semantic change policy

The following are protected semantic contracts and must not change implicitly:

- `metadataField` identifiers;
- `bindingId` identifiers;
- evidence-state meanings;
- validation-state meanings;
- staleness semantics;
- provenance semantics;
- controlled-vocabulary interpretation;
- cataloging rules;
- DSpace source-of-truth behavior.

A change to one of these requires explicit documentation and impact analysis and is normally release-significant.

## 15. DSpace governance

The default project contract is:

**DSpace integration is read-only.**

Any future capability that writes, synchronizes, publishes, or mutates metadata in DSpace requires, before implementation:

1. an explicit ADR;
2. an approved functional/technical specification;
3. review of authorization and security implications;
4. failure and rollback behavior;
5. provenance and audit behavior;
6. release-level validation.

No prototype or agent instruction may bypass this gate.

## 16. UX governance relationship

UX experimentation is governed additionally by the specialized UX governance artifacts under `docs/ux`.

The project-level rule is:

`UX experiment -> evidence -> acceptance -> implementation decision -> runtime`

not:

`UX experiment -> runtime`

Prompts, Lovable prototypes, screenshots, interaction mockups, and `PRESENTATION_ONLY` behavior do not independently redefine the product contract.

When a UX decision becomes runtime behavior, the relevant specification, implementation, tests, and release significance must be evaluated.

## 17. Experimental and future behavior

Experimental artifacts must be clearly distinguishable from current runtime behavior.

Where classification is used, the project should preserve distinctions such as:

- `CURRENT_RUNTIME`
- `PRESENTATION_ONLY`
- `FUTURE_CONTRACT`
- `REMOVE_OR_CORRECT`

Experimental behavior must not be described in release notes as implemented runtime capability unless that status has actually changed through the governed implementation process.

## 18. Privacy and repository hygiene

Public-facing repository documentation must avoid unnecessary personal information.

Do not include in README, About, examples, or public governance documents:

- personal filesystem paths;
- personal usernames where not technically required;
- private email addresses;
- tokens or credentials;
- private identifiers;
- machine-specific secrets or environment details.

Use neutral examples and project-relative paths.

Pilot-specific identifiers should appear only where necessary for reproducibility, evidence, or historical traceability and should not define the general product identity.

## 19. Licensing

Cataloging Assistant is licensed under the **Apache License 2.0** unless a specific third-party component or artifact carries its own compatible license.

The canonical license text is stored in the repository root `LICENSE` file.

Third-party dependencies and incorporated assets must retain their required notices and licensing conditions.

No project document may imply that third-party content is relicensed by the project when the project does not have the right to do so.

## 20. Changelog policy

A durable `CHANGELOG.md` may be introduced when the release cadence makes it useful.

Until then, GitHub Release notes are the canonical human-readable release summaries.

If a changelog is introduced, it should reflect released versions rather than every merged commit.

## 21. Governance changes

Changes to this contract must be explicit and reviewable.

A governance change should:

- be made through a dedicated or clearly scoped pull request;
- explain the motivation;
- identify affected project contracts;
- avoid silently retroactively reinterpreting prior releases or recorded cataloging decisions;
- update dependent governance or documentation when necessary.

Material governance changes may themselves be release-significant if they alter how current runtime behavior is interpreted or operated.

## 22. Initial release posture

At the adoption of this contract:

- the project remains in the MVP phase;
- release versions should remain in the `0.x` series;
- the first formal baseline may be designated `v0.1.0` once the current integrated capabilities are inventoried and pass the release gate;
- experimental UX work does not independently trigger a release;
- `main` remains the canonical integrated branch;
- DSpace remains read-only under the current product contract.

## 23. Normative summary

The minimum governance rules are:

1. Use focused branches and auditable PRs.
2. Treat `main` as integrated state, not automatically as a release.
3. Use SemVer release tags in the form `vMAJOR.MINOR.PATCH`.
4. Keep MVP releases in the `0.x` series.
5. Release only coherent baselines that pass the release gate.
6. Do not promote experimental UX artifacts directly to runtime semantics.
7. Document changes to metadata, evidence, validation, staleness, vocabulary, persistence, or DSpace contracts explicitly.
8. Preserve DSpace read-only behavior unless a governed decision explicitly changes it.
9. Keep public repository documentation free of unnecessary personal data.
10. Use Apache License 2.0 as the project license.

---

This document is the project-level governance baseline for Cataloging Assistant. Specialized contracts may add stricter controls, but they must remain compatible with this contract.