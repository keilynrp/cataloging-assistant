from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).parent / "golden" / "llm-evidence" / "human-review"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    assert all(case["authorization_status"] == "PENDING" for case in intake["cases"])
    assert all(case["review_status"] != "ADJUDICATED_GOLD" for case in intake["cases"])

    serialized = json.dumps(
        {"intake": intake, "reviewer": reviewer, "adjudication": adjudication},
        ensure_ascii=False,
    )
    assert "REPLACE_" in serialized
    assert "AUTHORIZED_LOCAL_EVALUATION" not in json.dumps(intake, ensure_ascii=False)


def test_stratum_a_adjudicated_gold_requires_two_reviewers_and_adjudicator() -> None:
    schema = _load(ROOT / "schemas" / "intake-manifest.schema.json")
    intake = _load(ROOT / "templates" / "intake-manifest.template.json")
    case = intake["cases"][0]

    case["authorization_status"] = "AUTHORIZED_LOCAL_EVALUATION"
    case["review_status"] = "ADJUDICATED_GOLD"
    case["reviewer_ids"] = ["cataloger-a"]
    case["adjudicator_id"] = None

    errors = list(Draft202012Validator(schema).iter_errors(intake))
    assert errors

    case["reviewer_ids"] = ["cataloger-a", "cataloger-b"]
    case["adjudicator_id"] = "adjudicator-c"
    Draft202012Validator(schema).validate(intake)


def test_stratum_a_adjudicated_gold_requires_authorized_local_evidence() -> None:
    schema = _load(ROOT / "schemas" / "intake-manifest.schema.json")
    intake = _load(ROOT / "templates" / "intake-manifest.template.json")
    case = intake["cases"][0]

    case["authorization_status"] = "PENDING"
    case["review_status"] = "ADJUDICATED_GOLD"
    case["reviewer_ids"] = ["cataloger-a", "cataloger-b"]
    case["adjudicator_id"] = "adjudicator-c"

    errors = list(Draft202012Validator(schema).iter_errors(intake))
    assert errors


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
