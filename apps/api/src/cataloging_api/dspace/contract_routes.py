import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.session import get_session
from cataloging_api.dspace.contract_governance import (
    ContractGovernanceError,
    approve_snapshot,
    get_contract_health,
)
from cataloging_api.dspace.contract_resolution import (
    ContractResolutionError,
    resolve_authoritative_evidence,
)
from cataloging_api.reviews.security import review_token_is_valid

router = APIRouter(prefix="/api/dspace-contract", tags=["DSpace contract"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class SnapshotApproval(BaseModel):
    expected_hash: str = Field(min_length=64, max_length=64)
    approved_by: str = Field(min_length=2, max_length=120)
    approval_note: str | None = Field(default=None, max_length=2000)


class EvidenceResolutionCreate(BaseModel):
    expected_snapshot_hash: str = Field(min_length=64, max_length=64)
    expected_effective_hash: str = Field(min_length=64, max_length=64)
    source_export_hash: str = Field(min_length=64, max_length=64)
    reconciliation_hash: str = Field(min_length=64, max_length=64)
    sections: list[dict[str, Any]] = Field(min_length=2, max_length=2)
    bindings: list[dict[str, Any]] = Field(min_length=1, max_length=200)
    resolved_by: str = Field(min_length=2, max_length=120)
    resolution_note: str = Field(min_length=1, max_length=4000)


def _require_review_token(token: str | None) -> None:
    settings = get_settings()
    if not settings.catalog_review_token:
        raise HTTPException(503, "Local review writes are not configured")
    if not review_token_is_valid(settings.catalog_review_token, token):
        raise HTTPException(401, "Invalid review token")


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


@router.post("/snapshots/{snapshot_id}/resolve-evidence")
async def resolve_contract_evidence(
    snapshot_id: uuid.UUID,
    payload: EvidenceResolutionCreate,
    session: SessionDep,
    x_catalog_review_token: Annotated[str | None, Header()] = None,
) -> dict:
    _require_review_token(x_catalog_review_token)
    try:
        snapshot = await resolve_authoritative_evidence(
            session,
            snapshot_id=snapshot_id,
            expected_snapshot_hash=payload.expected_snapshot_hash,
            expected_effective_hash=payload.expected_effective_hash,
            source_export_hash=payload.source_export_hash,
            reconciliation_hash=payload.reconciliation_hash,
            sections=payload.sections,
            bindings=payload.bindings,
            resolved_by=payload.resolved_by,
            resolution_note=payload.resolution_note,
        )
        await session.commit()
    except ContractResolutionError as exc:
        await session.rollback()
        code = str(exc)
        if code == "snapshot_not_found":
            raise HTTPException(404, code) from exc
        if code in {
            "snapshot_hash_mismatch",
            "authoritative_resolution_conflict",
            "effective_contract_hash_mismatch",
        }:
            raise HTTPException(409, code) from exc
        raise HTTPException(422, code) from exc

    return {
        "snapshot_id": snapshot.snapshot_id,
        "status": snapshot.status,
        "observed_hash": snapshot.semantic_hash,
        "effective_hash": snapshot.effective_hash,
        "resolution_surface": snapshot.resolution_surface,
        "resolution_source_hash": snapshot.resolution_source_hash,
        "resolution_reconciliation_hash": snapshot.resolution_reconciliation_hash,
        "resolved_by": snapshot.resolved_by,
        "resolved_at": snapshot.resolved_at,
    }


@router.post("/snapshots/{snapshot_id}/approve")
async def approve_contract_snapshot(
    snapshot_id: uuid.UUID,
    payload: SnapshotApproval,
    session: SessionDep,
    x_catalog_review_token: Annotated[str | None, Header()] = None,
) -> dict:
    _require_review_token(x_catalog_review_token)

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
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(409, "active_snapshot_conflict") from exc

    return {
        "snapshot_id": snapshot.snapshot_id,
        "status": snapshot.status,
        "observed_hash": snapshot.semantic_hash,
        "effective_hash": snapshot.effective_hash,
        "approved_hash": snapshot.approved_hash,
        "approved_by": snapshot.approved_by,
        "approved_at": snapshot.approved_at,
        "approval_note": snapshot.approval_note,
    }
