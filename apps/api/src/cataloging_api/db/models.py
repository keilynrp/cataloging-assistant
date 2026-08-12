from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cataloging_api.db.base import Base


class SyncStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    partial = "partial"
    failed = "failed"


class ReviewDecisionKind(enum.StrEnum):
    confirmed = "confirmed"
    dismissed = "dismissed"
    deferred = "deferred"


class DraftStatus(enum.StrEnum):
    open = "open"


class DraftRevisionDecisionKind(enum.StrEnum):
    approved = "approved"
    rejected = "rejected"


class SuggestionDecisionKind(enum.StrEnum):
    accepted = "accepted"
    corrected = "corrected"
    rejected = "rejected"
    deferred = "deferred"


class NotificationSeverity(enum.StrEnum):
    info = "info"
    warning = "warning"
    error = "error"


class NotificationDeliveryState(enum.StrEnum):
    unread = "unread"
    read = "read"
    archived = "archived"


class DSpaceCollection(Base):
    __tablename__ = "dspace_collections"

    uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    handle: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(Text)
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list[DSpaceItem]] = relationship(back_populates="collection")


class DSpaceItem(Base):
    __tablename__ = "dspace_items"

    uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    collection_uuid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_collections.uuid"), index=True
    )
    handle: Mapped[str | None] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(Text, index=True)
    last_modified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    diagnostic_source_hash: Mapped[str | None] = mapped_column(String(64))
    diagnostic_profile_version: Mapped[str | None] = mapped_column(String(64))
    diagnosed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    collection: Mapped[DSpaceCollection] = relationship(back_populates="items")
    metadata_values: Mapped[list[DSpaceMetadataValue]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="DSpaceMetadataValue.place"
    )
    review_decisions: Mapped[list[CatalogReviewDecision]] = relationship(
        back_populates="item", order_by="CatalogReviewDecision.created_at"
    )
    drafts: Mapped[list[CatalogDraft]] = relationship(
        back_populates="item", order_by="CatalogDraft.created_at"
    )
    bundles: Mapped[list[DSpaceBundle]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    findings: Mapped[list[CatalogFinding]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list[CatalogSuggestion]] = relationship(
        back_populates="item", order_by="CatalogSuggestion.created_at"
    )


class DSpaceMetadataValue(Base):
    __tablename__ = "dspace_metadata"
    __table_args__ = (
        UniqueConstraint("item_uuid", "field", "place", name="uq_metadata_item_field_place"),
        Index("ix_metadata_field_value", "field", "value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_uuid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_items.uuid", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(64))
    authority: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[int | None] = mapped_column(Integer)
    place: Mapped[int] = mapped_column(Integer)

    item: Mapped[DSpaceItem] = relationship(back_populates="metadata_values")


class DSpaceBundle(Base):
    __tablename__ = "dspace_bundles"

    uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    item_uuid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_items.uuid", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)

    item: Mapped[DSpaceItem] = relationship(back_populates="bundles")
    bitstreams: Mapped[list[DSpaceBitstream]] = relationship(
        back_populates="bundle", cascade="all, delete-orphan"
    )


class DSpaceBitstream(Base):
    __tablename__ = "dspace_bitstreams"

    uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    bundle_uuid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_bundles.uuid", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(255), index=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    content_url: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)

    bundle: Mapped[DSpaceBundle] = relationship(back_populates="bitstreams")


class CatalogFinding(Base):
    __tablename__ = "catalog_findings"
    __table_args__ = (
        UniqueConstraint("item_uuid", "fingerprint", name="uq_finding_item_fingerprint"),
        Index("ix_catalog_findings_code_severity", "code", "severity"),
    )

    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_uuid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_items.uuid", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(30), index=True)
    affected_fields: Mapped[list[str]] = mapped_column(JSONB)
    explanation: Mapped[str] = mapped_column(Text)
    fingerprint: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[str] = mapped_column(String(64))
    source_hash: Mapped[str] = mapped_column(String(64))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    item: Mapped[DSpaceItem] = relationship(back_populates="findings")


class CatalogReviewDecision(Base):
    __tablename__ = "catalog_review_decisions"
    __table_args__ = (
        Index("ix_review_decisions_item_created", "item_uuid", "created_at"),
        Index("ix_review_decisions_fingerprint", "item_uuid", "finding_fingerprint"),
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    item_uuid: Mapped[uuid.UUID] = mapped_column(ForeignKey("dspace_items.uuid"), index=True)
    finding_fingerprint: Mapped[str] = mapped_column(String(64))
    finding_code: Mapped[str] = mapped_column(String(100), index=True)
    finding_severity: Mapped[str] = mapped_column(String(30))
    finding_affected_fields: Mapped[list[str]] = mapped_column(JSONB)
    finding_explanation: Mapped[str] = mapped_column(Text)
    finding_rule_version: Mapped[str] = mapped_column(String(64))
    source_hash: Mapped[str] = mapped_column(String(64))
    decision: Mapped[ReviewDecisionKind] = mapped_column(
        Enum(ReviewDecisionKind, name="review_decision_kind"), index=True
    )
    reviewer: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    item: Mapped[DSpaceItem] = relationship(back_populates="review_decisions")


class CatalogSuggestion(Base):
    __tablename__ = "catalog_suggestions"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_catalog_suggestions_fingerprint"),
        Index("ix_catalog_suggestions_item_created", "item_uuid", "created_at"),
    )

    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_uuid: Mapped[uuid.UUID] = mapped_column(ForeignKey("dspace_items.uuid"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    source_hash: Mapped[str] = mapped_column(String(64), index=True)
    field: Mapped[str] = mapped_column(String(255), index=True)
    proposed_value: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    method: Mapped[str] = mapped_column(String(100))
    method_version: Mapped[str] = mapped_column(String(64))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    item: Mapped[DSpaceItem] = relationship(back_populates="suggestions")


class CatalogSuggestionDecision(Base):
    __tablename__ = "catalog_suggestion_decisions"

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_suggestions.suggestion_id"), index=True
    )
    item_uuid: Mapped[uuid.UUID] = mapped_column(ForeignKey("dspace_items.uuid"), index=True)
    decision: Mapped[SuggestionDecisionKind] = mapped_column(
        Enum(SuggestionDecisionKind, name="suggestion_decision_kind"), index=True
    )
    corrected_value: Mapped[str | None] = mapped_column(Text)
    reviewer: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text)
    suggestion_source_hash: Mapped[str] = mapped_column(String(64))
    current_source_hash: Mapped[str] = mapped_column(String(64))
    source_stale: Mapped[bool] = mapped_column(Boolean)
    draft_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("catalog_draft_revisions.revision_id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class CatalogDraft(Base):
    __tablename__ = "catalog_drafts"
    __table_args__ = (
        UniqueConstraint("item_uuid", name="uq_catalog_drafts_item_uuid"),
        Index("ix_catalog_drafts_status_updated", "status", "updated_at"),
    )

    draft_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_uuid: Mapped[uuid.UUID] = mapped_column(ForeignKey("dspace_items.uuid"), index=True)
    base_source_hash: Mapped[str] = mapped_column(String(64), index=True)
    base_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[DraftStatus] = mapped_column(
        Enum(DraftStatus, name="draft_status"), default=DraftStatus.open, index=True
    )
    created_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    item: Mapped[DSpaceItem] = relationship(back_populates="drafts")
    revisions: Mapped[list[CatalogDraftRevision]] = relationship(
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="CatalogDraftRevision.version",
    )


class CatalogDraftRevision(Base):
    __tablename__ = "catalog_draft_revisions"
    __table_args__ = (
        UniqueConstraint("draft_id", "version", name="uq_draft_revision_version"),
        Index("ix_draft_revisions_draft_created", "draft_id", "created_at"),
    )

    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_drafts.draft_id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    metadata_patch: Mapped[dict[str, Any]] = mapped_column(JSONB)
    validation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    author: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    draft: Mapped[CatalogDraft] = relationship(back_populates="revisions")
    decisions: Mapped[list[CatalogDraftRevisionDecision]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
        order_by="CatalogDraftRevisionDecision.created_at",
        lazy="selectin",
    )


class CatalogDraftRevisionDecision(Base):
    __tablename__ = "catalog_draft_revision_decisions"
    __table_args__ = (
        Index("ix_draft_revision_decisions_revision_created", "revision_id", "created_at"),
        Index("ix_draft_revision_decisions_item_created", "item_uuid", "created_at"),
    )

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    draft_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_drafts.draft_id", ondelete="CASCADE"), index=True
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_draft_revisions.revision_id", ondelete="CASCADE"), index=True
    )
    item_uuid: Mapped[uuid.UUID] = mapped_column(ForeignKey("dspace_items.uuid"), index=True)
    decision: Mapped[DraftRevisionDecisionKind] = mapped_column(
        Enum(DraftRevisionDecisionKind, name="draft_revision_decision_kind"), index=True
    )
    reviewer: Mapped[str] = mapped_column(String(120))
    note: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))
    validation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    validation_override: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    revision: Mapped[CatalogDraftRevision] = relationship(back_populates="decisions")


