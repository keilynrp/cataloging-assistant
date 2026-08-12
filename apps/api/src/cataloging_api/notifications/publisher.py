from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import NotificationDelivery, NotificationOutbox
from cataloging_api.notifications.constants import PILOT_RECIPIENT_ID

DEFAULT_BATCH_SIZE = 50


async def publish_pending(
    session: AsyncSession, *, batch_size: int = DEFAULT_BATCH_SIZE
) -> list[int]:
    """Claim pending outbox rows and fan them out to authorized recipients.

    Claims rows with ``FOR UPDATE SKIP LOCKED`` so concurrent publishers never
    double-claim, creates idempotent per-recipient deliveries, and marks the
    outbox rows published. Returns the ``delivery_seq`` of every delivery
    created in this call so the caller can signal connected WebSocket clients.
    The caller owns the transaction and must commit.
    """
    rows = (
        (
            await session.execute(
                select(NotificationOutbox)
                .where(NotificationOutbox.published_at.is_(None))
                .order_by(NotificationOutbox.available_at)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return []

    now = datetime.now(UTC)
    new_sequences: list[int] = []
    for row in rows:
        statement = (
            insert(NotificationDelivery)
            .values(event_id=row.event_id, recipient_id=PILOT_RECIPIENT_ID)
            .on_conflict_do_nothing(
                index_elements=[NotificationDelivery.event_id, NotificationDelivery.recipient_id]
            )
            .returning(NotificationDelivery.delivery_seq)
        )
        sequence = (await session.execute(statement)).scalar_one_or_none()
        if sequence is not None:
            new_sequences.append(sequence)
        row.published_at = now
        row.attempt_count += 1
    return new_sequences
