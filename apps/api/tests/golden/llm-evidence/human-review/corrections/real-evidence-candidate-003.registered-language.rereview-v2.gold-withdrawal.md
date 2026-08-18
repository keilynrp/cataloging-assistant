# Governance correction — candidate 003 / registered-language / rereview-v2

**Status:** CASE-LEVEL GOLD WITHDRAWN PENDING REREVIEW-V3

**Affected case:** `real-evidence-candidate-003-registered-language-rereview-v2`

**Historical adjudication:** `adjudication-real-evidence-candidate-003-registered-language-rereview-v2-v1`

**Historical final decision:** `ACCEPT_WITH_MINOR_EDIT`

**Historical final value:** `Purépecha`

## Reason for correction

A pre-merge review identified a semantic mismatch with ADR-012. `dc.description.registeredLanguage` denotes the language in which the resource itself is written/registered, independent of the language studied or discussed. The v2 evidence packet established P’urhepecha as a language used, taught, quoted, and discussed in the article, but did not establish P’urhepecha as the article's language of writing.

The human adjudication remains preserved as an immutable historical decision record. This correction withdraws only its case-level `ADJUDICATED_GOLD` status from current evaluation use. It does not silently rewrite or delete the v2 review or adjudication artifacts.

## Remediation

A new case, `real-evidence-candidate-003-registered-language-rereview-v3`, is opened against a corrected proposition:

`dc.description.registeredLanguage = Español`

The v3 evidence packet is based on explicit evidence about the article's writing language and must receive new independent human reviews. Any later adjudication that supersedes the v2 adjudication must explicitly reference the prior adjudication through `supersedes_adjudication_id`.

## Boundaries

This correction does not create runtime `VERIFICADO`, authorize provider egress, activate productive LLM behavior, or write to DSpace. Gate D remains open.
