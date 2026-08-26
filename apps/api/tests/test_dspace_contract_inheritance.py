from __future__ import annotations

from types import SimpleNamespace

from cataloging_api.cataloging_contract import FIELDS
from cataloging_api.dspace.contract_inheritance import build_inherited_effective_snapshot
from cataloging_api.dspace.contract_snapshot import (
    ContractSnapshotView,
    _canonical_bindings,
    _json_hash,
)


def _form_payload() -> dict:
    page_one_rows = []
    page_two_rows = []
    for index, field in enumerate(FIELDS):
        form_rows = page_one_rows if index < 44 else page_two_rows
        option = {"metadata": field.metadata_field}
        if field.vocabulary_id is not None:
            option["controlledVocabulary"] = field.vocabulary_id
        option["closed"] = field.controlled
        form_rows.append(
            {
                "fields": [
                    {
                        "label": field.ui_label,
                        "mandatory": field.required,
                        "repeatable": field.repeatable,
                        "input": {"type": "dropdown" if field.controlled else "onebox"},
                        "selectableMetadata": [option],
                        "typeBind": [],
                    }
                ]
            }
        )
    return {
        "_embedded": {
            "submissionforms": [
                {"id": "traditionalpageone", "rows": page_one_rows},
                {"id": "traditionalpagetwo", "rows": page_two_rows},
            ]
        },
        "page": {"number": 0, "totalPages": 1, "totalElements": 2},
    }


def _fixture():
    fields = [
        {"metadata": metadata, "id": f"id-{index}", "scopeNote": None}
        for index, metadata in enumerate(sorted({field.metadata_field for field in FIELDS}))
    ]
    schemas = [{"prefix": "dc", "id": "dc", "namespace": "http://purl.org/dc/elements/1.1/"}]
    observed_canonical = {
        "activeDefinition": "traditional",
        "schemas": schemas,
        "fields": fields,
        "sections": [],
        "bindings": [],
    }
    observed = ContractSnapshotView(
        canonical=observed_canonical,
        semantic_hash=_json_hash(observed_canonical),
        complete=False,
        warnings=(
            "NO_ACTIVE_SUBMISSION_FORMS",
            "UNOBSERVABLE_SURFACE:active_submission_sections:HTTP_204",
        ),
    )
    sections = [
        {
            "id": "traditionalpageone",
            "order": 0,
            "sectionType": "submission-form",
            "header": None,
            "mandatory": None,
            "scope": None,
            "configForm": "traditionalpageone",
        },
        {
            "id": "traditionalpagetwo",
            "order": 1,
            "sectionType": "submission-form",
            "header": None,
            "mandatory": None,
            "scope": None,
            "configForm": "traditionalpagetwo",
        },
    ]
    forms = _form_payload()["_embedded"]["submissionforms"]
    warnings: list[str] = []
    bindings = _canonical_bindings(
        forms,
        ["traditionalpageone", "traditionalpagetwo"],
        {field["metadata"] for field in fields},
        warnings,
    )
    assert not warnings
    effective = dict(observed_canonical)
    effective["sections"] = sections
    effective["bindings"] = bindings
    active = SimpleNamespace(
        effective_hash=_json_hash(effective),
        effective_canonical_json=effective,
        canonical_json=observed_canonical,
        resolution_surface="active_submission_sections",
        resolution_source_hash="a" * 64,
        resolution_reconciliation_hash="b" * 64,
        snapshot_id="active-id",
    )
    pages = {"submission_forms": [_form_payload()]}
    return active, observed, pages


def test_exact_match_inherits_approved_204_resolution() -> None:
    active, observed, pages = _fixture()
    inherited = build_inherited_effective_snapshot(
        active=active,
        observed=observed,
        pages_by_surface=pages,
    )
    assert inherited is not None
    assert inherited.complete is True
    assert inherited.semantic_hash == active.effective_hash
    assert len(inherited.canonical["bindings"]) == 56


def test_registry_change_invalidates_inheritance() -> None:
    active, observed, pages = _fixture()
    changed = dict(observed.canonical)
    changed["fields"] = list(changed["fields"]) + [
        {"metadata": "dc.test.new", "id": "new", "scopeNote": None}
    ]
    changed_observed = ContractSnapshotView(
        canonical=changed,
        semantic_hash=_json_hash(changed),
        complete=False,
        warnings=observed.warnings,
    )
    inherited = build_inherited_effective_snapshot(
        active=active,
        observed=changed_observed,
        pages_by_surface=pages,
    )
    assert inherited is None


def test_form_change_invalidates_inheritance() -> None:
    active, observed, pages = _fixture()
    modified = _form_payload()
    modified["_embedded"]["submissionforms"][0]["rows"][0]["fields"][0]["label"] = "Changed"
    inherited = build_inherited_effective_snapshot(
        active=active,
        observed=observed,
        pages_by_surface={"submission_forms": [modified]},
    )
    assert inherited is None


def test_unrelated_warning_invalidates_inheritance() -> None:
    active, observed, pages = _fixture()
    blocked = ContractSnapshotView(
        canonical=observed.canonical,
        semantic_hash=observed.semantic_hash,
        complete=False,
        warnings=observed.warnings + ("METADATA_FIELD_COVERAGE_MISMATCH:global=292:qualified=291",),
    )
    assert (
        build_inherited_effective_snapshot(
            active=active,
            observed=blocked,
            pages_by_surface=pages,
        )
        is None
    )
