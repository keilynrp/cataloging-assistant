"""VERTICAL-023-B: black-box regression coverage for scripts/production-smoke.sh.

The script is a repository-managed, read-only deployment smoke test. It is not
part of the Python package -- it is exercised here as a black box via
subprocess, with fake `docker` and `curl` executables on PATH standing in for
the real Compose stack and public URLs. No test talks to a real container,
a real network, or real DSpace/VERTICAL-022 state.
"""

from __future__ import annotations

import http.server
import os
import re
import stat
import subprocess
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "production-smoke.sh"

_FAKE_DOCKER = r"""#!/usr/bin/env python3
import json
import os
import sys
import time

args_file = os.environ.get("FAKE_DOCKER_ARGS_FILE")
if args_file:
    with open(args_file, "a") as fh:
        fh.write(" ".join(sys.argv[1:]) + "\n")

argv = sys.argv[1:]

if argv[:2] == ["compose", "ps"]:
    service = argv[2]
    state = os.environ.get(f"FAKE_COMPOSE_STATE_{service.upper()}", "running")
    if state == "missing":
        sys.exit(0)
    print(json.dumps({"State": state, "Service": service}))
    sys.exit(0)

if argv[:3] == ["compose", "exec", "-T"]:
    url = next((a for a in argv if a.startswith("http://")), "")

    defaults = {
        "FAKE_DSPACE": "ACTIVE",
        "FAKE_API_HEALTH": "LIVE",
        "FAKE_API_READY": "READY",
        "FAKE_WEB": "",
    }
    if "dspace-contract/status" in url:
        prefix = "FAKE_DSPACE"
    elif url.endswith("/health"):
        prefix = "FAKE_API_HEALTH"
    elif url.endswith("/ready"):
        prefix = "FAKE_API_READY"
    elif url.startswith("http://web:3000") or ":3000" in url:
        prefix = "FAKE_WEB"
    else:
        sys.exit(1)

    delay = float(os.environ.get(f"{prefix}_DELAY", "0"))
    if delay:
        time.sleep(delay)

    exit_code = int(os.environ.get(f"{prefix}_EXIT", "0"))
    if exit_code != 0:
        sys.exit(exit_code)

    http_status = os.environ.get(f"{prefix}_HTTP_STATUS", "200")
    body_status = os.environ.get(f"{prefix}_BODY_STATUS", defaults[prefix])
    print(f"HTTP_STATUS={http_status}")
    if body_status:
        print(f"BODY_STATUS={body_status}")
    sys.exit(0)

sys.exit(1)
"""

_FAKE_CURL = r"""#!/usr/bin/env python3
import os
import sys
import time

args_file = os.environ.get("FAKE_CURL_ARGS_FILE")
if args_file:
    with open(args_file, "a") as fh:
        fh.write(" ".join(sys.argv[1:]) + "\n")

url = sys.argv[-1]
prefix = "FAKE_FRONTEND" if "frontend" in url else "FAKE_API_PUBLIC"

delay = float(os.environ.get(f"{prefix}_DELAY", "0"))
if delay:
    time.sleep(delay)

exit_code = int(os.environ.get(f"{prefix}_EXIT", "0"))
if exit_code != 0:
    sys.exit(exit_code)

sys.stdout.write(os.environ.get(f"{prefix}_HTTP_STATUS", "200"))
sys.exit(0)
"""

DEFAULT_ENV = {
    "SMOKE_PUBLIC_FRONTEND_URL": "http://frontend.smoke-test.invalid/",
    "SMOKE_PUBLIC_API_URL": "http://api.smoke-test.invalid/",
    "SMOKE_CONNECT_TIMEOUT_SECONDS": "2",
    "SMOKE_HTTP_TIMEOUT_SECONDS": "2",
}

KNOWN_SECRETS = {
    "POSTGRES_PASSWORD": "super-secret-postgres-password",
    "DATABASE_URL": "postgresql+psycopg://cataloging:super-secret@db:5432/cataloging",
    "CATALOG_REVIEW_TOKEN": "super-secret-review-token",
    "DSPACE_READ_PASSWORD": "super-secret-dspace-password",
}


