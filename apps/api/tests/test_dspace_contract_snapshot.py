from cataloging_api.dspace.contract_snapshot import (
    build_contract_snapshot,
    diff_contract_snapshots,
)


def _field(field_id: int, element: str, qualifier: str | None = None) -> dict:
    return {
        "id": field_id,
        "element": element,
        "qualifier": qualifier,
        "scopeNote": None,
    }


def _paged(relation: str, values: list[dict], *, number: int = 0, total_pages: int = 1) -> dict:
    return {
        "_embedded": {relation: values},
        "page": {
            "number": number,
            "totalPages": total_pages,
            "totalElements": len(values),
        },
    }


def _form(*, label: str = "Title", required: bool = True, prepend_note: bool = False) -> dict:
    fields = []
    if prepend_note:
        fields.append(
            {
                "input": {"type": "onebox"},
                "label": "Note",
                "mandatory": False,
                "repeatable": False,
                "selectableMetadata": [{"metadata": "dc.description"}],
                "typeBind": [],
            }
        )
    fields.append(
        {
            "input": {"type": "onebox"},
            "label": label,
            "mandatory": required,
            "repeatable": False,
            "selectableMetadata": [
                {
                    "metadata": "dc.title",
                    "label": None,
                    "controlledVocabulary": None,
                    "closed": None,
                }
            ],
            "typeBind": [],
        }
    )
    return {
        "id": "traditionalpageone",
        "name": "traditionalpageone",
        "rows": [{"fields": fields}],
    }


def _pages(
    *,
    label: str = "Title",
    required: bool = True,
    include_form: bool = True,
    prepend_note: bool = False,
) -> dict[str, list[dict]]:
    registry = [_field(64, "title"), _field(65, "description")]
    forms = []
    if include_form:
        forms = [
            _form(
                label=label,
                required=required,
                prepend_note=prepend_note,
            )
        ]
    return {
        "metadata_schemas": [
            _paged(
                "metadataschemas",
                [
                    {
                        "id": 1,
                        "prefix": "dc",
                        "namespace": "http://purl.org/dc/elements/1.1/",
                    }
                ],
            )
        ],
        "metadata_fields": [_paged("metadatafields", registry)],
        "metadata_fields_by_schema:dc": [_paged("metadatafields", registry)],
        "submission_forms": [_paged("submissionforms", forms)] if include_form else [],
        "active_submission_definition": [{"name": "traditional"}],
        "active_submission_sections": [
            _paged(
                "submissionsections",
                [
                    {
                        "id": "traditionalpageone",
                        "sectionType": "submission-form",
                        "_links": {
                            "config": {
                                "href": (
                                    "http://example/server/api/config/"
                                    "submissionforms/traditionalpageone"
                                )
                            }
                        },
                    }
                ],
            )
        ],
    }


def test_snapshot_is_deterministic_and_extracts_effective_binding() -> None:
    first = build_contract_snapshot(_pages())
    second = build_contract_snapshot(_pages())
    assert first.complete is True
    assert first.semantic_hash == second.semantic_hash
    assert first.canonical["fields"][0]["metadata"] == "dc.description"
    title = next(
        binding for binding in first.canonical["bindings"] if binding["metadata"] == "dc.title"
    )
    assert title["bindingKey"] == "traditionalpageone:dc.title:0"
    assert title["required"] is True
    assert title["inputType"] == "onebox"


def test_required_change_is_high_severity() -> None:
    previous = build_contract_snapshot(_pages(required=False))
    current = build_contract_snapshot(_pages(required=True))
    changes = diff_contract_snapshots(previous, current)
    assert any(
        change.change_type == "REQUIRED_CHANGED" and change.severity == "HIGH"
        for change in changes
    )


def test_incomplete_observation_never_emits_binding_removal() -> None:
    previous = build_contract_snapshot(_pages())
    current = build_contract_snapshot(_pages(include_form=False))
    assert current.complete is False
    changes = diff_contract_snapshots(previous, current)
    assert any(change.change_type == "UNOBSERVABLE_SURFACE" for change in changes)
    assert not any(change.change_type == "BINDING_REMOVED" for change in changes)


def test_missing_schema_qualified_surface_makes_snapshot_incomplete() -> None:
    pages = _pages()
    pages.pop("metadata_fields_by_schema:dc")
    snapshot = build_contract_snapshot(pages)
    assert snapshot.complete is False
    assert "UNOBSERVABLE_SURFACE:metadata_fields_by_schema:dc" in snapshot.warnings


def test_registry_coverage_mismatch_makes_snapshot_incomplete() -> None:
    pages = _pages()
    pages["metadata_fields_by_schema:dc"][0]["_embedded"]["metadatafields"].pop()
    pages["metadata_fields_by_schema:dc"][0]["page"]["totalElements"] = 1
    snapshot = build_contract_snapshot(pages)
    assert snapshot.complete is False
    assert any(
        warning.startswith("METADATA_FIELD_COVERAGE_MISMATCH:")
        for warning in snapshot.warnings
    )


def test_missing_middle_page_makes_snapshot_incomplete_and_suppresses_removals() -> None:
    previous = build_contract_snapshot(_pages())
    pages = _pages()
    first = _paged("metadatafields", [_field(64, "title")], number=0, total_pages=3)
    first["page"]["totalElements"] = 3
    third = _paged("metadatafields", [_field(65, "description")], number=2, total_pages=3)
    third["page"]["totalElements"] = 3
    pages["metadata_fields"] = [first, third]
    current = build_contract_snapshot(pages)
    assert current.complete is False
    assert "INCOMPLETE_PAGE_SEQUENCE:metadata_fields" in current.warnings
    changes = diff_contract_snapshots(previous, current)
    assert not any(change.change_type == "FIELD_REMOVED" for change in changes)
    assert not any(change.change_type == "BINDING_REMOVED" for change in changes)
    assert not any(change.change_type == "SCHEMA_REMOVED" for change in changes)


def test_http_204_active_sections_is_incomplete_and_never_destructive() -> None:
    previous = build_contract_snapshot(_pages())
    pages = _pages()
    pages["active_submission_sections"] = [
        {
            "_observation": {
                "observable": False,
                "statusCode": 204,
                "reason": "no_content",
            },
            "page": {
                "number": 0,
                "totalPages": 0,
                "totalElements": 0,
            },
        }
    ]
    current = build_contract_snapshot(pages)
    assert current.complete is False
    changes = diff_contract_snapshots(previous, current)
    assert not any(change.change_type == "FIELD_REMOVED" for change in changes)
    assert not any(change.change_type == "BINDING_REMOVED" for change in changes)
    assert not any(change.change_type == "SCHEMA_REMOVED" for change in changes)


def test_inserting_unrelated_binding_reports_order_change_not_title_removal() -> None:
    previous = build_contract_snapshot(_pages(prepend_note=False))
    current = build_contract_snapshot(_pages(prepend_note=True))
    changes = diff_contract_snapshots(previous, current)
    title_key = "traditionalpageone:dc.title:0"
    assert any(
        change.change_type == "ORDER_CHANGED" and change.identity == title_key
        for change in changes
    )
    assert not any(
        change.change_type == "BINDING_REMOVED" and change.identity == title_key
        for change in changes
    )
