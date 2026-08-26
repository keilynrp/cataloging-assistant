#!/usr/bin/env bash
#
# VERTICAL-023-B deployment smoke test.
#
# Read-only, manually-executed check that the deployed Docker/Dokploy stack
# is actually reachable through the paths production traffic uses -- not
# just that containers report "Up". It does not repair, restart, redeploy,
# or mutate anything: DSpace/VERTICAL-022 state is observed only, never
# approved, resolved, promoted, or snapshotted.
#
# Checks, in order (steps 1-6 are mandatory; step 7 is observational):
#   1. expected Compose services (api, web, postgres) are running;
#   2. API internal liveness  (GET /health  inside the api container);
#   3. API internal readiness (GET /ready   inside the api container);
#   4. web:3000 reachable from the api service (never from web itself);
#   5. public frontend URL responds without 502/503;
#   6. public API health URL responds without 502/503;
#   7. VERTICAL-022 DSpace contract status, read-only, WARN-only.
#
# Exit code is 0 only when every mandatory check (1-6) passes. A WARN on the
# observational DSpace check never affects the exit code.
#
# Configuration (all optional, no secrets belong here -- secrets continue to
# flow only through the existing deployment's .env / Dokploy environment):
#
#   COMPOSE                          docker compose invocation, default "docker compose".
#   SMOKE_API_SERVICE                compose service name, default "api".
#   SMOKE_WEB_SERVICE                compose service name, default "web".
#   SMOKE_POSTGRES_SERVICE           compose service name, default "postgres".
#   SMOKE_PUBLIC_FRONTEND_URL        default "https://catalog.inbounduxd.com/".
#   SMOKE_PUBLIC_API_URL             default "https://api.catalog.inbounduxd.com/"
#                                     (the liveness path is appended automatically).
#   SMOKE_CONNECT_TIMEOUT_SECONDS    default 5, clamped to [1, 30].
#   SMOKE_HTTP_TIMEOUT_SECONDS       default 10, clamped to [1, 60].
#
# Output is line-oriented and safe to keep as operational evidence:
#   PASS <check>
#   WARN <check> <detail_code>
#   FAIL <check> <detail_code>
#   RESULT PASS|FAIL
#
# This script never prints .env contents, `docker compose config`, full
# `printenv`, or raw command/exception text that could carry hosts,
# credentials, or connection strings -- only the stable fields above.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

IFS=' ' read -r -a COMPOSE_CMD <<<"${COMPOSE:-docker compose}"
API_SERVICE="${SMOKE_API_SERVICE:-api}"
WEB_SERVICE="${SMOKE_WEB_SERVICE:-web}"
POSTGRES_SERVICE="${SMOKE_POSTGRES_SERVICE:-postgres}"
PUBLIC_FRONTEND_URL="${SMOKE_PUBLIC_FRONTEND_URL:-https://catalog.inbounduxd.com/}"
PUBLIC_API_URL="${SMOKE_PUBLIC_API_URL:-https://api.catalog.inbounduxd.com/}"

# Upper bounds are enforced regardless of what the environment requests, so a
# misconfigured override can never turn this into an unbounded probe.
MAX_CONNECT_TIMEOUT_SECONDS=30
MAX_HTTP_TIMEOUT_SECONDS=60

clamp_timeout() {
  local value="$1" max="$2" default="$3"
  case "$value" in
    '' | *[!0-9]*)
      printf '%s' "$default"
      return
      ;;
  esac
  if [ "$value" -lt 1 ]; then
    printf '%s' "$default"
  elif [ "$value" -gt "$max" ]; then
    printf '%s' "$max"
  else
    printf '%s' "$value"
  fi
}

CONNECT_TIMEOUT="$(clamp_timeout "${SMOKE_CONNECT_TIMEOUT_SECONDS:-5}" "$MAX_CONNECT_TIMEOUT_SECONDS" 5)"
HTTP_TIMEOUT="$(clamp_timeout "${SMOKE_HTTP_TIMEOUT_SECONDS:-10}" "$MAX_HTTP_TIMEOUT_SECONDS" 10)"
# Hard wall-clock bound for any single external command (compose exec / curl),
# on top of curl's/urllib's own connect+read timeouts.
EXEC_BOUND=$((CONNECT_TIMEOUT + HTTP_TIMEOUT + 5))

declare -A CHECK_RESULTS
MANDATORY_CHECKS=(compose_services api_liveness api_readiness web_internal public_frontend public_api)

