# Adjudication worksheet — candidate 003 / registered-language / rereview-v3

**Case:** `real-evidence-candidate-003-registered-language-rereview-v3`

**Binding:** `registered-language`

**Metadata field:** `dc.description.registeredLanguage`

**Candidate value:** `Español`

**Candidate intent:** `INFERRED_VALUE`

**Evidence snapshot SHA-256:** `58ec2dd6ae0c55a2118ae4c8c27fc21497ab3fc96a73acc2175f4af861c7a7b1`

**Catalog contract:** `dspace-cataloger-v3.6`

**Catalog contract SHA-256:** `a68fbf9664b7165ea240508da85167058cd57796fbda9c1a9869986afb0178bb`

## Independent reviews

- `cataloger-a`: `ACCEPT_AS_IS`, no corrected value, no abstention, no error codes.
- `cataloger-b`: `ACCEPT_AS_IS`, no corrected value, no abstention, no error codes.

Both reviews concern the same concrete proposition and the same immutable evidence snapshot. There is no substantive disagreement.

## Formal consensus closure

- Adjudicator: `adjudicator-1`
- Final decision: `ACCEPT_AS_IS`
- Final value: `Español`
- Final abstention: `false`
- Error codes: none
- Rationale: both independent catalogers accept Español as the language in which the resource itself is written/registered and distinguish P’urhepecha as language studied/discussed rather than the resource writing language.
- Timestamp UTC: `2026-08-18T06:52:00Z`

## Documentary correction

The scorer-facing candidate intent was normalized pre-merge from the non-contract label `RESOURCE_WRITING_LANGUAGE` to `INFERRED_VALUE`, one of the two VERTICAL-021 model intents. The writing-language distinction remains the semantics of `registered-language` under ADR-012. The immutable evidence snapshot and human decisions are unchanged.

## Governance status

The canonical v3 adjudication is `FINAL` and explicitly supersedes the prior v2 adjudication for current gold construction. The case-level resulting gold version is `0.2.0-stratum-a-rereview-v3-adjudicated-gold`. Gate D remains open, and no runtime `VERIFICADO`, provider egress, productive LLM behavior, or DSpace write is authorized.
