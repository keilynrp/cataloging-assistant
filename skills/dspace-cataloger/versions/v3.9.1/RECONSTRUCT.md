# Reconstruct `dspace-cataloger-v3.9.1.skill`

The release artifact is preserved as Base64 text split into ordered parts. Two initially truncated segments are completed by explicit continuation files; this is intentional and recorded in `manifest.json`.

From this directory, reconstruct with:

```bash
cat \
  dspace-cataloger-v3.9.1.skill.b64.part01 \
  dspace-cataloger-v3.9.1.skill.b64.part02 \
  dspace-cataloger-v3.9.1.skill.b64.part03 \
  dspace-cataloger-v3.9.1.skill.b64.part03.tail01 \
  dspace-cataloger-v3.9.1.skill.b64.part03.tail02 \
  dspace-cataloger-v3.9.1.skill.b64.part04 \
  dspace-cataloger-v3.9.1.skill.b64.part05 \
  dspace-cataloger-v3.9.1.skill.b64.part06 \
  dspace-cataloger-v3.9.1.skill.b64.part07 \
  dspace-cataloger-v3.9.1.skill.b64.part08 \
  dspace-cataloger-v3.9.1.skill.b64.part09 \
  dspace-cataloger-v3.9.1.skill.b64.part10 \
  dspace-cataloger-v3.9.1.skill.b64.part11 \
  dspace-cataloger-v3.9.1.skill.b64.part11.tail \
  | tr -d '\n' \
  | base64 --decode \
  > dspace-cataloger-v3.9.1.skill

sha256sum dspace-cataloger-v3.9.1.skill
unzip -t dspace-cataloger-v3.9.1.skill
```

Expected values:

- Base64 length: `174212`
- Decoded size: `130657` bytes
- SHA-256: `b099ff6e3e15cf6f033b36ea9d3e2f265cff3811c092a31e6f9e7d74d1e483e9`
- ZIP integrity: `PASS`

## Lineage note

The local v3.9 artifact used to construct this patch has SHA-256 `76fdc4674ef6b58474d224742005fbf6d4e885db80545ab1d9aa7a3e4e01c06c`, while the repository-preserved v3.9 artifact has SHA-256 `81e20a04162c8d6631eff7f5555e980102a68532d16e052731e015e1e615679e`.

This variance is recorded explicitly in the release audit and manifest. No byte-identical lineage is claimed between those two v3.9 artifacts.
