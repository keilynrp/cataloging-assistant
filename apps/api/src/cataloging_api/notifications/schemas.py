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
