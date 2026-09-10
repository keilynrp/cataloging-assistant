from __future__ import annotations

import copy

import pytest

from cataloging_api.evaluation.scorer import score_case, score_run


def _gold(binding: str = "linguistic-family", **overrides) -> dict:
    candidate = {
        "binding_id": binding,
        "metadata_field": "dc.subject.linguisticFamily",
        "candidate_intent": "INFERRED_VALUE",
        "accepted_values": ["Tarasca"],
        "normalization_rule": "casefold_if_contract_allows",
        "source_refs_allowed": ["source-1"],
        "grounding_required": False,
        "severity": "critical",
    }
    candidate.update(overrides)
    return {
        "expected_candidates": [candidate],
        "expected_abstentions": [],
        "recall_applicable": True,
        "hallucination_annotations": {"prohibited_values": []},
    }


def _candidate(
    binding: str, value: str = "Tarasca", intent: str = "INFERRED_VALUE", **overrides
) -> dict:
    proposal = {
        "binding_id": binding,
        "candidate_intent": intent,
        "value": value,
        "source_refs": ["source-1"],
    }
    proposal.update(overrides)
    return proposal


# ---------------------------------------------------------------------------
# Wrong intent independent of wrong binding / bad grounding
# ---------------------------------------------------------------------------


def test_wrong_intent_only_is_independent_of_wrong_binding_and_grounding() -> None:
    result = score_case(
        _gold(),
        {"candidates": [_candidate("linguistic-family", intent="GENERATED_CONTENT")]},
    )
    codes = [error["code"] for error in result["errors"]]
    # WRONG_INTENT explains the proposed candidate; MISSING_EXPECTED_CANDIDATE
    # is the independent, expected side effect of the gold opportunity never
    # receiving an authoritative match (recall_applicable=True by default).
    assert set(codes) == {"WRONG_INTENT", "MISSING_EXPECTED_CANDIDATE"}
    assert not any(code in ("WRONG_BINDING", "BAD_GROUNDING") for code in codes)
    assert result["tp"] == 0
    assert result["fp"] == 1
    # Binding is correct, so this candidate is excluded from the binding-
    # accuracy denominator (it never had a valid diagnostic_value_match for
    # that axis), but it was intent-evaluable and counted as wrong.
    assert result["binding_accuracy"] is None
    assert result["intent_accuracy"] == 0.0
    assert result["intent_accuracy_counts"] == {"correct": 0, "evaluable": 1}


def test_bad_grounding_only_is_independent_of_binding_and_intent() -> None:
    gold = _gold()
    candidate = gold["expected_candidates"][0]
    candidate["grounding_required"] = True
    candidate["grounding_policy"] = "exact_range"
    candidate["accepted_grounding_ranges"] = [{"source_id": "source-1", "start": 4, "end": 10}]
    result = score_case(
        gold,
        {
            "candidates": [
                _candidate(
                    "linguistic-family",
                    grounding_ranges=[{"source_id": "source-1", "start": 0, "end": 3}],
                )
            ]
        },
    )
    codes = [error["code"] for error in result["errors"]]
    assert set(codes) == {"BAD_GROUNDING", "MISSING_EXPECTED_CANDIDATE"}
    assert not any(code in ("WRONG_BINDING", "WRONG_INTENT") for code in codes)
    assert result["tp"] == 0
    assert result["grounding_accuracy"] == 0.0
    assert result["intent_accuracy"] == 1.0


def test_ambiguous_double_fault_does_not_guess_binding_or_intent() -> None:
    result = score_case(
        _gold(),
        {"candidates": [_candidate("linguistic-group", intent="GENERATED_CONTENT")]},
    )
    codes = [error["code"] for error in result["errors"]]
    # Both binding and intent differ simultaneously: the scorer refuses to
    # guess which axis is "the" explanation and falls back to
    # UNSUPPORTED_VALUE (plus the independent MISSING_EXPECTED_CANDIDATE for
    # the unmatched gold opportunity) rather than asserting an unproven
    # WRONG_BINDING or WRONG_INTENT diagnostic.
    assert set(codes) == {"UNSUPPORTED_VALUE", "MISSING_EXPECTED_CANDIDATE"}
    assert not any(code in ("WRONG_BINDING", "WRONG_INTENT") for code in codes)


