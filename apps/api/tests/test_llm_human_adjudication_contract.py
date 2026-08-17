from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parent / "golden" / "llm-evidence" / "human-review"
REAL_HASH = "a" * 64
CONTRACT_HASH = "b" * 64


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _completed_review(review_id: str, reviewer_id: str, case_id: str, binding_id: str) -> dict:
    return {
        "review_id": review_id,
        "reviewer_id": reviewer_id,
        "case_id": case_id,
        "binding_id": binding_id,
        "evidence_snapshot_sha256": REAL_HASH,
    }


def _make_final_case(intake: dict) -> dict:
    case = intake["cases"][0]
    case_id = case["case_id"]
    binding_id = case["bindings_under_review"][0]
    case["authorization_status"] = "AUTHORIZED_LOCAL_EVALUATION"
    case["evidence_snapshot_sha256"] = REAL_HASH
    case["completed_reviews"] = [
        _completed_review("review-1", "cataloger-a", case_id, binding_id),
        _completed_review("review-2", "cataloger-b", case_id, binding_id),
    ]
    case["adjudicator_id"] = "adjudicator-c"
    case["review_status"] = "ADJUDICATED_GOLD"
    intake["catalog_contract_sha256"] = CONTRACT_HASH
    return case


def test_human_review_templates_validate_and_cannot_claim_final_gold() -> None:
    intake_schema = _load(ROOT / "schemas" / "intake-manifest.schema.json")
    reviewer_schema = _load(ROOT / "schemas" / "reviewer-decision.schema.json")
    adjudication_schema = _load(ROOT / "schemas" / "adjudication.schema.json")

    intake = _load(ROOT / "templates" / "intake-manifest.template.json")
    reviewer = _load(ROOT / "templates" / "reviewer-decision.template.json")
    adjudication = _load(ROOT / "templates" / "adjudication.template.json")

    Draft202012Validator(intake_schema).validate(intake)
    Draft202012Validator(reviewer_schema).validate(reviewer)
    Draft202012Validator(adjudication_schema).validate(adjudication)

    assert intake["status"] == "AWAITING_AUTHORIZED_EVIDENCE"
    assert adjudication["adjudication_status"] == "TEMPLATE"
    assert all(case["authorization_status"] == "PENDING" for case in intake["cases"])
    assert all(case["review_status"] != "ADJUDICATED_GOLD" for case in intake["cases"])
    assert all(case["completed_reviews"] == [] for case in intake["cases"])

    serialized = json.dumps(
        {"intake": intake, "reviewer": reviewer, "adjudication": adjudication},
        ensure_ascii=False,
    )
    assert "REPLACE_" in serialized
    assert "AUTHORIZED_LOCAL_EVALUATION" not in json.dumps(intake, ensure_ascii=False)


def test_stratum_a_adjudicated_gold_requires_two_completed_reviews_and_adjudicator() -> None:
    schema = _load(ROOT / "schemas" / "intake-manifest.schema.json")
    intake = _load(ROOT / "templates" / "intake-manifest.template.json")
    case = _make_final_case(intake)

    case["completed_reviews"] = case["completed_reviews"][:1]
    case["adjudicator_id"] = None
    assert list(Draft202012Validator(schema).iter_errors(intake))

    _make_final_case(intake)
    Draft202012Validator(schema).validate(intake)


def test_stratum_a_adjudicated_gold_rejects_pending_authorization_and_placeholder_hash() -> None:
    schema = _load(ROOT / "schemas" / "intake-manifest.schema.json")
    intake = _load(ROOT / "templates" / "intake-manifest.template.json")
    case = _make_final_case(intake)

    case["authorization_status"] = "PENDING"
    assert list(Draft202012Validator(schema).iter_errors(intake))

    case["authorization_status"] = "AUTHORIZED_LOCAL_EVALUATION"
    case["evidence_snapshot_sha256"] = "REPLACE_EVIDENCE_SHA256"
    assert list(Draft202012Validator(schema).iter_errors(intake))