class CatalogVocabularyRevision(Base):
    __tablename__ = "catalog_vocabulary_revisions"
    __table_args__ = (
        Index(
            "ix_catalog_vocabulary_revisions_active_created",
            "is_active",
            "created_at",
        ),
    )

    revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, index=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    field: Mapped[str] = mapped_column(String(255), index=True)
    name: Mapped[str] = mapped_column(Text)
    source_uri: Mapped[str] = mapped_column(Text)
    version_label: Mapped[str] = mapped_column(String(120))
    approved_by: Mapped[str] = mapped_column(String(120))
    approval_note: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    terms: Mapped[list[CatalogControlledTerm]] = relationship(
        back_populates="revision",
        cascade="all, delete-orphan",
        order_by="CatalogControlledTerm.position",
    )


class CatalogControlledTerm(Base):
    __tablename__ = "catalog_controlled_terms"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "normalized_value",
            name="uq_catalog_term_revision_normalized",
        ),
        UniqueConstraint(
            "revision_id",
            "position",
            name="uq_catalog_term_revision_position",
        ),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    revision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_vocabulary_revisions.revision_id", ondelete="CASCADE"),
        index=True,
    )
    value: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str] = mapped_column(Text, index=True)
    authority: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(64))
    position: Mapped[int] = mapped_column(Integer)

    revision: Mapped[CatalogVocabularyRevision] = relationship(back_populates="terms")


