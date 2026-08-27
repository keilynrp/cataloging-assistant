from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from cataloging_api.evaluation.scorer import score_case, score_run

GOLDEN_ROOT = Path(__file__).parent / "golden" / "llm-evidence"


def _gold(
    binding: str = "linguistic-family",
    *,
    intent: str = "INFERRED_VALUE",
    value: str = "Tarasca",
) -> dict:
    return {
        "expected_candidates": [
            {
                "binding_id": binding,
                "metadata_field": "dc.subject.linguisticFamily",
                "candidate_intent": intent,
                "accepted_values": [value],
                "normalization_rule": "none",
                "source_refs_allowed": ["source-1"],
                "grounding_required": False,
                "severity": "critical",
            }
        ],
        "expected_abstentions": [],
        "recall_applicable": True,
        "hallucination_annotations": {"prohibited_values": []},
    }


def _candidate(
    binding: str = "linguistic-family",
    *,
    intent: str = "INFERRED_VALUE",
    value: str = "Tarasca",
) -> dict:
    return {
        "binding_id": binding,
        "candidate_intent": intent,
        "value": value,
        "source_refs": ["source-1"],
    }


def _case(
    case_id: str,
    expected: dict,
    candidates: list[dict],
    *,
    binding: str = "linguistic-family",
    stratum: str = "A",
    opportunities: int = 1,
    reviews: list[dict] | None = None,
) -> dict:
    return {
        "case_id": case_id,
        "manifest": {
            "risk_stratum": stratum,
            "bindings_under_test": [binding],
            "opportunity_count": opportunities,
            "languages": ["es"],
            "document_type": "article",
        },
        "expected": expected,
        "proposed": {"candidates": candidates},
        "human_reviews": reviews or [],
    }


def test_empty_denominators_are_explicitly_not_evaluable() -> None:
    result = score_case(
        {
            "expected_candidates": [],
            "expected_abstentions": [],
            "recall_applicable": False,
        },
        {"candidates": []},
    )

    assert result["precision"] is None
    assert result["metrics"]["micro_precision"] == {
        "value": None,
        "numerator": 0,
        "denominator": 0,
        "status": "NOT_EVALUABLE",
    }
    assert result["metrics"]["intent_accuracy"]["status"] == "NOT_EVALUABLE"


def test_recall_applicability_excludes_positive_cases_from_recall_denominators() -> None:
    open_gold = _gold()
    open_gold["recall_applicable"] = False
    open_result = score_case(open_gold, {"candidates": [_candidate()]})

    assert open_result["tp"] == 1
    assert open_result["recall"] is None
    assert open_result["metrics"]["micro_recall"]["status"] == "NOT_EVALUABLE"

    mixed = score_run(
        [
            _case("applicable", _gold(), [_candidate()]),
            _case("not-applicable", open_gold, [_candidate()]),
        ]
    )
    assert mixed["overall"]["micro_recall"] == {
        "value": 1.0,
        "numerator": 1,
        "denominator": 1,
        "status": "EVALUABLE",
    }


def test_wrong_intent_is_independent_from_binding_and_grounding() -> None:
    gold = _gold()
    result = score_case(
        gold,
        {"candidates": [_candidate(intent="GENERATED_CONTENT")]},
    )

    assert result["tp"] == 0
    assert result["intent_accuracy"] == 0.0
    assert result["binding_accuracy"] is None
    assert {error["code"] for error in result["errors"]} >= {
        "WRONG_INTENT",
        "MISSING_EXPECTED_CANDIDATE",
    }
    wrong_intent = next(error for error in result["errors"] if error["code"] == "WRONG_INTENT")
    assert wrong_intent["origin"] == "diagnostic_value_match"
    assert wrong_intent["severity"] == "critical"
    assert wrong_intent["proposed_index"] == 0
    assert wrong_intent["expected_index"] == 0
    assert "WRONG_BINDING" not in {error["code"] for error in result["errors"]}
    assert "BAD_GROUNDING" not in {error["code"] for error in result["errors"]}