def test_global_adjudicated_gold_requires_every_case_final_and_real_contract_hash() -> None:
    schema = _load(ROOT / "schemas" / "intake-manifest.schema.json")
    intake = _load(ROOT / "templates" / "intake-manifest.template.json")
    final_case = _make_final_case(intake)
    second_case = copy.deepcopy(final_case)
    second_case["case_id"] = "case-2"
    second_case["review_status"] = "AWAITING_AUTHORIZED_EVIDENCE"
    intake["cases"].append(second_case)
    intake["status"] = "ADJUDICATED_GOLD"

    assert list(Draft202012Validator(schema).iter_errors(intake))

    second_case["review_status"] = "ADJUDICATED_GOLD"
    intake["catalog_contract_sha256"] = "REPLACE_CATALOG_CONTRACT_SHA256"
    assert list(Draft202012Validator(schema).iter_errors(intake))

    intake["catalog_contract_sha256"] = CONTRACT_HASH
    Draft202012Validator(schema).validate(intake)


def test_completed_review_links_must_match_case_binding_and_snapshot_before_finalization() -> None:
    intake = _load(ROOT / "templates" / "intake-manifest.template.json")
    case = _make_final_case(intake)

    review_case_ids = {review["case_id"] for review in case["completed_reviews"]}
    review_binding_ids = {review["binding_id"] for review in case["completed_reviews"]}
    review_hashes = {review["evidence_snapshot_sha256"] for review in case["completed_reviews"]}
    reviewer_ids = {review["reviewer_id"] for review in case["completed_reviews"]}

    assert review_case_ids == {case["case_id"]}
    assert review_binding_ids == set(case["bindings_under_review"])
    assert review_hashes == {case["evidence_snapshot_sha256"]}
    assert len(reviewer_ids) == 2


def test_final_adjudication_requires_real_hashes_and_frozen_versions() -> None:
    schema = _load(ROOT / "schemas" / "adjudication.schema.json")
    adjudication = _load(ROOT / "templates" / "adjudication.template.json")
    adjudication["adjudication_status"] = "FINAL"
    assert list(Draft202012Validator(schema).iter_errors(adjudication))

    adjudication["evidence_snapshot_sha256"] = REAL_HASH
    adjudication["catalog_contract_sha256"] = CONTRACT_HASH
    adjudication["input_golden_set_version"] = "0.2.0-stratum-a"
    adjudication["catalog_contract_version"] = "dspace-cataloger-v3.6"
    adjudication["resulting_gold_version"] = "0.3.0-human-adjudicated"
    for review in adjudication["input_reviews"]:
        review["evidence_snapshot_sha256"] = REAL_HASH
    Draft202012Validator(schema).validate(adjudication)

    assert len({review["review_id"] for review in adjudication["input_reviews"]}) == 2
    assert len({review["reviewer_id"] for review in adjudication["input_reviews"]}) == 2
    assert {review["case_id"] for review in adjudication["input_reviews"]} == {adjudication["case_id"]}
    assert {review["binding_id"] for review in adjudication["input_reviews"]} == {adjudication["binding_id"]}
    assert {review["evidence_snapshot_sha256"] for review in adjudication["input_reviews"]} == {
        adjudication["evidence_snapshot_sha256"]
    }


def test_error_taxonomy_is_closed_in_both_review_schemas() -> None:
    reviewer_schema = _load(ROOT / "schemas" / "reviewer-decision.schema.json")
    adjudication_schema = _load(ROOT / "schemas" / "adjudication.schema.json")

    reviewer_errors = set(reviewer_schema["properties"]["error_codes"]["items"]["enum"])
    adjudication_errors = set(adjudication_schema["properties"]["error_codes"]["items"]["enum"])

    expected = {
        "UNSUPPORTED_VALUE",
        "WRONG_BINDING",
        "WRONG_INTENT",
        "GROUNDING_ERROR",
        "CARDINALITY_ERROR",
        "NORMALIZATION_ERROR",
        "CONTROLLED_VOCABULARY_ERROR",
        "MISSED_EXPECTED_CANDIDATE",
        "FALSE_PROPOSAL_WHEN_ABSTENTION_EXPECTED",
    }

    assert reviewer_errors == expected
    assert adjudication_errors == expected
