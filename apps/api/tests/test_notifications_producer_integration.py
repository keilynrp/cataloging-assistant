import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import NotificationEvent, NotificationOutbox, NotificationSeverity
from cataloging_api.db.session import engine
from cataloging_api.notifications.producer import record_notification_event


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_emission_is_deduplicated_and_writes_outbox() -> None:
    dedup_key = f"test.dedup:{uuid.uuid4()}"
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        first = await record_notification_event(
            session,
            event_type="sync.completed",
            aggregate_type="sync_run",
            aggregate_id=str(uuid.uuid4()),
            severity=NotificationSeverity.info,
            title="  Sincronización completada  ",
            summary="10 ítems vistos.",
            deduplication_key=dedup_key,
            occurred_at=datetime.now(UTC),
        )
        second = await record_notification_event(
            session,
            event_type="sync.completed",
            aggregate_type="sync_run",
            aggregate_id=str(uuid.uuid4()),
            severity=NotificationSeverity.info,
            title="Duplicate attempt",
            summary="Should be ignored.",
            deduplication_key=dedup_key,
        )
        assert first is not None
        assert first.title == "Sincronización completada"
        assert second is None

        event_count = await session.scalar(
            select(func.count())
            .select_from(NotificationEvent)
            .where(NotificationEvent.deduplication_key == dedup_key)
        )
        assert event_count == 1

        outbox_row = await session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.event_id == first.event_id)
        )
        assert outbox_row is not None
        assert outbox_row.published_at is None
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_emission_does_not_break_a_sibling_write_on_duplicate_key() -> None:
    """A collided deduplication_key must not roll back unrelated writes in the
    same transaction; notifications are best-effort alongside the domain write."""
    dedup_key = f"test.sibling:{uuid.uuid4()}"
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        await record_notification_event(
            session,
            event_type="sync.completed",
            aggregate_type="sync_run",
            aggregate_id=str(uuid.uuid4()),
            severity=NotificationSeverity.info,
            title="First",
            summary="First.",
            deduplication_key=dedup_key,
        )

        marker_event_id = uuid.uuid4()
        session.add(
            NotificationEvent(
                event_id=marker_event_id,
                event_type="marker",
                aggregate_type="marker",
                aggregate_id="marker",
                severity=NotificationSeverity.info,
                title="Sibling write",
                summary="Must survive.",
                deduplication_key=f"test.marker:{uuid.uuid4()}",
                occurred_at=datetime.now(UTC),
            )
        )
        await session.flush()

        duplicate = await record_notification_event(
            session,
            event_type="sync.completed",
            aggregate_type="sync_run",
            aggregate_id=str(uuid.uuid4()),
            severity=NotificationSeverity.info,
            title="Second",
            summary="Second.",
            deduplication_key=dedup_key,
        )
        assert duplicate is None

        # The sibling row inserted earlier in the same transaction must still be visible.
        marker = await session.scalar(
            select(NotificationEvent).where(NotificationEvent.event_id == marker_event_id)
        )
        assert marker is not None
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
