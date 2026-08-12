from dataclasses import dataclass

SEVERITY_RANK = {
    "error": 3,
    "warning": 2,
    "suggestion": 1,
    "review": 1,
}


@dataclass(frozen=True)
class QueueItemState:
    finding_count: int
    pending_finding_count: int
    pending_suggestion_count: int
    deferred_finding_count: int
    finding_codes: tuple[str, ...]
    highest_severity: str | None
    has_draft: bool
    draft_stale: bool
    latest_draft_version: int | None
    draft_state: str | None
    priority: str


CLOSED_REVIEW_DECISIONS = frozenset({"confirmed", "dismissed"})


def derive_draft_state(
    *,
    has_draft: bool,
    draft_stale: bool,
    latest_decisions: tuple[str, ...] = (),
    has_older_decisions: bool = False,
) -> str | None:
    """Derive operational state while preserving immutable decision history."""
    if not has_draft:
        return None
    if draft_stale:
        return "stale"
    if latest_decisions:
        return latest_decisions[-1]
    if has_older_decisions:
        return "superseded"
    return "open"


def closed_finding_fingerprints(
    decisions: list[tuple[str, str]],
) -> set[str]:
    """Return fingerprints whose latest human decision closes review."""
    latest_by_fingerprint: dict[str, str] = {}
    for fingerprint, decision in decisions:
        latest_by_fingerprint[fingerprint] = decision
    return {
        fingerprint
        for fingerprint, decision in latest_by_fingerprint.items()
        if decision in CLOSED_REVIEW_DECISIONS
    }


def classify_queue_item(
    findings: list[tuple[str, str, str]],
    reviewed_fingerprints: set[str],
    *,
    has_draft: bool,
    draft_stale: bool,
    latest_draft_version: int | None,
    draft_state: str | None = None,
    deferred_finding_count: int = 0,
    pending_suggestion_count: int = 0,
) -> QueueItemState:
    pending = [
        (fingerprint, code, severity)
        for fingerprint, code, severity in findings
        if fingerprint not in reviewed_fingerprints
    ]
    highest = max(
        (severity for _, _, severity in findings),
        key=lambda severity: SEVERITY_RANK.get(severity, 0),
        default=None,
    )
    resolved_draft_state = draft_state or derive_draft_state(
        has_draft=has_draft,
        draft_stale=draft_stale,
    )
    if any(severity == "error" for _, _, severity in pending):
        priority = "critical"
    elif pending:
        priority = "high"
    elif pending_suggestion_count:
        priority = "suggestion"
    elif resolved_draft_state == "stale":
        priority = "rebase"
    elif resolved_draft_state in {"open", "superseded"}:
        priority = "draft"
    elif resolved_draft_state in {"approved", "rejected"}:
        priority = resolved_draft_state
    else:
        priority = "reviewed"

    return QueueItemState(
        finding_count=len(findings),
        pending_finding_count=len(pending),
        pending_suggestion_count=pending_suggestion_count,
        finding_codes=tuple(sorted({code for _, code, _ in findings})),
        deferred_finding_count=deferred_finding_count,
        highest_severity=highest,
        has_draft=has_draft,
        draft_stale=draft_stale,
        latest_draft_version=latest_draft_version,
        draft_state=resolved_draft_state,
        priority=priority,
    )


def summarize_queue(states: list[QueueItemState]) -> dict[str, int]:
    return {
        "attention_items": sum(
            state.finding_count > 0 or state.has_draft or state.pending_suggestion_count > 0
            for state in states
        ),
        "items_with_findings": sum(state.finding_count > 0 for state in states),
        "pending_review_items": sum(state.pending_finding_count > 0 for state in states),
        "reviewed_items": sum(
            state.finding_count > 0 and state.pending_finding_count == 0 for state in states
        ),
        "items_with_draft": sum(state.has_draft for state in states),
        "stale_draft_items": sum(state.draft_stale for state in states),
        "open_draft_items": sum(state.draft_state == "open" for state in states),
        "approved_draft_items": sum(state.draft_state == "approved" for state in states),
        "rejected_draft_items": sum(state.draft_state == "rejected" for state in states),
        "superseded_draft_items": sum(state.draft_state == "superseded" for state in states),
        "items_with_pending_suggestions": sum(
            state.pending_suggestion_count > 0 for state in states
        ),
        "pending_suggestions": sum(state.pending_suggestion_count for state in states),
    }
