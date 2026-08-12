import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    NotificationDelivery,
    NotificationEvent,
    NotificationOutbox,
    NotificationSeverity,
)
from cataloging_api.db.session import engine
from cataloging_api.notifications.constants import PILOT_RECIPIENT_ID
from cataloging_api.notifications.publisher import publish_pending


async def _seed_event(session: AsyncSession, *, dedup_key: str) -> NotificationEvent:
    event = NotificationEvent(
        event_id=uuid.uuid4(),
        event_type="sync.completed",
        aggregate_type="sync_run",
        aggregate_id=str(uuid.uuid4()),
        severity=NotificationSeverity.info,
        title="Seeded event",
        summary="Seeded for publisher test.",
        deduplication_key=dedup_key,
        occurred_at=datetime.now(UTC),
    )
    session.add(event)
    await session.flush()
    session.add(NotificationOutbox(outbox_id=uuid.uuid4(), event_id=event.event_id))
    await session.flush()
    return event


@pytest.mark.integration
@pytest.mark.asyncio
async def test_publish_pending_claims_and_delivers_once() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        event = await _seed_event(session, dedup_key=f"test.publish:{uuid.uuid4()}")

        first_pass = await publish_pending(session)
        assert len(first_pass) == 1

        outbox_row = await session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.event_id == event.event_id)
        )
        assert outbox_row is not None
        assert outbox_row.published_at is not None
        assert outbox_row.attempt_count == 1

        delivery = await session.scalar(
            select(NotificationDelivery).where(NotificationDelivery.event_id == event.event_id)
        )
        assert delivery is not None
        assert delivery.recipient_id == PILOT_RECIPIENT_ID
        assert delivery.state == "unread"
        assert delivery.delivery_seq == first_pass[0]

        # Already-published rows are never reclaimed.
        second_pass = await publish_pending(session)
        assert second_pass == []
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_publish_pending_does_not_duplicate_an_existing_delivery() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        event = await _seed_event(session, dedup_key=f"test.publish-conflict:{uuid.uuid4()}")
        session.add(
            NotificationDelivery(
                notification_id=uuid.uuid4(),
                event_id=event.event_id,
                recipient_id=PILOT_RECIPIENT_ID,
            )
        )
        await session.flush()

        new_sequences = await publish_pending(session)
        assert new_sequences == []

        delivery_count = await session.scalar(
            select(NotificationDelivery.notification_id).where(
                NotificationDelivery.event_id == event.event_id
            )
        )
        assert delivery_count is not None
        outbox_row = await session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.event_id == event.event_id)
        )
        assert outbox_row.published_at is not None
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
