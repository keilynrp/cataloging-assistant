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
from cataloging_api.notifications.constants import P0_EVENT_TYPES
from cataloging_api.notifications.preferences import (
    UnknownEventTypeError,
    list_preferences,
    set_mute,
)
from cataloging_api.notifications.publisher import publish_pending


async def _seed_event(
    session: AsyncSession, *, event_type: str, dedup_key: str
) -> NotificationEvent:
    event = NotificationEvent(
        event_id=uuid.uuid4(),
        event_type=event_type,
        aggregate_type="test",
        aggregate_id=str(uuid.uuid4()),
        severity=NotificationSeverity.info,
        title="Seeded",
        summary="Seeded for preferences test.",
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
async def test_defaults_are_unmuted_and_reject_unknown_event_types() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        preferences = await list_preferences(session)
        assert {row["event_type"] for row in preferences} == P0_EVENT_TYPES
        assert all(row["muted"] is False for row in preferences)

        with pytest.raises(UnknownEventTypeError):
            await set_mute(session, event_type="not.a.real.type", muted=True, actor="Tester")
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_muted_event_type_is_recorded_but_not_delivered() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        await set_mute(session, event_type="vocabulary.promoted", muted=True, actor="Tester")
        preferences = await list_preferences(session)
        row = next(row for row in preferences if row["event_type"] == "vocabulary.promoted")
        assert row["muted"] is True

        event = await _seed_event(
            session, event_type="vocabulary.promoted", dedup_key=f"test.muted:{uuid.uuid4()}"
        )
        new_sequences = await publish_pending(session)
        assert new_sequences == []

        delivery = await session.scalar(
            select(NotificationDelivery).where(NotificationDelivery.event_id == event.event_id)
        )
        assert delivery is None

        published_outbox = await session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.event_id == event.event_id)
        )
        assert published_outbox.published_at is not None

        # Already-published outbox rows are never reclaimed, muted or not.
        await set_mute(session, event_type="vocabulary.promoted", muted=False, actor="Tester")
        again = await publish_pending(session)
        assert again == []
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
