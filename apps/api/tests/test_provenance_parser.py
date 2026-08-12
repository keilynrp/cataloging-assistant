from cataloging_api.provenance.parser import extract_actor


def test_extract_actor_is_deterministic_and_never_returns_email() -> None:
    value = "Submitted by Catalogadora (person@example.org) on 2026-01-01"
    first = extract_actor(value, secret="test-secret")
    second = extract_actor(value, secret="test-secret")
    assert first == second
    assert first is not None
    assert first["actor_key"] != "person@example.org"
    assert "person@example.org" not in repr(first)
    assert first["confidence"] == 0.8


def test_extract_actor_returns_none_without_email() -> None:
    assert extract_actor("Made available in DSpace", secret="test-secret") is None