# ---------------------------------------------------------------------------
# Controlled vocabulary
# ---------------------------------------------------------------------------


def _cv_gold() -> dict:
    return _gold(
        controlled_vocabulary={"vocabulary_id": "iso-639-3", "version": "2026.1", "hash": "abc123"},
    )


def test_controlled_vocabulary_authorized_exact_match() -> None:
    result = score_case(_cv_gold(), {"candidates": [_candidate("linguistic-family")]})
    assert result["controlled_vocab_exact_match"] == 1.0
    assert result["controlled_vocabulary"] == {"opportunities": 1, "authorized_exact_matches": 1}
    assert not any(error["code"] == "CONTROLLED_VOCAB_MISMATCH" for error in result["errors"])


def test_controlled_vocabulary_mismatch() -> None:
    result = score_case(
        _cv_gold(), {"candidates": [_candidate("linguistic-family", value="Nahuatl")]}
    )
    assert result["controlled_vocab_exact_match"] == 0.0
    assert result["controlled_vocabulary"] == {"opportunities": 1, "authorized_exact_matches": 0}
    codes = [error["code"] for error in result["errors"]]
    assert set(codes) == {"CONTROLLED_VOCAB_MISMATCH", "MISSING_EXPECTED_CANDIDATE"}


def test_controlled_vocabulary_not_evaluable_when_no_opportunity_declared() -> None:
    result = score_case(_gold(), {"candidates": [_candidate("linguistic-family")]})
    assert result["controlled_vocab_exact_match"] is None
    assert result["controlled_vocabulary"] == {"opportunities": 0, "authorized_exact_matches": 0}


# ---------------------------------------------------------------------------
# Intent accuracy
# ---------------------------------------------------------------------------


def test_intent_accuracy_not_evaluable_with_no_value_anchored_candidates() -> None:
    result = score_case(
        _gold(), {"candidates": [_candidate("linguistic-family", value="Purepecha")]}
    )
    assert result["intent_accuracy"] is None
    assert result["intent_accuracy_counts"] == {"correct": 0, "evaluable": 0}


def test_intent_accuracy_by_class_surface_in_run_report() -> None:
    case_correct = _run_case(
        "correct",
        _gold("linguistic-family"),
        [_candidate("linguistic-family")],
        _manifest("linguistic-family"),
    )
    case_wrong_intent = _run_case(
        "wrong-intent",
        _gold("linguistic-branch"),
        [_candidate("linguistic-branch", intent="GENERATED_CONTENT")],
        _manifest("linguistic-branch"),
    )
    run = score_run([case_correct, case_wrong_intent])
    # by_intent buckets by the *gold's* intent class. Both opportunities here
    # are gold INFERRED_VALUE (one proposed correctly, one proposed as
    # GENERATED_CONTENT), so the class-level accuracy reflects both.
    assert run["by_intent"]["INFERRED_VALUE"] == {
        "evaluable": 2,
        "correct": 1,
        "intent_accuracy": 0.5,
    }


# ---------------------------------------------------------------------------
# Abstention: full-case and selective
# ---------------------------------------------------------------------------


def test_full_case_abstention_true_when_no_candidates_proposed() -> None:
    gold = {
        "expected_candidates": [],
        "expected_abstentions": [{"reason": "INSUFFICIENT_EVIDENCE"}],
        "recall_applicable": True,
        "hallucination_annotations": {"prohibited_values": []},
    }
    result = score_case(gold, {"candidates": []})
    assert result["abstention"]["full_case_expected"] is True
    assert result["abstention"]["full_case_true"] is True
    assert result["errors"] == []


def test_full_case_false_proposal_on_abstention() -> None:
    gold = {
        "expected_candidates": [],
        "expected_abstentions": [{"reason": "INSUFFICIENT_EVIDENCE"}],
        "recall_applicable": True,
        "hallucination_annotations": {"prohibited_values": []},
    }
    result = score_case(gold, {"candidates": [_candidate("linguistic-family")]})
    assert result["abstention"]["full_case_expected"] is True
    assert result["abstention"]["full_case_true"] is False
    codes = [error["code"] for error in result["errors"]]
    assert codes == ["FALSE_PROPOSAL_ON_ABSTENTION"]
    assert result["hallucination_rate"] == 1.0


