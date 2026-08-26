from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.dspace.contract_governance import governed_canonical, governed_hash
from cataloging_api.dspace.contract_inheritance import (
    apply_inherited_resolution,
    build_inherited_effective_snapshot,
)
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
        canonical=governed_canonical(record),
        semantic_hash=governed_hash(record),
        complete=True if record.effective_hash else record.complete,
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
    if current.semantic_hash == governed_hash(active):
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

    A previously human-approved 204 resolution may be inherited only when the
    new run independently reproduces the exact approved schemas, registry and
    submission-form bindings. Inheritance never changes the observed snapshot
    and never promotes a new baseline.
    """

    run = await session.get(DSpaceContractSyncRun, run_id)
    if run is None:
        raise ValueError("contract_sync_run_not_found")
    if run.status != RUN_COMPLETE:
        raise ValueError("contract_sync_run_not_complete")

    pages_by_surface = await _load_pages_by_surface(session, run_id=run_id)
    observed = build_contract_snapshot(pages_by_surface)
    active = await _active_snapshot(session)

    inherited: ContractSnapshotView | None = None
    comparison = observed
    if active is not None and not observed.complete:
        inherited = build_inherited_effective_snapshot(
            active=active,
            observed=observed,
            pages_by_surface=pages_by_surface,
        )
        if inherited is not None:
            comparison = inherited

    changes = [] if active is None else diff_contract_snapshots(_as_view(active), comparison)
    status = classify_snapshot_status(active, comparison, changes)

    # Persist the immutable REST observation, not the synthesized effective view.
    record = await persist_snapshot(
        session,
        run_id=run_id,
        snapshot=observed,
        status=status,
        changes=changes,
    )
    if inherited is not None and active is not None:
        apply_inherited_resolution(record=record, active=active, inherited=inherited)
        await session.flush()

    await session.commit()
    return record
