from __future__ import annotations

import json
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import fmean
from typing import Any

SCORER_VERSION = "0.2.0"
MATCHING_ALGORITHM_VERSION = "deterministic-one-to-one-v2"
GROUNDING_POLICY_VERSION = "closed-range-v1"
THRESHOLD_PROFILE = "PROVISIONAL_TARGETS"

CRITICAL_BINDINGS = {
    "linguistic-family",
    "linguistic-branch",
    "linguistic-group",
    "linguistic-variant",
    "registered-language",
}
HUMAN_REVIEW_DECISIONS = {
    "ACCEPT_AS_IS",
    "ACCEPT_WITH_MINOR_EDIT",
    "RESEARCH_REQUIRED",
    "REJECT",
}
PROVISIONAL_TARGETS = {
    "micro_precision": (">=", 0.95),
    "binding_accuracy": (">=", 0.98),
    "grounding_accuracy": (">=", 0.98),
    "hallucination_rate": ("<=", 0.02),
    "false_proposal_rate_on_abstention": ("<=", 0.05),
    "controlled_vocab_exact_match": (">=", 0.98),
    "intent_accuracy": (">=", 0.98),
}


@dataclass(frozen=True)
class Match:
    expected_index: int
    proposed_index: int
    authoritative: bool
    binding_ok: bool
    intent_ok: bool
    grounding_ok: bool
    errors: tuple[str, ...]


def _normalize(value: str, rule: str, aliases: Iterable[str] = ()) -> str:
    del aliases
    if rule == "none":
        return value
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    if rule in {"unicode_whitespace", "closed_alias_set"}:
        return normalized
    if rule == "casefold_if_contract_allows":
        return normalized.casefold()
    raise ValueError(f"unsupported normalization rule: {rule}")


def _value_matches(expected: dict[str, Any], proposed: dict[str, Any]) -> bool:
    rule = expected.get("normalization_rule", "none")
    accepted = expected.get("accepted_values", [])
    proposed_value = _normalize(str(proposed.get("value", "")), rule, accepted)
    return proposed_value in {_normalize(str(value), rule, accepted) for value in accepted}


def _source_refs_match(expected: dict[str, Any], proposed: dict[str, Any]) -> bool:
    refs = set(proposed.get("source_refs", []))
    allowed = set(expected.get("source_refs_allowed", []))
    return (not allowed and not refs) or (bool(refs) and refs.issubset(allowed))


def _grounding_matches(expected: dict[str, Any], proposed: dict[str, Any]) -> bool:
    if not expected.get("grounding_required", False):
        return _source_refs_match(expected, proposed)
    refs = set(proposed.get("source_refs", []))
    allowed = set(expected.get("source_refs_allowed", []))
    if not refs or not refs.issubset(allowed):
        return False
    candidates = proposed.get("grounding_ranges", [])
    gold_ranges = expected.get("accepted_grounding_ranges", [])
    policy = expected.get("grounding_policy", "exact_range")
    if policy in {"exact_range", "EXACT_RANGE"}:
        return any(candidate in gold_ranges for candidate in candidates)
    if policy in {"range_within_gold", "RANGE_CONTAINED_IN_ANY"}:
        return any(
            candidate.get("source_id") == gold.get("source_id")
            and candidate.get("start", -1) >= gold.get("start", 0)
            and candidate.get("end", -1) <= gold.get("end", -1)
            for candidate in candidates
            for gold in gold_ranges
        )
    if policy == "GOLD_RANGE_CONTAINED_IN_CANDIDATE":
        return any(
            candidate.get("source_id") == gold.get("source_id")
            and candidate.get("start", -1) <= gold.get("start", 0)
            and candidate.get("end", -1) >= gold.get("end", -1)
            for candidate in candidates
            for gold in gold_ranges
        )
    if policy == "EXACT_PAGE":
        return any(
            candidate.get("source_id") == gold.get("source_id")
            and candidate.get("page") == gold.get("page")
            for candidate in candidates
            for gold in gold_ranges
        )
    raise ValueError(f"unsupported grounding policy: {policy}")


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "value": numerator / denominator if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
        "status": "EVALUABLE" if denominator else "NOT_EVALUABLE",
    }