def _write_fake(bin_dir: Path, name: str, source: str) -> None:
    fake = bin_dir / name
    fake.write_text(source)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _run_smoke(
    tmp_path: Path,
    env_overrides: dict[str, str] | None = None,
    timeout: float = 40,
) -> tuple[subprocess.CompletedProcess, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake(bin_dir, "docker", _FAKE_DOCKER)
    _write_fake(bin_dir, "curl", _FAKE_CURL)

    docker_args_file = tmp_path / "docker-args.txt"
    curl_args_file = tmp_path / "curl-args.txt"

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["FAKE_DOCKER_ARGS_FILE"] = str(docker_args_file)
    env["FAKE_CURL_ARGS_FILE"] = str(curl_args_file)
    env.update(DEFAULT_ENV)
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )
    return result, docker_args_file, curl_args_file


# --- static / style checks, mirroring test_dspace_contract_sync_script.py ---


def test_script_exists_and_is_executable() -> None:
    assert SCRIPT_PATH.is_file()
    mode = SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "smoke script must be executable (chmod +x)"


def test_script_syntax_is_valid() -> None:
    result = subprocess.run(["bash", "-n", str(SCRIPT_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_script_uses_strict_mode() -> None:
    content = SCRIPT_PATH.read_text()
    assert "set -euo pipefail" in content


def test_script_never_disables_tls_or_dumps_secrets_statically() -> None:
    content = SCRIPT_PATH.read_text()
    # Only the executable lines matter here -- the header comment documents
    # these exact tokens as things the script must NOT do.
    code_lines = "\n".join(
        line for line in content.splitlines() if not line.strip().startswith("#")
    )
    forbidden = (
        "--insecure",
        "-k ",
        "printenv",
        "compose config",
        ".env",
        "approve",
        "resolve-evidence",
        "promote",
        "restart",
        "docker compose down",
        "docker compose rm",
        "crontab",
        "while true",
    )
    for token in forbidden:
        assert token not in code_lines, f"smoke script must not reference {token!r}"


def test_script_probes_web_from_another_service_not_localhost() -> None:
    content = SCRIPT_PATH.read_text()
    assert "http://${WEB_SERVICE}:3000/" in content
    assert "127.0.0.1:3000" not in content


# --- behavioral checks (required tests 1-10) ---


def test_1_all_mandatory_checks_pass_yields_exit_zero(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    for line in (
        "PASS compose_services",
        "PASS api_liveness",
        "PASS api_readiness",
        "PASS web_internal",
        "PASS public_frontend",
        "PASS public_api",
        "RESULT PASS",
    ):
        assert line in result.stdout


def test_2_api_health_failure_is_non_zero(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(tmp_path, {"FAKE_API_HEALTH_EXIT": "1"})
    assert result.returncode != 0
    assert "FAIL api_liveness" in result.stdout
    assert "RESULT FAIL" in result.stdout


def test_3_api_ready_503_is_non_zero(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(
        tmp_path,
        {"FAKE_API_READY_HTTP_STATUS": "503", "FAKE_API_READY_BODY_STATUS": "NOT_READY"},
    )
    assert result.returncode != 0
    assert "FAIL api_readiness" in result.stdout
    assert "RESULT FAIL" in result.stdout


def test_4_web_up_but_web_3000_unreachable_is_non_zero(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(
        tmp_path,
        {
            "FAKE_COMPOSE_STATE_WEB": "running",
            "FAKE_WEB_EXIT": "1",
        },
    )
    assert result.returncode != 0
    assert "FAIL web_internal WEB_INTERNAL_UNREACHABLE" in result.stdout
    assert "RESULT FAIL" in result.stdout


def test_5_public_frontend_502_is_non_zero(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(tmp_path, {"FAKE_FRONTEND_HTTP_STATUS": "502"})
    assert result.returncode != 0
    assert "FAIL public_frontend PUBLIC_FRONTEND_BAD_GATEWAY" in result.stdout
    assert "RESULT FAIL" in result.stdout


def test_6_public_api_failure_is_non_zero(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(tmp_path, {"FAKE_API_PUBLIC_EXIT": "1"})
    assert result.returncode != 0
    assert "FAIL public_api" in result.stdout
    assert "RESULT FAIL" in result.stdout


@pytest.mark.parametrize("degraded_status", ["REVIEW_REQUIRED", "STALE_CHECK_FAILED"])
def test_7_degraded_vertical_022_is_warn_only(tmp_path: Path, degraded_status: str) -> None:
    result, docker_args_file, _ = _run_smoke(
        tmp_path, {"FAKE_DSPACE_BODY_STATUS": degraded_status}
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"WARN dspace_contract {degraded_status}" in result.stdout
    assert "RESULT PASS" in result.stdout

    invoked = docker_args_file.read_text()
    for forbidden in ("approve", "resolve-evidence", "/promote", "snapshot"):
        assert forbidden not in invoked


def test_dspace_contract_unobservable_is_warn_only(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(tmp_path, {"FAKE_DSPACE_EXIT": "1"})
    assert result.returncode == 0
    assert "WARN dspace_contract UNOBSERVABLE" in result.stdout
    assert "RESULT PASS" in result.stdout


def test_8_secret_looking_values_never_appear_in_output(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(tmp_path, dict(KNOWN_SECRETS))
    combined = result.stdout + result.stderr
    for secret_value in KNOWN_SECRETS.values():
        assert secret_value not in combined


def test_9_missing_mandatory_service_cannot_yield_exit_zero(tmp_path: Path) -> None:
    result, _, _ = _run_smoke(tmp_path, {"FAKE_COMPOSE_STATE_POSTGRES": "missing"})
    assert result.returncode != 0
    assert "FAIL compose_services" in result.stdout
    assert "PASS compose_services" not in result.stdout
    assert "RESULT FAIL" in result.stdout


def test_10_hung_internal_probe_terminates_within_a_bounded_interval(tmp_path: Path) -> None:
    start = time.monotonic()
    result, _, _ = _run_smoke(
        tmp_path,
        {
            "FAKE_WEB_DELAY": "999",
            "SMOKE_CONNECT_TIMEOUT_SECONDS": "1",
            "SMOKE_HTTP_TIMEOUT_SECONDS": "1",
        },
        timeout=20,
    )
    elapsed = time.monotonic() - start

    assert elapsed < 15, f"smoke script did not terminate within a bounded interval ({elapsed}s)"
    assert result.returncode != 0
    assert "FAIL web_internal WEB_INTERNAL_UNREACHABLE" in result.stdout
    assert "RESULT FAIL" in result.stdout


def test_public_urls_are_overridable_and_actually_used(tmp_path: Path) -> None:
    _, _, curl_args_file = _run_smoke(
        tmp_path,
        {
            "SMOKE_PUBLIC_FRONTEND_URL": "http://frontend.custom.invalid/",
            "SMOKE_PUBLIC_API_URL": "http://api.custom.invalid/",
        },
    )
    invoked = curl_args_file.read_text()
    assert "http://frontend.custom.invalid/" in invoked
    assert "http://api.custom.invalid/health" in invoked


def test_public_api_health_path_is_not_duplicated_when_already_present(tmp_path: Path) -> None:
    _, _, curl_args_file = _run_smoke(
        tmp_path,
        {"SMOKE_PUBLIC_API_URL": "http://api.custom.invalid/health"},
    )
    invoked = curl_args_file.read_text()
    assert "http://api.custom.invalid/health" in invoked
    assert "http://api.custom.invalid/health/health" not in invoked


class _RedirectToBadGatewayHandler(http.server.BaseHTTPRequestHandler):
    """A real HTTP server: /redirect-to-502 -> 302 -> /bad-gateway -> 502.

    Used with the REAL system curl (not the fake) to prove end-to-end that a
    public probe follows a redirect and evaluates the FINAL status code,
    rather than treating the initial 3xx as a pass.
    """

    def log_message(self, *args: object) -> None:  # noqa: D401 -- silence server logs
        pass

    def do_GET(self) -> None:  # noqa: N802 -- required BaseHTTPRequestHandler name
        if self.path == "/redirect-to-502":
            self.send_response(302)
            self.send_header("Location", "/bad-gateway")
            self.end_headers()
        elif self.path == "/bad-gateway":
            self.send_response(502)
            self.end_headers()
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def test_public_redirect_to_final_bad_gateway_is_fail(tmp_path: Path) -> None:
    server = http.server.HTTPServer(("127.0.0.1", 0), _RedirectToBadGatewayHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _write_fake(bin_dir, "docker", _FAKE_DOCKER)
        # Deliberately do NOT fake `curl` here -- the real system curl must
        # actually follow the redirect and report the final status code.

        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["FAKE_DOCKER_ARGS_FILE"] = str(tmp_path / "docker-args.txt")
        env["SMOKE_PUBLIC_FRONTEND_URL"] = f"http://127.0.0.1:{port}/redirect-to-502"
        env["SMOKE_PUBLIC_API_URL"] = f"http://127.0.0.1:{port}/health"
        env["SMOKE_CONNECT_TIMEOUT_SECONDS"] = "3"
        env["SMOKE_HTTP_TIMEOUT_SECONDS"] = "3"

        result = subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert "FAIL public_frontend PUBLIC_FRONTEND_BAD_GATEWAY" in result.stdout, result.stdout
    assert "PASS public_api" in result.stdout
    assert "RESULT FAIL" in result.stdout
    assert result.returncode != 0


class _RedirectToFinalRedirectHandler(http.server.BaseHTTPRequestHandler):
    """A real HTTP server: /redirect-to-3xx -> 302 -> /final-3xx (301, no
    further Location header, so curl cannot follow it any further).

    Used with the REAL system curl to prove that a FINAL status code that is
    still 3xx (i.e. the redirect chain terminates on a redirect response
    rather than resolving to a 2xx) is treated as a failure, not a pass.
    """

    def log_message(self, *args: object) -> None:  # noqa: D401 -- silence server logs
        pass

    def do_GET(self) -> None:  # noqa: N802 -- required BaseHTTPRequestHandler name
        if self.path == "/redirect-to-3xx":
            self.send_response(302)
            self.send_header("Location", "/final-3xx")
            self.end_headers()
        elif self.path == "/final-3xx":
            self.send_response(301)
            self.end_headers()
        elif self.path == "/health":
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


def test_public_final_redirect_status_is_fail(tmp_path: Path) -> None:
    server = http.server.HTTPServer(("127.0.0.1", 0), _RedirectToFinalRedirectHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        _write_fake(bin_dir, "docker", _FAKE_DOCKER)
        # Deliberately do NOT fake `curl` here -- the real system curl must
        # actually follow the redirect and report the final status code.

        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["FAKE_DOCKER_ARGS_FILE"] = str(tmp_path / "docker-args.txt")
        env["SMOKE_PUBLIC_FRONTEND_URL"] = f"http://127.0.0.1:{port}/redirect-to-3xx"
        env["SMOKE_PUBLIC_API_URL"] = f"http://127.0.0.1:{port}/health"
        env["SMOKE_CONNECT_TIMEOUT_SECONDS"] = "3"
        env["SMOKE_HTTP_TIMEOUT_SECONDS"] = "3"

        result = subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
    finally:
        server.shutdown()
        server.server_close()

    assert "FAIL public_frontend PUBLIC_FRONTEND_UNREACHABLE_301" in result.stdout, result.stdout
    assert "PASS public_api" in result.stdout
    assert "RESULT FAIL" in result.stdout
    assert result.returncode != 0


def test_script_follows_redirects_with_a_bounded_count_and_no_tls_bypass() -> None:
    content = SCRIPT_PATH.read_text()
    code_lines = "\n".join(
        line for line in content.splitlines() if not line.strip().startswith("#")
    )
    assert "--location" in code_lines
    assert "--max-redirs" in code_lines
    assert "--insecure" not in code_lines
    assert " -k " not in code_lines


def test_timeouts_have_a_safe_upper_bound_regardless_of_override() -> None:
    # Structural check (fast, no subprocess): an absurd override must be
    # clamped by the script itself, not trusted verbatim -- the behavioral
    # proof that a hung probe still terminates lives in test 10 above.
    content = SCRIPT_PATH.read_text()
    connect_max = int(re.search(r"MAX_CONNECT_TIMEOUT_SECONDS=(\d+)", content).group(1))
    http_max = int(re.search(r"MAX_HTTP_TIMEOUT_SECONDS=(\d+)", content).group(1))
    assert 0 < connect_max <= 60
    assert 0 < http_max <= 120
    assert "clamp_timeout" in content
