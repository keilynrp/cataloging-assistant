# VERTICAL-022 — Activation runbook

## Objective

Activate the DSpace contract synchronization pipeline against the configured production-like environment without weakening the human-approval and fail-closed safeguards established in VERTICAL-022.

This runbook assumes the repository `main` already contains migrations through `0024`, the authenticated read-only client, authoritative 204 evidence resolution, resolution inheritance, and `python -m cataloging_api.dspace.contract_job`.

## Safety invariants

- DSpace remains read-only for contract synchronization.
- The only POST sent to DSpace is `/authn/login` for authentication.
- No scheduled job may approve or promote a baseline.
- HTTP 204 from `traditional/sections` remains an unobservable surface, never an empty form.
- Raw HAL+JSON and observed semantic hashes remain immutable.
- A baseline can become ACTIVE only through explicit human approval.
- Automatic inheritance is allowed only after exact reconciliation against the ACTIVE effective contract.

## 1. Deploy current `main`

Deploy the commit that contains VERTICAL-022 through Slice 1F and the contract provenance fix.

Expected runtime contract label:

```text
dspace-cataloger-v3.9.1
```

## 2. Configure deployment secrets

The API service must receive these values through the deployment environment or secret manager:

```text
DSpace_BASE_URL=http://132.248.101.240:8080/server/api
DSpace_PILOT_COLLECTION_UUID=e9a8f44f-a8d3-4d22-b02a-cf590285bac6
DSpace_READ_USERNAME=<read-only DSpace user>
DSpace_READ_PASSWORD=<secret>
CATALOG_REVIEW_TOKEN=<existing long random review token>
```

Do not commit real credentials to `.env`, GitHub, logs, screenshots, or this repository.

## 3. Apply database migrations

From the repository host/runtime:

```bash
make migrate
```

Equivalent Docker Compose command:

```bash
docker compose run --rm api alembic upgrade head
```

Expected Alembic head includes migration `0024`.

If the command fails, stop activation. Do not run the contract job against a schema older than `0024`.

## 4. Run the first authenticated contract observation

```bash
make contract-sync
```

Equivalent:

```bash
docker compose run --rm api python -m cataloging_api.dspace.contract_job
```

The command prints one JSON object. Preserve that JSON in the deployment change record.

Before an ACTIVE baseline exists, the expected health is:

```text
contract_health = BASELINE_REQUIRED
```

The snapshot may still be incomplete at the observed layer because the live DSpace instance returns HTTP 204 for `active_submission_sections`.

## 5. Resolve authoritative HTTP 204 evidence

Use the governed `resolve-evidence` API only after confirming that the current snapshot is the one produced by the authenticated run and that the stored raw observation proves:

```json
{
  "_observation": {
    "observable": false,
    "statusCode": 204
  }
}
```

The authoritative effective contract must reconcile exactly to:

```text
traditionalpageone = 44 bindings
traditionalpagetwo = 12 bindings
total = 56 bindings
unique metadata keys = 54
```

Known evidence anchors from the authenticated reconciliation:

```text
source export semantic hash:
8260b2023b7b417f3056d3724664869f96cb613371c673517d6b7400af2a0b1c

56/56 reconciliation hash:
5b549a16307354b84b9327325532755877a622e323573616e92c8a0dee93ea92

effective canonical hash:
336972fc4461fce821ef8f9625087de864102ce2b2e7d411cd0daadaf3d9014d
```

Resolving evidence must leave the snapshot in `BASELINE_REVIEW_REQUIRED`; it must not make it ACTIVE.

## 6. Human baseline approval

Approve the resolved snapshot with the review-token protected approval endpoint and the exact effective hash returned by the resolved snapshot.

Approval must record:

- reviewer identity;
- approval timestamp;
- optional approval note;
- exact approved hash.

After approval, query:

```text
GET /api/dspace-contract/status
```

Expected health:

```text
SYNCED
```

and one, and only one, snapshot must have status `ACTIVE`.

## 7. Prove resolution inheritance

Run a second independent observation:

```bash
make contract-sync
```

Expected result when nothing changed in DSpace:

```text
snapshot_status = NO_CHANGE
resolution_inherited = true
contract_health = SYNCED
```

The governed hash must equal the ACTIVE baseline hash.

If the result is `REVIEW_REQUIRED` or `DRIFT_DETECTED`, do not enable the scheduler yet. Inspect the recorded changes first.

## 8. Enable the daily scheduler

Enable scheduling only after Step 7 succeeds.

### 8.1 Repository-managed wrapper

The repository provides `scripts/dspace-contract-sync.sh`, a thin, auditable wrapper
around the exact command from Step 4 (`make contract-sync` /
`docker compose run --rm api python -m cataloging_api.dspace.contract_job`). The
wrapper:

- runs under `set -euo pipefail`;
- executes the job through the existing Docker Compose `api` service, never DSpace
  directly;
- runs the read-only contract job and nothing else — no approval, resolution, or
  promotion call, no scheduler loop, no other command;
- returns the contract job's own exit code (`0` on a completed run — regardless of
  `contract_health` — non-zero on a job/auth/network failure such as a missing
  credential or an unhandled exception);
- writes timestamped, append-only operational output to a log file;
- reads its Docker Compose invocation and service name from environment variables
  (`COMPOSE`, `DSPACE_CONTRACT_SYNC_SERVICE`) so a Dokploy-managed compose project
  name can be supplied without editing the script or committing anything — no
  secret is read, set, or logged by the wrapper itself; DSpace credentials continue
  to flow to the `api` service exclusively through the deployment's `.env` /
  Dokploy environment, exactly as they already do for `docker compose up`.

Nothing in the repository installs a cron entry automatically. Installing the
schedule on the VPS/Dokploy host is a manual, opt-in step (8.2).

### 8.2 Installation (manual, opt-in)

On the VPS/Dokploy host, from the deployed repository checkout:

```bash
chmod +x scripts/dspace-contract-sync.sh
crontab -e
```

Add a line conceptually equivalent to:

```cron
CRON_TZ=America/Mexico_City
0 3 * * * /path/to/cataloging-assistant/scripts/dspace-contract-sync.sh
```

If the host's cron does not support the `CRON_TZ` prefix, either configure the
crond service timezone to `America/Mexico_City` or translate `03:00
America/Mexico_City` into the cron daemon's actual timezone before writing the
entry. Confirm which one applies before enabling the schedule — do not guess.

If Dokploy exposes its own scheduled-task/cron feature for the application, point
it at the same script path and the same daily cadence instead of maintaining a
duplicate host crontab entry. Do not run the job as a long-lived process or as a
loop inside FastAPI.

### 8.3 Manual verification

Before trusting the installed schedule, run the wrapper once by hand exactly as
cron would invoke it:

```bash
/path/to/cataloging-assistant/scripts/dspace-contract-sync.sh; echo "exit=$?"
```

Confirm:

- the exit code is `0`;
- the printed/logged JSON shows `contract_health = SYNCED`, `snapshot_status =
  NO_CHANGE`, `resolution_inherited = true` (per Step 7);
- a new line was appended to the log file (8.4).

### 8.4 Log inspection

The wrapper writes to `var/log/dspace-contract-sync/contract-sync.log` under the
repository checkout by default (override with `DSPACE_CONTRACT_SYNC_LOG_DIR` /
`DSPACE_CONTRACT_SYNC_LOG_FILE`). This path is git-ignored; it is operational
output, not repository content.

```bash
tail -f /path/to/cataloging-assistant/var/log/dspace-contract-sync/contract-sync.log
```

Each run writes a `start` line, one `job:` line per line of job output (the job's
JSON result), and a `completed` or `FAILED` summary line, each prefixed with a UTC
timestamp. See Section 9 for how to interpret the JSON result.

### 8.5 Removal / disable procedure

To disable the schedule without touching governance state:

```bash
crontab -e   # remove or comment out the dspace-contract-sync.sh line
```

or, if configured through Dokploy's scheduler feature, disable/delete the
scheduled task there instead. Disabling the schedule:

- does not delete snapshots, raw pages, change records, or the last ACTIVE
  baseline;
- does not require a database change or a code deploy;
- can be reversed by re-adding the same cron/Dokploy entry.

To re-run a one-off observation without a schedule, invoke the wrapper (or `make
contract-sync`) manually at any time — it is safe to run ad hoc.

## 9. Operational interpretation

- `SYNCED` + `NO_CHANGE` + `resolution_inherited=true`: healthy, no action.
- `DRIFT_DETECTED`: non-breaking observable change; review before promotion.
- `REVIEW_REQUIRED`: material change, failed inheritance, or incomplete observation; human review required.
- `BASELINE_REQUIRED`: no approved ACTIVE baseline exists.
- job/auth/network failure: retain the last ACTIVE baseline and investigate; never infer removals from the failed run.

## 10. Rollback / stop conditions

Disable the scheduler immediately if any of the following occurs:

- authentication begins failing;
- DSpace changes the active definition away from `traditional`;
- metadata registry coverage no longer reconciles;
- the 56-binding form reconciliation fails;
- multiple ACTIVE snapshots are ever observed;
- migrations are not at head;
- repeated jobs return `REVIEW_REQUIRED` without an understood cause.

Stopping the scheduler must not delete snapshots, raw pages, change records, or the last ACTIVE baseline.