def _mean(values: Iterable[float | None]) -> dict[str, Any]:
    evaluable = [value for value in values if value is not None]
    return {
        "value": fmean(evaluable) if evaluable else None,
        "evaluable_units": len(evaluable),
        "status": "EVALUABLE" if evaluable else "NOT_EVALUABLE",
    }


def _controlled_vocabulary(expected: dict[str, Any]) -> dict[str, Any] | None:
    nested = expected.get("controlled_vocabulary")
    if isinstance(nested, dict):
        metadata = {
            "vocabulary_id": nested.get("vocabulary_id"),
            "version": nested.get("version"),
            "hash": nested.get("hash"),
        }
    else:
        metadata = {
            "vocabulary_id": expected.get("controlled_vocabulary_id"),
            "version": expected.get("controlled_vocabulary_version"),
            "hash": expected.get("controlled_vocabulary_hash"),
        }
    return metadata if all(metadata.values()) else None


def _controlled_vocabulary_value_matches(
    expected: dict[str, Any], proposed: dict[str, Any]
) -> bool:
    proposed_value = str(proposed.get("value", ""))
    accepted = [str(value) for value in expected.get("accepted_values", [])]
    if expected.get("normalization_rule") == "closed_alias_set":
        proposed_value = _normalize(proposed_value, "closed_alias_set")
        accepted = [_normalize(value, "closed_alias_set") for value in accepted]
    return proposed_value in accepted


def _error(
    code: str,
    origin: str,
    severity: str,
    proposed_index: int | None = None,
    expected_index: int | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "origin": origin,
        "severity": severity,
        "proposed_index": proposed_index,
        "expected_index": expected_index,
    }


def _empty_counts() -> defaultdict[str, int]:
    return defaultdict(int)


def _compare_provisional(summary: dict[str, Any]) -> dict[str, Any]:
    comparisons = {}
    for metric, (operator, target) in PROVISIONAL_TARGETS.items():
        result = summary.get(metric, {})
        value = result.get("value") if isinstance(result, dict) else None
        if value is None:
            outcome = "NOT_EVALUABLE"
        elif (operator == ">=" and value >= target) or (operator == "<=" and value <= target):
            outcome = "MEETS_PROVISIONAL_TARGET"
        else:
            outcome = "MISSES_PROVISIONAL_TARGET"
        comparisons[metric] = {
            "operator": operator,
            "target": target,
            "observed": value,
            "outcome": outcome,
            "governance_status": "INFORMATIONAL_NON_GATING",
        }
    return comparisons


def _summarize(counts: dict[str, int], case_results: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "n_cases": counts.get("n_cases", 0),
        "tp": counts.get("tp", 0),
        "fp": counts.get("fp", 0),
        "fn": counts.get("fn", 0),
        "micro_precision": _ratio(counts.get("tp", 0), counts.get("tp", 0) + counts.get("fp", 0)),
        "micro_recall": _ratio(counts.get("tp", 0), counts.get("tp", 0) + counts.get("fn", 0)),
        "macro_precision": _mean(result.get("precision") for result in case_results),
        "macro_recall": _mean(result.get("recall") for result in case_results),
        "binding_accuracy": _ratio(
            counts.get("binding_correct", 0), counts.get("binding_evaluable", 0)
        ),
        "grounding_accuracy": _ratio(
            counts.get("grounding_correct", 0), counts.get("grounding_evaluable", 0)
        ),
        "hallucination_rate": _ratio(counts.get("unsupported", 0), counts.get("proposals", 0)),
        "controlled_vocab_exact_match": _ratio(
            counts.get("controlled_vocab_correct", 0),
            counts.get("controlled_vocab_opportunities", 0),
        ),
        "intent_accuracy": _ratio(
            counts.get("intent_correct", 0), counts.get("intent_evaluable", 0)
        ),
        "true_abstention_rate": _ratio(
            counts.get("true_abstentions", 0), counts.get("abstention_opportunities", 0)
        ),
        "false_proposal_rate_on_abstention": _ratio(
            counts.get("false_abstentions", 0), counts.get("abstention_opportunities", 0)
        ),
    }
    summary["threshold_comparison"] = _compare_provisional(summary)
    return summary


