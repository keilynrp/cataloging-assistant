import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from cataloging_api.notifications.broadcaster import NotificationBroadcaster
from cataloging_api.notifications.publisher import publish_pending

logger = structlog.get_logger()


async def run_publisher_loop(
    session_factory: async_sessionmaker[AsyncSession],
    broadcaster: NotificationBroadcaster,
    *,
    idle_interval_seconds: float = 1.0,
) -> None:
    """Poll the outbox for the lifetime of the API process.

    Drains pending outbox rows back-to-back while there is work, then falls
    back to polling every ``idle_interval_seconds``. The worker existing in
    this pilot (this loop, inside the long-running API process) is the
    publisher named in VERTICAL-014; no separate broker is introduced.
    """
    while True:
        try:
            async with session_factory() as session:
                new_sequences = await publish_pending(session)
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("notification_publisher_failed")
            await asyncio.sleep(idle_interval_seconds)
            continue

        if new_sequences:
            broadcaster.publish(max(new_sequences))
        else:
            await asyncio.sleep(idle_interval_seconds)
