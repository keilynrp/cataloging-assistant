# VERTICAL-022 — Scheduled DSpace contract synchronization

## Purpose

Run one authenticated, read-only contract observation against the configured DSpace collection, materialize its snapshot, compare it with the approved ACTIVE baseline, and emit a machine-readable result.

The scheduled job never approves a baseline and never writes repository content to DSpace.

## Runtime command

From the API runtime/container:

```bash
python -m cataloging_api.dspace.contract_job
```

Required runtime settings:

```text
DSpace_BASE_URL=http://132.248.101.240:8080/server/api
DSpace_PILOT_COLLECTION_UUID=e9a8f44f-a8d3-4d22-b02a-cf590285bac6
DSPACE_READ_USERNAME=<read-only account>
DSPACE_READ_PASSWORD=<secret>
```

`DSPACE_READ_USERNAME` and `DSPACE_READ_PASSWORD` are consumed through the existing case-insensitive Settings model fields `dspace_read_username` / `dspace_read_password`. They must be supplied as deployment secrets and must not be committed.

## Recommended cadence

Start with one execution per day. Example cron expression:

```cron
0 3 * * *
```

The actual clock time follows the scheduler/container timezone. Configure the deployment scheduler explicitly if `03:00 America/Mexico_City` is desired.

For Dokploy or another deployment scheduler, invoke the runtime command in the existing API container rather than running a second long-lived scheduler inside FastAPI.

## Resolution inheritance rule

The target DSpace 7.6.6 instance currently returns HTTP 204 for:

```text
/config/submissiondefinitions/traditional/sections
```

After the first authoritative resolution is human-approved, later runs may inherit that resolution automatically only when all of the following are true:

1. the new run observes the same active definition (`traditional`);
2. no unresolved warning exists except the known `active_submission_sections` 204 condition;
3. the schema canonical set exactly matches the ACTIVE effective baseline;
4. the metadata registry canonical set exactly matches the ACTIVE effective baseline;
5. the new run independently reconstructs `traditionalpageone` + `traditionalpagetwo` from its own `submission_forms` payload;
6. the reconstructed 56 bindings exactly match the ACTIVE effective baseline.

If any condition fails, the resolution is not inherited and the snapshot remains fail-closed (`REVIEW_REQUIRED`).

## Expected output

The command prints one JSON object, for example:

```json
{
  "active_snapshot_id": "...",
  "contract_health": "SYNCED",
  "effective_hash": "...",
  "governed_hash": "...",
  "last_verified_at": "...",
  "observed_hash": "...",
  "resolution_inherited": true,
  "run_id": "...",
  "snapshot_id": "...",
  "snapshot_status": "NO_CHANGE",
  "warning_count": 2
}
```

`warning_count` may remain non-zero because the immutable observed snapshot still records the HTTP 204 limitation. `resolution_inherited=true` indicates that the approved effective contract was re-established from the new run under the strict inheritance rule.

## Operational interpretation

- `SYNCED` + `NO_CHANGE`: contract matches the ACTIVE baseline.
- `REVIEW_REQUIRED`: automatic inheritance failed or a material/high-severity drift was observed; do not auto-promote.
- `DRIFT_DETECTED`: non-breaking observable drift exists and requires review before promotion.
- `BASELINE_REQUIRED`: no ACTIVE baseline has yet been approved.

## Safety invariants

- no DSpace content writes;
- authentication POST is used only to obtain the read session JWT;
- raw HAL+JSON remains append-only;
- observed `semantic_hash` / `canonical_json` remain immutable;
- inherited resolution is explicitly linked to the ACTIVE snapshot that authorized it;
- no scheduled job can call the baseline approval endpoint;
- any material mismatch invalidates inheritance.
