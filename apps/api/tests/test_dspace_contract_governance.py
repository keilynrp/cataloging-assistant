import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from cataloging_api.dspace.contract_governance import (
    ContractGovernanceError,
    derive_contract_health,
    validate_approval_transition,
)


def _snapshot(
    *,
    status: str,
    complete: bool = True,
    semantic_hash: str = "a" * 64,
    approved_hash: str | None = None,
    effective_hash: str | None = None,
    effective_canonical_json: dict | None = None,
    resolution_surface: str | None = None,
    resolved_by: str | None = None,
    resolved_at: datetime | None = None,
    fields: int = 56,
    bindings: int = 56,
    created_at: datetime | None = None,
):
    canonical = {
        "fields": [{"metadata": f"dc.test.{i}"} for i in range(fields)],
        "bindings": [{"bindingKey": str(i)} for i in range(bindings)],
    }
    return SimpleNamespace(
        snapshot_id=uuid.uuid4(),
        status=status,
        semantic_hash=semantic_hash,
        complete=complete,
        approved_hash=approved_hash,
        effective_hash=effective_hash,
        effective_canonical_json=effective_canonical_json,
        resolution_surface=resolution_surface,
        resolved_by=resolved_by,
        resolved_at=resolved_at,
        canonical_json=canonical,
        warnings=[],
        created_at=created_at or datetime(2026, 8, 26, tzinfo=timezone.utc),
    )


def test_without_active_snapshot_health_requires_baseline() -> None:
    latest = _snapshot(status="BASELINE_REVIEW_REQUIRED")
    health = derive_contract_health(active=None, latest=latest)
    assert health.status == "BASELINE_REQUIRED"
    assert health.active_hash is None
    assert health.metadata_field_count is None
    assert health.form_binding_count is None


def test_incomplete_first_check_does_not_claim_last_verified() -> None:
    latest = _snapshot(status="REVIEW_REQUIRED", complete=False)
    health = derive_contract_health(active=None, latest=latest)
    assert health.status == "BASELINE_REQUIRED"
    assert health.last_verified_at is None


def test_active_snapshot_health_reports_synced_contract_counts() -> None:
    active = _snapshot(status="ACTIVE", approved_hash="a" * 64, fields=54, bindings=56)
    health = derive_contract_health(active=active, latest=active)
    assert health.status == "SYNCED"
    assert health.active_hash == "a" * 64
    assert health.metadata_field_count == 54
    assert health.form_binding_count == 56


def test_resolved_active_health_uses_effective_contract() -> None:
    resolved_at = datetime(2026, 8, 26, 1, tzinfo=timezone.utc)
    effective = {
        "fields": [{"metadata": f"dc.live.{i}"} for i in range(54)],
        "bindings": [{"bindingKey": str(i)} for i in range(56)],
    }
    active = _snapshot(
        status="ACTIVE",
        complete=False,
        semantic_hash="a" * 64,
        approved_hash="b" * 64,
        effective_hash="b" * 64,
        effective_canonical_json=effective,
        resolution_surface="active_submission_sections",
        resolved_by="cataloger",
        resolved_at=resolved_at,
    )
    health = derive_contract_health(active=active, latest=active)
    assert health.status == "SYNCED"
    assert health.active_hash == "b" * 64
    assert health.metadata_field_count == 54
    assert health.form_binding_count == 56
    assert health.last_verified_at == resolved_at


def test_incomplete_latest_check_keeps_previous_verified_time() -> None:
    active_time = datetime(2026, 8, 25, tzinfo=timezone.utc)
    active = _snapshot(
        status="ACTIVE",
        approved_hash="a" * 64,
        created_at=active_time,
    )
    latest = _snapshot(
        status="REVIEW_REQUIRED",
        complete=False,
        semantic_hash="b" * 64,
        created_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
    )
    health = derive_contract_health(active=active, latest=latest)
    assert health.status == "REVIEW_REQUIRED"
    assert health.last_verified_at == active_time


def test_high_drift_health_requires_review_without_replacing_active() -> None:
    active = _snapshot(status="ACTIVE", approved_hash="a" * 64)
    latest = _snapshot(status="REVIEW_REQUIRED", semantic_hash="b" * 64)
    health = derive_contract_health(active=active, latest=latest)
    assert health.status == "REVIEW_REQUIRED"
    assert health.active_snapshot_id == active.snapshot_id
    assert health.latest_snapshot_id == latest.snapshot_id


def test_first_complete_candidate_can_be_approved_only_as_baseline() -> None:
    candidate = _snapshot(status="BASELINE_REVIEW_REQUIRED")
    assert (
        validate_approval_transition(
            candidate=candidate,
            active=None,
            expected_hash=candidate.semantic_hash,
        )
        == "baseline"
    )


def test_incomplete_snapshot_cannot_be_approved() -> None:
    candidate = _snapshot(status="BASELINE_REVIEW_REQUIRED", complete=False)
    with pytest.raises(ContractGovernanceError, match="incomplete_snapshot_cannot_be_approved"):
        validate_approval_transition(
            candidate=candidate,
            active=None,
            expected_hash=candidate.semantic_hash,
        )


def test_resolved_incomplete_snapshot_can_be_approved_by_effective_hash() -> None:
    candidate = _snapshot(
        status="BASELINE_REVIEW_REQUIRED",
        complete=False,
        effective_hash="b" * 64,
        effective_canonical_json={"fields": [], "bindings": []},
        resolution_surface="active_submission_sections",
        resolved_by="cataloger",
    )
    assert (
        validate_approval_transition(
            candidate=candidate,
            active=None,
            expected_hash="b" * 64,
        )
        == "baseline"
    )


def test_hash_mismatch_blocks_approval() -> None:
    candidate = _snapshot(status="BASELINE_REVIEW_REQUIRED")
    with pytest.raises(ContractGovernanceError, match="snapshot_hash_mismatch"):
        validate_approval_transition(
            candidate=candidate,
            active=None,
            expected_hash="b" * 64,
        )


def test_non_reviewed_snapshot_cannot_replace_active_baseline() -> None:
    active = _snapshot(status="ACTIVE", approved_hash="a" * 64)
    candidate = _snapshot(status="NO_CHANGE", semantic_hash="b" * 64)
    with pytest.raises(ContractGovernanceError, match="reviewed_snapshot_required"):
        validate_approval_transition(
            candidate=candidate,
            active=active,
            expected_hash=candidate.semantic_hash,
        )


def test_reviewed_drift_can_be_explicitly_promoted() -> None:
    active = _snapshot(status="ACTIVE", approved_hash="a" * 64)
    candidate = _snapshot(status="REVIEW_REQUIRED", semantic_hash="b" * 64)
    assert (
        validate_approval_transition(
            candidate=candidate,
            active=active,
            expected_hash=candidate.semantic_hash,
        )
        == "promotion"
    )


def test_reapproving_same_active_hash_is_idempotent() -> None:
    candidate = _snapshot(status="ACTIVE", approved_hash="a" * 64)
    assert (
        validate_approval_transition(
            candidate=candidate,
            active=candidate,
            expected_hash=candidate.semantic_hash,
        )
        == "idempotent"
    )
