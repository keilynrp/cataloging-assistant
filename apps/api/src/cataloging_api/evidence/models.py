from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from cataloging_api.db.base import Base


class CatalogEvidenceSession(Base):
    __tablename__ = "catalog_evidence_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    item_uuid: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dspace_items.uuid", ondelete="SET NULL"), index=True
    )
    base_source_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    contract_version: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CatalogEvidenceSource(Base):
    __tablename__ = "catalog_evidence_sources"
    __table_args__ = (
        Index("ix_evidence_sources_session_created", "session_id", "created_at"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_evidence_sessions.session_id", ondelete="CASCADE"),
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(30))
    locator: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    media_type: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CatalogEvidenceCandidate(Base):
    __tablename__ = "catalog_evidence_candidates"
    __table_args__ = (
        Index("ix_evidence_candidates_session_field", "session_id", "metadata_field"),
    )

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_evidence_sessions.session_id", ondelete="CASCADE"),
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("catalog_evidence_sources.source_id", ondelete="CASCADE"),
        index=True,
    )
    binding_id: Mapped[str] = mapped_column(String(120), index=True)
    metadata_field: Mapped[str] = mapped_column(String(255), index=True)
    value: Mapped[str] = mapped_column(Text)
    evidence_state: Mapped[str] = mapped_column(String(30), index=True)
    evidence_json: Mapped[dict[str, object]] = mapped_column(JSONB)
    validation_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
