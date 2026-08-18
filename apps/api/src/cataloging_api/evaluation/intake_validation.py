from __future__ import annotations

from collections.abc import Mapping
from typing import Any


REVIEW_LINK_STATES = {"AWAITING_ADJUDICATION", "ADJUDICATED_GOLD"}


def validate_intake_manifest_semantics(manifest: Mapping[str, Any]) -> list[str]:
    """Return cross-record provenance errors not expressible in JSON Schema.

    JSON Schema validates the shape of completed-review links. This second-stage
    validator enforces their relational integrity against the parent intake case.
    It is evaluation-only and performs no runtime mutation or provider action.
    """

    errors: list[str] = []

    for case_index, case in enumerate(manifest.get("cases", [])):
        if not isinstance(case, Mapping):
            continue

        prefix = f"cases[{case_index}]"
        case_id = case.get("case_id")
        bindings = set(case.get("bindings_under_review", []))
        parent_reviewers = set(case.get("reviewer_ids", []))
        parent_snapshot = case.get("evidence_snapshot_sha256")
        completed_reviews = case.get("completed_reviews", [])

        if not isinstance(completed_reviews, list):
            continue

        linked_reviewers: list[str] = []
        linked_review_ids: list[str] = []

        for review_index, review in enumerate(completed_reviews):
            if not isinstance(review, Mapping):
                continue

            review_prefix = f"{prefix}.completed_reviews[{review_index}]"
            review_id = review.get("review_id")
            reviewer_id = review.get("reviewer_id")
            linked_review_ids.append(str(review_id))
            linked_reviewers.append(str(reviewer_id))

            if review.get("case_id") != case_id:
                errors.append(f"{review_prefix}.case_id must match parent case_id")
            if reviewer_id not in parent_reviewers:
                errors.append(f"{review_prefix}.reviewer_id must belong to parent reviewer_ids")
            if review.get("binding_id") not in bindings:
                errors.append(f"{review_prefix}.binding_id must belong to parent bindings_under_review")
            if review.get("evidence_snapshot_sha256") != parent_snapshot:
                errors.append(
                    f"{review_prefix}.evidence_snapshot_sha256 must match parent evidence snapshot"
                )

        if len(linked_review_ids) != len(set(linked_review_ids)):
            errors.append(f"{prefix}.completed_reviews must use distinct review_id values")
        if len(linked_reviewers) != len(set(linked_reviewers)):
            errors.append(f"{prefix}.completed_reviews must use distinct reviewer_id values")

        if case.get("review_status") in REVIEW_LINK_STATES:
            if len(parent_reviewers) != 2:
                errors.append(f"{prefix}.reviewer_ids must contain exactly two distinct reviewers")
            if len(completed_reviews) != 2:
                errors.append(f"{prefix}.completed_reviews must contain exactly two reviews")
            if len(set(linked_review_ids)) != 2:
                errors.append(f"{prefix}.completed_reviews must contain two distinct review_id values")
            if len(set(linked_reviewers)) != 2:
                errors.append(f"{prefix}.completed_reviews must contain two distinct reviewer_id values")
            if set(linked_reviewers) != parent_reviewers:
                errors.append(
                    f"{prefix}.completed_reviews reviewer_ids must exactly match parent reviewer_ids"
                )
            if len(completed_reviews) != len(parent_reviewers):
                errors.append(
                    f"{prefix}.completed_reviews count must match parent reviewer_ids count"
                )

    return errors
