from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable
import unicodedata


SCORER_VERSION = "0.3.0-gate-d1-metrics"

CRITICAL_BINDINGS = {
    "linguistic-family",
    "linguistic-branch",
    "linguistic-group",
    "linguistic-variant",
    "registered-language",
}

RISK_STRATA = ("A", "B", "C")

HUMAN_REVIEW_DECISIONS = (
    "ACCEPT_AS_IS",
    "ACCEPT_WITH_MINOR_EDIT",
    "RESEARCH_REQUIRED",
    "REJECT",
)

# Comparators are informative only. They never rename PROVISIONAL_TARGETS as
# ratified/approved thresholds and never produce a PASS/FAIL semantic; see
# `_compare_to_target` and the `threshold_comparison`/`gate_assessment` output.
PROVISIONAL_TARGETS: dict[str, tuple[float, str]] = {
    "candidate_precision_micro": (0.95, "gte"),
    "binding_accuracy": (0.98, "gte"),
    "grounding_accuracy": (0.98, "gte"),
    "hallucination_rate": (0.02, "lte"),
    "false_proposal_rate_on_abstention": (0.05, "lte"),
    "controlled_vocab_exact_match": (0.98, "gte"),
    "intent_accuracy": (0.98, "gte"),
}

THRESHOLD_COMPARISON_NOTE = (
    "PROVISIONAL_TARGETS are not ratified thresholds. This comparison is "
    "informative only and never produces PASS/FAIL and never closes Gate D "
    "or Gate D1."
)


@dataclass(frozen=True)
class Match:
    expected_index: int
    proposed_index: int
    authoritative: bool
    diagnostic_value_match: bool
    binding_ok: bool
    intent_ok: bool
    grounding_ok: bool
    errors: tuple[str, ...]


def _normalize(value: str, rule: str, aliases: Iterable[str] = ()) -> str:
    if rule == "none":
        return value
    if rule == "unicode_whitespace":
        return " ".join(unicodedata.normalize("NFC", value).split())
    if rule == "casefold_if_contract_allows":
        return " ".join(unicodedata.normalize("NFC", value).split()).casefold()
    if rule == "closed_alias_set":
        normalized = " ".join(unicodedata.normalize("NFC", value).split())
        normalized_aliases = {
            " ".join(unicodedata.normalize("NFC", alias).split()) for alias in aliases
        }
        return normalized if normalized in normalized_aliases else normalized
    raise ValueError(f"unsupported normalization rule: {rule}")


def _value_matches(expected: dict[str, Any], proposed: dict[str, Any]) -> bool:
    rule = expected.get("normalization_rule", "none")
    aliases = expected.get("accepted_values", [])
    proposed_value = str(proposed.get("value", ""))
    normalized_proposed = _normalize(proposed_value, rule, aliases)
    normalized_expected = {_normalize(str(value), rule, aliases) for value in aliases}
    return normalized_proposed in normalized_expected


