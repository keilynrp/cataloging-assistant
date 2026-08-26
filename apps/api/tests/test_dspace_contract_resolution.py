from types import SimpleNamespace

import pytest

from cataloging_api.cataloging_contract import FIELDS
from cataloging_api.dspace.contract_resolution import (
    ContractResolutionError,
    EXPECTED_BINDING_COUNT,
    EXPECTED_UNIQUE_METADATA_COUNT,
    build_effective_canonical,
    validate_reconciled_overlay,
)


def _sections() -> list[dict]:
    return [
        {
            "id": "traditionalpageone",
            "order": 0,
            "sectionType": "submission-form",
            "header": "submit.progressbar.describe.stepone",
            "mandatory": True,
            "scope": None,
            "configForm": "traditionalpageone",
        },
        {
            "id": "traditionalpagetwo",
            "order": 1,
            "sectionType": "submission-form",
            "header": "submit.progressbar.describe.steptwo",
            "mandatory": True,
            "scope": None,
            "configForm": "traditionalpagetwo",
        },
    ]


def _bindings() -> list[dict]:
    result = []
    for index, field in enumerate(FIELDS):
        form = "traditionalpageone" if index < 44 else "traditionalpagetwo"
        result.append(
            {
                "bindingKey": f"{form}:{field.metadata_field}:{field.binding_id}",
                "form": form,
                "metadata": field.metadata_field,
                "occurrence": 0,
                "position": [0 if index < 44 else 1, index if index < 44 else index - 44, 0, 0],
                "label": field.ui_label,
                "selectorLabel": None,
                "required": field.required,
                "repeatable": field.repeatable,
                "inputType": "onebox",
                "controlledVocabulary": field.vocabulary_id,
                "closed": field.controlled,
                "typeBind": [],
            }
        )
    return result


def _snapshot(*, warnings: list[str] | None = None):
    metadata = sorted({field.metadata_field for field in FIELDS})
    return SimpleNamespace(
        complete=False,
        status="REVIEW_REQUIRED",
        warnings=warnings or ["NO_ACTIVE_SUBMISSION_FORMS"],
        canonical_json={
            "activeDefinition": "traditional",
            "schemas": [{"prefix": "dc", "id": 1, "namespace": "http://purl.org/dc/elements/1.1/"}],
            "fields": [
                {"metadata": value, "id": index + 1, "scopeNote": None}
                for index, value in enumerate(metadata)
            ],
            "sections": [],
            "bindings": [],
        },
    )


def test_resolution_contract_dimensions_match_master_contract() -> None:
    assert EXPECTED_BINDING_COUNT == 56
    assert EXPECTED_UNIQUE_METADATA_COUNT == 54
    assert len(_bindings()) == 56
    assert len({item["metadata"] for item in _bindings()}) == 54


def test_valid_204_reconciliation_overlay_is_accepted() -> None:
    snapshot = _snapshot()
    validate_reconciled_overlay(
        snapshot=snapshot,
        sections=_sections(),
        bindings=_bindings(),
    )
    effective = build_effective_canonical(
        observed_canonical=snapshot.canonical_json,
        sections=_sections(),
        bindings=_bindings(),
    )
    assert len(effective["bindings"]) == 56
    assert [section["configForm"] for section in effective["sections"]] == [
        "traditionalpageone",
        "traditionalpagetwo",
    ]
    assert snapshot.canonical_json["bindings"] == []
    assert snapshot.canonical_json["sections"] == []


def test_non_204_warning_cannot_be_resolved_by_overlay() -> None:
    snapshot = _snapshot(warnings=["METADATA_FIELD_COVERAGE_MISMATCH:global=292:qualified=291"])
    with pytest.raises(
        ContractResolutionError,
        match="snapshot_has_unresolved_non_204_warnings",
    ):
        validate_reconciled_overlay(
            snapshot=snapshot,
            sections=_sections(),
            bindings=_bindings(),
        )


def test_overlay_rejects_binding_metadata_outside_observed_registry() -> None:
    snapshot = _snapshot()
    bindings = _bindings()
    bindings[0] = {**bindings[0], "metadata": "dc.fake.notRegistered"}
    with pytest.raises(
        ContractResolutionError,
        match="resolved_binding_metadata_not_in_registry|resolved_unique_metadata_count_mismatch",
    ):
        validate_reconciled_overlay(
            snapshot=snapshot,
            sections=_sections(),
            bindings=bindings,
        )


def test_overlay_rejects_wrong_form_counts() -> None:
    snapshot = _snapshot()
    bindings = _bindings()
    bindings[-1] = {**bindings[-1], "form": "traditionalpageone"}
    with pytest.raises(
        ContractResolutionError,
        match="resolved_form_binding_counts_mismatch",
    ):
        validate_reconciled_overlay(
            snapshot=snapshot,
            sections=_sections(),
            bindings=bindings,
        )