def test_selective_abstention_true_for_untouched_binding() -> None:
    gold = _gold("linguistic-branch")
    gold["expected_abstentions"] = [
        {"binding_id": "linguistic-group", "reason": "INSUFFICIENT_EVIDENCE"}
    ]
    result = score_case(gold, {"candidates": [_candidate("linguistic-branch")]})
    assert result["abstention"]["selective_opportunities"] == [
        {
            "binding_id": "linguistic-group",
            "reason": "INSUFFICIENT_EVIDENCE",
            "true_abstention": True,
            "false_proposal": False,
        }
    ]


def test_selective_false_proposal_on_abstention_emits_error_and_hallucination() -> None:
    gold = _gold("linguistic-branch")
    gold["expected_abstentions"] = [
        {"binding_id": "linguistic-group", "reason": "INSUFFICIENT_EVIDENCE"}
    ]
    result = score_case(
        gold,
        {
            "candidates": [
                _candidate("linguistic-branch"),
                _candidate("linguistic-group", value="Occidental"),
            ]
        },
    )
    false_proposal_errors = [
        e for e in result["errors"] if e["code"] == "FALSE_PROPOSAL_ON_ABSTENTION"
    ]
    assert len(false_proposal_errors) == 1
    assert false_proposal_errors[0]["proposed_index"] == 1
    assert result["hallucination_counts"] == {"numerator": 1, "denominator": 2}


def test_abstention_aggregation_in_run_report() -> None:
    full_case = _run_case(
        "full-abstain",
        {
            "expected_candidates": [],
            "expected_abstentions": [{"reason": "INSUFFICIENT_EVIDENCE"}],
            "recall_applicable": True,
            "hallucination_annotations": {"prohibited_values": []},
        },
        [],
        _manifest("linguistic-family"),
    )
    selective_true = _run_case(
        "selective-true",
        {
            **_gold("linguistic-branch"),
            "expected_abstentions": [
                {"binding_id": "linguistic-group", "reason": "INSUFFICIENT_EVIDENCE"}
            ],
        },
        [_candidate("linguistic-branch")],
        _manifest("linguistic-branch"),
    )
    selective_false = _run_case(
        "selective-false",
        {
            **_gold("linguistic-variant"),
            "expected_abstentions": [
                {"binding_id": "linguistic-group", "reason": "INSUFFICIENT_EVIDENCE"}
            ],
        },
        [_candidate("linguistic-variant"), _candidate("linguistic-group", value="X")],
        {
            "risk_stratum": "A",
            "bindings_under_test": ["linguistic-variant"],
            "opportunity_count": 1,
        },
    )
    run = score_run([full_case, selective_true, selective_false])
    abstention = run["overall"]["abstention"]
    assert abstention["full_case"] == {
        "opportunities": 1,
        "true_abstention": 1,
        "false_proposal": 0,
        "true_abstention_rate": 1.0,
        "false_proposal_rate": 0.0,
    }
    assert abstention["selective"] == {
        "opportunities": 2,
        "true_abstention": 1,
        "false_proposal": 1,
        "true_abstention_rate": 0.5,
        "false_proposal_rate": 0.5,
    }
    assert abstention["selective_by_binding"]["linguistic-group"]["opportunities"] == 2
    assert abstention["combined"]["opportunities"] == 3


# ---------------------------------------------------------------------------
# Human review burden
# ---------------------------------------------------------------------------


