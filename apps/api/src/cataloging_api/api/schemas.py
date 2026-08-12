import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MetadataValueOut(BaseModel):
    value: str
    language: str | None
    authority: str | None
    confidence: int | None
    place: int


class BitstreamOut(BaseModel):
    uuid: uuid.UUID
    name: str
    mime_type: str | None
    size_bytes: int | None
    content_url: str | None


class BundleOut(BaseModel):
    uuid: uuid.UUID
    name: str
    bitstreams: list[BitstreamOut]


class ItemSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid.UUID
    handle: str | None
    name: str
    collection_uuid: uuid.UUID
    last_modified: datetime | None
    is_active: bool


class ItemListOut(BaseModel):
    items: list[ItemSummaryOut]
    page: int
    size: int
    total: int


class CatalogFindingOut(BaseModel):
    finding_id: uuid.UUID
    fingerprint: str
    code: str
    severity: str
    affected_fields: list[str]
    explanation: str
    rule_version: str
    detected_at: datetime


class DiagnosticsOut(BaseModel):
    status: str
    profile_version: str | None
    evaluated_at: datetime | None
    findings: list[CatalogFindingOut]


class ReviewDecisionCreate(BaseModel):
    request_id: uuid.UUID
    decision: Literal["confirmed", "dismissed", "deferred"]
    reviewer: str = Field(min_length=2, max_length=120)
    note: str = Field(min_length=1, max_length=2000)


class ReviewDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: uuid.UUID
    request_id: uuid.UUID
    item_uuid: uuid.UUID
    finding_fingerprint: str
    finding_code: str
    finding_severity: str
    finding_affected_fields: list[str]
    finding_explanation: str
    finding_rule_version: str
    source_hash: str
    decision: str
    reviewer: str
    note: str
    created_at: datetime


class DraftCreate(BaseModel):
    request_id: uuid.UUID
    author: str = Field(min_length=2, max_length=120)
    note: str = Field(min_length=1, max_length=2000)
    changes: dict[str, list[str]]


class DraftRevisionCreate(DraftCreate):
    expected_version: int = Field(ge=1)


class DraftRevisionDecisionCreate(BaseModel):
    request_id: uuid.UUID
    revision_id: uuid.UUID
    decision: Literal["approved", "rejected"]
    reviewer: str = Field(min_length=2, max_length=120)
    note: str = Field(min_length=1, max_length=2000)
    validation_override: bool = False


class DraftRevisionDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    decision_id: uuid.UUID
    request_id: uuid.UUID
    revision_id: uuid.UUID
    decision: str
    reviewer: str
    note: str
    source_hash: str
    validation_snapshot: dict[str, Any]
    validation_override: bool
    created_at: datetime


class DraftRevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    revision_id: uuid.UUID
    request_id: uuid.UUID
    version: int
    metadata_patch: dict[str, list[MetadataValueOut]]
    validation_snapshot: dict[str, Any]
    author: str
    note: str
    created_at: datetime
    decisions: list[DraftRevisionDecisionOut]


class CatalogDraftOut(BaseModel):
    draft_id: uuid.UUID
    item_uuid: uuid.UUID
    base_source_hash: str
    base_metadata: dict[str, list[MetadataValueOut]]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    stale: bool
    revisions: list[DraftRevisionOut]


class ItemDetailOut(ItemSummaryOut):
    metadata: dict[str, list[MetadataValueOut]]
    bundles: list[BundleOut]
    raw_json: dict[str, object]
    diagnostics: DiagnosticsOut
    review_decisions: list[ReviewDecisionOut]
    drafts: list[CatalogDraftOut]


class SimilarityEvidenceOut(BaseModel):
    kind: str
    field: str | None
    values: list[str]
    contribution: float


class SimilarItemOut(BaseModel):
    uuid: uuid.UUID
    handle: str | None
    name: str
    score: float
    evidence: list[SimilarityEvidenceOut]


class SimilarItemsOut(BaseModel):
    source_uuid: uuid.UUID
    method: str
    candidates_evaluated: int
    truncated: bool
    items: list[SimilarItemOut]


class CatalogSuggestionOut(BaseModel):
    field: str
    value: str
    confidence: float
    supporting_item_uuids: list[uuid.UUID]
    explanation: str


class CatalogSuggestionsOut(BaseModel):
    item_uuid: uuid.UUID
    method: str
    suggestions: list[CatalogSuggestionOut]


class PersistedSuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    suggestion_id: uuid.UUID
    item_uuid: uuid.UUID
    field: str
    proposed_value: str
    confidence: float
    method: str
    method_version: str
    created_at: datetime


class PersistedSuggestionsOut(BaseModel):
    item_uuid: uuid.UUID
    suggestions: list[PersistedSuggestionOut]


class SuggestionDecisionCreate(BaseModel):
    request_id: uuid.UUID
    decision: Literal["accepted", "corrected", "rejected", "deferred"]
    corrected_value: str | None = Field(default=None, max_length=20000)
    reviewer: str = Field(min_length=2, max_length=120)
    note: str = Field(min_length=1, max_length=2000)


class SuggestionDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    decision_id: uuid.UUID
    request_id: uuid.UUID
    suggestion_id: uuid.UUID
    item_uuid: uuid.UUID
    decision: str
    corrected_value: str | None
    reviewer: str
    note: str
    suggestion_source_hash: str
    current_source_hash: str
    source_stale: bool
    draft_revision_id: uuid.UUID | None
    created_at: datetime


class SuggestionHistoryEntryOut(BaseModel):
    suggestion_id: uuid.UUID
    fingerprint: str
    source_hash: str
    source_stale: bool
    field: str
    proposed_value: str
    confidence: float
    method: str
    method_version: str
    explanation: str
    evidence: dict[str, Any]
    created_at: datetime
    decisions: list[SuggestionDecisionOut]


class SuggestionHistoryOut(BaseModel):
    item_uuid: uuid.UUID
    entries: list[SuggestionHistoryEntryOut]


class SyncRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: uuid.UUID
    collection_uuid: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    checkpoint_page: int
    pages_processed: int
    items_seen: int
    items_changed: int
    error_code: str | None
