from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from cataloging_api.evaluation.scorer import score_case, score_run


GOLDEN_ROOT = Path(__file__).parent / "golden" / "llm-evidence"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _gold(binding: str = "linguistic-family") -> dict:
    return {
        "expected_candidates": [
            {
                "binding_id": binding,
                "metadata_field": "dc.subject.linguisticFamily",
                "candidate_intent": "INFERRED_VALUE",
                "accepted_values": ["Tarasca"],
                "normalization_rule": "casefold_if_contract_allows",
                "source_refs_allowed": ["source-1"],
                "grounding_required": False,
                "severity": "critical",
            }
        ],
        "expected_abstentions": [],
        "recall_applicable": True,
        "hallucination_annotations": {"prohibited_values": []},
    }


def test_authoritative_match_requires_exact_binding() -> None:
    result = score_case(
        _gold(),
        {
            "candidates": [
                {
                    "binding_id": "linguistic-family",
                    "candidate_intent": "INFERRED_VALUE",
                    "value": "tarasca",
                    "source_refs": ["source-1"],
                }
            ]
        },
    )
    assert result["tp"] == 1
    assert result["fp"] == 0
    assert result["binding_accuracy"] == 1.0


def test_wrong_binding_is_diagnostic_only_never_tp() -> None:
    result = score_case(
        _gold(),
        {
            "candidates": [
                {
                    "binding_id": "linguistic-group",
                    "candidate_intent": "INFERRED_VALUE",
                    "value": "Tarasca",
                    "source_refs": ["source-1"],
                }
            ]
        },
    )
    assert result["tp"] == 0
    assert result["fp"] == 1
    assert result["binding_accuracy"] == 0.0
    assert any(error["code"] == "WRONG_BINDING" for error in result["errors"])


def test_diagnostic_wrong_binding_is_one_to_one() -> None:
    result = score_case(
        _gold(),
        {
            "candidates": [
                {
                    "binding_id": "linguistic-group",
                    "candidate_intent": "INFERRED_VALUE",
                    "value": "Tarasca",
                    "source_refs": ["source-1"],
                },
                {
                    "binding_id": "registered-language",
                    "candidate_intent": "INFERRED_VALUE",
                    "value": "Tarasca",
                    "source_refs": ["source-1"],
                },
            ]
        },
    )
    wrong_binding = [error for error in result["errors"] if error["code"] == "WRONG_BINDING"]
    unsupported = [error for error in result["errors"] if error["code"] == "UNSUPPORTED_VALUE"]
    assert len(wrong_binding) == 1
    assert len(unsupported) == 1
    assert result["binding_accuracy"] == 0.0


def test_grounding_uses_closed_range_policy() -> None:
    gold = _gold()
    candidate = gold["expected_candidates"][0]
    candidate["grounding_required"] = True
    candidate["grounding_policy"] = "exact_range"
    candidate["accepted_grounding_ranges"] = [
        {"source_id": "source-1", "start": 4, "end": 10}
    ]
    result = score_case(
        gold,
        {
            "candidates": [
                {
                    "binding_id": "linguistic-family",
                    "candidate_intent": "INFERRED_VALUE",
                    "value": "Tarasca",
                    "source_refs": ["source-1"],
                    "grounding_ranges": [
                        {"source_id": "source-1", "start": 4, "end": 10}
                    ],
                }
            ]
        },
    )
    assert result["tp"] == 1
    assert result["grounding_accuracy"] == 1.0


def test_wrong_binding_and_grounding_are_independent_diagnostics() -> None:
    gold = _gold()
    expected = gold["expected_candidates"][0]
    expected["grounding_required"] = True
    expected["grounding_policy"] = "exact_range"
    expected["accepted_grounding_ranges"] = [
        {"source_id": "source-1", "start": 4, "end": 10}
    ]
    result = score_case(
        gold,
        {
            "candidates": [
                {
                    "binding_id": "linguistic-group",
                    "candidate_intent": "INFERRED_VALUE",
                    "value": "Tarasca",
                    "source_refs": ["source-1"],
                    "grounding_ranges": [
                        {"source_id": "source-1", "start": 4, "end": 10}
                    ],
                }
            ]
        },
    )
    assert result["binding_accuracy"] == 0.0
    assert result["grounding_accuracy"] == 1.0
    assert any(error["code"] == "WRONG_BINDING" for error in result["errors"])
    assert not any(error["code"] == "BAD_GROUNDING" for error in result["errors"])


