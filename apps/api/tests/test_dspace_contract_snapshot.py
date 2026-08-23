from cataloging_api.dspace.contract_snapshot import (
    build_contract_snapshot,
    diff_contract_snapshots,
)


def _pages(*, label: str = "Title", required: bool = True, include_form: bool = True):
    form_payloads = []
    if include_form:
        form_payloads = [
            {
                "_embedded": {
                    "submissionforms": [
                        {
                            "id": "traditionalpageone",
                            "name": "traditionalpageone",
                            "rows": [
                                {
                                    "fields": [
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
                                    ]
                                }
                            ],
                        }
                    ]
                }
            }
        ]
    return {
        "metadata_schemas": [
            {"_embedded": {"metadataschemas": [{"id": 1, "prefix": "dc"}]}}
        ],
        "metadata_fields": [
            {
                "_embedded": {
                    "metadatafields": [
                        {
                            "id": 64,
                            "element": "title",
                            "qualifier": None,
                            "scopeNote": None,
                            "_embedded": {"schema": {"prefix": "dc"}},
                        }
                    ]
                }
            }
        ],
        "submission_forms": form_payloads,
        "active_submission_definition": [{"name": "traditional"}],
        "active_submission_sections": [
            {
                "_embedded": {
                    "submissionsections": [
                        {
                            "id": "traditionalpageone",
                            "sectionType": "submission-form",
                            "_links": {
                                "config": {
                                    "href": "http://example/server/api/config/submissionforms/traditionalpageone"
                                }
                            },
                        }
                    ]
                }
            }
        ],
    }


def test_snapshot_is_deterministic_and_extracts_effective_binding() -> None:
    first = build_contract_snapshot(_pages())
    second = build_contract_snapshot(_pages())
    assert first.complete is True
    assert first.semantic_hash == second.semantic_hash
    assert first.canonical["fields"][0]["metadata"] == "dc.title"
    binding = first.canonical["bindings"][0]
    assert binding["metadata"] == "dc.title"
    assert binding["required"] is True
    assert binding["inputType"] == "onebox"


def test_required_change_is_high_severity() -> None:
    previous = build_contract_snapshot(_pages(required=False))
    current = build_contract_snapshot(_pages(required=True))
    changes = diff_contract_snapshots(previous, current)
    assert any(change.change_type == "REQUIRED_CHANGED" and change.severity == "HIGH" for change in changes)


def test_incomplete_observation_never_emits_binding_removal() -> None:
    previous = build_contract_snapshot(_pages())
    current = build_contract_snapshot(_pages(include_form=False))
    assert current.complete is False
    changes = diff_contract_snapshots(previous, current)
    assert any(change.change_type == "UNOBSERVABLE_SURFACE" for change in changes)
    assert not any(change.change_type == "BINDING_REMOVED" for change in changes)


def test_unresolved_field_schema_makes_snapshot_incomplete() -> None:
    pages = _pages()
    field = pages["metadata_fields"][0]["_embedded"]["metadatafields"][0]
    field.pop("_embedded")
    snapshot = build_contract_snapshot(pages)
    assert snapshot.complete is False
    assert any(warning.startswith("UNRESOLVED_FIELD_SCHEMA:") for warning in snapshot.warnings)
