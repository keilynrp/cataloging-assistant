from cataloging_api.work_queue.metrics import (
    classify_queue_item,
    closed_finding_fingerprints,
    summarize_queue,
)


def test_unreviewed_error_is_critical() -> None:
    state = classify_queue_item(
        [("fingerprint-1", "CAT-LING-002", "error")],
        set(),
        has_draft=False,
        draft_stale=False,
        latest_draft_version=None,
    )
    assert state.pending_finding_count == 1
    assert state.highest_severity == "error"
    assert state.priority == "critical"


def test_reviewed_finding_and_stale_draft_are_classified() -> None:
    reviewed = classify_queue_item(
        [("fingerprint-1", "CAT-LING-001", "warning")],
        {"fingerprint-1"},
        has_draft=False,
        draft_stale=False,
        latest_draft_version=None,
    )
    stale = classify_queue_item(
        [],
        set(),
        has_draft=True,
        draft_stale=True,
        latest_draft_version=2,
    )
    assert reviewed.priority == "reviewed"
    assert reviewed.pending_finding_count == 0
    assert stale.priority == "rebase"
    assert stale.latest_draft_version == 2


def test_queue_summary_uses_item_grain() -> None:
    states = [
        classify_queue_item(
            [("one", "CAT-1", "error")],
            set(),
            has_draft=False,
            draft_stale=False,
            latest_draft_version=None,
        ),
        classify_queue_item(
            [("two", "CAT-2", "warning")],
            {"two"},
            has_draft=True,
            draft_stale=False,
            latest_draft_version=1,
        ),
        classify_queue_item(
            [],
            set(),
            has_draft=True,
            draft_stale=True,
            latest_draft_version=3,
        ),
    ]
    assert summarize_queue(states) == {
        "attention_items": 3,
        "items_with_findings": 2,
        "pending_review_items": 1,
        "reviewed_items": 1,
        "items_with_draft": 2,
        "stale_draft_items": 1,
        "open_draft_items": 1,
        "approved_draft_items": 0,
        "rejected_draft_items": 0,
        "superseded_draft_items": 0,
        "items_with_pending_suggestions": 0,
        "pending_suggestions": 0,
    }


def test_pending_suggestion_has_queue_priority() -> None:
    state = classify_queue_item(
        [],
        set(),
        has_draft=False,
        draft_stale=False,
        latest_draft_version=None,
        pending_suggestion_count=2,
    )
    assert state.priority == "suggestion"
    assert state.pending_suggestion_count == 2


def test_deferred_review_remains_open() -> None:
    closed = closed_finding_fingerprints([("fingerprint-1", "deferred")])
    state = classify_queue_item(
        [("fingerprint-1", "CAT-LING-003", "warning")],
        closed,
        has_draft=True,
        draft_stale=False,
        latest_draft_version=1,
        deferred_finding_count=1,
    )

    assert state.pending_finding_count == 1
    assert state.deferred_finding_count == 1
    assert state.priority == "high"


def test_latest_review_decision_controls_whether_finding_is_closed() -> None:
    decisions = [
        ("fingerprint-1", "deferred"),
        ("fingerprint-1", "confirmed"),
        ("fingerprint-2", "confirmed"),
        ("fingerprint-2", "deferred"),
    ]

    assert closed_finding_fingerprints(decisions) == {"fingerprint-1"}
