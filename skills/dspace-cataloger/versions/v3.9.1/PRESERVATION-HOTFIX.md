# v3.9.1 preservation hotfix

This preservation-only correction follows review feedback on PR #26.

It does **not** change the packaged `dspace-cataloger-v3.9.1.skill` bytes or semantic version.

Resolved findings:

1. **P1 — incomplete Base64 reconstruction**: restore `1940` missing characters after `part03.tail01` and `5157` missing characters after `part11`, for a total of `7097`. GitHub-observed reconstruction segment lengths now total exactly `174212` characters.
2. **P1 — stale runtime contract mirror**: align the repository-readable SKILL mirror with `apps/api/src/cataloging_api/cataloging_contract.py`. Runtime-draftable linguistic fields include `dc.subject.linguisticVariant`; `dc.description.languageUsage` is not runtime-draftable.
3. **P2 — stale version registry**: root `skills/dspace-cataloger/README.md` now marks v3.9.1 current/canonical and v3.9 superseded.

Canonical artifact identity remains:

- size: `130657` bytes
- SHA-256: `b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9`
- ZIP integrity: `PASS`

See `manifest.json`, `RECONSTRUCT.md`, and `../../audits/dspace-cataloger-v3.9.1-audit.json`.
