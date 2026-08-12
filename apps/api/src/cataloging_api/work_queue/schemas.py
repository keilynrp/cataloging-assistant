import uuid
from datetime import datetime

from pydantic import BaseModel


class WorkQueueSummaryOut(BaseModel):
    active_items: int
    attention_items: int
    items_with_findings: int
    pending_review_items: int
    reviewed_items: int
    items_with_draft: int
    stale_draft_items: int
    open_draft_items: int
    approved_draft_items: int
    rejected_draft_items: int
    superseded_draft_items: int
    items_with_pending_suggestions: int
    pending_suggestions: int


class WorkQueueItemOut(BaseModel):
    uuid: uuid.UUID
    handle: str | None
    name: str
    last_modified: datetime | None
    finding_count: int
    pending_finding_count: int
    deferred_finding_count: int
    pending_suggestion_count: int
    finding_codes: list[str]
    highest_severity: str | None
    has_draft: bool
    draft_stale: bool
    latest_draft_version: int | None
    priority: str
    draft_state: str | None


class WorkQueueOut(BaseModel):
    collection_uuid: uuid.UUID
    collection_name: str
    generated_at: datetime
    source: str
    grain: str
    latest_sync_status: str | None
    latest_sync_finished_at: datetime | None
    available_finding_codes: list[str]
    summary: WorkQueueSummaryOut
    items: list[WorkQueueItemOut]
    page: int
    size: int
    total: int
