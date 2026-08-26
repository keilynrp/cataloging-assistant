import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.session import get_session
from cataloging_api.dspace.contract_governance import (
    ContractGovernanceError,
    approve_snapshot,
    get_contract_health,
)
from cataloging_api.reviews.security import review_token_is_valid

router = APIRouter(prefix="/api/dspace-contract", tags=["DSpace contract"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class SnapshotApproval(BaseModel):
    expected_hash: str = Field(min_length=64, max_length=64)
    approved_by: str = Field(min_length=2, max_length=120)
    approval_note: str | None = Field(default=None, max_length=2000)


@router.get("/status")
async def contract_status(session: SessionDep) -> dict:
    health = await get_contract_health(session)
    return {
        "status": health.status,
        "active_snapshot_id": health.active_snapshot_id,
        "active_hash": health.active_hash,
        "latest_snapshot_id": health.latest_snapshot_id,
        "latest_status": health.latest_status,
        "last_verified_at": health.last_verified_at,
        "metadata_field_count": health.metadata_field_count,
        "form_binding_count": health.form_binding_count,
        "warning_count": health.warning_count,
    }


@router.post("/snapshots/{snapshot_id}/approve")
async def approve_contract_snapshot(
    snapshot_id: uuid.UUID,
    payload: SnapshotApproval,
    session: SessionDep,
    x_catalog_review_token: Annotated[str | None, Header()] = None,
) -> dict:
    settings = get_settings()
    if not settings.catalog_review_token:
        raise HTTPException(503, "Local review writes are not configured")
    if not review_token_is_valid(settings.catalog_review_token, x_catalog_review_token):
        raise HTTPException(401, "Invalid review token")

    try:
        snapshot = await approve_snapshot(
            session,
            snapshot_id=snapshot_id,
            expected_hash=payload.expected_hash,
            approved_by=payload.approved_by,
            approval_note=payload.approval_note,
        )
        await session.commit()
    except ContractGovernanceError as exc:
        await session.rollback()
        code = str(exc)
        if code == "snapshot_not_found":
            raise HTTPException(404, code) from exc
        if code in {"snapshot_hash_mismatch", "active_snapshot_audit_mismatch"}:
            raise HTTPException(409, code) from exc
        raise HTTPException(422, code) from exc

    return {
        "snapshot_id": snapshot.snapshot_id,
        "status": snapshot.status,
        "semantic_hash": snapshot.semantic_hash,
        "approved_by": snapshot.approved_by,
        "approved_at": snapshot.approved_at,
        "approval_note": snapshot.approval_note,
    }
