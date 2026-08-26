from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from cataloging_api.db.base import Base
from cataloging_api.dspace.contract_snapshot import ContractChange, ContractSnapshotView


class DSpaceContractSnapshot(Base):
    __tablename__ = "dspace_contract_snapshots"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_dspace_contract_snapshot_run"),
        Index("ix_dspace_contract_snapshots_status_created", "status", "created_at"),
        Index(
            "uq_dspace_contract_single_active",
            "status",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_contract_sync_runs.run_id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="OBSERVED", index=True)
    semantic_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    canonical_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_note: Mapped[str | None] = mapped_column(Text)
    approved_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class DSpaceContractChangeRecord(Base):
    __tablename__ = "dspace_contract_changes"
    __table_args__ = (
        Index("ix_dspace_contract_changes_snapshot_type", "snapshot_id", "change_type"),
    )

    change_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_contract_snapshots.snapshot_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    change_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    identity: Mapped[str] = mapped_column(Text, nullable=False)
    before_json: Mapped[Any | None] = mapped_column(JSONB)
    after_json: Mapped[Any | None] = mapped_column(JSONB)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


async def persist_snapshot(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
    snapshot: ContractSnapshotView,
    status: str,
    changes: list[ContractChange] | None = None,
) -> DSpaceContractSnapshot:
    """Persist immutable snapshot content while leaving governance status mutable."""

    result = await session.execute(
        select(DSpaceContractSnapshot).where(DSpaceContractSnapshot.run_id == run_id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if existing.semantic_hash != snapshot.semantic_hash:
            raise ValueError("contract_snapshot_conflict")
        return existing

    record = DSpaceContractSnapshot(
        run_id=run_id,
        status=status,
        semantic_hash=snapshot.semantic_hash,
        complete=snapshot.complete,
        canonical_json=snapshot.canonical,
        warnings=list(snapshot.warnings),
    )
    session.add(record)
    await session.flush()

    for change in changes or []:
        session.add(
            DSpaceContractChangeRecord(
                snapshot_id=record.snapshot_id,
                change_type=change.change_type,
                severity=change.severity,
                identity=change.identity,
                before_json=change.before,
                after_json=change.after,
            )
        )
    await session.flush()
    return record