def test_abstention_is_scoped_to_its_binding() -> None:
    gold = _gold("linguistic-branch")
    gold["expected_abstentions"] = [
        {"binding_id": "linguistic-group", "reason": "INSUFFICIENT_EVIDENCE"}
    ]
    result = score_case(
        gold,
        {
            "candidates": [
                {
                    "binding_id": "linguistic-branch",
                    "candidate_intent": "INFERRED_VALUE",
                    "value": "Tarasca",
                    "source_refs": ["source-1"],
                }
            ]
        },
    )
    assert result["tp"] == 1
    assert result["hallucination_rate"] == 0.0


def test_seed_stratum_a_is_insufficient_by_design() -> None:
    bindings = [
        "linguistic-family",
        "linguistic-branch",
        "linguistic-group",
        "linguistic-variant",
        "registered-language",
    ]
    cases = []
    for binding in bindings:
        cases.append(
            {
                "case_id": binding,
                "manifest": {
                    "risk_stratum": "A",
                    "bindings_under_test": [binding],
                    "opportunity_count": 1,
                },
                "expected": _gold(binding),
                "proposed": {"candidates": []},
            }
        )
    result = score_run(cases)
    assert result["sample_sufficiency"]["status"] == "INSUFFICIENT_SAMPLE"
    assert set(result["sample_sufficiency"]["missing_minimums"]) == set(bindings)
    assert result["gate_assessment"] == "ASSESSMENT_ONLY"


def test_all_materialized_seed_artifacts_validate_against_json_schemas() -> None:
    manifest = _load_json(GOLDEN_ROOT / "manifest.json")
    manifest_schema = _load_json(GOLDEN_ROOT / "schemas" / "manifest.schema.json")
    source_schema = _load_json(GOLDEN_ROOT / "schemas" / "source.schema.json")
    expected_schema = _load_json(GOLDEN_ROOT / "schemas" / "expected.schema.json")

    Draft202012Validator(manifest_schema).validate(manifest)
    source_validator = Draft202012Validator(source_schema)
    expected_validator = Draft202012Validator(expected_schema)

    for case in manifest["cases"]:
        case_dir = GOLDEN_ROOT / "cases" / case["id"]
        source = _load_json(case_dir / "source.json")
        expected = _load_json(case_dir / "expected.json")
        source_validator.validate(source)
        expected_validator.validate(expected)
        assert source["case_id"] == case["id"]
        assert expected["case_id"] == case["id"]


def test_materialized_seed_fixtures_score_end_to_end() -> None:
    manifest = _load_json(GOLDEN_ROOT / "manifest.json")
    cases = []

    for case_manifest in manifest["cases"]:
        case_dir = GOLDEN_ROOT / "cases" / case_manifest["id"]
        source = _load_json(case_dir / "source.json")
        expected = _load_json(case_dir / "expected.json")
        expected_candidate = expected["expected_candidates"][0]
        source_ref = expected_candidate["source_refs_allowed"][0]
        assert source_ref in {item["source_id"] for item in source["sources"]}

        proposed = {
            "candidates": [
                {
                    "binding_id": expected_candidate["binding_id"],
                    "candidate_intent": expected_candidate["candidate_intent"],
                    "value": expected_candidate["accepted_values"][0],
                    "source_refs": [source_ref],
                    "grounding_ranges": expected_candidate.get(
                        "accepted_grounding_ranges", []
                    ),
                }
            ]
        }
        per_case = score_case(expected, proposed)
        assert per_case["tp"] == 1
        assert per_case["fp"] == 0

        cases.append(
            {
                "case_id": case_manifest["id"],
                "manifest": case_manifest,
                "expected": expected,
                "proposed": proposed,
            }
        )

    run = score_run(cases)
    assert run["overall"]["tp"] == len(manifest["cases"])
    assert run["overall"]["fp"] == 0
    assert run["sample_sufficiency"]["status"] == "SUFFICIENT"
    assert run["gate_assessment"] == "ASSESSMENT_ONLY"
