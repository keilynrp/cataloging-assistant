from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import NotificationDelivery, NotificationEvent, NotificationOutbox


async def build_metrics(session: AsyncSession) -> dict[str, object]:
    """Operational counters from VERTICAL-014's Observabilidad section.

    Connection-level counters (accepted/rejected WebSocket handshakes) live in
    the API process's memory (see notifications.routes) and are merged in by
    the caller; everything here is reconstructible from PostgreSQL alone.
    """
    events_by_type = {
        event_type: count
        for event_type, count in (
            await session.execute(
                select(NotificationEvent.event_type, func.count()).group_by(
                    NotificationEvent.event_type
                )
            )
        ).all()
    }
    deliveries_by_state = {
        str(state): count
        for state, count in (
            await session.execute(
                select(NotificationDelivery.state, func.count()).group_by(
                    NotificationDelivery.state
                )
            )
        ).all()
    }
    outbox_pending = (
        await session.scalar(
            select(func.count())
            .select_from(NotificationOutbox)
            .where(NotificationOutbox.published_at.is_(None))
        )
    ) or 0
    oldest_pending_available_at = await session.scalar(
        select(func.min(NotificationOutbox.available_at)).where(
            NotificationOutbox.published_at.is_(None)
        )
    )
    outbox_total_attempts = int(
        (await session.scalar(select(func.sum(NotificationOutbox.attempt_count)))) or 0
    )
    oldest_pending_age_seconds = (
        (datetime.now(UTC) - oldest_pending_available_at).total_seconds()
        if oldest_pending_available_at is not None
        else None
    )
    return {
        "events_by_type": events_by_type,
        "deliveries_by_state": deliveries_by_state,
        "outbox_pending": outbox_pending,
        "outbox_oldest_pending_age_seconds": oldest_pending_age_seconds,
        "outbox_total_attempts": outbox_total_attempts,
    }
