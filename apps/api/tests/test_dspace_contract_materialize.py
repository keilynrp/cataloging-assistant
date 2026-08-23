from types import SimpleNamespace

from cataloging_api.dspace.contract_materialize import classify_snapshot_status
from cataloging_api.dspace.contract_snapshot import ContractChange, ContractSnapshotView


def _view(*, complete: bool, semantic_hash: str = "new") -> ContractSnapshotView:
    return ContractSnapshotView(
        canonical={},
        semantic_hash=semantic_hash,
        complete=complete,
        warnings=() if complete else ("UNOBSERVABLE_SURFACE:x",),
    )


def test_first_complete_snapshot_requires_baseline_review() -> None:
    assert classify_snapshot_status(None, _view(complete=True), []) == "BASELINE_REVIEW_REQUIRED"


def test_first_incomplete_snapshot_cannot_be_baseline_candidate() -> None:
    assert classify_snapshot_status(None, _view(complete=False), []) == "REVIEW_REQUIRED"


def test_matching_active_hash_is_no_change() -> None:
    active = SimpleNamespace(semantic_hash="same")
    assert classify_snapshot_status(active, _view(complete=True, semantic_hash="same"), []) == "NO_CHANGE"


def test_high_severity_change_requires_review() -> None:
    active = SimpleNamespace(semantic_hash="old")
    changes = [ContractChange("REQUIRED_CHANGED", "HIGH", "binding")]
    assert classify_snapshot_status(active, _view(complete=True), changes) == "REVIEW_REQUIRED"


def test_safe_drift_is_detected_without_auto_promotion() -> None:
    active = SimpleNamespace(semantic_hash="old")
    changes = [ContractChange("LABEL_CHANGED", "LOW", "binding")]
    assert classify_snapshot_status(active, _view(complete=True), changes) == "DIFF_DETECTED"