def _score_case_internal(
    expected_doc: dict[str, Any], proposed_doc: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, dict[str, defaultdict[str, int]]]]:
    expected = list(expected_doc.get("expected_candidates", []))
    proposed = list(proposed_doc.get("candidates", []))
    used_expected: set[int] = set()
    used_proposed: set[int] = set()
    diagnostic_expected: set[int] = set()
    matches: list[Match] = []

    for p_idx, candidate in enumerate(proposed):
        for e_idx, gold in enumerate(expected):
            if e_idx in used_expected:
                continue
            binding_ok = candidate.get("binding_id") == gold.get("binding_id")
            intent_ok = candidate.get("candidate_intent") == gold.get("candidate_intent")
            grounding_ok = _grounding_matches(gold, candidate)
            if _value_matches(gold, candidate) and binding_ok and intent_ok and grounding_ok:
                used_expected.add(e_idx)
                used_proposed.add(p_idx)
                matches.append(Match(e_idx, p_idx, True, True, True, True, ()))
                break

    # Diagnostic pairing is deterministic and one-to-one and can never create a TP.
    for p_idx, candidate in enumerate(proposed):
        if p_idx in used_proposed:
            continue
        for e_idx, gold in enumerate(expected):
            if e_idx in used_expected or e_idx in diagnostic_expected:
                continue
            if not _value_matches(gold, candidate):
                continue
            binding_ok = candidate.get("binding_id") == gold.get("binding_id")
            intent_ok = candidate.get("candidate_intent") == gold.get("candidate_intent")
            grounding_ok = _grounding_matches(gold, candidate)
            errors = tuple(
                code
                for code, ok in (
                    ("WRONG_BINDING", binding_ok),
                    ("WRONG_INTENT", intent_ok),
                    ("BAD_GROUNDING", grounding_ok),
                )
                if not ok
            )
            diagnostic_expected.add(e_idx)
            matches.append(Match(e_idx, p_idx, False, binding_ok, intent_ok, grounding_ok, errors))
            break

    authoritative_expected = {match.expected_index for match in matches if match.authoritative}
    matched_proposed = {match.proposed_index for match in matches}
    tp = len(authoritative_expected)
    fp = len(proposed) - tp
    fn = len(expected) - tp if expected_doc.get("recall_applicable", True) else 0

    binding_matches = [
        match
        for match in matches
        if match.authoritative or (match.intent_ok and match.grounding_ok)
    ]
    intent_matches = [
        match
        for match in matches
        if match.authoritative or (match.binding_ok and match.grounding_ok)
    ]
    grounding_matches = [
        match
        for match in matches
        if expected[match.expected_index].get("grounding_required", False)
        and (match.authoritative or match.intent_ok)
    ]

    abstentions = list(expected_doc.get("expected_abstentions", []))
    failed_abstentions: dict[int, int] = {}
    for a_idx, abstention in enumerate(abstentions):
        binding = abstention.get("binding_id")
        violation = next(
            (
                p_idx
                for p_idx, candidate in enumerate(proposed)
                if binding in {None, "*"} or candidate.get("binding_id") == binding
            ),
            None,
        )
        if violation is not None:
            failed_abstentions[a_idx] = violation

    prohibited = set(expected_doc.get("hallucination_annotations", {}).get("prohibited_values", []))
    unsupported_indices = {
        p_idx for p_idx, candidate in enumerate(proposed) if candidate.get("value") in prohibited
    }
    unsupported_indices.update(failed_abstentions.values())

    controlled_opportunities = 0
    controlled_correct = 0
    controlled_errors = []
    for e_idx, gold in enumerate(expected):
        if _controlled_vocabulary(gold) is None:
            continue
        controlled_opportunities += 1
        authoritative = next(
            (match for match in matches if match.authoritative and match.expected_index == e_idx),
            None,
        )
        if authoritative is not None and _controlled_vocabulary_value_matches(
            gold, proposed[authoritative.proposed_index]
        ):
            controlled_correct += 1
        else:
            controlled_errors.append(e_idx)

    errors = []
    for match in matches:
        severity = expected[match.expected_index].get("severity", "major")
        errors.extend(
            _error(
                code, "diagnostic_value_match", severity, match.proposed_index, match.expected_index
            )
            for code in match.errors
        )
    for a_idx, p_idx in failed_abstentions.items():
        errors.append(
            _error(
                "FALSE_PROPOSAL_ON_ABSTENTION",
                "abstention_gold",
                abstentions[a_idx].get("severity", expected_doc.get("severity", "major")),
                p_idx,
            )
        )
    for p_idx in range(len(proposed)):
        if p_idx not in used_proposed and p_idx not in matched_proposed:
            errors.append(
                _error(
                    "UNSUPPORTED_VALUE",
                    "authoritative_match",
                    proposed[p_idx].get("severity", expected_doc.get("severity", "major")),
                    p_idx,
                )
            )
    if expected_doc.get("recall_applicable", True):
        for e_idx, gold in enumerate(expected):
            if e_idx not in authoritative_expected:
                errors.append(
                    _error(
                        "MISSING_EXPECTED_CANDIDATE",
                        "authoritative_match",
                        gold.get("severity", "major"),
                        expected_index=e_idx,
                    )
                )
    errors.extend(
        _error(
            "CONTROLLED_VOCAB_MISMATCH",
            "controlled_vocabulary_gold",
            expected[e_idx].get("severity", "major"),
            expected_index=e_idx,
        )
        for e_idx in controlled_errors
    )

    for p_idx, candidate in enumerate(proposed):
        source_gold = next(
            (
                (e_idx, gold)
                for e_idx, gold in enumerate(expected)
                if candidate.get("binding_id") == gold.get("binding_id")
                and _value_matches(gold, candidate)
            ),
            None,
        )
        if source_gold is not None and not _source_refs_match(source_gold[1], candidate):
            e_idx, gold = source_gold
            errors.append(
                _error(
                    "INVALID_SOURCE_REF",
                    "source_manifest_validation",
                    gold.get("severity", "major"),
                    p_idx,
                    e_idx,
                )
            )

    proposals_by_binding: dict[str, list[int]] = defaultdict(list)
    for p_idx, candidate in enumerate(proposed):
        proposals_by_binding[candidate.get("binding_id", "UNKNOWN")].append(p_idx)
    for e_idx, gold in enumerate(expected):
        binding = gold.get("binding_id", "UNKNOWN")
        proposed_count = len(proposals_by_binding[binding])
        minimum = gold.get("min_cardinality")
        maximum = gold.get("max_cardinality")
        if maximum is None and gold.get("cardinality") == "single":
            maximum = 1
        cardinality_invalid = (minimum is not None and proposed_count < int(minimum)) or (
            maximum is not None and proposed_count > int(maximum)
        )
        if cardinality_invalid:
            errors.append(
                _error(
                    "CARDINALITY_ERROR",
                    "cardinality_gold",
                    gold.get("severity", "major"),
                    expected_index=e_idx,
                )
            )

    seen_candidates: dict[str, int] = {}
    for p_idx, candidate in enumerate(proposed):
        identity = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if identity in seen_candidates:
            match = next((item for item in matches if item.proposed_index == p_idx), None)
            severity = (
                expected[match.expected_index].get("severity", "major")
                if match is not None
                else candidate.get("severity", expected_doc.get("severity", "major"))
            )
            errors.append(
                _error(
                    "DUPLICATE_CANDIDATE",
                    "candidate_identity",
                    severity,
                    p_idx,
                    match.expected_index if match is not None else None,
                )
            )
        else:
            seen_candidates[identity] = p_idx

    order_expected = {
        e_idx for e_idx, gold in enumerate(expected) if gold.get("order_significant", False)
    }
    ordered_matches = sorted(
        (
            match
            for match in matches
            if match.authoritative and match.expected_index in order_expected
        ),
        key=lambda match: match.proposed_index,
    )
    observed_order = [match.expected_index for match in ordered_matches]
    if (
        observed_order
        and set(observed_order) == order_expected
        and observed_order != sorted(order_expected)
    ):
        first = ordered_matches[0]
        errors.append(
            _error(
                "ORDER_ERROR",
                "order_gold",
                expected[first.expected_index].get("severity", "major"),
                first.proposed_index,
                first.expected_index,
            )
        )

    counts = _empty_counts()
    counts.update(
        n_cases=1,
        tp=tp,
        fp=fp,
        fn=fn,
        binding_correct=sum(match.binding_ok for match in binding_matches),
        binding_evaluable=len(binding_matches),
        intent_correct=sum(match.intent_ok for match in intent_matches),
        intent_evaluable=len(intent_matches),
        grounding_correct=sum(match.grounding_ok for match in grounding_matches),
        grounding_evaluable=len(grounding_matches),
        unsupported=len(unsupported_indices),
        proposals=len(proposed),
        controlled_vocab_correct=controlled_correct,
        controlled_vocab_opportunities=controlled_opportunities,
        true_abstentions=len(abstentions) - len(failed_abstentions),
        false_abstentions=len(failed_abstentions),
        abstention_opportunities=len(abstentions),
    )

    dimensions: dict[str, dict[str, defaultdict[str, int]]] = {
        "binding": defaultdict(_empty_counts),
        "intent": defaultdict(_empty_counts),
    }
    for match in matches:
        gold = expected[match.expected_index]
        for dimension, value in (
            ("binding", gold.get("binding_id", "UNKNOWN")),
            ("intent", gold.get("candidate_intent", "UNKNOWN")),
        ):
            target = dimensions[dimension][value]
            target["n_cases"] = 1
            target["tp"] += int(match.authoritative)
            if match.authoritative or (match.intent_ok and match.grounding_ok):
                target["binding_evaluable"] += 1
                target["binding_correct"] += int(match.binding_ok)
            if match.authoritative or (match.binding_ok and match.grounding_ok):
                target["intent_evaluable"] += 1
                target["intent_correct"] += int(match.intent_ok)
            if gold.get("grounding_required", False) and (match.authoritative or match.intent_ok):
                target["grounding_evaluable"] += 1
                target["grounding_correct"] += int(match.grounding_ok)
    for e_idx, gold in enumerate(expected):
        for dimension, value in (
            ("binding", gold.get("binding_id", "UNKNOWN")),
            ("intent", gold.get("candidate_intent", "UNKNOWN")),
        ):
            target = dimensions[dimension][value]
            target["n_cases"] = 1
            if expected_doc.get("recall_applicable", True) and e_idx not in authoritative_expected:
                target["fn"] += 1
            if _controlled_vocabulary(gold) is not None:
                target["controlled_vocab_opportunities"] += 1
                target["controlled_vocab_correct"] += int(e_idx not in controlled_errors)
    for p_idx, candidate in enumerate(proposed):
        for dimension, value in (
            ("binding", candidate.get("binding_id", "UNKNOWN")),
            ("intent", candidate.get("candidate_intent", "UNKNOWN")),
        ):
            target = dimensions[dimension][value]
            target["n_cases"] = 1
            target["proposals"] += 1
            target["fp"] += int(p_idx not in used_proposed)
            target["unsupported"] += int(p_idx in unsupported_indices)
    for a_idx, abstention in enumerate(abstentions):
        target = dimensions["binding"][abstention.get("binding_id", "ALL_BINDINGS")]
        target["n_cases"] = 1
        target["abstention_opportunities"] += 1
        target["false_abstentions"] += int(a_idx in failed_abstentions)
        target["true_abstentions"] += int(a_idx not in failed_abstentions)

    metrics = _summarize(counts, [])
    result = {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": metrics["micro_precision"]["value"],
        "recall": metrics["micro_recall"]["value"],
        "binding_accuracy": metrics["binding_accuracy"]["value"],
        "grounding_accuracy": metrics["grounding_accuracy"]["value"],
        "hallucination_rate": metrics["hallucination_rate"]["value"],
        "controlled_vocab_exact_match": metrics["controlled_vocab_exact_match"]["value"],
        "intent_accuracy": metrics["intent_accuracy"]["value"],
        "true_abstention_rate": metrics["true_abstention_rate"]["value"],
        "false_proposal_rate_on_abstention": metrics["false_proposal_rate_on_abstention"]["value"],
        "metrics": metrics,
        "errors": sorted(
            errors,
            key=lambda item: (
                item["code"],
                item["proposed_index"] if item["proposed_index"] is not None else -1,
                item["expected_index"] if item["expected_index"] is not None else -1,
            ),
        ),
    }
    return result, dimensions


