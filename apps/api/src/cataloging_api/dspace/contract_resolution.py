from __future__ import annotations

import hashlib
import json
import string
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.cataloging_contract import FIELDS
from cataloging_api.dspace.contract_snapshot_store import DSpaceContractSnapshot
from cataloging_api.dspace.contract_store import DSpaceContractRawPage


RESOLVABLE_SURFACE = "active_submission_sections"
EXPECTED_FORMS = ("traditionalpageone", "traditionalpagetwo")
EXPECTED_FORM_BINDING_COUNTS = {"traditionalpageone": 44, "traditionalpagetwo": 12}
EXPECTED_BINDING_COUNT = len(FIELDS)
EXPECTED_UNIQUE_METADATA_COUNT = len({field.metadata_field for field in FIELDS})
ALLOWED_RESOLUTION_WARNINGS = {
    "NO_ACTIVE_SUBMISSION_FORMS",
    "UNOBSERVABLE_SURFACE:active_submission_sections",
    "UNOBSERVABLE_SURFACE:active_submission_sections:HTTP_204",
}


class ContractResolutionError(ValueError):
    pass


def _json_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in string.hexdigits for character in value)


def build_effective_canonical(
    *,
    observed_canonical: dict[str, Any],
    sections: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical = dict(observed_canonical)
    canonical["sections"] = sections
    canonical["bindings"] = sorted(bindings, key=lambda item: item["bindingKey"])
    return canonical


def validate_reconciled_overlay(
    *,
    snapshot: DSpaceContractSnapshot,
    sections: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
) -> None:
    if snapshot.complete:
        raise ContractResolutionError("complete_snapshot_does_not_require_resolution")
    if snapshot.status == "ACTIVE":
        raise ContractResolutionError("active_snapshot_resolution_is_immutable")

    unexpected = set(snapshot.warnings or []) - ALLOWED_RESOLUTION_WARNINGS
    if unexpected:
        raise ContractResolutionError("snapshot_has_unresolved_non_204_warnings")

    active_definition = snapshot.canonical_json.get("activeDefinition")
    if active_definition != "traditional":
        raise ContractResolutionError("unsupported_active_definition")

    if len(sections) != 2:
        raise ContractResolutionError("resolved_sections_must_contain_two_forms")
    section_forms = tuple(section.get("configForm") for section in sections)
    if section_forms != EXPECTED_FORMS:
        raise ContractResolutionError("resolved_section_form_order_mismatch")

    if len(bindings) != EXPECTED_BINDING_COUNT:
        raise ContractResolutionError("resolved_binding_count_mismatch")
    binding_keys = [binding.get("bindingKey") for binding in bindings]
    if any(not isinstance(key, str) or not key for key in binding_keys):
        raise ContractResolutionError("resolved_binding_key_missing")
    if len(binding_keys) != len(set(binding_keys)):
        raise ContractResolutionError("resolved_binding_key_duplicate")

    form_counts = Counter(binding.get("form") for binding in bindings)
    if dict(form_counts) != EXPECTED_FORM_BINDING_COUNTS:
        raise ContractResolutionError("resolved_form_binding_counts_mismatch")

    metadata = {binding.get("metadata") for binding in bindings}
    if None in metadata or len(metadata) != EXPECTED_UNIQUE_METADATA_COUNT:
        raise ContractResolutionError("resolved_unique_metadata_count_mismatch")

    registry = {
        field.get("metadata")
        for field in snapshot.canonical_json.get("fields", [])
        if isinstance(field, dict)
    }
    if not metadata.issubset(registry):
        raise ContractResolutionError("resolved_binding_metadata_not_in_registry")

    # The authenticated reconciliation established render-order identity 56/56.
    # Enforce the dimensions represented in the runtime master contract so a
    # payload cannot pass merely by having the right counts.
    ordered = sorted(bindings, key=lambda item: tuple(item.get("position") or []))
    if len(ordered) != len(FIELDS):
        raise ContractResolutionError("resolved_binding_order_mismatch")
    for index, (binding, expected) in enumerate(zip(ordered, FIELDS, strict=True)):
        expected_form = "traditionalpageone" if index < 44 else "traditionalpagetwo"
        if binding.get("form") != expected_form:
            raise ContractResolutionError("resolved_binding_form_order_mismatch")
        if binding.get("metadata") != expected.metadata_field:
            raise ContractResolutionError("resolved_binding_metadata_mismatch")
        if binding.get("label") != expected.ui_label:
            raise ContractResolutionError("resolved_binding_label_mismatch")
        if bool(binding.get("required", False)) != expected.required:
            raise ContractResolutionError("resolved_binding_required_mismatch")
        if bool(binding.get("repeatable", False)) != expected.repeatable:
            raise ContractResolutionError("resolved_binding_repeatable_mismatch")
        if binding.get("controlledVocabulary") != expected.vocabulary_id:
            raise ContractResolutionError("resolved_binding_vocabulary_mismatch")


def _raw_page_is_204_observation(page: DSpaceContractRawPage) -> bool:
    observation = page.raw_payload.get("_observation")
    return bool(
        isinstance(observation, dict)
        and observation.get("observable") is False
        and observation.get("statusCode") == 204
    )


async def resolve_authoritative_evidence(
    session: AsyncSession,
    *,
    snapshot_id: uuid.UUID,
    expected_snapshot_hash: str,
    expected_effective_hash: str,
    source_export_hash: str,
    reconciliation_hash: str,
    sections: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
    resolved_by: str,
    resolution_note: str,
) -> DSpaceContractSnapshot:
    for value in (
        expected_snapshot_hash,
        expected_effective_hash,
        source_export_hash,
        reconciliation_hash,
    ):
        if not _is_sha256(value):
            raise ContractResolutionError("invalid_sha256")

    result = await session.execute(
        select(DSpaceContractSnapshot)
        .where(DSpaceContractSnapshot.snapshot_id == snapshot_id)
        .with_for_update()
    )
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        raise ContractResolutionError("snapshot_not_found")
    if snapshot.semantic_hash != expected_snapshot_hash:
        raise ContractResolutionError("snapshot_hash_mismatch")

    if snapshot.effective_hash is not None:
        if (
            snapshot.effective_hash == expected_effective_hash
            and snapshot.resolution_source_hash == source_export_hash
            and snapshot.resolution_reconciliation_hash == reconciliation_hash
        ):
            return snapshot
        raise ContractResolutionError("authoritative_resolution_conflict")

    raw_result = await session.execute(
        select(DSpaceContractRawPage).where(
            DSpaceContractRawPage.run_id == snapshot.run_id,
            DSpaceContractRawPage.surface == RESOLVABLE_SURFACE,
        )
    )
    raw_pages = list(raw_result.scalars().all())
    if len(raw_pages) != 1 or not _raw_page_is_204_observation(raw_pages[0]):
        raise ContractResolutionError("missing_authoritative_http_204_observation")

    validate_reconciled_overlay(
        snapshot=snapshot,
        sections=sections,
        bindings=bindings,
    )
    effective = build_effective_canonical(
        observed_canonical=snapshot.canonical_json,
        sections=sections,
        bindings=bindings,
    )
    effective_hash = _json_hash(effective)
    if effective_hash != expected_effective_hash:
        raise ContractResolutionError("effective_contract_hash_mismatch")

    snapshot.effective_hash = effective_hash
    snapshot.effective_canonical_json = effective
    snapshot.resolution_surface = RESOLVABLE_SURFACE
    snapshot.resolution_source_hash = source_export_hash
    snapshot.resolution_reconciliation_hash = reconciliation_hash
    snapshot.resolved_by = resolved_by
    snapshot.resolved_at = datetime.now(timezone.utc)
    snapshot.resolution_note = resolution_note

    active_result = await session.execute(
        select(DSpaceContractSnapshot)
        .where(DSpaceContractSnapshot.status == "ACTIVE")
        .limit(1)
    )
    active = active_result.scalar_one_or_none()
    if active is None:
        snapshot.status = "BASELINE_REVIEW_REQUIRED"
    elif snapshot.status not in {"REVIEW_REQUIRED", "DIFF_DETECTED"}:
        snapshot.status = "REVIEW_REQUIRED"

    await session.flush()
    return snapshot
