"""VERTICAL-024-B: structural regression coverage for the governed restart policy.

`docs/governance/VERTICAL-024-A-RECOVERY-POLICY-CONTRACT.md` selects
`restart: unless-stopped` as the approved recovery policy for `postgres`,
`api`, and `web` in the repository-managed `compose.yaml`. This module
parses the Compose YAML structurally (not via string search) so that
comments, unrelated text, or reordering cannot produce a false positive,
and asserts the policy plus the invariants VERTICAL-024-B must preserve
unchanged: the PostgreSQL volume/healthcheck, the API readiness
dependency, and the web bind contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = REPO_ROOT / "compose.yaml"

GOVERNED_SERVICES = ("postgres", "api", "web")
EXPECTED_RESTART_POLICY = "unless-stopped"


def _load_compose() -> dict:
    with COMPOSE_PATH.open("r", encoding="utf-8") as fh:
        document = yaml.safe_load(fh)
    assert isinstance(document, dict), "compose.yaml must parse to a mapping"
    return document


def _service(document: dict, name: str) -> dict:
    services = document.get("services")
    assert isinstance(services, dict), "compose.yaml must declare a services mapping"
    service = services.get(name)
    assert isinstance(service, dict), f"service '{name}' must be a mapping"
    return service


@pytest.fixture(scope="module")
def compose_document() -> dict:
    return _load_compose()


@pytest.mark.parametrize("service_name", GOVERNED_SERVICES)
def test_governed_service_declares_unless_stopped(compose_document: dict, service_name: str) -> None:
    service = _service(compose_document, service_name)
    assert service.get("restart") == EXPECTED_RESTART_POLICY


@pytest.mark.parametrize("service_name", GOVERNED_SERVICES)
def test_governed_service_restart_is_not_absent_null_or_no(
    compose_document: dict, service_name: str
) -> None:
    service = _service(compose_document, service_name)
    restart = service.get("restart")
    assert restart is not None, f"service '{service_name}' must declare a restart policy"
    assert restart != "no", f"service '{service_name}' must not use restart: \"no\""
    assert "restart" in service, f"service '{service_name}' is missing the restart key entirely"


def test_postgres_volume_mapping_is_unchanged(compose_document: dict) -> None:
    postgres = _service(compose_document, "postgres")
    volumes = postgres.get("volumes")
    assert volumes == ["cataloging_postgres:/var/lib/postgresql/data"]

    top_level_volumes = compose_document.get("volumes")
    assert isinstance(top_level_volumes, dict)
    assert "cataloging_postgres" in top_level_volumes


def test_postgres_healthcheck_is_preserved(compose_document: dict) -> None:
    postgres = _service(compose_document, "postgres")
    healthcheck = postgres.get("healthcheck")
    assert isinstance(healthcheck, dict)
    assert healthcheck.get("test") == [
        "CMD-SHELL",
        "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}",
    ]
    assert healthcheck.get("interval") == "3s"
    assert healthcheck.get("timeout") == "3s"
    assert healthcheck.get("retries") == 20


def test_api_depends_on_healthy_postgres(compose_document: dict) -> None:
    api = _service(compose_document, "api")
    depends_on = api.get("depends_on")
    assert isinstance(depends_on, dict)
    postgres_dependency = depends_on.get("postgres")
    assert isinstance(postgres_dependency, dict)
    assert postgres_dependency.get("condition") == "service_healthy"


def test_web_bind_contract_is_preserved(compose_document: dict) -> None:
    web = _service(compose_document, "web")
    environment = web.get("environment")
    assert isinstance(environment, dict)
    assert environment.get("HOSTNAME") == "0.0.0.0"
    assert environment.get("PORT") == "3000"
