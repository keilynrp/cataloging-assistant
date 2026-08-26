from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.dspace.contract_snapshot import (
    ContractChange,
    ContractSnapshotView,
    build_contract_snapshot,
    diff_contract_snapshots,
)
from cataloging_api.dspace.contract_snapshot_store import (
    DSpaceContractSnapshot,
    persist_snapshot,
)
from cataloging_api.dspace.contract_store import (
    DSpaceContractRawPage,
    DSpaceContractSyncRun,
    RUN_COMPLETE,
)


async def _load_pages_by_surface(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
) -> dict[str, list[dict]]:
    result = await session.execute(
        select(DSpaceContractRawPage)
        .where(DSpaceContractRawPage.run_id == run_id)
        .order_by(DSpaceContractRawPage.surface, DSpaceContractRawPage.page_number)
    )
    grouped: dict[str, list[dict]] = defaultdict(list)
    for page in result.scalars().all():
        grouped[page.surface].append(page.raw_payload)
    return dict(grouped)


async def _active_snapshot(session: AsyncSession) -> DSpaceContractSnapshot | None:
    result = await session.execute(
        select(DSpaceContractSnapshot)
        .where(DSpaceContractSnapshot.status == "ACTIVE")
        .order_by(DSpaceContractSnapshot.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _as_view(record: DSpaceContractSnapshot) -> ContractSnapshotView:
    return ContractSnapshotView(
        canonical=record.canonical_json,
        semantic_hash=record.semantic_hash,
        complete=record.complete,
        warnings=tuple(record.warnings or []),
    )


def classify_snapshot_status(
    active: DSpaceContractSnapshot | None,
    current: ContractSnapshotView,
    changes: list[ContractChange],
) -> str:
    if active is None:
        return "BASELINE_REVIEW_REQUIRED" if current.complete else "REVIEW_REQUIRED"
    if not current.complete:
        return "REVIEW_REQUIRED"
    if current.semantic_hash == active.semantic_hash:
        return "NO_CHANGE"
    if any(change.severity in {"HIGH", "CRITICAL"} for change in changes):
        return "REVIEW_REQUIRED"
    return "DIFF_DETECTED"


async def materialize_snapshot_for_run(
    session: AsyncSession,
    *,
    run_id: uuid.UUID,
) -> DSpaceContractSnapshot:
    """Build and persist one governed snapshot from an immutable COMPLETE run.

    This function never promotes a snapshot to ACTIVE. Only a complete first
    observation can become BASELINE_REVIEW_REQUIRED.
    """

    run = await session.get(DSpaceContractSyncRun, run_id)
    if run is None:
        raise ValueError("contract_sync_run_not_found")
    if run.status != RUN_COMPLETE:
        raise ValueError("contract_sync_run_not_complete")

    pages_by_surface = await _load_pages_by_surface(session, run_id=run_id)
    current = build_contract_snapshot(pages_by_surface)
    active = await _active_snapshot(session)
    changes = [] if active is None else diff_contract_snapshots(_as_view(active), current)
    status = classify_snapshot_status(active, current, changes)

    record = await persist_snapshot(
        session,
        run_id=run_id,
        snapshot=current,
        status=status,
        changes=changes,
    )
    await session.commit()
    return record