def test_human_review_burden_global_stratum_and_binding() -> None:
    annotations = [
        {
            "case_id": "c1",
            "binding_id": "linguistic-family",
            "risk_stratum": "A",
            "decision": "ACCEPT_AS_IS",
        },
        {
            "case_id": "c1",
            "binding_id": "linguistic-family",
            "risk_stratum": "A",
            "decision": "ACCEPT_AS_IS",
        },
        {
            "case_id": "c2",
            "binding_id": "registered-language",
            "risk_stratum": "A",
            "decision": "RESEARCH_REQUIRED",
        },
    ]
    run = score_run([], human_review_annotations=annotations)
    burden = run["human_review_burden"]
    assert burden["overall"]["n"] == 3
    assert burden["overall"]["counts"]["ACCEPT_AS_IS"] == 2
    assert burden["overall"]["proportions"]["ACCEPT_AS_IS"] == pytest.approx(2 / 3)
    assert burden["by_risk_stratum"]["A"]["n"] == 3
    assert burden["by_binding"]["linguistic-family"]["n"] == 2
    assert burden["by_binding"]["registered-language"]["n"] == 1


def test_human_review_burden_empty_is_explicitly_non_evaluable() -> None:
    run = score_run([])
    burden = run["human_review_burden"]["overall"]
    assert burden["n"] == 0
    assert burden["proportions"] is None


def test_human_review_burden_rejects_unknown_decision() -> None:
    with pytest.raises(ValueError):
        score_run(
            [],
            human_review_annotations=[
                {"case_id": "c1", "binding_id": "x", "risk_stratum": "A", "decision": "MAYBE"}
            ],
        )


# ---------------------------------------------------------------------------
# Macro metrics, aggregation by binding/stratum, explicit non-evaluable states
# ---------------------------------------------------------------------------


def _run_case(case_id: str, expected: dict, candidates: list[dict], manifest: dict) -> dict:
    return {
        "case_id": case_id,
        "manifest": manifest,
        "expected": expected,
        "proposed": {"candidates": candidates},
    }


def _manifest(binding: str, opportunity_count: int = 1, risk_stratum: str = "A") -> dict:
    return {
        "risk_stratum": risk_stratum,
        "bindings_under_test": [binding],
        "opportunity_count": opportunity_count,
    }


def test_macro_metrics_average_across_evaluable_bindings_only() -> None:
    perfect = _run_case(
        "perfect",
        _gold("linguistic-family"),
        [_candidate("linguistic-family")],
        _manifest("linguistic-family"),
    )
    all_wrong = _run_case(
        "all-wrong",
        _gold("linguistic-branch"),
        [_candidate("linguistic-branch", value="Nope")],
        _manifest("linguistic-branch"),
    )
    run = score_run([perfect, all_wrong])
    # linguistic-family precision=1.0, linguistic-branch precision=0.0 (proposed
    # but not matched); other 3 critical bindings remain non-evaluable (None)
    # and macro averaging must skip them rather than treating them as 0.
    assert run["by_binding"]["linguistic-family"]["precision"] == 1.0
    assert run["by_binding"]["linguistic-branch"]["precision"] == 0.0
    for binding in ("linguistic-group", "linguistic-variant", "registered-language"):
        assert run["by_binding"][binding]["precision"] is None
    assert run["overall"]["macro_precision_by_binding"] == pytest.approx(0.5)


def test_macro_metrics_none_when_nothing_evaluable() -> None:
    run = score_run([])
    assert run["overall"]["macro_precision_by_binding"] is None
    assert run["overall"]["macro_recall_by_binding"] is None
    assert run["overall"]["macro_precision_by_case"] is None
    assert run["overall"]["macro_recall_by_case"] is None


def test_aggregation_by_binding_and_stratum_is_visible_even_when_empty() -> None:
    case = _run_case(
        "only-family",
        _gold("linguistic-family"),
        [_candidate("linguistic-family")],
        _manifest("linguistic-family"),
    )
    run = score_run([case])
    # All five critical bindings and all three strata are always present,
    # even with zero opportunities, so a critical-but-untested binding can
    # never silently disappear from the report.
    assert set(run["by_binding"]) >= {
        "linguistic-family",
        "linguistic-branch",
        "linguistic-group",
        "linguistic-variant",
        "registered-language",
    }
    assert run["by_binding"]["registered-language"]["case_count"] == 0
    assert run["by_binding"]["registered-language"]["precision"] is None
    assert set(run["by_risk_stratum"]) == {"A", "B", "C"}
    assert run["by_risk_stratum"]["B"]["case_count"] == 0


