import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import NotificationEvent, NotificationSeverity
from cataloging_api.notifications.constants import EventType
from cataloging_api.notifications.producer import record_notification_event

DEFAULT_LOOKBACK = timedelta(hours=24)

EVENT_TYPE_LABELS: dict[str, tuple[str, str]] = {
    EventType.SYNC_COMPLETED: ("sincronización completada", "sincronizaciones completadas"),
    EventType.SYNC_FAILED: ("sincronización fallida", "sincronizaciones fallidas"),
    EventType.ITEMS_CHANGED: ("lote de ítems modificados", "lotes de ítems modificados"),
    EventType.DIAGNOSTICS_CHANGED: ("lote de hallazgos nuevos", "lotes de hallazgos nuevos"),
    EventType.DRAFT_STALE: ("borrador obsoleto", "borradores obsoletos"),
    EventType.REVIEW_DEFERRED: ("revisión pospuesta", "revisiones pospuestas"),
    EventType.SUGGESTION_PENDING: ("sugerencia pendiente", "sugerencias pendientes"),
    EventType.VOCABULARY_PROMOTED: ("vocabulario promovido", "vocabularios promovidos"),
}


def _describe(count: int, event_type: str) -> str:
    singular, plural = EVENT_TYPE_LABELS.get(event_type, (event_type, event_type))
    return f"{count} {singular if count == 1 else plural}"


async def build_digest_summary(
    session: AsyncSession, *, now: datetime | None = None
) -> NotificationEvent | None:
    """Aggregate P0 event activity into a single periodic digest.

    Reuses the existing outbox/publisher/WebSocket/HTTP pipeline instead of a
    new delivery mechanism: the digest is just another notification event, so
    it shows up in the bell, history, and preferences like any other type.
    Meant to be run periodically out-of-process (see digest_cli), the way
    sync and diagnostics are already operator-triggered CLIs rather than an
    in-app scheduler.

    Returns None (emitting nothing) when there was no activity since the last
    digest, so idle periods do not produce empty noise.
    """
    now = now or datetime.now(UTC)
    last_digest_at = await session.scalar(
        select(func.max(NotificationEvent.occurred_at)).where(
            NotificationEvent.event_type == EventType.DIGEST_SUMMARY
        )
    )
    since = last_digest_at or (now - DEFAULT_LOOKBACK)

    counts = dict(
        (
            await session.execute(
                select(NotificationEvent.event_type, func.count())
                .where(
                    NotificationEvent.event_type != EventType.DIGEST_SUMMARY,
                    NotificationEvent.occurred_at > since,
                    NotificationEvent.occurred_at <= now,
                )
                .group_by(NotificationEvent.event_type)
            )
        ).all()
    )
    if not counts:
        return None

    parts = [_describe(count, event_type) for event_type, count in sorted(counts.items())]
    total = sum(counts.values())
    since_label = since.strftime("%d/%m %H:%M UTC")
    digest_id = uuid.uuid4()

    return await record_notification_event(
        session,
        event_type=EventType.DIGEST_SUMMARY,
        aggregate_type="digest",
        aggregate_id=str(digest_id),
        severity=NotificationSeverity.info,
        title=f"Resumen de actividad ({total})",
        summary=f"Desde {since_label}: " + ", ".join(parts) + ".",
        deduplication_key=f"digest.summary:{digest_id}",
        target_path="/notifications",
        payload={"since": since.isoformat(), "until": now.isoformat(), "counts": counts},
        occurred_at=now,
    )