def _grounding_matches(expected: dict[str, Any], proposed: dict[str, Any]) -> bool:
    if not expected.get("grounding_required", False):
        return True
    refs = set(proposed.get("source_refs", []))
    allowed_refs = set(expected.get("source_refs_allowed", []))
    if not refs or not refs.issubset(allowed_refs):
        return False
    proposed_ranges = proposed.get("grounding_ranges", [])
    accepted = expected.get("accepted_grounding_ranges", [])
    policy = expected.get("grounding_policy", "exact_range")
    if policy == "exact_range":
        return any(candidate in accepted for candidate in proposed_ranges)
    if policy == "range_within_gold":
        for candidate in proposed_ranges:
            for gold in accepted:
                if candidate.get("source_id") != gold.get("source_id"):
                    continue
                if (
                    candidate.get("start", -1) >= gold.get("start", 0)
                    and candidate.get("end", -1) <= gold.get("end", -1)
                ):
                    return True
        return False
    raise ValueError(f"unsupported grounding policy: {policy}")


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _macro_average(values: Iterable[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return sum(usable) / len(usable)


def score_case(expected_doc: dict[str, Any], proposed_doc: dict[str, Any]) -> dict[str, Any]:
    """Score one case against its adjudicated gold.

    Two independent diagnostic axes are computed for any proposed candidate
    whose *value* can be anchored to an expected opportunity but whose full
    authoritative match fails: WRONG_BINDING (binding differs while intent
    still coincides) and WRONG_INTENT (intent differs while binding still
    coincides). BAD_GROUNDING is orthogonal to both and is reported whenever
    grounding is required and fails, regardless of binding/intent outcome.
    A candidate that fails *both* binding and intent is intentionally left
    undiagnosed on those two axes (the scorer does not guess which one was
    "more wrong") and falls back to UNSUPPORTED_VALUE.
    """

    expected = list(expected_doc.get("expected_candidates", []))
    proposed = list(proposed_doc.get("candidates", []))
    recall_applicable = bool(expected_doc.get("recall_applicable", True))

    used_expected: set[int] = set()
    used_proposed: set[int] = set()
    diagnostic_used_expected: set[int] = set()
    matches: list[Match] = []

    # Phase 1 — authoritative matching. A binding-incorrect candidate can
    # never become TP here, by construction (binding_ok is a hard gate).
    for p_idx, candidate in enumerate(proposed):
        for e_idx, gold in enumerate(expected):
            if e_idx in used_expected:
                continue
            value_ok = _value_matches(gold, candidate)
            intent_ok = candidate.get("candidate_intent") == gold.get("candidate_intent")
            binding_ok = candidate.get("binding_id") == gold.get("binding_id")
            grounding_ok = _grounding_matches(gold, candidate)
            if value_ok and intent_ok and binding_ok and grounding_ok:
                used_expected.add(e_idx)
                used_proposed.add(p_idx)
                matches.append(Match(e_idx, p_idx, True, True, True, True, True, ()))
                break

    # Phase 2 — diagnostic matching. One-to-one, never produces TP, never
    # reduces authoritative FP/FN. Anchored purely on value equality; binding
    # / intent / grounding are then diagnosed as independent axes.
    for p_idx, candidate in enumerate(proposed):
        if p_idx in used_proposed:
            continue
        for e_idx, gold in enumerate(expected):
            if e_idx in diagnostic_used_expected:
                continue
            if not _value_matches(gold, candidate):
                continue
            intent_ok = candidate.get("candidate_intent") == gold.get("candidate_intent")
            binding_ok = candidate.get("binding_id") == gold.get("binding_id")
            grounding_ok = _grounding_matches(gold, candidate)
            diag_errors: list[str] = []
            if not binding_ok and intent_ok:
                diag_errors.append("WRONG_BINDING")
            if not intent_ok and binding_ok:
                diag_errors.append("WRONG_INTENT")
            if not grounding_ok:
                diag_errors.append("BAD_GROUNDING")
            diagnostic_used_expected.add(e_idx)
            matches.append(
                Match(
                    e_idx,
                    p_idx,
                    False,
                    True,
                    binding_ok,
                    intent_ok,
                    grounding_ok,
                    tuple(diag_errors),
                )
            )
            break

    tp = sum(1 for match in matches if match.authoritative)
    fp = len(proposed) - tp
    fn = (len(expected) - tp) if recall_applicable else 0

    binding_diagnostics = [
        match for match in matches if match.authoritative or "WRONG_BINDING" in match.errors
    ]
    binding_evaluable = len(binding_diagnostics)
    binding_correct = sum(1 for match in binding_diagnostics if match.binding_ok)
    binding_accuracy = _ratio(binding_correct, binding_evaluable)

    grounding_diagnostics = [
        match
        for match in matches
        if expected[match.expected_index].get("grounding_required", False)
        and match.diagnostic_value_match
    ]
    grounding_evaluable = len(grounding_diagnostics)
    grounding_correct = sum(1 for match in grounding_diagnostics if match.grounding_ok)
    grounding_accuracy = _ratio(grounding_correct, grounding_evaluable)

    # Exact intent accuracy: evaluable exactly over value-anchored pairs
    # (authoritative or diagnostic), since only those have a gold intent to
    # compare against.
    intent_evaluable = len(matches)
    intent_correct = sum(1 for match in matches if match.intent_ok)
    intent_accuracy = _ratio(intent_correct, intent_evaluable)

    intent_by_class: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "evaluable": 0})
    for match in matches:
        gold_intent = expected[match.expected_index].get("candidate_intent")
        if gold_intent is None:
            continue
        intent_by_class[gold_intent]["evaluable"] += 1
        if match.intent_ok:
            intent_by_class[gold_intent]["correct"] += 1

    # Controlled-vocabulary exact-match: only for expected opportunities that
    # declare a frozen `controlled_vocabulary` identity. Reuses the
    # authoritative-match outcome (never a binding-incorrect TP) rather than
    # a separate value-only comparison.
    authoritative_expected_idx = {match.expected_index for match in matches if match.authoritative}
    cv_indices = [e_idx for e_idx, gold in enumerate(expected) if gold.get("controlled_vocabulary")]
    cv_opportunities = len(cv_indices)
    cv_authorized_matches = sum(1 for e_idx in cv_indices if e_idx in authoritative_expected_idx)
    controlled_vocab_exact_match = _ratio(cv_authorized_matches, cv_opportunities)

    unresolved_cv_by_binding: dict[str, list[int]] = defaultdict(list)
    for e_idx in cv_indices:
        if e_idx not in authoritative_expected_idx:
            unresolved_cv_by_binding[expected[e_idx].get("binding_id")].append(e_idx)

    # Abstention. An `expected_abstentions` entry without `binding_id` is a
    # full-case (complete) abstention opportunity; one with `binding_id` is a
    # selective, binding/opportunity-scoped abstention.
    abstention_entries = expected_doc.get("expected_abstentions", [])
    full_case_entries = [entry for entry in abstention_entries if not entry.get("binding_id")]
    selective_entries = [entry for entry in abstention_entries if entry.get("binding_id")]

    full_case_abstention_expected = len(full_case_entries) > 0
    full_case_true_abstention = (
        (len(proposed) == 0) if full_case_abstention_expected else None
    )

    abstention_flagged_proposed: set[int] = set()
    selective_opportunities: list[dict[str, Any]] = []
    for entry in selective_entries:
        binding_id = entry["binding_id"]
        matching_proposed = [
            p_idx
            for p_idx, candidate in enumerate(proposed)
            if candidate.get("binding_id") == binding_id
        ]
        true_abstention = not matching_proposed
        selective_opportunities.append(
            {
                "binding_id": binding_id,
                "reason": entry.get("reason"),
                "true_abstention": true_abstention,
                "false_proposal": not true_abstention,
            }
        )
        abstention_flagged_proposed.update(matching_proposed)

    if full_case_abstention_expected and proposed:
        abstention_flagged_proposed.update(range(len(proposed)))

    # Hallucination rate (gold-based). Uses index sets so a candidate that is
    # simultaneously a prohibited value and an abstention false-proposal is
    # never double counted.
    hallucination_annotations = expected_doc.get("hallucination_annotations", {})
    prohibited = set(hallucination_annotations.get("prohibited_values", []))
    prohibited_indices = {
        p_idx for p_idx, candidate in enumerate(proposed) if candidate.get("value") in prohibited
    }
    hallucination_indices = prohibited_indices | abstention_flagged_proposed
    hallucination_denominator = len(proposed)
    hallucination_rate = (
        len(hallucination_indices) / hallucination_denominator if hallucination_denominator else 0.0
    )

    # Error assembly — stable, machine-readable, preserving code/origin/
    # severity/candidate index/expected index.
    errors: list[dict[str, Any]] = []
    for match in matches:
        for code in match.errors:
            errors.append(
                {
                    "code": code,
                    "origin": "diagnostic_match",
                    "severity": expected[match.expected_index].get("severity"),
                    "proposed_index": match.proposed_index,
                    "expected_index": match.expected_index,
                }
            )

    for entry in selective_opportunities:
        if not entry["false_proposal"]:
            continue
        for p_idx, candidate in enumerate(proposed):
            if candidate.get("binding_id") == entry["binding_id"]:
                errors.append(
                    {
                        "code": "FALSE_PROPOSAL_ON_ABSTENTION",
                        "origin": "abstention",
                        "severity": None,
                        "proposed_index": p_idx,
                        "expected_index": None,
                    }
                )
    if full_case_abstention_expected and proposed:
        for p_idx in range(len(proposed)):
            errors.append(
                {
                    "code": "FALSE_PROPOSAL_ON_ABSTENTION",
                    "origin": "abstention",
                    "severity": None,
                    "proposed_index": p_idx,
                    "expected_index": None,
                }
            )

    # Only a diagnostic match that actually carries an explanatory error code
    # counts as "explained". An ambiguous double-fault (both binding and
    # intent wrong) intentionally records an errorless diagnostic Match (so
    # it still contributes to intent/binding-accuracy denominators without
    # asserting an unproven axis) but must still surface as UNSUPPORTED_VALUE
    # below rather than silently vanishing from the error report.
    explained_proposed = {
        match.proposed_index for match in matches if match.errors
    } | abstention_flagged_proposed
    cv_claimed: set[int] = set()
    for p_idx in range(len(proposed)):
        if p_idx in used_proposed or p_idx in explained_proposed:
            continue
        binding_id = proposed[p_idx].get("binding_id")
        cv_candidates = [
            e_idx
            for e_idx in unresolved_cv_by_binding.get(binding_id, [])
            if e_idx not in cv_claimed
        ]
        if cv_candidates:
            e_idx = cv_candidates[0]
            cv_claimed.add(e_idx)
            errors.append(
                {
                    "code": "CONTROLLED_VOCAB_MISMATCH",
                    "origin": "controlled_vocabulary",
                    "severity": expected[e_idx].get("severity"),
                    "proposed_index": p_idx,
                    "expected_index": e_idx,
                }
            )
        else:
            errors.append(
                {
                    "code": "UNSUPPORTED_VALUE",
                    "origin": "structural",
                    "severity": None,
                    "proposed_index": p_idx,
                    "expected_index": None,
                }
            )

    if recall_applicable:
        authoritative_expected = {match.expected_index for match in matches if match.authoritative}
        for e_idx in range(len(expected)):
            if e_idx not in authoritative_expected:
                errors.append(
                    {
                        "code": "MISSING_EXPECTED_CANDIDATE",
                        "origin": "structural",
                        "severity": expected[e_idx].get("severity"),
                        "proposed_index": None,
                        "expected_index": e_idx,
                    }
                )

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if (tp + fp) else 1.0,
        "recall": tp / (tp + fn) if (tp + fn) else None,
        "binding_accuracy": binding_accuracy,
        "binding_accuracy_counts": {"correct": binding_correct, "evaluable": binding_evaluable},
        "grounding_accuracy": grounding_accuracy,
        "grounding_accuracy_counts": {
            "correct": grounding_correct,
            "evaluable": grounding_evaluable,
        },
        "intent_accuracy": intent_accuracy,
        "intent_accuracy_counts": {"correct": intent_correct, "evaluable": intent_evaluable},
        "intent_by_class": {
            intent_class: dict(counts) for intent_class, counts in intent_by_class.items()
        },
        "controlled_vocab_exact_match": controlled_vocab_exact_match,
        "controlled_vocabulary": {
            "opportunities": cv_opportunities,
            "authorized_exact_matches": cv_authorized_matches,
        },
        "hallucination_rate": hallucination_rate,
        "hallucination_counts": {
            "numerator": len(hallucination_indices),
            "denominator": hallucination_denominator,
        },
        "abstention": {
            "full_case_expected": full_case_abstention_expected,
            "full_case_true": full_case_true_abstention,
            "selective_opportunities": selective_opportunities,
        },
        "errors": errors,
    }


