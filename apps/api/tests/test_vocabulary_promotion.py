import pytest

from cataloging_api.vocabularies.promotion_routes import resolve_promotion_values
from cataloging_api.vocabularies.service import VocabularyValidationError


def test_literal_duplicates_collapse_to_first_position_with_audit_note() -> None:
    selected, notes = resolve_promotion_values(
        ["Álgica", "Maya", "Álgica"],
        [],
    )

    assert selected == ["Álgica", "Maya"]
    assert notes == [
        "Colapso literal determinista: Álgica (posiciones ordinales 1, 3; se conservó la primera)"
    ]


def test_ambiguous_collision_requires_and_records_human_choice() -> None:
    selected, notes = resolve_promotion_values(
        ["Inglés", "inglés", "Español"],
        ["Inglés"],
    )

    assert selected == ["Inglés", "Español"]
    assert notes == ["Resolución humana: Inglés <= Inglés, inglés (posiciones ordinales 1, 2)"]


def test_ambiguous_collision_cannot_be_promoted_without_choice() -> None:
    with pytest.raises(
        VocabularyValidationError,
        match="Every ambiguous normalized collision",
    ):
        resolve_promotion_values(["Inglés", "inglés"], [])
