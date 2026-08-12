from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import NotificationMuteRule
from cataloging_api.notifications.constants import KNOWN_EVENT_TYPES


class UnknownEventTypeError(ValueError):
    """The event type is not part of the known catalog."""


async def list_muted_event_types(session: AsyncSession) -> frozenset[str]:
    rows = await session.scalars(select(NotificationMuteRule.event_type))
    return frozenset(rows)


async def list_preferences(session: AsyncSession) -> list[dict[str, object]]:
    muted = await list_muted_event_types(session)
    return [
        {"event_type": event_type, "muted": event_type in muted}
        for event_type in sorted(KNOWN_EVENT_TYPES)
    ]


async def set_mute(
    session: AsyncSession, *, event_type: str, muted: bool, actor: str
) -> None:
    if event_type not in KNOWN_EVENT_TYPES:
        raise UnknownEventTypeError(event_type)
    if muted:
        existing = await session.get(NotificationMuteRule, event_type)
        if existing is None:
            session.add(
                NotificationMuteRule(
                    event_type=event_type,
                    muted_at=datetime.now(UTC),
                    muted_by=actor.strip(),
                )
            )
            await session.flush()
        return
    await session.execute(
        delete(NotificationMuteRule).where(NotificationMuteRule.event_type == event_type)
    )
