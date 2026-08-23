from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from cataloging_api.db.base import Base


RUN_RUNNING = "RUNNING"
RUN_INTERRUPTED = "INTERRUPTED"
RUN_FAILED = "FAILED"
RUN_COMPLETE = "COMPLETE"


class DSpaceContractSyncRun(Base):
    __tablename__ = "dspace_contract_sync_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    collector_version: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(20), default=RUN_RUNNING, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_surface: Mapped[str | None] = mapped_column(String(80))
    checkpoints: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    pages_completed: Mapped[int] = mapped_column(Integer, default=0)
    raw_payload_hashes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(String(500))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DSpaceContractRawPage(Base):
    __tablename__ = "dspace_contract_raw_pages"
    __table_args__ = (
        UniqueConstraint(
            "run_id", "surface", "page_number", name="uq_dspace_contract_raw_page"
        ),
        Index("ix_dspace_contract_raw_pages_run_surface", "run_id", "surface"),
    )

    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dspace_contract_sync_runs.run_id", ondelete="CASCADE"), index=True
    )
    surface: Mapped[str] = mapped_column(String(80))
    page_number: Mapped[int] = mapped_column(Integer)
    request_params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    raw_hash: Mapped[str] = mapped_column(String(64), index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


def canonical_raw_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def checkpoint_next_page(run: DSpaceContractSyncRun, surface: str) -> int:
    return int((run.checkpoints or {}).get(surface, 0))


async def create_sync_run(
    session: AsyncSession,
    *,
    collector_version: str,
) -> DSpaceContractSyncRun:
    run = DSpaceContractSyncRun(
        collector_version=collector_version,
        status=RUN_RUNNING,
        checkpoints={},
        raw_payload_hashes=[],
    )
    session.add(run)
    await session.flush()
    return run


async def find_resumable_run(
    session: AsyncSession,
    *,
    collector_version: str,
) -> DSpaceContractSyncRun | None:
    result = await session.execute(
        select(DSpaceContractSyncRun)
        .where(
            DSpaceContractSyncRun.collector_version == collector_version,
            DSpaceContractSyncRun.status.in_([RUN_RUNNING, RUN_INTERRUPTED]),
        )
        .order_by(DSpaceContractSyncRun.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def persist_page_and_advance_checkpoint(
    session: AsyncSession,
    *,
    run: DSpaceContractSyncRun,
    surface: str,
    page_number: int,
    request_params: dict[str, Any],
    raw_payload: dict[str, Any],
) -> DSpaceContractRawPage:
    """Persist evidence before advancing the checkpoint.

    Retrying the same ``run_id + surface + page_number`` is idempotent when the raw
    hash is identical. A different payload for the same key is an evidence conflict
    and is never overwritten.
    """

    raw_hash = canonical_raw_hash(raw_payload)
    result = await session.execute(
        select(DSpaceContractRawPage).where(
            DSpaceContractRawPage.run_id == run.run_id,
            DSpaceContractRawPage.surface == surface,
            DSpaceContractRawPage.page_number == page_number,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if existing.raw_hash != raw_hash:
            raise ValueError("contract_raw_page_conflict")
        page = existing
    else:
        page = DSpaceContractRawPage(
            run_id=run.run_id,
            surface=surface,
            page_number=page_number,
            request_params=request_params,
            raw_payload=raw_payload,
            raw_hash=raw_hash,
        )
        session.add(page)
        await session.flush()
        run.pages_completed += 1
        hashes = list(run.raw_payload_hashes or [])
        hashes.append(raw_hash)
        run.raw_payload_hashes = hashes

    checkpoints = dict(run.checkpoints or {})
    checkpoints[surface] = max(int(checkpoints.get(surface, 0)), page_number + 1)
    run.checkpoints = checkpoints
    run.current_surface = surface
    await session.flush()
    return page


async def mark_run_interrupted(
    session: AsyncSession,
    *,
    run: DSpaceContractSyncRun,
    error_code: str,
    error_message: str,
) -> None:
    run.status = RUN_INTERRUPTED
    run.error_code = error_code
    run.error_message = error_message[:500]
    run.failed_at = func.now()
    await session.flush()


async def mark_run_failed(
    session: AsyncSession,
    *,
    run: DSpaceContractSyncRun,
    error_code: str,
    error_message: str,
) -> None:
    run.status = RUN_FAILED
    run.error_code = error_code
    run.error_message = error_message[:500]
    run.failed_at = func.now()
    await session.flush()


async def mark_run_complete(session: AsyncSession, *, run: DSpaceContractSyncRun) -> None:
    run.status = RUN_COMPLETE
    run.completed_at = func.now()
    run.error_code = None
    run.error_message = None
    await session.flush()
