# Reconstruct `dspace-cataloger-v3.9.1.skill`

The canonical release artifact is preserved as ordered Base64 segments. PR #26 exposed two connector-truncated uploads; the missing bytes are restored by the two explicit `.cont` files listed below. `manifest.json` is authoritative for order and observed segment lengths.

From this directory:

```bash
cat \
  dspace-cataloger-v3.9.1.skill.b64.part01 \
  dspace-cataloger-v3.9.1.skill.b64.part02 \
  dspace-cataloger-v3.9.1.skill.b64.part03 \
  dspace-cataloger-v3.9.1.skill.b64.part03.tail01 \
  dspace-cataloger-v3.9.1.skill.b64.part03.tail01.cont \
  dspace-cataloger-v3.9.1.skill.b64.part03.tail02 \
  dspace-cataloger-v3.9.1.skill.b64.part04 \
  dspace-cataloger-v3.9.1.skill.b64.part05 \
  dspace-cataloger-v3.9.1.skill.b64.part06 \
  dspace-cataloger-v3.9.1.skill.b64.part07 \
  dspace-cataloger-v3.9.1.skill.b64.part08 \
  dspace-cataloger-v3.9.1.skill.b64.part09 \
  dspace-cataloger-v3.9.1.skill.b64.part10 \
  dspace-cataloger-v3.9.1.skill.b64.part11 \
  dspace-cataloger-v3.9.1.skill.b64.part11.cont \
  dspace-cataloger-v3.9.1.skill.b64.part11.tail \
  | tr -d '\n' \
  > dspace-cataloger-v3.9.1.skill.b64

wc -c dspace-cataloger-v3.9.1.skill.b64
base64 --decode dspace-cataloger-v3.9.1.skill.b64 > dspace-cataloger-v3.9.1.skill
wc -c dspace-cataloger-v3.9.1.skill
sha256sum dspace-cataloger-v3.9.1.skill
unzip -t dspace-cataloger-v3.9.1.skill
```

Expected values:

- Base64 length: `174212`
- Decoded size: `130657` bytes
- SHA-256: `b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9`
- ZIP integrity: `PASS`

## Preservation repair

The two restored continuation lengths are:

- `dspace-cataloger-v3.9.1.skill.b64.part03.tail01.cont`: `1940` characters
- `dspace-cataloger-v3.9.1.skill.b64.part11.cont`: `5157` characters

Together they restore the `7097` Base64 characters identified as missing by review. GitHub's observed segment sizes, in the reconstruction order above, total exactly `174212` characters. The continuation contents were derived from the Base64 encoding of the canonical 130657-byte artifact whose local round-trip, checksum and ZIP integrity were validated before publication.

## Lineage note

The local v3.9 artifact used to construct the semantic patch has SHA-256 `76fdc4674ef6b58474d224742005fbf6d4e885db80545ab1d9aa7a3e4e01c06c`, while the repository-preserved v3.9 artifact has SHA-256 `81e20a04162c8d6631eff7f5555e980102a68532d16e052731e015e1e615679e`.

This variance is recorded as `SOURCE_VARIANCE_RECORDED`. No byte-identical lineage is claimed between those two v3.9 artifacts; v3.9.1 is independently identified by its checksum above.
