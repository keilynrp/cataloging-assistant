from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from cataloging_api.dspace.contract_governance import governed_canonical
from cataloging_api.dspace.contract_snapshot import (
    ContractSnapshotView,
    _canonical_bindings,
    _json_hash,
    _surface_items,
)
from cataloging_api.dspace.contract_snapshot_store import DSpaceContractSnapshot


INHERITABLE_WARNINGS = {
    "NO_ACTIVE_SUBMISSION_FORMS",
    "UNOBSERVABLE_SURFACE:active_submission_sections",
    "UNOBSERVABLE_SURFACE:active_submission_sections:HTTP_204",
}
EXPECTED_FORMS = ["traditionalpageone", "traditionalpagetwo"]


def _normalized_binding_for_compare(binding: dict[str, Any]) -> dict[str, Any] | None:
    form = binding.get("form")
    if form not in EXPECTED_FORMS:
        return None
    position = binding.get("position")
    if not isinstance(position, list) or len(position) != 4:
        return None
    normalized = deepcopy(binding)
    normalized["position"] = [EXPECTED_FORMS.index(form), *position[1:]]
    return normalized


def _normalized_bindings(bindings: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    normalized: list[dict[str, Any]] = []
    for binding in bindings:
        value = _normalized_binding_for_compare(binding)
        if value is None:
            return None
        normalized.append(value)
    return sorted(normalized, key=lambda item: item["bindingKey"])


def build_inherited_effective_snapshot(
    *,
    active: DSpaceContractSnapshot,
    observed: ContractSnapshotView,
    pages_by_surface: dict[str, list[dict[str, Any]]],
) -> ContractSnapshotView | None:
    """Rebuild the current effective contract under the approved 204 resolution.

    Inheritance is deliberately all-or-nothing. It is allowed only when the
    active baseline itself has a governed resolution and the new run proves
    the same schemas, registry fields and 56 bindings from its own
    submission_forms payloads. Any material difference returns None and the
    normal fail-closed REVIEW_REQUIRED path remains in force.
    """

    if not active.effective_hash or active.resolution_surface != "active_submission_sections":
        return None
    if set(observed.warnings) - INHERITABLE_WARNINGS:
        return None
    if observed.canonical.get("activeDefinition") != "traditional":
        return None

    active_canonical = governed_canonical(active)
    active_sections = active_canonical.get("sections")
    active_bindings = active_canonical.get("bindings")
    if not isinstance(active_sections, list) or not isinstance(active_bindings, list):
        return None

    form_ids = [
        section.get("configForm")
        for section in active_sections
        if isinstance(section, dict) and section.get("sectionType") == "submission-form"
    ]
    if form_ids != EXPECTED_FORMS:
        return None

    forms = _surface_items(
        "submission_forms",
        pages_by_surface.get("submission_forms", []),
    )
    registry_fields = {
        field.get("metadata")
        for field in observed.canonical.get("fields", [])
        if isinstance(field, dict) and isinstance(field.get("metadata"), str)
    }
    binding_warnings: list[str] = []
    current_bindings = _canonical_bindings(
        forms,
        form_ids,
        registry_fields,
        binding_warnings,
    )
    if binding_warnings:
        return None

    # Do not inherit across any material structural change. Registry/schema
    # drift and form-binding drift must require review instead of being hidden
    # behind the historical 204 resolution.
    if observed.canonical.get("schemas") != active_canonical.get("schemas"):
        return None
    if observed.canonical.get("fields") != active_canonical.get("fields"):
        return None

    # The first component of `position` in the approved 1E evidence came from
    # the global-section fallback and is not authoritative for the two active
    # forms. Normalize only that component; row/field/option order and every
    # semantic attribute still have to match exactly.
    normalized_current = _normalized_bindings(current_bindings)
    normalized_active = _normalized_bindings(active_bindings)
    if normalized_current is None or normalized_active is None:
        return None
    if normalized_current != normalized_active:
        return None

    # The new run proved the same contract independently. Preserve the exact
    # approved canonical representation so its governed hash remains stable.
    effective = dict(observed.canonical)
    effective["sections"] = deepcopy(active_sections)
    effective["bindings"] = deepcopy(active_bindings)
    return ContractSnapshotView(
        canonical=effective,
        semantic_hash=_json_hash(effective),
        complete=True,
        warnings=(),
    )


def apply_inherited_resolution(
    *,
    record: DSpaceContractSnapshot,
    active: DSpaceContractSnapshot,
    inherited: ContractSnapshotView,
) -> None:
    """Persist provenance for an automatically inherited, previously approved resolution."""

    record.effective_hash = inherited.semantic_hash
    record.effective_canonical_json = inherited.canonical
    record.resolution_surface = active.resolution_surface
    record.resolution_source_hash = active.resolution_source_hash
    record.resolution_reconciliation_hash = active.resolution_reconciliation_hash
    record.resolution_inherited_from_snapshot_id = active.snapshot_id
    record.resolved_by = "SYSTEM_INHERITED"
    record.resolved_at = datetime.now(timezone.utc)
    record.resolution_note = (
        "Inherited approved active_submission_sections HTTP 204 resolution after exact "
        "schema, registry and submission-form reconciliation against ACTIVE baseline."
    )
