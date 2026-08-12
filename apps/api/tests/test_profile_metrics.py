import uuid

from cataloging_api.profile.metrics import safe_rate, summarize_completeness_patterns

ITEM_A = uuid.UUID("11111111-1111-4111-8111-111111111111")
ITEM_B = uuid.UUID("22222222-2222-4222-8222-222222222222")
ITEM_C = uuid.UUID("33333333-3333-4333-8333-333333333333")


def test_safe_rate_handles_empty_denominator() -> None:
    assert safe_rate(1, 4) == 0.25
    assert safe_rate(0, 0) == 0.0


def test_completeness_patterns_include_items_without_linguistic_fields() -> None:
    patterns = summarize_completeness_patterns(
        [ITEM_A, ITEM_B, ITEM_C],
        [
            (ITEM_A, "dc.subject.linguisticFamily"),
            (ITEM_A, "dc.subject.linguisticBranch"),
            (ITEM_B, "dc.subject.linguisticFamily"),
            (ITEM_B, "dc.unknown"),
        ],
    )

    assert [pattern.fields_present for pattern in patterns] == [
        (),
        ("dc.subject.linguisticFamily",),
        ("dc.subject.linguisticFamily", "dc.subject.linguisticBranch"),
    ]
    assert sum(pattern.item_count for pattern in patterns) == 3
    assert sum(pattern.rate for pattern in patterns) == 0.9999
