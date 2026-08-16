from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.session import get_session
from cataloging_api.drafts.service import DraftConflictError, DraftStaleError, DraftValidationError
from cataloging_api.evidence.schemas import (
    EvidenceCandidateOut,
    EvidenceCopyResult,
    EvidenceCopyToDraft,
    EvidenceSessionCreate,
    EvidenceSessionOut,
    EvidenceSourceOut,
)
from cataloging_api.evidence.service import (
    EvidenceStaleError,
    EvidenceValidationError,
    copy_candidates_to_draft,
    create_evidence_session,
    extract_evidence_candidates,
    get_evidence_session,
)
from cataloging_api.reviews.security import review_token_is_valid

router = APIRouter(prefix="/api/evidence-sessions", tags=["evidence"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def require_review_token(
    x_catalog_review_token: Annotated[str | None, Header()] = None,
) -> None:
    configured_token = get_settings().catalog_review_token
    if not configured_token:
        raise HTTPException(status_code=503, detail="Local review writes are not configured")
    if not review_token_is_valid(configured_token, x_catalog_review_token):
        raise HTTPException(status_code=401, detail="Invalid review token")


def _to_out(
    evidence_session,
    sources,
    candidates,
    *,
    stale: bool,
) -> EvidenceSessionOut:
    return EvidenceSessionOut(
        session_id=evidence_session.session_id,
        item_uuid=evidence_session.item_uuid,
        base_source_hash=evidence_session.base_source_hash,
        contract_version=evidence_session.contract_version,
        created_by=evidence_session.created_by,
        created_at=evidence_session.created_at,
        stale=stale,
        sources=[
            EvidenceSourceOut(
                source_id=source.source_id,
                kind=source.kind,
                locator=source.locator,
                content_hash=source.content_hash,
                media_type=source.media_type,
                metadata_json=source.metadata_json,
                created_at=source.created_at,
            )
            for source in sources
        ],
        candidates=[
            EvidenceCandidateOut(
                candidate_id=candidate.candidate_id,
                source_id=candidate.source_id,
                metadata_field=candidate.metadata_field,
                value=candidate.value,
                evidence_state=candidate.evidence_state,
                evidence_json=candidate.evidence_json,
                validation_json=candidate.validation_json,
                created_at=candidate.created_at,
            )
            for candidate in candidates
        ],
    )


@router.post("", response_model=EvidenceSessionOut, dependencies=[Depends(require_review_token)])
async def create_session(payload: EvidenceSessionCreate, session: SessionDep) -> EvidenceSessionOut:
    try:
        created = await create_evidence_session(
            session,
            item_uuid=payload.item_uuid,
            created_by=payload.created_by,
            url=payload.url,
            text=payload.text,
        )
        await session.commit()
    except EvidenceValidationError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error

    loaded, sources, candidates, stale = await get_evidence_session(session, created.session_id)
    assert loaded is not None
    return _to_out(loaded, sources, candidates, stale=stale)


@router.get("/{session_id}", response_model=EvidenceSessionOut)
async def get_session(session_id: uuid.UUID, session: SessionDep) -> EvidenceSessionOut:
    loaded, sources, candidates, stale = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    return _to_out(loaded, sources, candidates, stale=stale)


@router.post(
    "/{session_id}/extract",
    response_model=EvidenceSessionOut,
    dependencies=[Depends(require_review_token)],
)
async def extract_session(session_id: uuid.UUID, session: SessionDep) -> EvidenceSessionOut:
    loaded, _, _, stale = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    if stale:
        raise HTTPException(status_code=409, detail="Evidence session is stale against DSpace")
    await extract_evidence_candidates(session, loaded)
    await session.commit()
    loaded, sources, candidates, stale = await get_evidence_session(session, session_id)
    assert loaded is not None
    return _to_out(loaded, sources, candidates, stale=stale)


@router.get("/{session_id}/candidates", response_model=list[EvidenceCandidateOut])
async def get_candidates(session_id: uuid.UUID, session: SessionDep) -> list[EvidenceCandidateOut]:
    loaded, _, candidates, _ = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    return [
        EvidenceCandidateOut(
            candidate_id=candidate.candidate_id,
            source_id=candidate.source_id,
            metadata_field=candidate.metadata_field,
            value=candidate.value,
            evidence_state=candidate.evidence_state,
            evidence_json=candidate.evidence_json,
            validation_json=candidate.validation_json,
            created_at=candidate.created_at,
        )
        for candidate in candidates
    ]


@router.post(
    "/{session_id}/copy-to-draft",
    response_model=EvidenceCopyResult,
    dependencies=[Depends(require_review_token)],
)
async def copy_to_draft(
    session_id: uuid.UUID,
    payload: EvidenceCopyToDraft,
    session: SessionDep,
) -> EvidenceCopyResult:
    loaded, _, _, stale = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    if stale:
        raise HTTPException(status_code=409, detail="Evidence session is stale against DSpace")
    try:
        draft = await copy_candidates_to_draft(
            session,
            evidence_session=loaded,
            candidate_ids=payload.candidate_ids,
            request_id=payload.request_id,
            author=payload.author,
            note=payload.note,
            draft_id=payload.draft_id,
            expected_version=payload.expected_version,
        )
        if draft is None:
            raise HTTPException(status_code=404, detail="DSpace item not found")
        await session.commit()
    except EvidenceStaleError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (EvidenceValidationError, DraftValidationError) as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (DraftConflictError, DraftStaleError) as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail=error.__class__.__name__) from error

    latest = draft.revisions[-1]
    return EvidenceCopyResult(
        draft_id=draft.draft_id,
        revision_id=latest.revision_id,
        version=latest.version,
        item_uuid=draft.item_uuid,
    )
