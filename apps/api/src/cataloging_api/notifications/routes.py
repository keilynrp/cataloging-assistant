import asyncio
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.api.routes import require_review_token
from cataloging_api.config import get_settings
from cataloging_api.db.models import NotificationDelivery, NotificationEvent
from cataloging_api.db.session import get_session
from cataloging_api.notifications.broadcaster import broadcaster
from cataloging_api.notifications.metrics import build_metrics
from cataloging_api.notifications.preferences import (
    UnknownEventTypeError,
    list_preferences,
    set_mute,
)
from cataloging_api.notifications.schemas import (
    MarkAllReadOut,
    MetricsOut,
    NotificationActionOut,
    NotificationListOut,
    NotificationOut,
    PreferenceListOut,
    PreferenceOut,
    PreferenceUpdate,
    UnreadCountOut,
)
from cataloging_api.notifications.service import (
    InvalidCursorError,
    archive,
    count_unread,
    list_notifications,
    mark_all_read,
    mark_read,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/notifications", tags=["notifications"])
ws_router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_session)]

HEARTBEAT_SECONDS = 30
IDLE_TIMEOUT_SECONDS = 90
MAX_CONCURRENT_CONNECTIONS = 200
_active_connections = 0
_total_connections_accepted = 0
_total_connections_rejected = 0


def _to_out(delivery: NotificationDelivery, event: NotificationEvent) -> NotificationOut:
    return NotificationOut(
        notification_id=delivery.notification_id,
        event_type=event.event_type,
        severity=event.severity,
        title=event.title,
        summary=event.summary,
        target_path=event.target_path,
        state=delivery.state,
        occurred_at=event.occurred_at,
    )


@router.get("", response_model=NotificationListOut)
async def get_notifications(
    session: SessionDep,
    state: str | None = Query(default=None, pattern="^(unread|read|archived)$"),
    event_type: str | None = Query(default=None, max_length=100),
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> NotificationListOut:
    try:
        page, next_cursor, unread_count = await list_notifications(
            session, state=state, event_type=event_type, cursor=cursor, limit=limit
        )
    except InvalidCursorError as error:
        raise HTTPException(status_code=410, detail="Cursor expired; reload without it") from error
    return NotificationListOut(
        items=[_to_out(delivery, event) for delivery, event in page],
        next_cursor=next_cursor,
        unread_count=unread_count,
    )


@router.get("/unread-count", response_model=UnreadCountOut)
async def get_unread_count(session: SessionDep) -> UnreadCountOut:
    return UnreadCountOut(unread_count=await count_unread(session))


@router.get("/preferences", response_model=PreferenceListOut)
async def get_preferences(session: SessionDep) -> PreferenceListOut:
    rows = await list_preferences(session)
    return PreferenceListOut(preferences=[PreferenceOut(**row) for row in rows])


@router.put(
    "/preferences/{event_type}",
    response_model=PreferenceOut,
    dependencies=[Depends(require_review_token)],
)
async def put_preference(
    event_type: str, payload: PreferenceUpdate, session: SessionDep
) -> PreferenceOut:
    try:
        await set_mute(session, event_type=event_type, muted=payload.muted, actor=payload.actor)
    except UnknownEventTypeError as error:
        raise HTTPException(status_code=404, detail="Unknown event type") from error
    await session.commit()
    return PreferenceOut(event_type=event_type, muted=payload.muted)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationActionOut,
    dependencies=[Depends(require_review_token)],
)
async def post_mark_read(
    notification_id: uuid.UUID, session: SessionDep
) -> NotificationActionOut:
    delivery = await mark_read(session, notification_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.commit()
    return NotificationActionOut(notification_id=delivery.notification_id, state=delivery.state)


@router.post(
    "/read-all",
    response_model=MarkAllReadOut,
    dependencies=[Depends(require_review_token)],
)
async def post_mark_all_read(session: SessionDep) -> MarkAllReadOut:
    updated = await mark_all_read(session)
    await session.commit()
    return MarkAllReadOut(updated=updated, unread_count=await count_unread(session))


@router.post(
    "/{notification_id}/archive",
    response_model=NotificationActionOut,
    dependencies=[Depends(require_review_token)],
)
async def post_archive(notification_id: uuid.UUID, session: SessionDep) -> NotificationActionOut:
    delivery = await archive(session, notification_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.commit()
    return NotificationActionOut(notification_id=delivery.notification_id, state=delivery.state)


@router.get("/metrics", response_model=MetricsOut)
async def get_metrics(session: SessionDep) -> MetricsOut:
    metrics = await build_metrics(session)
    return MetricsOut(
        **metrics,
        active_connections=_active_connections,
        total_connections_accepted=_total_connections_accepted,
        total_connections_rejected=_total_connections_rejected,
    )


@ws_router.websocket("/ws/notifications")
async def notifications_socket(websocket: WebSocket) -> None:
    global _active_connections, _total_connections_accepted, _total_connections_rejected

    allowed_origin = get_settings().catalog_web_origin
    if websocket.headers.get("origin") != allowed_origin:
        _total_connections_rejected += 1
        await websocket.close(code=4403)
        return
    if _active_connections >= MAX_CONCURRENT_CONNECTIONS:
        _total_connections_rejected += 1
        await websocket.close(code=4408)
        return

    await websocket.accept()
    _active_connections += 1
    _total_connections_accepted += 1
    queue = broadcaster.subscribe()
    last_activity = datetime.now(UTC)

    async def receive_loop() -> None:
        nonlocal last_activity
        while True:
            raw = await websocket.receive_text()
            last_activity = datetime.now(UTC)
            try:
                message = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(message, dict) or message.get("type") != "resume":
                continue
            after_cursor = message.get("after_cursor")
            if isinstance(after_cursor, int) and broadcaster.cursor > after_cursor:
                await websocket.send_json(
                    {"type": "notifications.available", "cursor": broadcaster.cursor}
                )

    async def heartbeat_loop() -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            if (datetime.now(UTC) - last_activity).total_seconds() >= IDLE_TIMEOUT_SECONDS:
                raise TimeoutError
            await websocket.send_json(
                {"type": "heartbeat", "server_time": datetime.now(UTC).isoformat()}
            )

    async def relay_loop() -> None:
        while True:
            cursor = await queue.get()
            await websocket.send_json({"type": "notifications.available", "cursor": cursor})

    try:
        if broadcaster.cursor:
            await websocket.send_json(
                {"type": "notifications.available", "cursor": broadcaster.cursor}
            )
        async with asyncio.TaskGroup() as group:
            group.create_task(receive_loop())
            group.create_task(heartbeat_loop())
            group.create_task(relay_loop())
    except* WebSocketDisconnect:
        pass
    except* TimeoutError:
        pass
    except* Exception:
        logger.exception("notifications_socket_failed")
    finally:
        broadcaster.unsubscribe(queue)
        _active_connections -= 1
        try:
            await websocket.close()
        except Exception:
            pass
