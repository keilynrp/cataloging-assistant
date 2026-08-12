import pytest

from cataloging_api.drafts.service import (
    DraftValidationError,
    normalize_metadata_patch,
)


def test_normalize_metadata_patch_preserves_repeated_value_order() -> None:
    patch = normalize_metadata_patch(
        {"dc.subject.linguiscgroup": [" Tarasco (Purépecha) ", "Purépecha"]}
    )
    values = patch["dc.subject.linguiscgroup"]
    assert [value["value"] for value in values] == ["Tarasco (Purépecha)", "Purépecha"]
    assert [value["place"] for value in values] == [0, 1]
    assert all(value["authority"] is None for value in values)


def test_normalize_metadata_patch_rejects_unknown_fields() -> None:
    with pytest.raises(DraftValidationError):
        normalize_metadata_patch({"dc.title": ["Invented title"]})


def test_normalize_metadata_patch_allows_explicit_field_removal() -> None:
    assert normalize_metadata_patch({"dc.subject.linguisticFamily": []}) == {
        "dc.subject.linguisticFamily": []
    }