def _new_agg_bucket() -> dict[str, Any]:
    return {
        "case_count": 0,
        "opportunity_count": 0,
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "tp_recall_applicable": 0,
        "binding_correct": 0,
        "binding_evaluable": 0,
        "grounding_correct": 0,
        "grounding_evaluable": 0,
        "hallucination_numerator": 0,
        "hallucination_denominator": 0,
        "intent_correct": 0,
        "intent_evaluable": 0,
        "cv_correct": 0,
        "cv_evaluable": 0,
    }


def _accumulate(
    bucket: dict[str, Any],
    case_result: dict[str, Any],
    recall_applicable: bool,
    opportunity_count: int,
) -> None:
    bucket["case_count"] += 1
    bucket["opportunity_count"] += opportunity_count
    bucket["tp"] += case_result["tp"]
    bucket["fp"] += case_result["fp"]
    bucket["fn"] += case_result["fn"]
    if recall_applicable:
        bucket["tp_recall_applicable"] += case_result["tp"]
    bucket["binding_correct"] += case_result["binding_accuracy_counts"]["correct"]
    bucket["binding_evaluable"] += case_result["binding_accuracy_counts"]["evaluable"]
    bucket["grounding_correct"] += case_result["grounding_accuracy_counts"]["correct"]
    bucket["grounding_evaluable"] += case_result["grounding_accuracy_counts"]["evaluable"]
    bucket["hallucination_numerator"] += case_result["hallucination_counts"]["numerator"]
    bucket["hallucination_denominator"] += case_result["hallucination_counts"]["denominator"]
    bucket["intent_correct"] += case_result["intent_accuracy_counts"]["correct"]
    bucket["intent_evaluable"] += case_result["intent_accuracy_counts"]["evaluable"]
    bucket["cv_correct"] += case_result["controlled_vocabulary"]["authorized_exact_matches"]
    bucket["cv_evaluable"] += case_result["controlled_vocabulary"]["opportunities"]