def test_grounding_accuracy_not_evaluable_without_grounding_required_opportunities() -> None:
    result = score_case(_gold(), {"candidates": [_candidate("linguistic-family")]})
    assert result["grounding_accuracy"] is None


def test_recall_not_evaluable_when_recall_not_applicable_and_nothing_expected() -> None:
    gold = {
        "expected_candidates": [],
        "expected_abstentions": [],
        "recall_applicable": False,
        "hallucination_annotations": {"prohibited_values": []},
    }
    result = score_case(gold, {"candidates": []})
    assert result["recall"] is None
    assert result["fn"] == 0


# ---------------------------------------------------------------------------
# Stability under reordering
# ---------------------------------------------------------------------------


def test_reordering_equivalent_inputs_does_not_change_aggregate_results() -> None:
    cases = [
        _run_case(
            "family",
            _gold("linguistic-family"),
            [_candidate("linguistic-family")],
            _manifest("linguistic-family", 3),
        ),
        _run_case(
            "branch",
            _gold("linguistic-branch"),
            [_candidate("linguistic-branch", value="Nope")],
            _manifest("linguistic-branch", 3),
        ),
        _run_case(
            "group",
            _gold("linguistic-group"),
            [],
            _manifest("linguistic-group", 3),
        ),
    ]
    reversed_cases = list(reversed(copy.deepcopy(cases)))

    run_forward = score_run(cases)
    run_reversed = score_run(reversed_cases)

    def _without_case_order(report: dict) -> dict:
        clone = dict(report)
        clone["cases"] = sorted(clone["cases"], key=lambda c: c["case_id"])
        return clone

    assert _without_case_order(run_forward) == _without_case_order(run_reversed)


# ---------------------------------------------------------------------------
# gate_assessment / threshold_profile invariants
# ---------------------------------------------------------------------------


def test_gate_assessment_and_threshold_profile_never_ratify() -> None:
    case = _run_case(
        "family",
        _gold("linguistic-family"),
        [_candidate("linguistic-family")],
        _manifest("linguistic-family", 20),
    )
    run = score_run([case] * 20)
    assert run["gate_assessment"] == "ASSESSMENT_ONLY"
    assert run["threshold_profile"] == "PROVISIONAL_TARGETS"
    serialized_values = _flatten(run)
    assert "PASS" not in serialized_values
    assert "FAIL" not in serialized_values


def test_threshold_comparison_is_informative_only_and_covers_every_provisional_target() -> None:
    run = score_run([])
    comparison = run["threshold_comparison"]
    expected_metrics = {
        "candidate_precision_micro",
        "binding_accuracy",
        "grounding_accuracy",
        "hallucination_rate",
        "false_proposal_rate_on_abstention",
        "controlled_vocab_exact_match",
        "intent_accuracy",
    }
    assert expected_metrics.issubset(comparison.keys())
    for metric in expected_metrics:
        entry = comparison[metric]
        assert entry["evaluable"] is False
        assert entry["meets_provisional_target"] is None
    assert "note" in comparison


def _flatten(value) -> set:
    found: set = set()
    if isinstance(value, dict):
        for v in value.values():
            found |= _flatten(v)
    elif isinstance(value, list):
        for v in value:
            found |= _flatten(v)
    elif isinstance(value, str):
        found.add(value)
    return found


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


def test_score_run_positional_call_still_works_without_new_kwargs() -> None:
    case = _run_case(
        "family",
        _gold("linguistic-family"),
        [_candidate("linguistic-family")],
        _manifest("linguistic-family"),
    )
    run = score_run([case])
    assert run["evaluation_run_id"] is None
    assert run["golden_set_version"] is None
    assert run["catalog_contract_version"] is None
    assert run["scorer_version"]
    assert run["overall"]["tp"] == 1


def test_score_case_preserves_original_return_keys() -> None:
    result = score_case(_gold(), {"candidates": [_candidate("linguistic-family")]})
    original_keys = (
        "tp",
        "fp",
        "fn",
        "precision",
        "recall",
        "binding_accuracy",
        "grounding_accuracy",
        "hallucination_rate",
        "errors",
    )
    for key in original_keys:
        assert key in result
