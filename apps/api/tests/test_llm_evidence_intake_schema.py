import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


SCHEMA_PATH = (
    Path(__file__).parent
    / "golden"
    / "llm-evidence"
    / "human-review"
    / "schemas"
    / "intake-manifest.schema.json"
)


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _review_manifest(status: str = "READY_FOR_INDEPENDENT_REVIEW") -> dict:
    snapshot_hash = "a" * 64
    contract_hash = "b" * 64
    case = {
        "case_id": "test-case",
        "risk_stratum": "A",
        "bindings_under_review": ["registered-language"],
        "authorization_status": "AUTHORIZED_LOCAL_EVALUATION",
        "evidence_location_mode": "REPOSITORY_FIXTURE",
        "evidence_snapshot_sha256": snapshot_hash,
        "reviewer_ids": ["cataloger-a", "cataloger-b"],
        "completed_reviews": [],
        "review_status": status,
        "metadata_field": "dc.description.registeredLanguage",
        "candidate_value": "Español",
        "candidate_intent": "INFERRED_VALUE",
        "expected_abstention": False,
    }
    if status in {"AWAITING_ADJUDICATION", "ADJUDICATED_GOLD"}:
        case["completed_reviews"] = [
            {
                "review_id": "review-a",
                "reviewer_id": "cataloger-a",
                "case_id": "test-case",
                "binding_id": "registered-language",
                "evidence_snapshot_sha256": snapshot_hash,
            },
            {
                "review_id": "review-b",
                "reviewer_id": "cataloger-b",
                "case_id": "test-case",
                "binding_id": "registered-language",
                "evidence_snapshot_sha256": snapshot_hash,
            },
        ]
    if status == "ADJUDICATED_GOLD":
        case["adjudicator_id"] = "adjudicator-1"
        case["resulting_gold_version"] = "test-gold-adjudicated"

    return {
        "intake_version": "test-active-review",
        "status": "BLOCKED_FOR_INTAKE",
        "golden_set_version": "test-gold",
        "catalog_contract_version": "dspace-cataloger-v3.6",
        "catalog_contract_sha256": contract_hash,
        "cases": [case],
    }


@pytest.mark.parametrize(
    "status",
    [
        "READY_FOR_INDEPENDENT_REVIEW",
        "UNDER_INDEPENDENT_REVIEW",
        "AWAITING_ADJUDICATION",
        "ADJUDICATED_GOLD",
    ],
)
def test_review_target_is_valid_when_fully_materialized(status: str) -> None:
    _validator().validate(_review_manifest(status))


@pytest.mark.parametrize(
    ("status", "field"),
    [
        (status, field)
        for status in [
            "READY_FOR_INDEPENDENT_REVIEW",
            "UNDER_INDEPENDENT_REVIEW",
            "AWAITING_ADJUDICATION",
            "ADJUDICATED_GOLD",
        ]
        for field in ["metadata_field", "candidate_intent", "expected_abstention"]
    ],
)
def test_review_target_rejects_null_required_semantics(status: str, field: str) -> None:
    manifest = deepcopy(_review_manifest(status))
    manifest["cases"][0][field] = None

    assert list(_validator().iter_errors(manifest))


@pytest.mark.parametrize(
    "status",
    [
        "READY_FOR_INDEPENDENT_REVIEW",
        "UNDER_INDEPENDENT_REVIEW",
        "AWAITING_ADJUDICATION",
        "ADJUDICATED_GOLD",
    ],
)
def test_review_target_requires_candidate_when_not_abstaining(status: str) -> None:
    manifest = deepcopy(_review_manifest(status))
    manifest["cases"][0]["candidate_value"] = None

    assert list(_validator().iter_errors(manifest))


def test_active_review_target_allows_explicit_abstention_without_candidate() -> None:
    manifest = deepcopy(_review_manifest())
    manifest["cases"][0]["candidate_value"] = None
    manifest["cases"][0]["expected_abstention"] = True

    _validator().validate(manifest)


@pytest.mark.parametrize(
    "status",
    [
        "READY_FOR_INDEPENDENT_REVIEW",
        "UNDER_INDEPENDENT_REVIEW",
        "AWAITING_ADJUDICATION",
        "ADJUDICATED_GOLD",
    ],
)
def test_review_target_rejects_placeholder_evidence_hash(status: str) -> None:
    manifest = deepcopy(_review_manifest(status))
    manifest["cases"][0]["evidence_snapshot_sha256"] = "REPLACE_EVIDENCE_HASH"

    assert list(_validator().iter_errors(manifest))


@pytest.mark.parametrize(
    "status",
    [
        "READY_FOR_INDEPENDENT_REVIEW",
        "UNDER_INDEPENDENT_REVIEW",
        "AWAITING_ADJUDICATION",
        "ADJUDICATED_GOLD",
    ],
)
def test_review_target_rejects_placeholder_catalog_contract_hash(status: str) -> None:
    manifest = deepcopy(_review_manifest(status))
    manifest["catalog_contract_sha256"] = "REPLACE_CONTRACT_HASH"

    assert list(_validator().iter_errors(manifest))


def test_adjudicated_gold_requires_structured_target_and_resulting_version() -> None:
    manifest = deepcopy(_review_manifest("ADJUDICATED_GOLD"))
    case = manifest["cases"][0]
    for field in [
        "metadata_field",
        "candidate_intent",
        "expected_abstention",
        "resulting_gold_version",
    ]:
        case.pop(field)

    assert list(_validator().iter_errors(manifest))


def test_review_target_rejects_unsupported_candidate_intent() -> None:
    manifest = deepcopy(_review_manifest())
    manifest["cases"][0]["candidate_intent"] = "RESOURCE_WRITING_LANGUAGE"

    assert list(_validator().iter_errors(manifest))