def test_full_and_selective_abstention_are_first_class_metrics() -> None:
    full = {
        "expected_candidates": [],
        "expected_abstentions": [{"reason": "INSUFFICIENT_EVIDENCE"}],
        "recall_applicable": False,
    }
    full_result = score_case(full, {"candidates": []})
    assert full_result["true_abstention_rate"] == 1.0
    assert full_result["false_proposal_rate_on_abstention"] == 0.0

    selective = _gold("linguistic-family")
    selective["expected_abstentions"] = [
        {"binding_id": "linguistic-group", "reason": "INSUFFICIENT_EVIDENCE"}
    ]
    failing = score_case(
        selective,
        {
            "candidates": [
                _candidate(),
                _candidate(binding="linguistic-group", value="Purépecha"),
            ]
        },
    )
    assert failing["false_proposal_rate_on_abstention"] == 1.0
    assert any(error["code"] == "FALSE_PROPOSAL_ON_ABSTENTION" for error in failing["errors"])

    source_scoped = _gold("linguistic-family")
    source_scoped["expected_abstentions"] = [
        {
            "binding_id": "linguistic-family",
            "source_refs": ["source-2"],
            "reason": "CONFLICTING_EVIDENCE",
        }
    ]
    passing = score_case(source_scoped, {"candidates": [_candidate()]})
    assert passing["true_abstention_rate"] == 1.0
    assert passing["false_proposal_rate_on_abstention"] == 0.0
    assert passing["hallucination_rate"] == 0.0


def test_controlled_vocabulary_uses_frozen_metadata_and_exact_match() -> None:
    gold = _gold(binding="linguistic-group", value="Purépecha")
    expected = gold["expected_candidates"][0]
    expected["controlled_vocabulary"] = {
        "vocabulary_id": "linguistic-groups",
        "version": "2026-08",
        "hash": "sha256:frozen",
    }
    accepted = score_case(
        gold,
        {"candidates": [_candidate(binding="linguistic-group", value="Purépecha")]},
    )
    rejected = score_case(
        gold,
        {"candidates": [_candidate(binding="linguistic-group", value="Purépecha regional")]},
    )

    assert accepted["controlled_vocab_exact_match"] == 1.0
    assert rejected["controlled_vocab_exact_match"] == 0.0
    assert any(error["code"] == "CONTROLLED_VOCAB_MISMATCH" for error in rejected["errors"])

    normalized_but_not_exact = score_case(
        {
            **gold,
            "expected_candidates": [
                {**expected, "normalization_rule": "casefold_if_contract_allows"}
            ],
        },
        {"candidates": [_candidate(binding="linguistic-group", value="purépecha")]},
    )
    assert normalized_but_not_exact["tp"] == 1
    assert normalized_but_not_exact["controlled_vocab_exact_match"] == 0.0


def test_unsupported_same_binding_value_uses_gold_severity_and_counts_hallucination() -> None:
    result = score_case(_gold(), {"candidates": [_candidate(value="Inventada")]})

    assert result["hallucination_rate"] == 1.0
    unsupported = next(error for error in result["errors"] if error["code"] == "UNSUPPORTED_VALUE")
    assert unsupported == {
        "code": "UNSUPPORTED_VALUE",
        "origin": "authoritative_match",
        "severity": "critical",
        "proposed_index": 0,
        "expected_index": 0,
    }


