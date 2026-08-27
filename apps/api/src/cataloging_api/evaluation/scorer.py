from __future__ import annotations

import json
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from statistics import fmean
from typing import Any

SCORER_VERSION = "0.3.0"
MATCHING_ALGORITHM_VERSION = "deterministic-maximum-bipartite-v3"
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
    return metadata if any(value is not None for value in metadata.values()) else None


def _controlled_vocabulary_complete(metadata: dict[str, Any] | None) -> bool:
    return metadata is not None and all(metadata.values())


def _manifest_controlled_vocabulary(manifest: dict[str, Any]) -> dict[str, Any] | None:
    nested = manifest.get("controlled_vocabulary")
    if isinstance(nested, dict):
        metadata = {
            "vocabulary_id": nested.get("vocabulary_id"),
            "version": nested.get("version"),
            "hash": nested.get("hash"),
        }
    else:
        metadata = {
            "vocabulary_id": manifest.get("controlled_vocabulary_id"),
            "version": manifest.get("controlled_vocabulary_version"),
            "hash": manifest.get("controlled_vocabulary_hash"),
        }
    return metadata if any(value is not None for value in metadata.values()) else None


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


def _canonical_key(item: dict[str, Any], index: int) -> tuple[str, int]:
    return (
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        index,
    )


def _opportunity_matches(expected: dict[str, Any], candidate: dict[str, Any]) -> bool:
    expected_id = expected.get("opportunity_id")
    proposed_id = candidate.get("opportunity_id")
    if expected_id is None and proposed_id is None:
        return True
    return expected_id == proposed_id


def _maximum_matching(
    proposed: list[dict[str, Any]],
    expected: list[dict[str, Any]],
    eligible: Callable[[dict[str, Any], dict[str, Any]], bool],
    *,
    proposed_indices: Iterable[int] | None = None,
) -> list[tuple[int, int]]:
    left = list(range(len(proposed))) if proposed_indices is None else list(proposed_indices)
    left.sort(key=lambda index: _canonical_key(proposed[index], index))
    right = sorted(range(len(expected)), key=lambda index: _canonical_key(expected[index], index))
    adjacency = {
        p_idx: [e_idx for e_idx in right if eligible(expected[e_idx], proposed[p_idx])]
        for p_idx in left
    }
    matched_right: dict[int, int] = {}

    def augment(p_idx: int, visited: set[int]) -> bool:
        for e_idx in adjacency[p_idx]:
            if e_idx in visited:
                continue
            visited.add(e_idx)
            incumbent = matched_right.get(e_idx)
            if incumbent is None or augment(incumbent, visited):
                matched_right[e_idx] = p_idx
                return True
        return False

    for p_idx in left:
        augment(p_idx, set())

    return sorted(
        ((e_idx, p_idx) for e_idx, p_idx in matched_right.items()),
        key=lambda pair: (_canonical_key(proposed[pair[1]], pair[1]), pair[0]),
    )


def _abstention_matches_candidate(abstention: dict[str, Any], candidate: dict[str, Any]) -> bool:
    binding = abstention.get("binding_id")
    if binding not in {None, "*"} and candidate.get("binding_id") != binding:
        return False
    opportunity_id = abstention.get("opportunity_id")
    if opportunity_id is not None and candidate.get("opportunity_id") != opportunity_id:
        return False
    source_refs = set(abstention.get("source_refs", []))
    if source_refs and source_refs.isdisjoint(candidate.get("source_refs", [])):
        return False
    return True


