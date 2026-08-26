from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from typing import Any

from cataloging_api.db.session import SessionFactory
from cataloging_api.dspace.contract_materialize import _load_pages_by_surface
from cataloging_api.dspace.contract_resolution import (
    EXPECTED_FORMS,
    _json_hash,
    build_effective_canonical,
    validate_reconciled_overlay,
)
from cataloging_api.dspace.contract_snapshot import (
    _canonical_bindings,
    _canonical_sections,
    _config_form_id,
    _surface_items,
)
from cataloging_api.dspace.contract_snapshot_store import DSpaceContractSnapshot

SOURCE_EXPORT_HASH = "8260b2023b7b417f3056d3724664869f96cb613371c673517d6b7400af2a0b1c"
RECONCILIATION_HASH = "5b549a16307354b84b9327325532755877a622e323573616e92c8a0dee93ea92"
DEFAULT_RESOLUTION_NOTE = (
    "Initial production baseline: authoritative 56/56 reconciliation resolves the "
    "DSpace 7.6.6 active_submission_sections HTTP 204 observation."
)


def _embedded_items(payloads: list[dict[str, Any]], relation: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for payload in payloads:
        embedded = payload.get("_embedded")
        values = embedded.get(relation) if isinstance(embedded, dict) else None
        if isinstance(values, list):
            items.extend(value for value in values if isinstance(value, dict))
    return items


def _resolved_sections(pages_by_surface: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    global_sections = _embedded_items(
        pages_by_surface.get("submission_sections", []),
        "submissionsections",
    )
    sections_by_form: dict[str, dict[str, Any]] = {}
    for section in global_sections:
        form_id = _config_form_id(section)
        if form_id is None:
            section_id = section.get("id")
            form_id = section_id if isinstance(section_id, str) else None
        if form_id in EXPECTED_FORMS:
            if form_id in sections_by_form:
                raise ValueError(f"duplicate_authoritative_section:{form_id}")
            sections_by_form[form_id] = section

    missing = [form_id for form_id in EXPECTED_FORMS if form_id not in sections_by_form]
    if missing:
        raise ValueError(f"missing_authoritative_sections:{','.join(missing)}")

    ordered = [sections_by_form[form_id] for form_id in EXPECTED_FORMS]
    canonical = _canonical_sections(ordered)
    if tuple(section.get("configForm") for section in canonical) != EXPECTED_FORMS:
        raise ValueError("authoritative_section_form_order_mismatch")
    return canonical


def _resolved_bindings(
    *,
    snapshot: DSpaceContractSnapshot,
    pages_by_surface: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    forms = _surface_items(
        "submission_forms",
        pages_by_surface.get("submission_forms", []),
    )
    registry_fields = {
        field.get("metadata")
        for field in snapshot.canonical_json.get("fields", [])
        if isinstance(field, dict) and isinstance(field.get("metadata"), str)
    }
    warnings: list[str] = []
    bindings = _canonical_bindings(
        forms,
        list(EXPECTED_FORMS),
        registry_fields,
        warnings,
    )
    if warnings:
        raise ValueError("binding_reconstruction_warnings:" + ";".join(sorted(set(warnings))))
    return bindings


async def build_resolution_payload(
    *,
    snapshot_id: uuid.UUID,
    resolved_by: str,
    resolution_note: str = DEFAULT_RESOLUTION_NOTE,
    source_export_hash: str = SOURCE_EXPORT_HASH,
    reconciliation_hash: str = RECONCILIATION_HASH,
) -> dict[str, Any]:
    async with SessionFactory() as session:
        snapshot = await session.get(DSpaceContractSnapshot, snapshot_id)
        if snapshot is None:
            raise ValueError("snapshot_not_found")
        if snapshot.effective_hash is not None:
            raise ValueError("snapshot_already_resolved")

        pages_by_surface = await _load_pages_by_surface(session, run_id=snapshot.run_id)
        sections = _resolved_sections(pages_by_surface)
        bindings = _resolved_bindings(snapshot=snapshot, pages_by_surface=pages_by_surface)

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

        return {
            "expected_snapshot_hash": snapshot.semantic_hash,
            "expected_effective_hash": effective_hash,
            "source_export_hash": source_export_hash,
            "reconciliation_hash": reconciliation_hash,
            "sections": sections,
            "bindings": bindings,
            "resolved_by": resolved_by,
            "resolution_note": resolution_note,
        }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the reviewed resolve-evidence payload for a VERTICAL-022 baseline snapshot."
    )
    parser.add_argument("--snapshot-id", type=uuid.UUID, required=True)
    parser.add_argument(
        "--resolved-by",
        required=True,
        help="Human reviewer identifier recorded in resolution provenance.",
    )
    parser.add_argument("--resolution-note", default=DEFAULT_RESOLUTION_NOTE)
    parser.add_argument("--source-export-hash", default=SOURCE_EXPORT_HASH)
    parser.add_argument("--reconciliation-hash", default=RECONCILIATION_HASH)
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    payload = await build_resolution_payload(
        snapshot_id=args.snapshot_id,
        resolved_by=args.resolved_by,
        resolution_note=args.resolution_note,
        source_export_hash=args.source_export_hash,
        reconciliation_hash=args.reconciliation_hash,
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
