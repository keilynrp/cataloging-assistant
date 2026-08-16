from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EvidenceSessionCreate(BaseModel):
    item_uuid: uuid.UUID | None = None
    created_by: str = Field(min_length=2, max_length=120)
    url: str | None = Field(default=None, max_length=4000)
    text: str | None = None


class EvidenceSourceOut(BaseModel):
    source_id: uuid.UUID
    kind: str
    locator: str | None
    content_hash: str
    media_type: str | None
    metadata_json: dict[str, object]
    created_at: datetime


class EvidenceCandidateOut(BaseModel):
    candidate_id: uuid.UUID
    source_id: uuid.UUID
    metadata_field: str
    value: str
    evidence_state: str
    evidence_json: dict[str, object]
    validation_json: dict[str, object]
    created_at: datetime


class EvidenceSessionOut(BaseModel):
    session_id: uuid.UUID
    item_uuid: uuid.UUID | None
    base_source_hash: str | None
    contract_version: str
    created_by: str
    created_at: datetime
    stale: bool
    sources: list[EvidenceSourceOut]
    candidates: list[EvidenceCandidateOut]


class EvidenceCopyToDraft(BaseModel):
    request_id: uuid.UUID
    candidate_ids: list[uuid.UUID] = Field(min_length=1, max_length=20)
    author: str = Field(min_length=2, max_length=120)
    note: str = Field(min_length=1, max_length=2000)
    draft_id: uuid.UUID | None = None
    expected_version: int | None = Field(default=None, ge=1)


class EvidenceCopyResult(BaseModel):
    draft_id: uuid.UUID
    revision_id: uuid.UUID
    version: int
    item_uuid: uuid.UUID
