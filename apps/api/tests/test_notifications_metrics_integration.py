import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    NotificationDelivery,
    NotificationEvent,
    NotificationOutbox,
    NotificationSeverity,
)
from cataloging_api.db.session import engine
from cataloging_api.notifications.constants import PILOT_RECIPIENT_ID
from cataloging_api.notifications.metrics import build_metrics


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_metrics_summarizes_events_deliveries_and_outbox_backlog() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        published_event = NotificationEvent(
            event_id=uuid.uuid4(),
            event_type="sync.completed",
            aggregate_type="test",
            aggregate_id="1",
            severity=NotificationSeverity.info,
            title="Published",
            summary="Published.",
            deduplication_key=f"test.metrics.published:{uuid.uuid4()}",
            occurred_at=datetime.now(UTC),
        )
        pending_event = NotificationEvent(
            event_id=uuid.uuid4(),
            event_type="vocabulary.promoted",
            aggregate_type="test",
            aggregate_id="2",
            severity=NotificationSeverity.info,
            title="Pending",
            summary="Pending.",
            deduplication_key=f"test.metrics.pending:{uuid.uuid4()}",
            occurred_at=datetime.now(UTC),
        )
        session.add_all([published_event, pending_event])
        await session.flush()
        session.add(
            NotificationOutbox(
                outbox_id=uuid.uuid4(),
                event_id=published_event.event_id,
                published_at=datetime.now(UTC),
                attempt_count=1,
            )
        )
        session.add(
            NotificationOutbox(outbox_id=uuid.uuid4(), event_id=pending_event.event_id)
        )
        session.add(
            NotificationDelivery(
                notification_id=uuid.uuid4(),
                event_id=published_event.event_id,
                recipient_id=PILOT_RECIPIENT_ID,
            )
        )
        await session.flush()

        metrics = await build_metrics(session)

        assert metrics["events_by_type"]["sync.completed"] >= 1
        assert metrics["events_by_type"]["vocabulary.promoted"] >= 1
        assert metrics["deliveries_by_state"]["unread"] >= 1
        assert metrics["outbox_pending"] >= 1
        assert metrics["outbox_oldest_pending_age_seconds"] is not None
        assert metrics["outbox_oldest_pending_age_seconds"] >= 0
        assert metrics["outbox_total_attempts"] >= 1
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
