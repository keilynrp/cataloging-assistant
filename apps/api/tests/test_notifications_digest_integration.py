import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import NotificationEvent, NotificationSeverity
from cataloging_api.db.session import engine
from cataloging_api.notifications.digest import build_digest_summary


async def _seed_event(
    session: AsyncSession, *, event_type: str, occurred_at: datetime
) -> NotificationEvent:
    event = NotificationEvent(
        event_id=uuid.uuid4(),
        event_type=event_type,
        aggregate_type="test",
        aggregate_id=str(uuid.uuid4()),
        severity=NotificationSeverity.info,
        title="Seeded",
        summary="Seeded for digest test.",
        deduplication_key=f"test.digest.{event_type}:{uuid.uuid4()}",
        occurred_at=occurred_at,
    )
    session.add(event)
    await session.flush()
    return event


@pytest.mark.integration
@pytest.mark.asyncio
async def test_digest_returns_none_when_no_activity() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        event = await build_digest_summary(session, now=datetime.now(UTC))
        assert event is None
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_digest_summarizes_activity_and_advances_the_boundary() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        t0 = datetime.now(UTC) - timedelta(hours=2)
        await _seed_event(session, event_type="sync.completed", occurred_at=t0)
        await _seed_event(session, event_type="sync.completed", occurred_at=t0)
        await _seed_event(session, event_type="vocabulary.promoted", occurred_at=t0)

        first_digest_at = datetime.now(UTC) - timedelta(hours=1)
        digest = await build_digest_summary(session, now=first_digest_at)
        assert digest is not None
        assert digest.event_type == "digest.summary"
        assert "2 sincronizaciones completadas" in digest.summary
        assert "1 vocabulario promovido" in digest.summary
        assert digest.target_path == "/notifications"

        # Nothing new happened since the digest just emitted: the next run,
        # even later, must find no activity and emit nothing.
        empty_followup = await build_digest_summary(session, now=datetime.now(UTC))
        assert empty_followup is None

        # A later event is only picked up by the *next* digest.
        t1 = datetime.now(UTC)
        await _seed_event(session, event_type="draft.stale", occurred_at=t1)
        second_digest = await build_digest_summary(session, now=t1 + timedelta(seconds=1))
        assert second_digest is not None
        assert "1 borrador obsoleto" in second_digest.summary
        assert "sincronizacion" not in second_digest.summary.lower()
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