def _finalize_agg_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    tp_fp = bucket["tp"] + bucket["fp"]
    precision = (
        bucket["tp"] / tp_fp if tp_fp else (1.0 if bucket["case_count"] else None)
    )
    recall = _ratio(bucket["tp_recall_applicable"], bucket["tp_recall_applicable"] + bucket["fn"])
    hallucination_rate = (
        bucket["hallucination_numerator"] / bucket["hallucination_denominator"]
        if bucket["hallucination_denominator"]
        else (0.0 if bucket["case_count"] else None)
    )
    return {
        "case_count": bucket["case_count"],
        "opportunity_count": bucket["opportunity_count"],
        "tp": bucket["tp"],
        "fp": bucket["fp"],
        "fn": bucket["fn"],
        "precision": precision,
        "recall": recall,
        "binding_accuracy": _ratio(bucket["binding_correct"], bucket["binding_evaluable"]),
        "grounding_accuracy": _ratio(bucket["grounding_correct"], bucket["grounding_evaluable"]),
        "hallucination_rate": hallucination_rate,
        "intent_accuracy": _ratio(bucket["intent_correct"], bucket["intent_evaluable"]),
        "controlled_vocab_exact_match": _ratio(bucket["cv_correct"], bucket["cv_evaluable"]),
    }


