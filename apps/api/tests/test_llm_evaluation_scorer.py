from __future__ import annotations

from cataloging_api.evaluation.scorer import score_case, score_run


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
        {"candidates": [{"binding_id": "linguistic-family", "candidate_intent": "INFERRED_VALUE", "value": "tarasca", "source_refs": ["source-1"]}]},
    )
    assert result["tp"] == 1
    assert result["fp"] == 0
    assert result["binding_accuracy"] == 1.0


def test_wrong_binding_is_diagnostic_only_never_tp() -> None:
    result = score_case(
        _gold(),
        {"candidates": [{"binding_id": "linguistic-group", "candidate_intent": "INFERRED_VALUE", "value": "Tarasca", "source_refs": ["source-1"]}]},
    )
    assert result["tp"] == 0
    assert result["fp"] == 1
    assert result["binding_accuracy"] == 0.0
    assert any(error["code"] == "WRONG_BINDING" for error in result["errors"])


def test_grounding_uses_closed_range_policy() -> None:
    gold = _gold()
    candidate = gold["expected_candidates"][0]
    candidate["grounding_required"] = True
    candidate["grounding_policy"] = "exact_range"
    candidate["accepted_grounding_ranges"] = [{"source_id": "source-1", "start": 4, "end": 10}]
    result = score_case(
        gold,
        {"candidates": [{"binding_id": "linguistic-family", "candidate_intent": "INFERRED_VALUE", "value": "Tarasca", "source_refs": ["source-1"], "grounding_ranges": [{"source_id": "source-1", "start": 4, "end": 10}]}]},
    )
    assert result["tp"] == 1
    assert result["grounding_accuracy"] == 1.0


def test_abstention_is_scoped_to_its_binding() -> None:
    gold = _gold("linguistic-branch")
    gold["expected_abstentions"] = [{"binding_id": "linguistic-group", "reason": "INSUFFICIENT_EVIDENCE"}]
    result = score_case(
        gold,
        {"candidates": [{"binding_id": "linguistic-branch", "candidate_intent": "INFERRED_VALUE", "value": "Tarasca", "source_refs": ["source-1"]}]},
    )
    assert result["tp"] == 1
    assert result["hallucination_rate"] == 0.0


def test_seed_stratum_a_is_insufficient_by_design() -> None:
    bindings = ["linguistic-family", "linguistic-branch", "linguistic-group", "linguistic-variant", "registered-language"]
    cases = []
    for binding in bindings:
        cases.append({
            "case_id": binding,
            "manifest": {"risk_stratum": "A", "bindings_under_test": [binding], "opportunity_count": 1},
            "expected": _gold(binding),
            "proposed": {"candidates": []},
        })
    result = score_run(cases)
    assert result["sample_sufficiency"]["status"] == "INSUFFICIENT_SAMPLE"
    assert set(result["sample_sufficiency"]["missing_minimums"]) == set(bindings)
    assert result["gate_assessment"] == "ASSESSMENT_ONLY"