class DSpaceVocabulary(Base):
    __tablename__ = "dspace_vocabularies"
    vocabulary_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    hierarchical: Mapped[bool] = mapped_column(Boolean)
    scrollable: Mapped[bool] = mapped_column(Boolean)
    source_uri: Mapped[str] = mapped_column(Text)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_hash: Mapped[str] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    entries: Mapped[list[DSpaceVocabularyEntry]] = relationship(
        back_populates="vocabulary", cascade="all, delete-orphan"
    )


class DSpaceVocabularyEntry(Base):
    __tablename__ = "dspace_vocabulary_entries"
    __table_args__ = (
        UniqueConstraint("vocabulary_id", "entry_id", name="uq_dspace_vocabulary_entry"),
        Index("ix_dspace_vocabulary_entries_value", "vocabulary_id", "value"),
    )
    row_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vocabulary_id: Mapped[str] = mapped_column(
        ForeignKey("dspace_vocabularies.vocabulary_id", ondelete="CASCADE"), index=True
    )
    entry_id: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    display: Mapped[str | None] = mapped_column(Text)
    selectable: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_id: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_hash: Mapped[str] = mapped_column(String(64))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vocabulary: Mapped[DSpaceVocabulary] = relationship(back_populates="entries")


class SyncRun(Base):
    __tablename__ = "sync_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collection_uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status"), default=SyncStatus.queued, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkpoint_page: Mapped[int] = mapped_column(Integer, default=0)
    pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_seen: Mapped[int] = mapped_column(Integer, default=0)
    items_changed: Mapped[int] = mapped_column(Integer, default=0)
    retries: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_detail: Mapped[str | None] = mapped_column(Text)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        Index("ix_notification_events_collection_occurred", "collection_uuid", "occurred_at"),
        Index("ix_notification_events_type_occurred", "event_type", "occurred_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    aggregate_type: Mapped[str] = mapped_column(String(50))
    aggregate_id: Mapped[str] = mapped_column(String(255))
    collection_uuid: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, name="notification_severity")
    )
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    target_path: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    deduplication_key: Mapped[str] = mapped_column(String(255), unique=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        Index(
            "ix_notification_outbox_pending",
            "available_at",
            postgresql_where=text("published_at is null"),
        ),
    )

    outbox_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notification_events.event_id", ondelete="CASCADE"), unique=True
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "recipient_id", name="uq_notification_delivery_event_recipient"
        ),
        Index(
            "ix_notification_deliveries_recipient_state_delivered",
            "recipient_id",
            "state",
            "delivered_at",
        ),
    )

    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notification_events.event_id", ondelete="CASCADE"), index=True
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    state: Mapped[NotificationDeliveryState] = mapped_column(
        Enum(NotificationDeliveryState, name="notification_delivery_state"),
        default=NotificationDeliveryState.unread,
        index=True,
    )
    delivery_seq: Mapped[int] = mapped_column(BigInteger, Identity(always=False), unique=True)
    delivered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    event: Mapped[NotificationEvent] = relationship()
