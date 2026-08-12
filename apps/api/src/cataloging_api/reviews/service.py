import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogFinding,
    CatalogReviewDecision,
    DSpaceItem,
    NotificationSeverity,
    ReviewDecisionKind,
)
from cataloging_api.notifications.constants import EventType
from cataloging_api.notifications.producer import record_notification_event


class ReviewConflictError(Exception):
    """The idempotency key was already used for a different review."""


async def record_review_decision(
    session: AsyncSession,
    *,
    item_uuid: uuid.UUID,
    finding_id: uuid.UUID,
    request_id: uuid.UUID,
    decision: ReviewDecisionKind,
    reviewer: str,
    note: str,
) -> CatalogReviewDecision | None:
    existing = await session.scalar(
        select(CatalogReviewDecision).where(CatalogReviewDecision.request_id == request_id)
    )
    if existing is not None:
        if existing.item_uuid != item_uuid:
            raise ReviewConflictError
        return existing

    finding = await session.scalar(
        select(CatalogFinding).where(
            CatalogFinding.finding_id == finding_id,
            CatalogFinding.item_uuid == item_uuid,
        )
    )
    if finding is None:
        return None

    review = CatalogReviewDecision(
        request_id=request_id,
        item_uuid=item_uuid,
        finding_fingerprint=finding.fingerprint,
        finding_code=finding.code,
        finding_severity=finding.severity,
        finding_affected_fields=list(finding.affected_fields),
        finding_explanation=finding.explanation,
        finding_rule_version=finding.rule_version,
        source_hash=finding.source_hash,
        decision=decision,
        reviewer=reviewer.strip(),
        note=note.strip(),
    )
    session.add(review)
    await session.flush()

    if decision == ReviewDecisionKind.deferred:
        collection_uuid = await session.scalar(
            select(DSpaceItem.collection_uuid).where(DSpaceItem.uuid == item_uuid)
        )
        await record_notification_event(
            session,
            event_type=EventType.REVIEW_DEFERRED,
            aggregate_type="review_decision",
            aggregate_id=str(review.decision_id),
            collection_uuid=collection_uuid,
            severity=NotificationSeverity.info,
            title="Revisión pospuesta",
            summary=f"{reviewer.strip()} pospuso una decisión sobre {finding.code}.",
            deduplication_key=f"review.deferred:{request_id}",
            target_path=f"/items/{item_uuid}",
        )
    return review
