import pytest

from cataloging_api.notifications.service import InvalidCursorError, decode_cursor, encode_cursor


def test_cursor_round_trips() -> None:
    assert decode_cursor(encode_cursor(42)) == 42


def test_cursor_rejects_non_numeric() -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor("not-a-number")


def test_cursor_rejects_negative() -> None:
    with pytest.raises(InvalidCursorError):
        decode_cursor("-1")
