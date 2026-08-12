from cataloging_api.reviews.security import review_token_is_valid


def test_review_token_requires_both_values() -> None:
    assert review_token_is_valid("", None) is False
    assert review_token_is_valid("configured", None) is False
    assert review_token_is_valid("", "provided") is False


def test_review_token_matches_exactly() -> None:
    assert review_token_is_valid("configured", "configured") is True
    assert review_token_is_valid("configured", "different") is False
