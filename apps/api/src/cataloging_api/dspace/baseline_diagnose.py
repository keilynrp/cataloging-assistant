from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from typing import Any

from cataloging_api.cataloging_contract import (
    FIELDS,
    live_dspace_label,
    live_dspace_selector_label,
)
from cataloging_api.db.session import SessionFactory
from cataloging_api.dspace.baseline_payload import _resolved_bindings, _resolved_sections
from cataloging_api.dspace.contract_materialize import _load_pages_by_surface
from cataloging_api.dspace.contract_resolution import EXPECTED_FORMS
from cataloging_api.dspace.contract_snapshot_store import DSpaceContractSnapshot


def _mismatch(
    *,
    index: int,
    dimension: str,
    live: Any,
    expected: Any,
    binding: dict[str, Any],
    expected_binding_id: str,
) -> dict[str, Any]:
    return {
        "index": index,
        "dimension": dimension,
        "form": binding.get("form"),
        "metadata": binding.get("metadata"),
        "label": binding.get("label"),
        "selectorLabel": binding.get("selectorLabel"),
        "position": binding.get("position"),
        "live": live,
        "expected": expected,
        "binding_id": expected_binding_id,
    }


def diagnose_bindings(bindings: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(bindings, key=lambda item: tuple(item.get("position") or []))
    mismatches: list[dict[str, Any]] = []

    if len(ordered) != len(FIELDS):
        return {
            "binding_count": len(ordered),
            "expected_binding_count": len(FIELDS),
            "mismatch_count": 1,
            "mismatches": [
                {
                    "dimension": "binding_count",
                    "live": len(ordered),
                    "expected": len(FIELDS),
                }
            ],
        }

    for index, (binding, expected) in enumerate(zip(ordered, FIELDS, strict=True)):
        expected_form = EXPECTED_FORMS[0] if index < 44 else EXPECTED_FORMS[1]
        checks = (
            ("form", binding.get("form"), expected_form),
            ("metadata", binding.get("metadata"), expected.metadata_field),
            ("label", binding.get("label"), live_dspace_label(expected)),
            (
                "selectorLabel",
                binding.get("selectorLabel"),
                live_dspace_selector_label(expected),
            ),
            ("required", bool(binding.get("required", False)), expected.required),
            ("repeatable", bool(binding.get("repeatable", False)), expected.repeatable),
            (
                "controlledVocabulary",
                binding.get("controlledVocabulary"),
                expected.vocabulary_id,
            ),
        )
        for dimension, live_value, expected_value in checks:
            if live_value != expected_value:
                mismatches.append(
                    _mismatch(
                        index=index,
                        dimension=dimension,
                        live=live_value,
                        expected=expected_value,
                        binding=binding,
                        expected_binding_id=expected.binding_id,
                    )
                )

    dimensions: dict[str, int] = {}
    for mismatch in mismatches:
        dimension = str(mismatch["dimension"])
        dimensions[dimension] = dimensions.get(dimension, 0) + 1

    return {
        "binding_count": len(ordered),
        "expected_binding_count": len(FIELDS),
        "mismatch_count": len(mismatches),
        "mismatch_dimensions": dict(sorted(dimensions.items())),
        "mismatches": mismatches,
    }


async def diagnose_snapshot(snapshot_id: uuid.UUID) -> dict[str, Any]:
    async with SessionFactory() as session:
        snapshot = await session.get(DSpaceContractSnapshot, snapshot_id)
        if snapshot is None:
            raise ValueError("snapshot_not_found")

        pages_by_surface = await _load_pages_by_surface(session, run_id=snapshot.run_id)
        sections = _resolved_sections(pages_by_surface)
        bindings = _resolved_bindings(snapshot=snapshot, pages_by_surface=pages_by_surface)
        report = diagnose_bindings(bindings)
        report.update(
            {
                "snapshot_id": str(snapshot.snapshot_id),
                "run_id": str(snapshot.run_id),
                "semantic_hash": snapshot.semantic_hash,
                "section_forms": [section.get("configForm") for section in sections],
            }
        )
        return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report all live-vs-runtime binding mismatches for a VERTICAL-022 snapshot."
    )
    parser.add_argument("--snapshot-id", type=uuid.UUID, required=True)
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    report = await diagnose_snapshot(args.snapshot_id)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())
