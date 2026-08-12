import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import NotificationEvent, NotificationOutbox, NotificationSeverity


async def record_notification_event(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    severity: NotificationSeverity,
    title: str,
    summary: str,
    deduplication_key: str,
    collection_uuid: uuid.UUID | None = None,
    target_path: str | None = None,
    payload: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> NotificationEvent | None:
    """Insert an immutable event and its outbox row inside the caller's transaction.

    Notification emission must never break the domain write it accompanies, so a
    duplicate `deduplication_key` (checked up front, and again defensively under a
    SAVEPOINT in case of a concurrent writer) simply yields ``None`` instead of
    raising into the caller's transaction. The event only takes effect once the
    caller commits, per VERTICAL-014 principle 6.
    """
    existing = await session.scalar(
        select(NotificationEvent.event_id).where(
            NotificationEvent.deduplication_key == deduplication_key
        )
    )
    if existing is not None:
        return None

    event = NotificationEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        collection_uuid=collection_uuid,
        severity=severity,
        title=title.strip(),
        summary=summary.strip(),
        target_path=target_path,
        payload=payload or {},
        deduplication_key=deduplication_key,
        occurred_at=occurred_at or datetime.now(UTC),
    )
    try:
        async with session.begin_nested():
            session.add(event)
            await session.flush()
            session.add(NotificationOutbox(event_id=event.event_id))
            await session.flush()
    except IntegrityError:
        return None
    return event
