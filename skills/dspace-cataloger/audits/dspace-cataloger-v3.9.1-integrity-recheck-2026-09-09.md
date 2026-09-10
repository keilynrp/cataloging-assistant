# dspace-cataloger v3.9.1 — integrity recheck

Date: 2026-09-09

## Result

**FAIL — recovery required.**

The repository's ordered Base64 segments decode successfully, and the resulting
archive has the size recorded in `manifest.json` (`130657` bytes). Its computed
SHA-256 is nevertheless:

```text
b1b1e91bf2d451b8caa4db7560269052bba6719ca1076eb35b06b5ab1ad9462c
```

This does not equal the manifest's claimed SHA-256:

```text
b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9
```

The extracted `assets/dspace-cataloguing-profile-v3.json` is also not valid
UTF-8/JSON. ZIP container readability is not sufficient to validate a governed
skill artifact.

## Scope and preservation

- No existing v3.9.1 Base64 segment, manifest, or historical audit was changed.
- The prior audit remains historical evidence of its original claim; this file
  records the later recheck result.
- v3.9.1 must not be declared current, canonical, or adopted until recovery.
- No v3.9.2 release was created from this unverified base.

## Recovery gate

To restore adoption eligibility, obtain the complete original
`dspace-cataloger-v3.9.1.skill` from provenance, then verify all of the
following before publishing a new preservation record:

1. SHA-256 equals the claimed v3.9.1 hash, or provenance records a different
   authoritative hash.
2. ZIP integrity passes.
3. Every packaged JSON file is valid UTF-8 and parses successfully.
4. The complete artifact, reconstruction manifest, checksum, and independent
   audit are committed together.

Only after that gate can a successor such as v3.9.2 add the ORCID identifier
classification rule and GR23 fixture.
