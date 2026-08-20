# dspace-cataloger v3.9 — Lossless artifact preservation

Status: **PRESERVED — LOSSLESS MULTIPART REPRESENTATION**

The original `dspace-cataloger-v3.9.skill` package is preserved as ordered Base64 text parts because the repository connector used during migration could not safely transmit the binary package in a single request.

This representation is lossless. The original artifact is reconstructed by concatenating the parts in the exact order recorded in `manifest.json`, then Base64-decoding the result.

## Original artifact identity

- Version: `3.9`
- Original size: `122755` bytes
- Base64 length: `163676` characters
- SHA-256: `81e20a04162c8d6631eff7f5555e980102a68532d16e052731e015e1e615679e`
- ZIP integrity: `PASS`

## Reconstruction

From this directory, run:

```python
import base64, hashlib, json
from pathlib import Path

root = Path('.')
manifest = json.loads((root / 'manifest.json').read_text())
encoded = ''.join((root / part['file']).read_text() for part in manifest['parts'])
artifact = base64.b64decode(encoded, validate=True)
output = root / 'dspace-cataloger-v3.9.skill'
output.write_bytes(artifact)
sha256 = hashlib.sha256(artifact).hexdigest()
assert len(artifact) == manifest['sourceSizeBytes']
assert sha256 == manifest['sha256']
print(output, sha256)
```

Expected SHA-256:

```text
81e20a04162c8d6631eff7f5555e980102a68532d16e052731e015e1e615679e
```

## Part order

`manifest.json` is normative for reconstruction order. Its part entries also record each Git blob SHA-1, allowing each text part to be checked independently before reconstruction.

## Provenance

The source package was supplied by the project owner on 2026-08-20 and verified before repository preservation. No package member was edited or repackaged as part of this migration.