def test_structural_diagnostics_preserve_cardinality_duplicates_order_and_source_refs() -> None:
    first = _gold(value="First")["expected_candidates"][0]
    first["cardinality"] = "single"
    first["order_significant"] = True
    second = deepcopy(first)
    second["accepted_values"] = ["Second"]
    second["cardinality"] = "repeatable"
    gold = {
        "expected_candidates": [first, second],
        "expected_abstentions": [],
        "recall_applicable": True,
    }
    second_candidate = _candidate(value="Second")
    first_candidate = _candidate(value="First")
    invalid_source_candidate = deepcopy(first_candidate)
    invalid_source_candidate["source_refs"] = ["source-outside-manifest"]
    result = score_case(
        gold,
        {
            "candidates": [
                second_candidate,
                first_candidate,
                deepcopy(first_candidate),
                invalid_source_candidate,
            ]
        },
    )

    codes = {error["code"] for error in result["errors"]}
    assert {
        "CARDINALITY_ERROR",
        "DUPLICATE_CANDIDATE",
        "ORDER_ERROR",
        "INVALID_SOURCE_REF",
    }.issubset(codes)


def test_run_materializes_all_dimensions_macro_metrics_and_provisional_comparison() -> None:
    passing = _case("a-pass", _gold(), [_candidate()], opportunities=20)
    failing_gold = _gold(binding="linguistic-group", value="Purépecha")
    failing = _case(
        "b-fail",
        failing_gold,
        [_candidate(binding="linguistic-group", value="Unsupported")],
        binding="linguistic-group",
        stratum="B",
    )
    result = score_run([passing, failing])

    assert result["overall"]["micro_precision"]["value"] == 0.5
    assert result["overall"]["macro_precision"]["value"] == 0.5
    assert result["by_risk_stratum"]["A"]["micro_precision"]["value"] == 1.0
    assert result["by_risk_stratum"]["B"]["micro_precision"]["value"] == 0.0
    assert result["by_binding"]["linguistic-family"]["micro_precision"]["value"] == 1.0
    assert result["by_binding"]["linguistic-group"]["micro_precision"]["value"] == 0.0
    assert result["by_intent"]["INFERRED_VALUE"]["micro_recall"]["value"] == 0.5
    assert result["by_language"]["es"]["n_cases"] == 2
    assert result["by_document_type"]["article"]["n_cases"] == 2
    assert result["threshold_profile"] == "PROVISIONAL_TARGETS"
    assert result["threshold_comparison"]["micro_precision"]["outcome"] == (
        "MISSES_PROVISIONAL_TARGET"
    )
    assert result["threshold_comparison"]["micro_precision"]["governance_status"] == (
        "INFORMATIONAL_NON_GATING"
    )
    assert result["gate_assessment"] == "ASSESSMENT_ONLY"
    assert result["gate_assessment"] not in {"PASS", "FAIL"}


def test_micro_success_cannot_hide_unevaluable_critical_binding() -> None:
    cases = [
        _case("family", _gold(), [_candidate()], opportunities=20),
        _case(
            "group-empty",
            {
                "expected_candidates": [],
                "expected_abstentions": [],
                "recall_applicable": False,
            },
            [],
            binding="linguistic-group",
        ),
    ]
    result = score_run(cases)

    assert result["overall"]["micro_precision"]["value"] == 1.0
    assert result["by_binding"]["linguistic-group"]["micro_precision"]["status"] == (
        "NOT_EVALUABLE"
    )
    assert result["by_binding"]["linguistic-group"]["sample_status"] == ("INSUFFICIENT_SAMPLE")
    assert result["sample_sufficiency"]["status"] == "INSUFFICIENT_SAMPLE"
    assert result["gate_assessment"] == "ASSESSMENT_ONLY"