def score_case(expected_doc: dict[str, Any], proposed_doc: dict[str, Any]) -> dict[str, Any]:
    result, _ = _score_case_internal(expected_doc, proposed_doc)
    return result


def _add_counts(target: defaultdict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] += value


def _counts_from_result(result: dict[str, Any]) -> defaultdict[str, int]:
    metrics = result["metrics"]
    counts = _empty_counts()
    counts.update(
        n_cases=1,
        tp=result["tp"],
        fp=result["fp"],
        fn=result["fn"],
        binding_correct=metrics["binding_accuracy"]["numerator"],
        binding_evaluable=metrics["binding_accuracy"]["denominator"],
        grounding_correct=metrics["grounding_accuracy"]["numerator"],
        grounding_evaluable=metrics["grounding_accuracy"]["denominator"],
        unsupported=metrics["hallucination_rate"]["numerator"],
        proposals=metrics["hallucination_rate"]["denominator"],
        controlled_vocab_correct=metrics["controlled_vocab_exact_match"]["numerator"],
        controlled_vocab_opportunities=metrics["controlled_vocab_exact_match"]["denominator"],
        intent_correct=metrics["intent_accuracy"]["numerator"],
        intent_evaluable=metrics["intent_accuracy"]["denominator"],
        true_abstentions=metrics["true_abstention_rate"]["numerator"],
        false_abstentions=metrics["false_proposal_rate_on_abstention"]["numerator"],
        abstention_opportunities=metrics["true_abstention_rate"]["denominator"],
    )
    return counts


