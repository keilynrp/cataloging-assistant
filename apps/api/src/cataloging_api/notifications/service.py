import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    NotificationDelivery,
    NotificationDeliveryState,
    NotificationEvent,
)
from cataloging_api.notifications.constants import PILOT_RECIPIENT_ID

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class InvalidCursorError(ValueError):
    """The opaque cursor could not be decoded; the client should reload without it."""


def encode_cursor(delivery_seq: int) -> str:
    return str(delivery_seq)


def decode_cursor(cursor: str) -> int:
    try:
        value = int(cursor)
    except ValueError as error:
        raise InvalidCursorError from error
    if value < 0:
        raise InvalidCursorError
    return value


async def count_unread(session: AsyncSession) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(NotificationDelivery)
            .where(
                NotificationDelivery.recipient_id == PILOT_RECIPIENT_ID,
                NotificationDelivery.state == NotificationDeliveryState.unread,
            )
        )
    ) or 0


async def list_notifications(
    session: AsyncSession,
    *,
    state: str | None = None,
    event_type: str | None = None,
    cursor: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> tuple[list[tuple[NotificationDelivery, NotificationEvent]], str | None, int]:
    limit = max(1, min(limit, MAX_LIMIT))
    query = (
        select(NotificationDelivery, NotificationEvent)
        .join(NotificationEvent, NotificationDelivery.event_id == NotificationEvent.event_id)
        .where(NotificationDelivery.recipient_id == PILOT_RECIPIENT_ID)
        .order_by(NotificationDelivery.delivery_seq.desc())
        .limit(limit + 1)
    )
    if state:
        query = query.where(NotificationDelivery.state == NotificationDeliveryState(state))
    if event_type:
        query = query.where(NotificationEvent.event_type == event_type)
    if cursor:
        query = query.where(NotificationDelivery.delivery_seq < decode_cursor(cursor))

    rows = (await session.execute(query)).all()
    has_more = len(rows) > limit
    page = [(delivery, event) for delivery, event in rows[:limit]]
    next_cursor = encode_cursor(page[-1][0].delivery_seq) if has_more and page else None
    unread_count = await count_unread(session)
    return page, next_cursor, unread_count


async def _get_own_delivery(
    session: AsyncSession, notification_id: uuid.UUID
) -> NotificationDelivery | None:
    return await session.scalar(
        select(NotificationDelivery).where(
            NotificationDelivery.notification_id == notification_id,
            NotificationDelivery.recipient_id == PILOT_RECIPIENT_ID,
        )
    )


async def mark_read(
    session: AsyncSession, notification_id: uuid.UUID
) -> NotificationDelivery | None:
    delivery = await _get_own_delivery(session, notification_id)
    if delivery is None:
        return None
    if delivery.state == NotificationDeliveryState.unread:
        delivery.state = NotificationDeliveryState.read
        delivery.read_at = datetime.now(UTC)
        await session.flush()
    return delivery


async def mark_all_read(session: AsyncSession) -> int:
    result = await session.execute(
        update(NotificationDelivery)
        .where(
            NotificationDelivery.recipient_id == PILOT_RECIPIENT_ID,
            NotificationDelivery.state == NotificationDeliveryState.unread,
        )
        .values(state=NotificationDeliveryState.read, read_at=datetime.now(UTC))
    )
    return result.rowcount or 0


async def archive(
    session: AsyncSession, notification_id: uuid.UUID
) -> NotificationDelivery | None:
    delivery = await _get_own_delivery(session, notification_id)
    if delivery is None:
        return None
    if delivery.state != NotificationDeliveryState.archived:
        delivery.state = NotificationDeliveryState.archived
        delivery.archived_at = datetime.now(UTC)
        await session.flush()
    return delivery
