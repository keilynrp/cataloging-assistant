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


def _active_review_manifest() -> dict:
    snapshot_hash = "a" * 64
    contract_hash = "b" * 64
    return {
        "intake_version": "test-active-review",
        "status": "READY_FOR_INDEPENDENT_REVIEW",
        "golden_set_version": "test-gold",
        "catalog_contract_version": "dspace-cataloger-v3.6",
        "catalog_contract_sha256": contract_hash,
        "cases": [
            {
                "case_id": "test-case",
                "risk_stratum": "A",
                "bindings_under_review": ["registered-language"],
                "authorization_status": "AUTHORIZED_LOCAL_EVALUATION",
                "evidence_location_mode": "REPOSITORY_FIXTURE",
                "evidence_snapshot_sha256": snapshot_hash,
                "reviewer_ids": ["cataloger-a", "cataloger-b"],
                "completed_reviews": [],
                "review_status": "READY_FOR_INDEPENDENT_REVIEW",
                "metadata_field": "dc.description.registeredLanguage",
                "candidate_value": "Español",
                "candidate_intent": "RESOURCE_WRITING_LANGUAGE",
                "expected_abstention": False,
            }
        ],
    }


def test_active_review_target_is_valid_when_fully_materialized() -> None:
    _validator().validate(_active_review_manifest())


@pytest.mark.parametrize("field", ["metadata_field", "candidate_intent", "expected_abstention"])
def test_active_review_target_rejects_null_required_semantics(field: str) -> None:
    manifest = deepcopy(_active_review_manifest())
    manifest["cases"][0][field] = None

    errors = list(_validator().iter_errors(manifest))

    assert errors, f"Expected null {field} to be rejected for active review"


def test_active_review_target_requires_candidate_when_not_abstaining() -> None:
    manifest = deepcopy(_active_review_manifest())
    manifest["cases"][0]["candidate_value"] = None

    errors = list(_validator().iter_errors(manifest))

    assert errors, "Expected null candidate_value to fail when expected_abstention is false"


def test_active_review_target_allows_explicit_abstention_without_candidate() -> None:
    manifest = deepcopy(_active_review_manifest())
    manifest["cases"][0]["candidate_value"] = None
    manifest["cases"][0]["expected_abstention"] = True

    _validator().validate(manifest)
