#!/usr/bin/env bash
#
# VERTICAL-022 operational scheduler wrapper.
#
# Runs the existing, read-only DSpace contract synchronization job
# (`python -m cataloging_api.dspace.contract_job`) inside the existing
# Docker Compose `api` service -- the same invocation as `make contract-sync`
# -- and writes timestamped operational output to a log file.
#
# This script does not talk to DSpace directly, does not add a scheduler
# loop, does not write anything to DSpace, and does not approve, resolve,
# or promote any contract snapshot. It only invokes the existing job and
# reports its result and exit code.
#
# It is designed to be driven by a host-level cron entry on the
# VPS/Dokploy host (see docs/vertical-022-activation-runbook.md, step 8).
# Nothing in this repository installs that cron entry automatically.
#
# Configuration (all optional, no secrets belong here -- secrets flow to
# the `api` service through the deployment's `.env` / Dokploy environment,
# exactly as they already do for `docker compose up`):
#
#   COMPOSE                        docker compose invocation, default "docker compose".
#                                   Override to target a specific Dokploy-managed
#                                   compose project, e.g.:
#                                     COMPOSE="docker compose -p cataloging-assistant"
#   DSPACE_CONTRACT_SYNC_SERVICE   compose service name, default "api".
#   DSPACE_CONTRACT_SYNC_LOG_DIR   directory for operational logs, default
#                                   "<repo>/var/log/dspace-contract-sync".
#   DSPACE_CONTRACT_SYNC_LOG_FILE  log file path, default
#                                   "<log dir>/contract-sync.log".

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IFS=' ' read -r -a COMPOSE_CMD <<<"${COMPOSE:-docker compose}"
API_SERVICE="${DSPACE_CONTRACT_SYNC_SERVICE:-api}"
JOB_MODULE="cataloging_api.dspace.contract_job"

LOG_DIR="${DSPACE_CONTRACT_SYNC_LOG_DIR:-${REPO_ROOT}/var/log/dspace-contract-sync}"
LOG_FILE="${DSPACE_CONTRACT_SYNC_LOG_FILE:-${LOG_DIR}/contract-sync.log}"

mkdir -p "${LOG_DIR}"

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

log() {
  printf '%s %s\n' "$(timestamp)" "$1" | tee -a "${LOG_FILE}"
}

cd "${REPO_ROOT}"

log "dspace-contract-sync: start (compose='${COMPOSE_CMD[*]}' service='${API_SERVICE}' module='${JOB_MODULE}')"

# The job itself is read-only against DSpace (see
# cataloging_api/dspace/contract_job.py); this wrapper never calls any
# approval, resolution, or promotion endpoint and never runs any command
# other than the contract job below.
set +e
JOB_OUTPUT="$("${COMPOSE_CMD[@]}" run --rm "${API_SERVICE}" python -m "${JOB_MODULE}" 2>&1)"
JOB_EXIT_CODE=$?
set -e

if [ -n "${JOB_OUTPUT}" ]; then
  while IFS= read -r line; do
    log "job: ${line}"
  done <<<"${JOB_OUTPUT}"
fi

if [ "${JOB_EXIT_CODE}" -eq 0 ]; then
  log "dspace-contract-sync: completed (exit=${JOB_EXIT_CODE})"
else
  log "dspace-contract-sync: FAILED (exit=${JOB_EXIT_CODE}) -- see docs/vertical-022-activation-runbook.md section 9 for interpretation"
fi

exit "${JOB_EXIT_CODE}"