def test_human_review_burden_is_annotated_not_inferred() -> None:
    review_metadata = {
        "binding_id": "linguistic-family",
        "evidence_snapshot_sha256": "sha256:evidence",
        "golden_set_version": "gold-1",
        "catalog_contract_version": "contract-1",
    }
    reviews = [
        {**review_metadata, "review_id": "review-1", "decision": "ACCEPT_AS_IS"},
        {
            **review_metadata,
            "review_id": "review-2",
            "decision": "RESEARCH_REQUIRED",
        },
    ]
    reviewed = _case("reviewed", _gold(), [_candidate()], reviews=reviews)
    unreviewed = _case(
        "unreviewed",
        _gold(binding="linguistic-group", value="Purépecha"),
        [_candidate(binding="linguistic-group", value="Purépecha")],
        binding="linguistic-group",
        stratum="B",
    )
    result = score_run([reviewed, unreviewed])

    burden = result["overall"]["human_review_burden"]
    assert burden["total"] == 2
    assert burden["proportions"]["ACCEPT_AS_IS"] == 0.5
    assert burden["proportions"]["RESEARCH_REQUIRED"] == 0.5
    assert result["by_binding"]["linguistic-family"]["human_review_burden"]["total"] == 2
    assert result["by_binding"]["linguistic-group"]["human_review_burden"]["status"] == (
        "NOT_EVALUABLE"
    )


def test_materialized_adjudicated_reviews_feed_human_burden() -> None:
    review_root = GOLDEN_ROOT / "human-review" / "reviews"
    filenames = [
        "real-evidence-candidate-003.registered-language.cataloger-a.rereview-v3.json",
        "real-evidence-candidate-003.registered-language.cataloger-b.rereview-v3.json",
    ]
    reviews = [
        json.loads((review_root / filename).read_text(encoding="utf-8")) for filename in filenames
    ]
    case = _case(
        "real-evidence-candidate-003-registered-language-rereview-v3",
        _gold(binding="registered-language", value="Español"),
        [_candidate(binding="registered-language", value="Español")],
        binding="registered-language",
        reviews=reviews,
    )

    burden = score_run([case])["overall"]["human_review_burden"]
    assert burden["status"] == "EVALUABLE"
    assert burden["total"] == 2
    assert burden["counts"]["ACCEPT_AS_IS"] == 2


def test_run_is_stable_under_case_reordering_and_does_not_invent_provenance() -> None:
    controlled_gold = _gold()
    controlled_gold["expected_candidates"][0]["controlled_vocabulary"] = {
        "vocabulary_id": "linguistic-families",
        "version": "2026-08",
        "hash": "sha256:frozen",
    }
    cases = [
        _case("z-case", controlled_gold, [_candidate()]),
        _case(
            "a-case",
            _gold(binding="registered-language", value="Español"),
            [_candidate(binding="registered-language", value="Español")],
            binding="registered-language",
        ),
    ]
    first = score_run(cases)
    second = score_run(list(reversed(deepcopy(cases))))

    assert first == second
    assert [case["case_id"] for case in first["cases"]] == ["a-case", "z-case"]
    assert first["evaluation_run_id"] is None
    assert first["provenance"]["status"] == "INCOMPLETE"
    assert "evaluation_run_id" in first["provenance"]["missing_required_fields"]
    assert first["provenance"]["controlled_vocabularies"] == [
        {
            "vocabulary_id": "linguistic-families",
            "version": "2026-08",
            "hash": "sha256:frozen",
        }
    ]


def test_complete_versioned_provenance_is_preserved() -> None:
    metadata = {
        "evaluation_run_id": "run-001",
        "golden_set_version": "gold-1",
        "golden_set_hash": "sha256:gold",
        "catalog_contract_version": "contract-1",
        "catalog_contract_hash": "sha256:contract",
        "config_hash": "sha256:config",
        "input_manifest_hashes": ["sha256:input"],
        "output_hashes": ["sha256:output"],
        "run_timestamp": "2026-08-27T00:00:00Z",
        "environment_runtime_id": "python-3.12",
    }
    result = score_run([_case("case", _gold(), [_candidate()])], metadata)

    assert result["evaluation_run_id"] == "run-001"
    assert result["golden_set_version"] == "gold-1"
    assert result["catalog_contract_version"] == "contract-1"
    assert result["provenance"]["status"] == "COMPLETE"
    assert result["provenance"]["missing_required_fields"] == []