record() {
  local name="$1" status="$2" detail="${3:-}"
  CHECK_RESULTS["$name"]="$status"
  if [ "$status" = "PASS" ] || [ -z "$detail" ]; then
    printf '%s %s\n' "$status" "$name"
  else
    printf '%s %s %s\n' "$status" "$name" "$detail"
  fi
}

# Runs "$@", capturing combined stdout+stderr into OUT and the exit code into
# RC, without ever tripping `set -e`. Callers branch on RC explicitly so a
# single failed probe never aborts the rest of the smoke sequence.
run_capture() {
  set +e
  OUT="$("$@" 2>&1)"
  RC=$?
  set -e
}

# Read into a variable rather than executed directly, so this source never
# runs on the host -- only inside the target container via `python3 -c`.
read -r -d '' HTTP_PROBE_PY <<'PY' || true
import json
import sys
import urllib.error
import urllib.request

url, timeout = sys.argv[1], float(sys.argv[2])
try:
    request = urllib.request.Request(url, headers={"User-Agent": "production-smoke/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        status = response.status
        raw = response.read(4096)
except urllib.error.HTTPError as exc:
    status = exc.code
    raw = exc.read(4096) if hasattr(exc, "read") else b""
except Exception:
    print("HTTP_STATUS=ERROR")
    sys.exit(0)

print(f"HTTP_STATUS={status}")
body_status = "NA"
try:
    parsed = json.loads(raw.decode("utf-8", "replace"))
    if isinstance(parsed, dict) and isinstance(parsed.get("status"), str):
        body_status = parsed["status"]
except Exception:
    pass
print(f"BODY_STATUS={body_status}")
PY

read -r -d '' COMPOSE_STATE_PY <<'PY' || true
import json
import sys

lines = [line for line in sys.stdin.read().splitlines() if line.strip()]
if not lines:
    print("STATE=MISSING")
    sys.exit(0)

all_running = True
for line in lines:
    try:
        entry = json.loads(line)
    except Exception:
        print("STATE=UNKNOWN")
        sys.exit(0)
    if entry.get("State") != "running":
        all_running = False

print("STATE=RUNNING" if all_running else "STATE=NOT_RUNNING")
PY

extract_field() {
  # extract_field <field-name> <text>
  printf '%s\n' "$2" | sed -n "s/^${1}=//p" | head -n1
}

compose_exec_probe() {
  local url="$1"
  run_capture timeout "$EXEC_BOUND" "${COMPOSE_CMD[@]}" exec -T "$API_SERVICE" \
    python3 -c "$HTTP_PROBE_PY" "$url" "$HTTP_TIMEOUT"
}

check_compose_services() {
  local services=("$API_SERVICE" "$WEB_SERVICE" "$POSTGRES_SERVICE")
  local failed=()
  local svc
  for svc in "${services[@]}"; do
    run_capture timeout "$EXEC_BOUND" "${COMPOSE_CMD[@]}" ps "$svc" --format json
    if [ "$RC" -ne 0 ] || [ -z "$OUT" ]; then
      failed+=("$svc")
      continue
    fi
    local state
    state="$(printf '%s' "$OUT" | python3 -c "$COMPOSE_STATE_PY")"
    if [ "$state" != "STATE=RUNNING" ]; then
      failed+=("$svc")
    fi
  done

  if [ "${#failed[@]}" -eq 0 ]; then
    record compose_services PASS COMPOSE_SERVICES_RUNNING
  else
    local joined
    joined="$(
      IFS=,
      echo "${failed[*]}"
    )"
    record compose_services FAIL "COMPOSE_SERVICE_NOT_RUNNING:${joined}"
  fi
}

check_api_liveness() {
  compose_exec_probe "http://localhost:8000/health"
  if [ "$RC" -ne 0 ]; then
    record api_liveness FAIL API_LIVENESS_UNREACHABLE
    return
  fi
  local http_status body_status
  http_status="$(extract_field HTTP_STATUS "$OUT")"
  body_status="$(extract_field BODY_STATUS "$OUT")"
  if [ "$http_status" = "200" ] && [ "$body_status" = "LIVE" ]; then
    record api_liveness PASS PROCESS_OK
  else
    record api_liveness FAIL "API_LIVENESS_UNEXPECTED_${http_status:-ERROR}"
  fi
}

check_api_readiness() {
  compose_exec_probe "http://localhost:8000/ready"
  if [ "$RC" -ne 0 ]; then
    record api_readiness FAIL API_READINESS_UNREACHABLE
    return
  fi
  local http_status body_status
  http_status="$(extract_field HTTP_STATUS "$OUT")"
  body_status="$(extract_field BODY_STATUS "$OUT")"
  if [ "$http_status" = "200" ] && [ "$body_status" = "READY" ]; then
    record api_readiness PASS DATABASE_OK
  else
    record api_readiness FAIL "API_READINESS_NOT_READY_${http_status:-ERROR}"
  fi
}

check_web_internal() {
  # Must originate outside the web process itself (from the api service),
  # against the Compose DNS name -- never 127.0.0.1 inside the web container.
  compose_exec_probe "http://${WEB_SERVICE}:3000/"
  if [ "$RC" -ne 0 ]; then
    record web_internal FAIL WEB_INTERNAL_UNREACHABLE
    return
  fi
  local http_status
  http_status="$(extract_field HTTP_STATUS "$OUT")"
  case "$http_status" in
    2?? | 3??)
      record web_internal PASS WEB_INTERNAL_OK
      ;;
    *)
      record web_internal FAIL WEB_INTERNAL_UNREACHABLE
      ;;
  esac
}

