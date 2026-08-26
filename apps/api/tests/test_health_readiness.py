"""VERTICAL-023-A: liveness/readiness semantics for the API.

/health is process liveness only and must never touch PostgreSQL or DSpace.
/ready is the only surface allowed to depend on PostgreSQL, and must fail
closed (503) on connection failure or timeout without leaking driver
internals, secrets, or blocking indefinitely.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from cataloging_api import config as config_module
from cataloging_api.api import routes as routes_module
from cataloging_api.db.session import get_session
from cataloging_api.dspace import (
    contract_governance,
    contract_resolution,
    contract_snapshot_store,
)
from cataloging_api.dspace.client import DSpaceClient, DSpaceError
from cataloging_api.dspace.contract_governance import derive_contract_health

KNOWN_SECRETS = {
    "POSTGRES_PASSWORD": "super-secret-postgres-password",
    "DATABASE_URL": "postgresql+psycopg://cataloging:super-secret@db:5432/cataloging",
    "CATALOG_REVIEW_TOKEN": "super-secret-review-token",
    "DSPACE_READ_PASSWORD": "super-secret-dspace-password",
    "SETTINGS_ENCRYPTION_KEY": "super-secret-encryption-key",
}


class _FakeSession:
    """Stands in for AsyncSession at the narrowest boundary the probe uses."""

    def __init__(self, *, error: Exception | None = None, delay: float = 0.0) -> None:
        self._error = error
        self._delay = delay
        self.execute_calls = 0

    async def execute(self, _statement):
        self.execute_calls += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error
        return None


def _client_with_session(fake_session: _FakeSession) -> TestClient:
    app = FastAPI()
    app.include_router(routes_module.router)

    async def _override_get_session() -> AsyncIterator[_FakeSession]:
        yield fake_session

    app.dependency_overrides[get_session] = _override_get_session
    return TestClient(app)


def test_health_reports_live_without_querying_the_database() -> None:
    fake_session = _FakeSession(error=AssertionError("health must not query the database"))
    client = _client_with_session(fake_session)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "LIVE", "dspace_mode": "read-only"}
    assert fake_session.execute_calls == 0


def test_ready_returns_200_with_database_ok_when_probe_succeeds() -> None:
    client = _client_with_session(_FakeSession())

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "READY",
        "components": [{"name": "database", "status": "READY", "detail_code": "DATABASE_OK"}],
    }


def test_ready_returns_503_with_database_unreachable_on_connection_failure() -> None:
    connection_error = OperationalError(
        "select 1", {}, Exception("connection to server at db:5432 refused")
    )
    client = _client_with_session(_FakeSession(error=connection_error))

    ready_response = client.get("/ready")

    assert ready_response.status_code == 503
    body = ready_response.json()
    assert body["status"] == "NOT_READY"
    assert body["components"] == [
        {"name": "database", "status": "NOT_READY", "detail_code": "DATABASE_UNREACHABLE"}
    ]
    # driver-level exception text (host/port/refusal detail) must never leak
    assert "5432" not in ready_response.text
    assert "refused" not in ready_response.text

    # liveness is unaffected by the same database outage
    assert client.get("/health").status_code == 200


def test_ready_times_out_quickly_instead_of_hanging(monkeypatch) -> None:
    overridden_settings = config_module.get_settings().model_copy(
        update={"readiness_database_timeout_seconds": 0.2}
    )
    monkeypatch.setattr(routes_module, "get_settings", lambda: overridden_settings)
    client = _client_with_session(_FakeSession(delay=5.0))

    started = time.monotonic()
    response = client.get("/ready")
    elapsed = time.monotonic() - started

    assert response.status_code == 503
    assert response.json()["components"][0]["detail_code"] == "DATABASE_UNREACHABLE"
    assert elapsed < 2.0


def test_health_and_ready_payloads_never_contain_known_secrets() -> None:
    error_session = _client_with_session(
        _FakeSession(error=OperationalError("select 1", {}, Exception("boom")))
    )
    ok_session = _client_with_session(_FakeSession())

    for client in (ok_session, error_session):
        for response in (client.get("/health"), client.get("/ready")):
            for secret_name, secret_value in KNOWN_SECRETS.items():
                assert secret_name not in response.text
                assert secret_value not in response.text


def _governance_snapshot(*, status: str, created_at: datetime) -> SimpleNamespace:
    """Minimal VERTICAL-022 snapshot stand-in, matching the fixture shape used by
    test_dspace_contract_governance.py, just enough for derive_contract_health."""
    return SimpleNamespace(
        snapshot_id=uuid.uuid4(),
        status=status,
        semantic_hash="a" * 64,
        complete=True,
        approved_hash=None,
        effective_hash=None,
        effective_canonical_json=None,
        resolution_surface=None,
        resolved_by=None,
        resolved_at=None,
        canonical_json={"fields": [], "bindings": []},
        warnings=[],
        created_at=created_at,
    )


def _forbid_mutation(boundary_name: str):
    async def _guard(*_args, **_kwargs):
        raise AssertionError(f"unexpected VERTICAL-022 mutation call: {boundary_name}")

    return _guard


def test_review_required_dspace_contract_does_not_mutate_governance_or_break_health(
    monkeypatch,
) -> None:
    """A degraded/REVIEW_REQUIRED VERTICAL-022 contract state must never reach any
    governance mutation boundary (baseline ACTIVE, snapshot persistence, evidence
    resolution, approve/promote/supersede) from health/readiness, and must not
    change /health or /ready semantics."""
    active = _governance_snapshot(
        status="ACTIVE", created_at=datetime(2026, 1, 1, tzinfo=UTC)
    )
    latest = _governance_snapshot(
        status="REVIEW_REQUIRED", created_at=datetime(2026, 1, 2, tzinfo=UTC)
    )
    degraded_health = derive_contract_health(active=active, latest=latest)
    assert degraded_health.status == "REVIEW_REQUIRED"

    monkeypatch.setattr(
        contract_governance, "approve_snapshot", _forbid_mutation("approve_snapshot")
    )
    monkeypatch.setattr(
        contract_snapshot_store, "persist_snapshot", _forbid_mutation("persist_snapshot")
    )
    monkeypatch.setattr(
        contract_resolution,
        "resolve_authoritative_evidence",
        _forbid_mutation("resolve_authoritative_evidence"),
    )

    client = _client_with_session(_FakeSession())

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_health_stays_live_when_dspace_is_unavailable(monkeypatch) -> None:
    """/health must never construct or call the DSpace client (liveness has no DSpace edge)."""

    def _unavailable(*_args, **_kwargs):
        raise DSpaceError("unavailable", "DSpace is unreachable")

    monkeypatch.setattr(DSpaceClient, "__init__", _unavailable)
    client = _client_with_session(_FakeSession())

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_health_and_ready_issue_no_writes(monkeypatch) -> None:
    """Guards against a probe regressing into anything beyond a read-only SELECT."""
    fake_session = _FakeSession()
    client = _client_with_session(fake_session)

    def _make_guard(method_name: str):
        def _guard(self, *args, **kwargs):
            raise AssertionError(f"unexpected {method_name} call from health/ready")

        return _guard

    for guarded_method in ("add", "commit", "flush", "delete", "merge"):
        monkeypatch.setattr(
            _FakeSession,
            guarded_method,
            _make_guard(guarded_method),
            raising=False,
        )

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
