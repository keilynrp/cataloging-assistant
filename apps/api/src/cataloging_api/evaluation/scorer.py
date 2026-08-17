from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable
import unicodedata


CRITICAL_BINDINGS = {
    "linguistic-family",
    "linguistic-branch",
    "linguistic-group",
    "linguistic-variant",
    "registered-language",
}


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


def score_case(expected_doc: dict[str, Any], proposed_doc: dict[str, Any]) -> dict[str, Any]:
    expected = list(expected_doc.get("expected_candidates", []))
    proposed = list(proposed_doc.get("candidates", []))
    used_expected: set[int] = set()
    used_proposed: set[int] = set()
    diagnostic_used_expected: set[int] = set()
    matches: list[Match] = []

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
                matches.append(
                    Match(e_idx, p_idx, True, True, True, True, True, ())
                )
                break

    # Diagnostic matching is intentionally one-to-one and independent of authoritative use.
    # It can explain wrong binding / bad grounding but can never create a TP.
    for p_idx, candidate in enumerate(proposed):
        if p_idx in used_proposed:
            continue
        for e_idx, gold in enumerate(expected):
            if e_idx in diagnostic_used_expected:
                continue
            value_ok = _value_matches(gold, candidate)
            intent_ok = candidate.get("candidate_intent") == gold.get("candidate_intent")
            if not (value_ok and intent_ok):
                continue
            binding_ok = candidate.get("binding_id") == gold.get("binding_id")
            grounding_ok = _grounding_matches(gold, candidate)
            errors = []
            if not binding_ok:
                errors.append("WRONG_BINDING")
            if not grounding_ok:
                errors.append("BAD_GROUNDING")
            if errors:
                diagnostic_used_expected.add(e_idx)
                matches.append(
                    Match(
                        e_idx,
                        p_idx,
                        False,
                        True,
                        binding_ok,
                        True,
                        grounding_ok,
                        tuple(errors),
                    )
                )
                break

    tp = sum(1 for match in matches if match.authoritative)
    fp = len(proposed) - tp
    fn = len(expected) - tp if expected_doc.get("recall_applicable", True) else 0

    binding_diagnostics = [
        match for match in matches if match.authoritative or "WRONG_BINDING" in match.errors
    ]
    binding_evaluable = len(binding_diagnostics)
    binding_correct = sum(match.binding_ok for match in binding_diagnostics)
    binding_accuracy = binding_correct / binding_evaluable if binding_evaluable else None

    grounding_diagnostics = []
    for match in matches:
        gold = expected[match.expected_index]
        if gold.get("grounding_required", False) and match.diagnostic_value_match:
            grounding_diagnostics.append(match)
    grounding_evaluable = len(grounding_diagnostics)
    grounding_correct = sum(match.grounding_ok for match in grounding_diagnostics)
    grounding_accuracy = (
        grounding_correct / grounding_evaluable if grounding_evaluable else None
    )

    abstention_bindings = {
        item.get("binding_id")
        for item in expected_doc.get("expected_abstentions", [])
        if item.get("binding_id")
    }
    false_on_abstention = sum(
        1 for candidate in proposed if candidate.get("binding_id") in abstention_bindings
    )

    hallucination_annotations = expected_doc.get("hallucination_annotations", {})
    prohibited = set(hallucination_annotations.get("prohibited_values", []))
    unsupported = sum(1 for candidate in proposed if candidate.get("value") in prohibited)
    unsupported += false_on_abstention
    hallucination_rate = unsupported / len(proposed) if proposed else 0.0

    errors: list[dict[str, Any]] = []
    for match in matches:
        for code in match.errors:
            errors.append(
                {
                    "code": code,
                    "proposed_index": match.proposed_index,
                    "expected_index": match.expected_index,
                }
            )

    explained_proposed = {match.proposed_index for match in matches}
    for p_idx in range(len(proposed)):
        if p_idx not in used_proposed and p_idx not in explained_proposed:
            errors.append({"code": "UNSUPPORTED_VALUE", "proposed_index": p_idx})
    if expected_doc.get("recall_applicable", True):
        authoritative_expected = {m.expected_index for m in matches if m.authoritative}
        for e_idx in range(len(expected)):
            if e_idx not in authoritative_expected:
                errors.append({"code": "MISSING_EXPECTED_CANDIDATE", "expected_index": e_idx})

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": tp / (tp + fp) if tp + fp else 1.0,
        "recall": tp / (tp + fn) if tp + fn else None,
        "binding_accuracy": binding_accuracy,
        "grounding_accuracy": grounding_accuracy,
        "hallucination_rate": hallucination_rate,
        "errors": errors,
    }


def score_run(cases: list[dict[str, Any]]) -> dict[str, Any]:
    scored = []
    totals = defaultdict(int)
    by_binding_opportunities = defaultdict(int)
    stratum_a_opportunities = 0

    for case in cases:
        result = score_case(case["expected"], case["proposed"])
        scored.append({"case_id": case["case_id"], **result})
        totals["tp"] += result["tp"]
        totals["fp"] += result["fp"]
        totals["fn"] += result["fn"]

        manifest = case.get("manifest", {})
        opportunities = int(manifest.get("opportunity_count", 0))
        if manifest.get("risk_stratum") == "A":
            stratum_a_opportunities += opportunities
            for binding in manifest.get("bindings_under_test", []):
                if binding in CRITICAL_BINDINGS:
                    by_binding_opportunities[binding] += opportunities

    micro_precision = (
        totals["tp"] / (totals["tp"] + totals["fp"])
        if totals["tp"] + totals["fp"]
        else 1.0
    )
    micro_recall = (
        totals["tp"] / (totals["tp"] + totals["fn"])
        if totals["tp"] + totals["fn"]
        else None
    )

    missing_critical = {
        binding: count
        for binding, count in {
            binding: by_binding_opportunities.get(binding, 0) for binding in CRITICAL_BINDINGS
        }.items()
        if count < 3
    }
    sample_sufficient = stratum_a_opportunities >= 20 and not missing_critical

    return {
        "overall": {
            "tp": totals["tp"],
            "fp": totals["fp"],
            "fn": totals["fn"],
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
        },
        "cases": scored,
        "sample_sufficiency": {
            "stratum_a_opportunities": stratum_a_opportunities,
            "critical_binding_opportunities": dict(sorted(by_binding_opportunities.items())),
            "missing_minimums": missing_critical,
            "status": "SUFFICIENT" if sample_sufficient else "INSUFFICIENT_SAMPLE",
        },
        "gate_assessment": "ASSESSMENT_ONLY",
    }