public_http_check() {
  local name="$1" url="$2" ok_code="$3" bad_gateway_code="$4" unreachable_code="$5"
  # --location follows redirects so %{http_code} reflects the FINAL response,
  # not the initial 3xx -- otherwise a 301/302 to a broken destination
  # (502/503) would be misread as a pass. --max-redirs keeps the chain bounded;
  # TLS verification stays on (no -k/--insecure).
  run_capture timeout "$EXEC_BOUND" curl -sS -o /dev/null -w '%{http_code}' \
    --location --max-redirs 5 \
    --connect-timeout "$CONNECT_TIMEOUT" --max-time "$HTTP_TIMEOUT" -- "$url"
  if [ "$RC" -ne 0 ]; then
    record "$name" FAIL "$unreachable_code"
    return
  fi
  local code="$OUT"
  case "$code" in
    2?? | 3??)
      record "$name" PASS "$ok_code"
      ;;
    502 | 503)
      record "$name" FAIL "$bad_gateway_code"
      ;;
    *)
      record "$name" FAIL "${unreachable_code}_${code:-ERROR}"
      ;;
  esac
}

check_public_frontend() {
  public_http_check public_frontend "$PUBLIC_FRONTEND_URL" \
    PUBLIC_FRONTEND_OK PUBLIC_FRONTEND_BAD_GATEWAY PUBLIC_FRONTEND_UNREACHABLE
}

public_api_health_url() {
  local base="${1%/}"
  case "$base" in
    */health) printf '%s' "$base" ;;
    *) printf '%s/health' "$base" ;;
  esac
}

check_public_api() {
  local url
  url="$(public_api_health_url "$PUBLIC_API_URL")"
  public_http_check public_api "$url" \
    PUBLIC_API_OK PUBLIC_API_BAD_GATEWAY PUBLIC_API_UNREACHABLE
}

check_dspace_contract() {
  # VERTICAL-022 is the sole authority for DSpace contract state; this reads
  # the existing status endpoint and never approves, resolves, promotes, or
  # persists a snapshot. A degraded or unobservable status is WARN-only and
  # never affects the mandatory RESULT.
  compose_exec_probe "http://localhost:8000/api/dspace-contract/status"
  if [ "$RC" -ne 0 ]; then
    record dspace_contract WARN UNOBSERVABLE
    return
  fi
  local http_status body_status
  http_status="$(extract_field HTTP_STATUS "$OUT")"
  body_status="$(extract_field BODY_STATUS "$OUT")"
  if [ "$http_status" != "200" ] || [ -z "$body_status" ] || [ "$body_status" = "NA" ]; then
    record dspace_contract WARN UNOBSERVABLE
    return
  fi
  if [ "$body_status" = "ACTIVE" ]; then
    record dspace_contract PASS "$body_status"
  else
    record dspace_contract WARN "$body_status"
  fi
}

finalize() {
  local overall="PASS"
  local name status
  for name in "${MANDATORY_CHECKS[@]}"; do
    status="${CHECK_RESULTS[$name]:-}"
    if [ -z "$status" ]; then
      # A mandatory check that never recorded a result must never be treated
      # as a pass -- record it as a failure instead of silently skipping it.
      record "$name" FAIL CHECK_NOT_EXECUTED
      status="FAIL"
    fi
    if [ "$status" != "PASS" ]; then
      overall="FAIL"
    fi
  done

  printf 'RESULT %s\n' "$overall"
  if [ "$overall" = "PASS" ]; then
    exit 0
  fi
  exit 1
}

main() {
  check_compose_services
  check_api_liveness
  check_api_readiness
  check_web_internal
  check_public_frontend
  check_public_api
  check_dspace_contract
  finalize
}

main "$@"
