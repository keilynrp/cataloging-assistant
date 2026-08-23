---
name: dspace-cataloger
description: >
  Repository-readable contract mirror for dspace-cataloger v3.9.1. The canonical
  packaged artifact is dspace-cataloger-v3.9.1.skill, identified by the SHA-256
  recorded in manifest.json and the release audit.
---

# dspace-cataloger — contract mirror v3.9.1

> **Status:** CURRENT / CANONICAL / REPOSITORY-PRESERVED after reconstruction verification.
>
> This Markdown file is a human-readable contract mirror. The complete packaged skill,
> its references, assets, tests, schemas and fixtures are preserved through the lossless
> representation defined by `manifest.json` and `RECONSTRUCT.md`.

## Artifact identity

- Artifact: `dspace-cataloger-v3.9.1.skill`
- SHA-256: `b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9`
- Size: `130657` bytes
- Package files: `82`
- JSON members: `35` — validation `PASS`
- Form bindings: `56`
- Golden Set: `GR01–GR22`
- Human approval: required
- Runtime OCR: `false`
- Runtime DSpace write: `false`
- Runtime agent mutations: `false`

## Mission and execution modes

The skill is an auditable cataloging copilot for the target DSpace 7.6.6 profile. It
separates:

`extraction → normalization → vocabulary validation → inference → QA → human approval`

It distinguishes two modes:

1. **Standalone Evidence Cataloging Mode** — may acquire and analyze user-provided or
   explicitly requested evidence and produce cataloging proposals. It does not imply
   persistence or DSpace writes.
2. **Cataloging Assistant Runtime Mode** — follows the application contract. The
   conversational agent remains read-only and cannot initiate ingestion, mutate
   findings, approve/reject evidence, change vocabularies or write to DSpace.

If the standalone capability and application runtime contract differ, the application
runtime contract takes precedence during Runtime Mode.

## Canonical evidence states

- `EXTRAÍDO` — explicitly present in the primary source.
- `VERIFICADO` — confirmed against an authority or reliable external source.
- `INFERIDO` — cataloging inference requiring review.
- `PENDIENTE` — insufficient evidence.
- `GENERADO` — assistant-authored content, not source evidence.

## DSpace linguistic fields

Preserve the registered metadata keys literally:

| Function | Metadata field | Controlled vocabulary |
| --- | --- | --- |
| Lengua de registro | `dc.description.registeredLanguage` | `registeredLanguagePairs` |
| Uso de lengua | `dc.description.languageUsage` | `languageUsagePairs` |
| Agrupación lingüística | `dc.subject.linguiscgroup` | `linguiscgroupPairs` |
| Familia lingüística | `dc.subject.linguisticFamily` | `linguisticFamilyPairs` |
| Rama lingüística | `dc.subject.linguisticBranch` | `linguisticBranchPairs` |
| Variante lingüística | `dc.subject.linguisticVariant` | no local DSpace vocabulary is presumed by runtime |

`dc.subject.linguiscgroup` is the literal registered key. Do not silently rewrite it as
`dc.subject.linguisticGroup` or `dc.subject.linguistic-group`.

### Runtime-draftable linguistic set — authoritative alignment

The authoritative application contract in
`apps/api/src/cataloging_api/cataloging_contract.py` exposes the following linguistic
fields as `runtime_draftable=True`:

- `dc.description.registeredLanguage`
- `dc.subject.linguiscgroup`
- `dc.subject.linguisticFamily`
- `dc.subject.linguisticBranch`
- `dc.subject.linguisticVariant`

`dc.description.languageUsage` is a controlled metadata field but **is not** part of
that runtime-draftable set.

`dc.subject.linguisticVariant` is therefore supported by the runtime draft workflow.
The application does not presume a `linguisticVariantPairs` vocabulary for it; absence
of such a vocabulary must not be converted into a false claim that the field itself is
unsupported.

## Mexican Indigenous Language governance

For Indigenous languages of Mexico:

- CLIN/INALI is the primary authority for the normative chain
  `Familia → Agrupación → Variante`.
- `Rama lingüística` is optional non-CLIN genealogical enrichment and requires an
  explicit secondary authority.
- `Lengua de registro` describes the language in which the resource is recorded;
  `Agrupación lingüística` describes the language that is an object of study.
- Do not turn toponyms, regions, self-denominations or informal dialect labels into
  CLIN variants without authority reconciliation.
- Do not substitute a semantically nearby value when a closed vocabulary lacks the
  required authorized value; record a vocabulary gap instead.

## v3.9.1 linguistic relevance patch

### GR21 — Relevance for linguistic indexing

When a resource mentions multiple languages or linguistic groups, classify their role
before proposing subject metadata:

- `PRIMARY_SUBJECT_LANGUAGE` — substantive object of analysis; candidate for
  `dc.subject.linguiscgroup` after authority/vocabulary validation.
- `SECONDARY_LANGUAGE_MENTION` — contextual, comparative, exemplary, bibliographic or
  enumerative mention; preserve as evidence but do not automatically write subject
  metadata from it.
- `VARIANT_EVIDENCE` — self-denomination, linguistic form, place label or other
  evidence relevant to resolving a variant; insufficient by itself to write
  `dc.subject.linguisticVariant`.

This rule prevents over-indexing from panoramic or multilingual resources.

### GR22 — No genealogical propagation from secondary mentions

A `SECONDARY_LANGUAGE_MENTION` must not automatically generate values for linguistic
family, branch, grouping or variant. Genealogical propagation may begin only from an
accepted primary subject language and an authority-supported relationship.

Associated QA rules:

- `CAT-LING-REL-001`
- `CAT-LING-REL-002`
- `CAT-LING-REL-003`
- `CAT-LING-REL-004`

Golden Set fixtures `GR21` and `GR22` preserve these cases; `GR01–GR20` were retained
byte-for-byte against the local patch base used to produce v3.9.1.

## Runtime evidence boundaries

The application may expose human-controlled evidence ingestion surfaces, including
local text PDFs and backend-only remote evidence fetch under its feature and security
controls. These are human/backend surfaces; the conversational agent cannot initiate
or mutate them. Runtime OCR remains disabled and DSpace writes remain disabled.

## Lineage disclosure

The local v3.9 artifact used as the direct patch base has SHA-256
`76fdc4674ef6b58474d224742005fbf6d4e885db80545ab1d9aa7a3e4e01c06c`. The
repository-preserved v3.9 predecessor has SHA-256
`81e20a04162c8d6631eff7f5555e980102a68532d16e052731e015e1e615679e`.

These are not byte-identical. The repository records this as
`SOURCE_VARIANCE_RECORDED` and makes no false byte-lineage claim. v3.9.1 is identified
and verified independently by its own checksum.

## Canonical evidence for this release

- `manifest.json` — exact lossless reconstruction order and validation facts.
- `RECONSTRUCT.md` — reconstruction and verification procedure.
- `RELEASE-NOTES.md` — semantic patch summary.
- `../../audits/dspace-cataloger-v3.9.1-audit.json` — release audit and provenance.
- `../../CURRENT_RELEASE.md` — current-release pointer.

Any future change to semantic behavior or packaged bytes requires a new governed
version or an explicitly documented preservation-only correction that leaves the
artifact checksum unchanged.
