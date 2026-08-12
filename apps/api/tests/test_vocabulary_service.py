import pytest

from cataloging_api.diagnostics.engine import VocabularyRule
from cataloging_api.vocabularies.service import (
    VocabularyValidationError,
    build_metadata_validation_snapshot,
    normalize_term,
    prepare_terms,
)


def test_normalization_is_only_used_for_duplicate_identity() -> None:
    assert normalize_term("  P’URHEPECHA  ") == "p’urhepecha"
    prepared = prepare_terms(
        [
            {
                "value": "P’URHEPECHA",
                "authority": "https://example.test/term/1",
                "language": "es",
            }
        ]
    )
    assert prepared[0]["value"] == "P’URHEPECHA"
    assert prepared[0]["normalized_value"] == "p’urhepecha"


def test_duplicate_terms_after_normalization_are_rejected() -> None:
    with pytest.raises(VocabularyValidationError):
        prepare_terms(
            [
                {"value": "Tarasca", "authority": None, "language": None},
                {"value": " tarasca ", "authority": None, "language": None},
            ]
        )


def test_validation_snapshot_is_evidence_and_does_not_rewrite_values() -> None:
    field = "dc.subject.linguisticFamily"
    rule = VocabularyRule(
        revision_key=f"{field}:revision-1",
        name="Familias aprobadas",
        source_uri="https://example.test/families",
        version_label="1",
        approved_by="Referente",
        terms=frozenset({"Tarasca"}),
    )
    snapshot = build_metadata_validation_snapshot(
        {
            field: ["Tarasca", "Otra"],
            "dc.subject.linguiscgroup": ["Grupo propuesto"],
        },
        {field: rule},
    )

    assert snapshot["status"] == "invalid"
    assert snapshot["vocabulary_profile"] == [rule.profile_key]
    assert snapshot["fields"][0]["values"] == [
        {"value": "Tarasca", "approved": True},
        {"value": "Otra", "approved": False},
    ]
    assert snapshot["fields"][1]["status"] == "no_vocabulary"
    assert snapshot["fields"][1]["values"][0]["approved"] is None


def test_validation_snapshot_is_not_configured_without_active_rules() -> None:
    snapshot = build_metadata_validation_snapshot(
        {"dc.subject.linguisticFamily": ["Propuesta humana"]},
        {},
    )

    assert snapshot["status"] == "not_configured"
    assert snapshot["fields"][0]["status"] == "no_vocabulary"
