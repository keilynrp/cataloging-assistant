"""Static and behavioral validation for scripts/dspace-contract-sync.sh.

The script itself is not part of the Python package -- it is a repository-managed
cron wrapper for `python -m cataloging_api.dspace.contract_job` (VERTICAL-022).
These tests exercise it as a black box via subprocess with a fake `docker` on
PATH, and statically check the safety invariants from the activation runbook.
"""

from __future__ import annotations

import os
import shlex
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "dspace-contract-sync.sh"

FAKE_DOCKER_TEMPLATE = """#!/usr/bin/env bash
echo "$@" >> {args_file}
echo {stdout}
exit {exit_code}
"""


def _write_fake_docker(bin_dir: Path, args_file: Path, exit_code: int, stdout: str) -> None:
    fake = bin_dir / "docker"
    fake.write_text(
        FAKE_DOCKER_TEMPLATE.format(
            args_file=shlex.quote(str(args_file)),
            stdout=shlex.quote(stdout),
            exit_code=exit_code,
        )
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _run_wrapper(
    tmp_path: Path, exit_code: int, stdout: str
) -> tuple[subprocess.CompletedProcess, Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    args_file = tmp_path / "args.txt"
    _write_fake_docker(bin_dir, args_file, exit_code, stdout)

    log_dir = tmp_path / "logs"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DSPACE_CONTRACT_SYNC_LOG_DIR"] = str(log_dir)

    result = subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result, log_dir, args_file


def test_script_exists_and_is_executable() -> None:
    assert SCRIPT_PATH.is_file()
    mode = SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "wrapper must be executable (chmod +x)"


def test_script_syntax_is_valid() -> None:
    result = subprocess.run(["bash", "-n", str(SCRIPT_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_script_uses_strict_mode() -> None:
    content = SCRIPT_PATH.read_text()
    assert "set -euo pipefail" in content


def test_script_invokes_the_contract_job_module_via_compose() -> None:
    content = SCRIPT_PATH.read_text()
    assert "cataloging_api.dspace.contract_job" in content
    assert "COMPOSE_CMD[@]" in content
    assert "run --rm" in content


_SYNCED_JSON = (
    '{"contract_health": "SYNCED", "snapshot_status": "NO_CHANGE", "resolution_inherited": true}'
)
_DRIFT_JSON = '{"contract_health": "DRIFT_DETECTED", "snapshot_status": "DIFF_DETECTED"}'


@pytest.mark.parametrize(
    ("fake_exit_code", "fake_stdout"),
    [
        (0, _SYNCED_JSON),
        (0, _DRIFT_JSON),
        (1, "dspace_read_credentials_required"),
        (7, "connection refused"),
    ],
)
def test_wrapper_propagates_job_exit_code(
    tmp_path: Path, fake_exit_code: int, fake_stdout: str
) -> None:
    result, log_dir, _ = _run_wrapper(tmp_path, fake_exit_code, fake_stdout)

    assert result.returncode == fake_exit_code

    log_file = log_dir / "contract-sync.log"
    assert log_file.is_file(), "wrapper must write a log file"
    log_content = log_file.read_text()
    assert fake_stdout in log_content
    assert "dspace-contract-sync: start" in log_content

    if fake_exit_code == 0:
        assert "completed (exit=0)" in log_content
    else:
        assert "FAILED" in log_content


def test_wrapper_writes_timestamped_lines(tmp_path: Path) -> None:
    _, log_dir, _ = _run_wrapper(tmp_path, 0, "{}")
    log_content = (log_dir / "contract-sync.log").read_text()
    lines = [line for line in log_content.splitlines() if line.strip()]
    assert lines
    for line in lines:
        timestamp = line.split(" ", 1)[0]
        assert timestamp.endswith("Z")
        assert timestamp.count("-") == 2
        assert "T" in timestamp


def test_wrapper_calls_compose_run_with_expected_arguments(tmp_path: Path) -> None:
    _, _, args_file = _run_wrapper(tmp_path, 0, "{}")
    invoked = args_file.read_text().strip()
    assert invoked == "compose run --rm api python -m cataloging_api.dspace.contract_job"


def test_wrapper_only_invokes_the_read_only_contract_job() -> None:
    """The wrapper must run exactly one command: the contract_job module.

    It must not call curl/httpie against the API, and must not reference any
    other cataloging_api module (e.g. an approval or resolution endpoint).
    """
    content = SCRIPT_PATH.read_text()
    for forbidden in ("curl ", "httpie", "wget ", "requests.", "resolve-evidence", "/approve"):
        assert forbidden not in content, f"wrapper must not reference {forbidden!r}"

    assert 'JOB_MODULE="cataloging_api.dspace.contract_job"' in content
    python_dash_m_invocations = [
        line
        for line in content.splitlines()
        if "python -m" in line and not line.strip().startswith("#")
    ]
    assert python_dash_m_invocations, "expected exactly one `python -m` invocation"
    for line in python_dash_m_invocations:
        assert '"${JOB_MODULE}"' in line, "the sole python -m target must be JOB_MODULE"


def test_wrapper_does_not_run_a_scheduler_loop() -> None:
    content = SCRIPT_PATH.read_text().lower()
    for forbidden in ("while true", "uvicorn", "fastapi", "apscheduler"):
        assert forbidden not in content


def test_wrapper_does_not_hardcode_credentials() -> None:
    content = SCRIPT_PATH.read_text()
    for suspicious in ("password=", "PASSWORD=", "token=", "TOKEN=", "secret=", "SECRET="):
        assert suspicious not in content, f"wrapper must not hardcode {suspicious!r}"
