from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.dspace.contract_snapshot_store import DSpaceContractSnapshot


class ContractGovernanceError(ValueError):
    pass


@dataclass(frozen=True)
class ContractHealth:
    status: str
    active_snapshot_id: uuid.UUID | None
    active_hash: str | None
    latest_snapshot_id: uuid.UUID | None
    latest_status: str | None
    last_verified_at: datetime | None
    metadata_field_count: int | None
    form_binding_count: int | None
    warning_count: int


def derive_contract_health(
    *,
    active: DSpaceContractSnapshot | None,
    latest: DSpaceContractSnapshot | None,
) -> ContractHealth:
    if active is None:
        operational = "BASELINE_REQUIRED"
    elif latest is None or latest.snapshot_id == active.snapshot_id:
        operational = "SYNCED"
    elif latest.status == "REVIEW_REQUIRED":
        operational = "REVIEW_REQUIRED"
    elif latest.status == "DIFF_DETECTED":
        operational = "DRIFT_DETECTED"
    elif latest.status == "NO_CHANGE":
        operational = "SYNCED"
    else:
        operational = "SYNCED"

    canonical = (active.canonical_json if active is not None else None) or {}
    return ContractHealth(
        status=operational,
        active_snapshot_id=active.snapshot_id if active is not None else None,
        active_hash=active.semantic_hash if active is not None else None,
        latest_snapshot_id=latest.snapshot_id if latest is not None else None,
        latest_status=latest.status if latest is not None else None,
        last_verified_at=latest.created_at if latest is not None else None,
        metadata_field_count=(len(canonical.get("fields", [])) if active is not None else None),
        form_binding_count=(len(canonical.get("bindings", [])) if active is not None else None),
        warning_count=len((latest.warnings if latest is not None else None) or []),
    )


async def get_contract_health(session: AsyncSession) -> ContractHealth:
    active_result = await session.execute(
        select(DSpaceContractSnapshot)
        .where(DSpaceContractSnapshot.status == "ACTIVE")
        .order_by(DSpaceContractSnapshot.created_at.desc())
        .limit(1)
    )
    active = active_result.scalar_one_or_none()

    latest_result = await session.execute(
        select(DSpaceContractSnapshot)
        .order_by(DSpaceContractSnapshot.created_at.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()
    return derive_contract_health(active=active, latest=latest)


async def approve_snapshot(
    session: AsyncSession,
    *,
    snapshot_id: uuid.UUID,
    expected_hash: str,
    approved_by: str,
    approval_note: str | None = None,
) -> DSpaceContractSnapshot:
    candidate_result = await session.execute(
        select(DSpaceContractSnapshot)
        .where(DSpaceContractSnapshot.snapshot_id == snapshot_id)
        .with_for_update()
    )
    candidate = candidate_result.scalar_one_or_none()
    if candidate is None:
        raise ContractGovernanceError("snapshot_not_found")
    if candidate.semantic_hash != expected_hash:
        raise ContractGovernanceError("snapshot_hash_mismatch")
    if not candidate.complete:
        raise ContractGovernanceError("incomplete_snapshot_cannot_be_approved")

    active_result = await session.execute(
        select(DSpaceContractSnapshot)
        .where(DSpaceContractSnapshot.status == "ACTIVE")
        .with_for_update()
    )
    active = active_result.scalar_one_or_none()

    if candidate.status == "ACTIVE":
        if candidate.approved_hash != expected_hash:
            raise ContractGovernanceError("active_snapshot_audit_mismatch")
        return candidate

    if active is None:
        if candidate.status != "BASELINE_REVIEW_REQUIRED":
            raise ContractGovernanceError("baseline_candidate_required")
    else:
        if candidate.status not in {"DIFF_DETECTED", "REVIEW_REQUIRED"}:
            raise ContractGovernanceError("reviewed_snapshot_required")
        if active.snapshot_id == candidate.snapshot_id:
            return candidate
        active.status = "SUPERSEDED"

    candidate.status = "ACTIVE"
    candidate.approved_by = approved_by
    candidate.approved_at = datetime.now(timezone.utc)
    candidate.approval_note = approval_note
    candidate.approved_hash = expected_hash
    await session.flush()
    return candidate