def _new_human_review_bucket() -> dict[str, int]:
    return {decision: 0 for decision in HUMAN_REVIEW_DECISIONS}


def _finalize_human_review_bucket(counts: dict[str, int]) -> dict[str, Any]:
    total = sum(counts.values())
    return {
        "n": total,
        "counts": dict(counts),
        "proportions": (
            {decision: counts[decision] / total for decision in HUMAN_REVIEW_DECISIONS}
            if total
            else None
        ),
    }


def _abstention_rates(counts: dict[str, int]) -> dict[str, Any]:
    opportunities = counts["opportunities"]
    return {
        "opportunities": opportunities,
        "true_abstention": counts["true_abstention"],
        "false_proposal": counts["false_proposal"],
        "true_abstention_rate": _ratio(counts["true_abstention"], opportunities),
        "false_proposal_rate": _ratio(counts["false_proposal"], opportunities),
    }


def _compare_to_target(observed: float | None, target: float, comparator: str) -> bool | None:
    if observed is None:
        return None
    return observed >= target if comparator == "gte" else observed <= target


def score_run(
    cases: list[dict[str, Any]],
    *,
    evaluation_run_id: str | None = None,
    golden_set_version: str | None = None,
    catalog_contract_version: str | None = None,
    human_review_annotations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score a full evaluation run.

    `human_review_annotations` must be pre-joined, explicit records —
    `{"case_id", "binding_id", "risk_stratum", "decision"}` — typically built
    from FINAL adjudication artifacts. Human-review burden is never inferred
    from candidate matching; only from these versioned annotations.

    Report identity fields (`evaluation_run_id`, `golden_set_version`,
    `catalog_contract_version`) are taken verbatim from the caller and never
    fabricated; when omitted they are reported as `None` rather than guessed.
    `scorer_version` is intrinsic to this module and always populated.
    """

    scored: list[dict[str, Any]] = []

    overall_bucket = _new_agg_bucket()
    stratum_buckets: dict[str, dict[str, Any]] = defaultdict(_new_agg_bucket)
    binding_buckets: dict[str, dict[str, Any]] = defaultdict(_new_agg_bucket)
    language_buckets: dict[str, dict[str, Any]] = defaultdict(_new_agg_bucket)
    doc_type_buckets: dict[str, dict[str, Any]] = defaultdict(_new_agg_bucket)
    intent_buckets: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "evaluable": 0})

    full_case_abstention = {"opportunities": 0, "true_abstention": 0, "false_proposal": 0}
    selective_abstention = {"opportunities": 0, "true_abstention": 0, "false_proposal": 0}
    selective_abstention_by_binding: dict[str, dict[str, int]] = defaultdict(
        lambda: {"opportunities": 0, "true_abstention": 0, "false_proposal": 0}
    )

    by_binding_opportunities: dict[str, int] = defaultdict(int)
    stratum_a_opportunities = 0

    for case in cases:
        case_id = case["case_id"]
        expected_doc = case["expected"]
        proposed_doc = case["proposed"]
        manifest = case.get("manifest", {})

        result = score_case(expected_doc, proposed_doc)
        scored.append({"case_id": case_id, **result})

        recall_applicable = bool(expected_doc.get("recall_applicable", True))
        opportunity_count = int(manifest.get("opportunity_count", 0))

        _accumulate(overall_bucket, result, recall_applicable, opportunity_count)

        stratum = manifest.get("risk_stratum")
        if stratum:
            _accumulate(stratum_buckets[stratum], result, recall_applicable, opportunity_count)

        for binding in manifest.get("bindings_under_test", []):
            _accumulate(binding_buckets[binding], result, recall_applicable, opportunity_count)
            if stratum == "A" and binding in CRITICAL_BINDINGS:
                by_binding_opportunities[binding] += opportunity_count

        for language in manifest.get("languages", []) or []:
            _accumulate(language_buckets[language], result, recall_applicable, opportunity_count)

        doc_type = manifest.get("document_type") or "UNSPECIFIED"
        _accumulate(doc_type_buckets[doc_type], result, recall_applicable, opportunity_count)

        for intent_class, counts in result["intent_by_class"].items():
            intent_buckets[intent_class]["correct"] += counts["correct"]
            intent_buckets[intent_class]["evaluable"] += counts["evaluable"]

        if stratum == "A":
            stratum_a_opportunities += opportunity_count

        abstention = result["abstention"]
        if abstention["full_case_expected"]:
            full_case_abstention["opportunities"] += 1
            if abstention["full_case_true"]:
                full_case_abstention["true_abstention"] += 1
            else:
                full_case_abstention["false_proposal"] += 1
        for entry in abstention["selective_opportunities"]:
            selective_abstention["opportunities"] += 1
            binding_bucket = selective_abstention_by_binding[entry["binding_id"]]
            binding_bucket["opportunities"] += 1
            if entry["true_abstention"]:
                selective_abstention["true_abstention"] += 1
                binding_bucket["true_abstention"] += 1
            else:
                selective_abstention["false_proposal"] += 1
                binding_bucket["false_proposal"] += 1

    # A critical binding with zero opportunities must remain visibly
    # non-evaluable rather than silently absent from the report.
    for binding in CRITICAL_BINDINGS:
        binding_buckets[binding]  # noqa: B018 - defaultdict touch to force presence
    for stratum in RISK_STRATA:
        stratum_buckets[stratum]  # noqa: B018

    by_risk_stratum_out = {
        stratum: _finalize_agg_bucket(bucket)
        for stratum, bucket in sorted(stratum_buckets.items())
    }
    by_binding_out = {
        binding: _finalize_agg_bucket(bucket)
        for binding, bucket in sorted(binding_buckets.items())
    }
    by_language_out = {
        language: _finalize_agg_bucket(bucket)
        for language, bucket in sorted(language_buckets.items())
    }
    by_document_type_out = {
        doc_type: _finalize_agg_bucket(bucket)
        for doc_type, bucket in sorted(doc_type_buckets.items())
    }
    by_intent_out = {
        intent_class: {
            "evaluable": counts["evaluable"],
            "correct": counts["correct"],
            "intent_accuracy": _ratio(counts["correct"], counts["evaluable"]),
        }
        for intent_class, counts in sorted(intent_buckets.items())
    }

    overall = _finalize_agg_bucket(overall_bucket)
    overall["micro_precision"] = overall["precision"]
    overall["micro_recall"] = overall["recall"]
    overall["macro_precision_by_binding"] = _macro_average(
        bucket["precision"] for bucket in by_binding_out.values()
    )
    overall["macro_recall_by_binding"] = _macro_average(
        bucket["recall"] for bucket in by_binding_out.values()
    )
    overall["macro_precision_by_stratum"] = _macro_average(
        bucket["precision"] for bucket in by_risk_stratum_out.values()
    )
    overall["macro_recall_by_stratum"] = _macro_average(
        bucket["recall"] for bucket in by_risk_stratum_out.values()
    )
    overall["macro_precision_by_case"] = _macro_average(case["precision"] for case in scored)
    overall["macro_recall_by_case"] = _macro_average(case["recall"] for case in scored)

    combined_abstention_counts = {
        "opportunities": (
            full_case_abstention["opportunities"] + selective_abstention["opportunities"]
        ),
        "true_abstention": (
            full_case_abstention["true_abstention"] + selective_abstention["true_abstention"]
        ),
        "false_proposal": (
            full_case_abstention["false_proposal"] + selective_abstention["false_proposal"]
        ),
    }
    overall["abstention"] = {
        "full_case": _abstention_rates(full_case_abstention),
        "selective": _abstention_rates(selective_abstention),
        "combined": _abstention_rates(combined_abstention_counts),
        "selective_by_binding": {
            binding: _abstention_rates(counts)
            for binding, counts in sorted(selective_abstention_by_binding.items())
        },
    }

    missing_critical = {
        binding: count
        for binding, count in {
            binding: by_binding_opportunities.get(binding, 0) for binding in CRITICAL_BINDINGS
        }.items()
        if count < 3
    }
    sample_sufficient = stratum_a_opportunities >= 20 and not missing_critical

    # Human review burden — from versioned, pre-adjudicated annotations only.
    overall_hr = _new_human_review_bucket()
    stratum_hr: dict[str, dict[str, int]] = defaultdict(_new_human_review_bucket)
    binding_hr: dict[str, dict[str, int]] = defaultdict(_new_human_review_bucket)
    for annotation in human_review_annotations or []:
        decision = annotation.get("decision")
        if decision not in HUMAN_REVIEW_DECISIONS:
            raise ValueError(f"unknown human review decision: {decision!r}")
        overall_hr[decision] += 1
        binding_id = annotation.get("binding_id")
        if binding_id is not None:
            binding_hr[binding_id][decision] += 1
        risk_stratum = annotation.get("risk_stratum")
        if risk_stratum is not None:
            stratum_hr[risk_stratum][decision] += 1

    human_review_burden = {
        "overall": _finalize_human_review_bucket(overall_hr),
        "by_risk_stratum": {
            stratum: _finalize_human_review_bucket(counts)
            for stratum, counts in sorted(stratum_hr.items())
        },
        "by_binding": {
            binding: _finalize_human_review_bucket(counts)
            for binding, counts in sorted(binding_hr.items())
        },
    }

    threshold_comparison: dict[str, Any] = {}
    metric_observations = {
        "candidate_precision_micro": overall["micro_precision"],
        "binding_accuracy": overall["binding_accuracy"],
        "grounding_accuracy": overall["grounding_accuracy"],
        "hallucination_rate": overall["hallucination_rate"],
        "false_proposal_rate_on_abstention": (
            overall["abstention"]["combined"]["false_proposal_rate"]
        ),
        "controlled_vocab_exact_match": overall["controlled_vocab_exact_match"],
        "intent_accuracy": overall["intent_accuracy"],
    }
    for name, (target, comparator) in PROVISIONAL_TARGETS.items():
        observed = metric_observations[name]
        threshold_comparison[name] = {
            "observed": observed,
            "target": target,
            "comparator": ">=" if comparator == "gte" else "<=",
            "meets_provisional_target": _compare_to_target(observed, target, comparator),
            "evaluable": observed is not None,
        }
    threshold_comparison["note"] = THRESHOLD_COMPARISON_NOTE

    return {
        "evaluation_run_id": evaluation_run_id,
        "golden_set_version": golden_set_version,
        "catalog_contract_version": catalog_contract_version,
        "scorer_version": SCORER_VERSION,
        "overall": overall,
        "by_risk_stratum": by_risk_stratum_out,
        "by_binding": by_binding_out,
        "by_intent": by_intent_out,
        "by_language": by_language_out,
        "by_document_type": by_document_type_out,
        "cases": scored,
        "sample_sufficiency": {
            "stratum_a_opportunities": stratum_a_opportunities,
            "critical_binding_opportunities": dict(sorted(by_binding_opportunities.items())),
            "missing_minimums": missing_critical,
            "status": "SUFFICIENT" if sample_sufficient else "INSUFFICIENT_SAMPLE",
        },
        "human_review_burden": human_review_burden,
        "threshold_profile": "PROVISIONAL_TARGETS",
        "threshold_comparison": threshold_comparison,
        "gate_assessment": "ASSESSMENT_ONLY",
    }