def _human_review_summary(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    if not reviews:
        return {
            "status": "NOT_EVALUABLE",
            "total": 0,
            "counts": {decision: 0 for decision in sorted(HUMAN_REVIEW_DECISIONS)},
            "proportions": {decision: None for decision in sorted(HUMAN_REVIEW_DECISIONS)},
        }
    required = {
        "review_id",
        "binding_id",
        "decision",
        "evidence_snapshot_sha256",
        "golden_set_version",
        "catalog_contract_version",
    }
    incomplete = [
        index
        for index, review in enumerate(reviews)
        if any(not review.get(field) for field in required)
    ]
    if incomplete:
        raise ValueError(
            "human review annotations must be versioned; incomplete review index(es): "
            + ", ".join(map(str, incomplete))
        )
    decisions = [review.get("decision") for review in reviews]
    unknown = sorted({decision for decision in decisions if decision not in HUMAN_REVIEW_DECISIONS})
    if unknown:
        raise ValueError(f"unsupported human review decision(s): {', '.join(map(str, unknown))}")
    counts = Counter(decisions)
    total = len(decisions)
    return {
        "status": "EVALUABLE",
        "total": total,
        "counts": {
            decision: counts.get(decision, 0) for decision in sorted(HUMAN_REVIEW_DECISIONS)
        },
        "proportions": {
            decision: counts.get(decision, 0) / total for decision in sorted(HUMAN_REVIEW_DECISIONS)
        },
    }


def score_run(
    cases: list[dict[str, Any]], run_metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    run_metadata = dict(run_metadata or {})
    scored = []
    overall_counts = _empty_counts()
    overall_case_results = []
    group_counts = {
        dimension: defaultdict(_empty_counts)
        for dimension in ("risk_stratum", "binding", "intent", "language", "document_type")
    }
    group_results = {dimension: defaultdict(list) for dimension in group_counts}
    reviews = []
    reviews_by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reviews_by_binding: dict[str, list[dict[str, Any]]] = defaultdict(list)
    critical_opportunities = defaultdict(int)
    stratum_a_opportunities = 0

    for case in sorted(cases, key=lambda item: item["case_id"]):
        result, dimensions = _score_case_internal(case["expected"], case["proposed"])
        scored.append({"case_id": case["case_id"], **result})
        case_counts = _counts_from_result(result)
        _add_counts(overall_counts, case_counts)
        overall_case_results.append(result)

        manifest = case.get("manifest", {})
        stratum = manifest.get("risk_stratum", "UNKNOWN")
        dimension_values = {
            "risk_stratum": [stratum],
            "language": manifest.get("languages", []) or ["UNKNOWN"],
            "document_type": [manifest.get("document_type", "UNKNOWN")],
        }
        for dimension, values in dimension_values.items():
            for value in values:
                _add_counts(group_counts[dimension][value], case_counts)
                group_results[dimension][value].append(result)
        for dimension in ("binding", "intent"):
            for value, counts in dimensions[dimension].items():
                _add_counts(group_counts[dimension][value], counts)
                local = _summarize(counts, [])
                group_results[dimension][value].append(
                    {
                        "precision": local["micro_precision"]["value"],
                        "recall": local["micro_recall"]["value"],
                    }
                )

        for binding in manifest.get("bindings_under_test", []):
            group_counts["binding"][binding]["n_cases"] += 0
            group_results["binding"][binding].append({"precision": None, "recall": None})
        for intent in manifest.get("intent_classes", []):
            group_counts["intent"][intent]["n_cases"] += 0
            group_results["intent"][intent].append({"precision": None, "recall": None})

        opportunities = int(manifest.get("opportunity_count", 0))
        if stratum == "A":
            stratum_a_opportunities += opportunities
            for binding in manifest.get("bindings_under_test", []):
                if binding in CRITICAL_BINDINGS:
                    critical_opportunities[binding] += opportunities

        case_reviews = list(case.get("human_reviews", []))
        reviews.extend(case_reviews)
        reviews_by_stratum[stratum].extend(case_reviews)
        for review in case_reviews:
            reviews_by_binding[review.get("binding_id", "UNKNOWN")].append(review)

    missing_critical = {
        binding: critical_opportunities.get(binding, 0)
        for binding in sorted(CRITICAL_BINDINGS)
        if critical_opportunities.get(binding, 0) < 3
    }
    sample_sufficient = stratum_a_opportunities >= 20 and not missing_critical

    overall = _summarize(overall_counts, overall_case_results)
    overall["human_review_burden"] = _human_review_summary(reviews)

    def summarize_dimension(dimension: str) -> dict[str, Any]:
        output = {}
        for value in sorted(group_counts[dimension]):
            summary = _summarize(group_counts[dimension][value], group_results[dimension][value])
            if dimension == "risk_stratum":
                summary["human_review_burden"] = _human_review_summary(reviews_by_stratum[value])
            if dimension == "binding":
                summary["human_review_burden"] = _human_review_summary(reviews_by_binding[value])
                if value in CRITICAL_BINDINGS:
                    n = critical_opportunities.get(value, 0)
                    summary["sample_opportunities"] = n
                    summary["sample_status"] = "SUFFICIENT" if n >= 3 else "INSUFFICIENT_SAMPLE"
            output[value] = summary
        return output

    metadata_fields = (
        "evaluation_run_id",
        "golden_set_version",
        "golden_set_hash",
        "catalog_contract_version",
        "catalog_contract_hash",
        "prompt_template_version",
        "adapter_version",
        "provider_model_id",
        "config_hash",
        "input_manifest_hashes",
        "output_hashes",
        "run_timestamp",
        "environment_runtime_id",
    )
    provenance = {field: run_metadata.get(field) for field in metadata_fields}
    required = (
        "evaluation_run_id",
        "golden_set_version",
        "golden_set_hash",
        "catalog_contract_version",
        "catalog_contract_hash",
        "config_hash",
        "input_manifest_hashes",
        "output_hashes",
        "run_timestamp",
        "environment_runtime_id",
    )
    missing = [field for field in required if provenance[field] is None]

    return {
        "evaluation_run_id": provenance["evaluation_run_id"],
        "golden_set_version": provenance["golden_set_version"],
        "catalog_contract_version": provenance["catalog_contract_version"],
        "scorer_version": SCORER_VERSION,
        "provenance": {
            **provenance,
            "scorer_version": SCORER_VERSION,
            "matching_algorithm_version": MATCHING_ALGORITHM_VERSION,
            "grounding_policy_version": GROUNDING_POLICY_VERSION,
            "status": "COMPLETE" if not missing else "INCOMPLETE",
            "missing_required_fields": missing,
        },
        "overall": overall,
        "by_risk_stratum": summarize_dimension("risk_stratum"),
        "by_binding": summarize_dimension("binding"),
        "by_intent": summarize_dimension("intent"),
        "by_language": summarize_dimension("language"),
        "by_document_type": summarize_dimension("document_type"),
        "cases": scored,
        "sample_sufficiency": {
            "stratum_a_opportunities": stratum_a_opportunities,
            "critical_binding_opportunities": dict(sorted(critical_opportunities.items())),
            "missing_minimums": missing_critical,
            "status": "SUFFICIENT" if sample_sufficient else "INSUFFICIENT_SAMPLE",
        },
        "threshold_profile": THRESHOLD_PROFILE,
        "threshold_comparison": overall["threshold_comparison"],
        "gate_assessment": "ASSESSMENT_ONLY",
    }
