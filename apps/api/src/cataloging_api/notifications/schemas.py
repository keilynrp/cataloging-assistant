import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class NotificationOut(BaseModel):
    notification_id: uuid.UUID
    event_type: str
    severity: Literal["info", "warning", "error"]
    title: str
    summary: str
    target_path: str | None
    state: Literal["unread", "read", "archived"]
    occurred_at: datetime


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    next_cursor: str | None
    unread_count: int


class UnreadCountOut(BaseModel):
    unread_count: int


class NotificationActionOut(BaseModel):
    notification_id: uuid.UUID
    state: Literal["unread", "read", "archived"]


class MarkAllReadOut(BaseModel):
    updated: int
    unread_count: int


class PreferenceOut(BaseModel):
    event_type: str
    muted: bool


class PreferenceListOut(BaseModel):
    preferences: list[PreferenceOut]


class PreferenceUpdate(BaseModel):
    muted: bool
    actor: str = "Referente catalográfico"


class MetricsOut(BaseModel):
    events_by_type: dict[str, int]
    deliveries_by_state: dict[str, int]
    outbox_pending: int
    outbox_oldest_pending_age_seconds: float | None
    outbox_total_attempts: int
    active_connections: int
    total_connections_accepted: int
    total_connections_rejected: int