def _pertinent_gold(
    expected: list[dict[str, Any]], candidate: dict[str, Any]
) -> tuple[int, dict[str, Any]] | None:
    severity_rank = {"minor": 0, "major": 1, "critical": 2}
    pertinent = [
        (index, gold)
        for index, gold in enumerate(expected)
        if gold.get("binding_id") == candidate.get("binding_id")
    ]
    if not pertinent:
        return None
    return max(
        pertinent,
        key=lambda item: (
            int(_opportunity_matches(item[1], candidate)),
            int(item[1].get("candidate_intent") == candidate.get("candidate_intent")),
            int(_value_matches(item[1], candidate)),
            severity_rank.get(item[1].get("severity", "major"), 1),
            -item[0],
        ),
    )


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
        "micro_recall": _ratio(
            counts.get("recall_tp", 0),
            counts.get("recall_tp", 0) + counts.get("recall_fn", 0),
        ),
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
    abstentions = list(expected_doc.get("expected_abstentions", []))
    abstention_violations: dict[int, list[int]] = {}
    abstained_proposed: set[int] = set()
    for a_idx, abstention in enumerate(abstentions):
        violations = [
            p_idx
            for p_idx, candidate in enumerate(proposed)
            if _abstention_matches_candidate(abstention, candidate)
        ]
        if violations:
            abstention_violations[a_idx] = violations
            abstained_proposed.update(violations)

    authoritative_pairs = _maximum_matching(
        proposed,
        expected,
        lambda gold, candidate: (
            _value_matches(gold, candidate)
            and candidate.get("binding_id") == gold.get("binding_id")
            and candidate.get("candidate_intent") == gold.get("candidate_intent")
            and _grounding_matches(gold, candidate)
            and _opportunity_matches(gold, candidate)
        ),
        proposed_indices=(
            index for index in range(len(proposed)) if index not in abstained_proposed
        ),
    )
    authoritative_matches = [
        Match(e_idx, p_idx, True, True, True, True, ()) for e_idx, p_idx in authoritative_pairs
    ]
    used_proposed = {p_idx for _e_idx, p_idx in authoritative_pairs}
    unmatched_proposed = [index for index in range(len(proposed)) if index not in used_proposed]

    binding_pairs = _maximum_matching(
        proposed,
        expected,
        lambda gold, candidate: (
            _value_matches(gold, candidate)
            and candidate.get("binding_id") != gold.get("binding_id")
            and candidate.get("candidate_intent") == gold.get("candidate_intent")
            and _grounding_matches(gold, candidate)
            and _opportunity_matches(gold, candidate)
        ),
        proposed_indices=unmatched_proposed,
    )
    binding_diagnostics = [
        Match(e_idx, p_idx, False, False, True, True, ("WRONG_BINDING",))
        for e_idx, p_idx in binding_pairs
    ]

    intent_pairs = _maximum_matching(
        proposed,
        expected,
        lambda gold, candidate: (
            _value_matches(gold, candidate)
            and candidate.get("binding_id") == gold.get("binding_id")
            and candidate.get("candidate_intent") != gold.get("candidate_intent")
            and _grounding_matches(gold, candidate)
            and _opportunity_matches(gold, candidate)
        ),
        proposed_indices=unmatched_proposed,
    )
    intent_diagnostics = [
        Match(e_idx, p_idx, False, True, False, True, ("WRONG_INTENT",))
        for e_idx, p_idx in intent_pairs
    ]

    grounding_pairs = _maximum_matching(
        proposed,
        expected,
        lambda gold, candidate: (
            gold.get("grounding_required", False)
            and _value_matches(gold, candidate)
            and candidate.get("binding_id") == gold.get("binding_id")
            and candidate.get("candidate_intent") == gold.get("candidate_intent")
            and not _grounding_matches(gold, candidate)
            and _opportunity_matches(gold, candidate)
        ),
        proposed_indices=unmatched_proposed,
    )
    grounding_diagnostics = [
        Match(e_idx, p_idx, False, True, True, False, ("BAD_GROUNDING",))
        for e_idx, p_idx in grounding_pairs
    ]
    matches = (
        authoritative_matches + binding_diagnostics + intent_diagnostics + grounding_diagnostics
    )

    authoritative_expected = {match.expected_index for match in authoritative_matches}
    tp = len(authoritative_expected)
    fp = len(proposed) - tp
    fn = len(expected) - tp if expected_doc.get("recall_applicable", True) else 0

    binding_matches = authoritative_matches + binding_diagnostics
    intent_matches = authoritative_matches + intent_diagnostics
    grounding_matches = [
        match
        for match in authoritative_matches + binding_diagnostics + grounding_diagnostics
        if expected[match.expected_index].get("grounding_required", False)
    ]

    prohibited = set(expected_doc.get("hallucination_annotations", {}).get("prohibited_values", []))
    unsupported_indices = {
        p_idx for p_idx, candidate in enumerate(proposed) if candidate.get("value") in prohibited
    }
    unsupported_indices.update(abstained_proposed)
    unsupported_indices.update(
        p_idx
        for p_idx, candidate in enumerate(proposed)
        if not any(_value_matches(gold, candidate) for gold in expected)
    )

    controlled_opportunities = 0
    controlled_correct = 0
    controlled_errors = []
    schema_errors = []
    for e_idx, gold in enumerate(expected):
        vocabulary = _controlled_vocabulary(gold)
        if vocabulary is None:
            continue
        if not _controlled_vocabulary_complete(vocabulary):
            schema_errors.append(e_idx)
            continue
        controlled_opportunities += 1
        authoritative = next(
            (match for match in authoritative_matches if match.expected_index == e_idx),
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
    for a_idx, proposed_indices in abstention_violations.items():
        for p_idx in proposed_indices:
            abstention_error = _error(
                "FALSE_PROPOSAL_ON_ABSTENTION",
                "abstention_gold",
                abstentions[a_idx].get("severity", expected_doc.get("severity", "major")),
                p_idx,
                a_idx,
            )
            abstention_error["expected_kind"] = "abstention"
            abstention_error["abstention_index"] = a_idx
            errors.append(abstention_error)
    for p_idx in range(len(proposed)):
        if p_idx in unsupported_indices and p_idx not in abstained_proposed:
            pertinent = _pertinent_gold(expected, proposed[p_idx])
            errors.append(
                _error(
                    "UNSUPPORTED_VALUE",
                    "authoritative_match",
                    (
                        pertinent[1].get("severity", "major")
                        if pertinent is not None
                        else proposed[p_idx].get("severity", expected_doc.get("severity", "major"))
                    ),
                    p_idx,
                    pertinent[0] if pertinent is not None else None,
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
    errors.extend(
        _error(
            "SCHEMA_INVALID",
            "controlled_vocabulary_gold",
            expected[e_idx].get("severity", "major"),
            expected_index=e_idx,
        )
        for e_idx in schema_errors
    )

    known_source_refs = {ref for gold in expected for ref in gold.get("source_refs_allowed", [])}
    known_source_refs.update(
        ref for abstention in abstentions for ref in abstention.get("source_refs", [])
    )
    for p_idx, candidate in enumerate(proposed):
        refs = set(candidate.get("source_refs", []))
        source_gold = [
            (e_idx, gold)
            for e_idx, gold in enumerate(expected)
            if candidate.get("binding_id") == gold.get("binding_id")
            and _value_matches(gold, candidate)
            and _opportunity_matches(gold, candidate)
        ]
        invalid_for_candidate = bool(source_gold) and not any(
            _source_refs_match(gold, candidate) for _e_idx, gold in source_gold
        )
        outside_manifest = bool(refs - known_source_refs)
        if invalid_for_candidate or outside_manifest:
            pertinent = source_gold[0] if source_gold else _pertinent_gold(expected, candidate)
            e_idx = pertinent[0] if pertinent is not None else None
            gold = pertinent[1] if pertinent is not None else {}
            errors.append(
                _error(
                    "INVALID_SOURCE_REF",
                    "source_manifest_validation",
                    gold.get("severity", expected_doc.get("severity", "major")),
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
        semantic_identity = {
            "binding_id": candidate.get("binding_id"),
            "candidate_intent": candidate.get("candidate_intent"),
            "value": candidate.get("value"),
            "opportunity_id": candidate.get("opportunity_id"),
            "source_refs": sorted(set(candidate.get("source_refs", []))),
            "grounding_ranges": sorted(
                candidate.get("grounding_ranges", []),
                key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
            ),
        }
        identity = json.dumps(
            semantic_identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
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
        recall_tp=tp if expected_doc.get("recall_applicable", True) else 0,
        recall_fn=fn,
        binding_correct=len(authoritative_matches),
        binding_evaluable=len(binding_matches),
        intent_correct=len(authoritative_matches),
        intent_evaluable=len(intent_matches),
        grounding_correct=sum(match.grounding_ok for match in grounding_matches),
        grounding_evaluable=len(grounding_matches),
        unsupported=len(unsupported_indices),
        proposals=len(proposed),
        controlled_vocab_correct=controlled_correct,
        controlled_vocab_opportunities=controlled_opportunities,
        true_abstentions=len(abstentions) - len(abstention_violations),
        false_abstentions=len(abstention_violations),
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
            if expected_doc.get("recall_applicable", True):
                target["recall_tp"] += int(match.authoritative)
            if match.authoritative or "WRONG_BINDING" in match.errors:
                target["binding_evaluable"] += 1
                target["binding_correct"] += int(match.binding_ok)
            if match.authoritative or "WRONG_INTENT" in match.errors:
                target["intent_evaluable"] += 1
                target["intent_correct"] += int(match.intent_ok)
            if gold.get("grounding_required", False) and (
                match.authoritative
                or "WRONG_BINDING" in match.errors
                or "BAD_GROUNDING" in match.errors
            ):
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
                target["recall_fn"] += 1
            if _controlled_vocabulary_complete(_controlled_vocabulary(gold)):
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
        target["false_abstentions"] += int(a_idx in abstention_violations)
        target["true_abstentions"] += int(a_idx not in abstention_violations)

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
        recall_tp=metrics["micro_recall"]["numerator"],
        recall_fn=(metrics["micro_recall"]["denominator"] - metrics["micro_recall"]["numerator"]),
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


def _expected_with_manifest_vocabulary(
    expected_doc: dict[str, Any], manifest: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_vocabulary = _manifest_controlled_vocabulary(manifest)
    prepared = dict(expected_doc)
    prepared_candidates = []
    issues = []
    if manifest_vocabulary is not None and not _controlled_vocabulary_complete(manifest_vocabulary):
        issues.append(
            {
                "expected_index": None,
                "code": "CONTROLLED_VOCABULARY_MANIFEST_IDENTITY_INCOMPLETE",
                "missing_fields": sorted(
                    key for key, value in manifest_vocabulary.items() if not value
                ),
            }
        )
    for e_idx, original in enumerate(expected_doc.get("expected_candidates", [])):
        gold = dict(original)
        declared = _controlled_vocabulary(gold)
        if declared is None and manifest_vocabulary is not None:
            gold["controlled_vocabulary"] = dict(manifest_vocabulary)
            declared = manifest_vocabulary
        elif (
            declared is not None
            and manifest_vocabulary is not None
            and declared != manifest_vocabulary
        ):
            issues.append(
                {
                    "expected_index": e_idx,
                    "code": "CONTROLLED_VOCABULARY_IDENTITY_CONFLICT",
                    "expected": declared,
                    "manifest": manifest_vocabulary,
                }
            )
        if declared is not None and not _controlled_vocabulary_complete(declared):
            issues.append(
                {
                    "expected_index": e_idx,
                    "code": "CONTROLLED_VOCABULARY_IDENTITY_INCOMPLETE",
                    "missing_fields": sorted(key for key, value in declared.items() if not value),
                }
            )
        prepared_candidates.append(gold)
    prepared["expected_candidates"] = prepared_candidates
    return prepared, issues


def _normalize_final_adjudication(
    annotation: dict[str, Any],
    *,
    case_id: str,
    risk_stratum: str,
    allowed_bindings: set[str],
    run_metadata: dict[str, Any],
) -> dict[str, Any]:
    required = {
        "adjudication_id",
        "adjudication_status",
        "case_id",
        "binding_id",
        "final_decision",
        "evidence_snapshot_sha256",
        "input_golden_set_version",
        "catalog_contract_version",
        "catalog_contract_sha256",
        "resulting_gold_version",
        "input_review_ids",
    }
    missing = sorted(field for field in required if not annotation.get(field))
    if missing:
        raise ValueError(
            "human review burden requires versioned FINAL adjudication; missing fields: "
            + ", ".join(missing)
        )
    if annotation["adjudication_status"] != "FINAL":
        raise ValueError("human review burden accepts only adjudication_status=FINAL")
    if annotation["case_id"] != case_id:
        raise ValueError(
            f"adjudication case_id {annotation['case_id']} does not match case {case_id}"
        )
    binding = annotation["binding_id"]
    if binding not in allowed_bindings:
        raise ValueError(f"adjudication binding_id {binding} is not part of case {case_id}")
    review_ids = annotation["input_review_ids"]
    if len(review_ids) != len(set(review_ids)):
        raise ValueError("adjudication input_review_ids must be distinct")
    if risk_stratum == "A" and len(review_ids) < 2:
        raise ValueError("Stratum A burden requires two independent input reviews")
    run_contract = run_metadata.get("catalog_contract_version")
    if run_contract and annotation["catalog_contract_version"] != run_contract:
        raise ValueError("adjudication catalog contract does not match evaluation run")
    run_gold = run_metadata.get("golden_set_version")
    accepted_gold_versions = {
        annotation["input_golden_set_version"],
        annotation["resulting_gold_version"],
    }
    if run_gold and run_gold not in accepted_gold_versions:
        raise ValueError("adjudication Golden Set version does not match evaluation run")
    decision = annotation["final_decision"]
    if decision not in HUMAN_REVIEW_DECISIONS:
        raise ValueError(f"unsupported human review decision: {decision}")
    return {
        **annotation,
        "review_id": annotation["adjudication_id"],
        "decision": decision,
        "golden_set_version": annotation["resulting_gold_version"],
    }


def _human_review_summary(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    if not reviews:
        return {
            "status": "NOT_EVALUABLE",
            "total": 0,
            "counts": {decision: 0 for decision in sorted(HUMAN_REVIEW_DECISIONS)},
            "proportions": {decision: None for decision in sorted(HUMAN_REVIEW_DECISIONS)},
        }
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
    for value in ("A", "B", "C"):
        group_counts["risk_stratum"][value]
    for value in sorted(CRITICAL_BINDINGS):
        group_counts["binding"][value]
    for value in ("INFERRED_VALUE", "GENERATED_CONTENT"):
        group_counts["intent"][value]
    reviews = []
    reviews_by_stratum: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reviews_by_binding: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_adjudication_ids: set[str] = set()
    seen_adjudication_units: set[tuple[str, str]] = set()
    critical_opportunities = defaultdict(int)
    stratum_a_opportunities = 0
    controlled_vocabularies: dict[tuple[str, str, str], dict[str, Any]] = {}
    controlled_vocabulary_issues = []

    for case in sorted(cases, key=lambda item: item["case_id"]):
        manifest = case.get("manifest", {})
        prepared_expected, vocabulary_issues = _expected_with_manifest_vocabulary(
            case["expected"], manifest
        )
        controlled_vocabulary_issues.extend(
            {"case_id": case["case_id"], **issue} for issue in vocabulary_issues
        )
        result, dimensions = _score_case_internal(prepared_expected, case["proposed"])
        manifest_vocabulary = _manifest_controlled_vocabulary(manifest)
        if _controlled_vocabulary_complete(manifest_vocabulary):
            assert manifest_vocabulary is not None
            key = (
                str(manifest_vocabulary["vocabulary_id"]),
                str(manifest_vocabulary["version"]),
                str(manifest_vocabulary["hash"]),
            )
            controlled_vocabularies[key] = manifest_vocabulary
        for gold in prepared_expected.get("expected_candidates", []):
            vocabulary = _controlled_vocabulary(gold)
            if _controlled_vocabulary_complete(vocabulary):
                assert vocabulary is not None
                key = (
                    str(vocabulary["vocabulary_id"]),
                    str(vocabulary["version"]),
                    str(vocabulary["hash"]),
                )
                controlled_vocabularies[key] = vocabulary
        scored.append({"case_id": case["case_id"], **result})
        case_counts = _counts_from_result(result)
        _add_counts(overall_counts, case_counts)
        overall_case_results.append(result)

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

        bindings_under_test = list(dict.fromkeys(manifest.get("bindings_under_test", [])))
        opportunities = int(manifest.get("opportunity_count", 0))
        explicit_by_binding = manifest.get("opportunity_count_by_binding")
        if isinstance(explicit_by_binding, dict):
            opportunities_by_binding = {
                binding: int(explicit_by_binding.get(binding, 0)) for binding in bindings_under_test
            }
        elif len(bindings_under_test) == 1:
            opportunities_by_binding = {bindings_under_test[0]: opportunities}
        else:
            opportunities_by_binding = Counter(
                gold.get("binding_id")
                for gold in prepared_expected.get("expected_candidates", [])
                if gold.get("binding_id") in bindings_under_test
            )
            opportunities_by_binding.update(
                abstention.get("binding_id")
                for abstention in prepared_expected.get("expected_abstentions", [])
                if abstention.get("binding_id") in bindings_under_test
            )
        if stratum == "A":
            stratum_a_opportunities += (
                opportunities
                if len(bindings_under_test) <= 1
                else sum(opportunities_by_binding.values())
            )
            for binding, binding_opportunities in opportunities_by_binding.items():
                if binding in CRITICAL_BINDINGS:
                    critical_opportunities[binding] += binding_opportunities

        allowed_bindings = {
            gold.get("binding_id")
            for gold in prepared_expected.get("expected_candidates", [])
            if gold.get("binding_id")
        }
        allowed_bindings.update(bindings_under_test)
        case_reviews = []
        for annotation in case.get("human_reviews", []):
            normalized = _normalize_final_adjudication(
                annotation,
                case_id=case["case_id"],
                risk_stratum=stratum,
                allowed_bindings=allowed_bindings,
                run_metadata=run_metadata,
            )
            adjudication_id = normalized["adjudication_id"]
            unit = (normalized["case_id"], normalized["binding_id"])
            if adjudication_id in seen_adjudication_ids:
                raise ValueError(f"duplicate adjudication_id: {adjudication_id}")
            if unit in seen_adjudication_units:
                raise ValueError(
                    "human review burden accepts one FINAL adjudication per case/binding"
                )
            seen_adjudication_ids.add(adjudication_id)
            seen_adjudication_units.add(unit)
            case_reviews.append(normalized)
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

    by_risk_stratum = summarize_dimension("risk_stratum")
    by_binding = summarize_dimension("binding")
    by_intent = summarize_dimension("intent")
    by_language = summarize_dimension("language")
    by_document_type = summarize_dimension("document_type")
    overall["macro_precision_by_case"] = dict(overall["macro_precision"])
    overall["macro_recall_by_case"] = dict(overall["macro_recall"])
    overall["macro_precision_by_binding"] = _mean(
        summary["micro_precision"]["value"] for summary in by_binding.values()
    )
    overall["macro_recall_by_binding"] = _mean(
        summary["micro_recall"]["value"] for summary in by_binding.values()
    )
    overall["macro_precision_by_risk_stratum"] = _mean(
        summary["micro_precision"]["value"] for summary in by_risk_stratum.values()
    )
    overall["macro_recall_by_risk_stratum"] = _mean(
        summary["micro_recall"]["value"] for summary in by_risk_stratum.values()
    )

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
    missing = [field for field in required if not provenance[field]]
    if controlled_vocabulary_issues:
        missing.append("controlled_vocabulary_identity")

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
            "controlled_vocabularies": [
                controlled_vocabularies[key] for key in sorted(controlled_vocabularies)
            ],
            "controlled_vocabulary_issues": controlled_vocabulary_issues,
            "status": "COMPLETE" if not missing else "INCOMPLETE",
            "missing_required_fields": missing,
        },
        "overall": overall,
        "by_risk_stratum": by_risk_stratum,
        "by_binding": by_binding,
        "by_intent": by_intent,
        "by_language": by_language,
        "by_document_type": by_document_type,
        "cases": scored,
        "sample_sufficiency": {
            "stratum_a_opportunities": stratum_a_opportunities,
            "critical_binding_opportunities": {
                binding: critical_opportunities.get(binding, 0)
                for binding in sorted(CRITICAL_BINDINGS)
            },
            "missing_minimums": missing_critical,
            "status": "SUFFICIENT" if sample_sufficient else "INSUFFICIENT_SAMPLE",
        },
        "threshold_profile": THRESHOLD_PROFILE,
        "threshold_comparison": overall["threshold_comparison"],
        "gate_assessment": "ASSESSMENT_ONLY",
    }
