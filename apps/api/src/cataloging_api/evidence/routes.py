from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.session import get_session
from cataloging_api.drafts.service import (
    DraftConflictError,
    DraftStaleError,
    DraftValidationError,
)
from cataloging_api.evidence.pdf_extraction import MAX_PDF_BYTES
from cataloging_api.evidence.schemas import (
    EvidenceCandidateOut,
    EvidenceCopyResult,
    EvidenceCopyToDraft,
    EvidenceRemoteSourceCreate,
    EvidenceSessionCreate,
    EvidenceSessionOut,
    EvidenceSourceOut,
)
from cataloging_api.evidence.service import (
    EvidencePdfInvalidTypeError,
    EvidencePdfTimeoutError,
    EvidencePdfTooLargeError,
    EvidenceRemoteContentInvalidError,
    EvidenceRemoteContentTooLargeError,
    EvidenceRemoteContentTypeNotAllowedError,
    EvidenceRemoteDnsResolutionError,
    EvidenceRemoteFetchDisabledError,
    EvidenceRemoteFetchTimeoutError,
    EvidenceRemotePdfInvalidError,
    EvidenceRemoteRedirectBlockedError,
    EvidenceRemoteRedirectLimitError,
    EvidenceRemoteTargetNotPublicError,
    EvidenceRemoteUpstreamError,
    EvidenceRemoteUrlInvalidError,
    EvidenceStaleError,
    EvidenceValidationError,
    add_pdf_evidence_source,
    add_remote_evidence_source,
    copy_candidates_to_draft,
    create_evidence_session,
    delete_pdf_artifact,
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
        raise HTTPException(
            status_code=503,
            detail="Local review writes are not configured",
        )
    if not review_token_is_valid(configured_token, x_catalog_review_token):
        raise HTTPException(status_code=401, detail="Invalid review token")


def _candidate_out(candidate) -> EvidenceCandidateOut:
    return EvidenceCandidateOut(
        candidate_id=candidate.candidate_id,
        source_id=candidate.source_id,
        binding_id=candidate.binding_id,
        metadata_field=candidate.metadata_field,
        value=candidate.value,
        evidence_state=candidate.evidence_state,
        evidence_json=candidate.evidence_json,
        validation_json=candidate.validation_json,
        created_at=candidate.created_at,
    )


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
                extraction_status=source.extraction_status,
                extraction_metadata_json=source.extraction_metadata_json,
                extracted_text_hash=source.extracted_text_hash,
                page_count=source.page_count,
                created_at=source.created_at,
            )
            for source in sources
        ],
        candidates=[_candidate_out(candidate) for candidate in candidates],
    )


@router.post(
    "",
    response_model=EvidenceSessionOut,
    dependencies=[Depends(require_review_token)],
)
async def create_session(
    payload: EvidenceSessionCreate,
    session: SessionDep,
) -> EvidenceSessionOut:
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

    loaded, sources, candidates, stale = await get_evidence_session(
        session,
        created.session_id,
    )
    assert loaded is not None
    return _to_out(loaded, sources, candidates, stale=stale)


@router.get("/{session_id}", response_model=EvidenceSessionOut)
async def get_session(
    session_id: uuid.UUID,
    session: SessionDep,
) -> EvidenceSessionOut:
    loaded, sources, candidates, stale = await get_evidence_session(
        session,
        session_id,
    )
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    return _to_out(loaded, sources, candidates, stale=stale)


@router.post(
    "/{session_id}/extract",
    response_model=EvidenceSessionOut,
    dependencies=[Depends(require_review_token)],
)
async def extract_session(
    session_id: uuid.UUID,
    session: SessionDep,
) -> EvidenceSessionOut:
    loaded, _, _, stale = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    if stale:
        raise HTTPException(
            status_code=409,
            detail="Evidence session is stale against DSpace",
        )
    await extract_evidence_candidates(session, loaded)
    await session.commit()
    loaded, sources, candidates, stale = await get_evidence_session(
        session,
        session_id,
    )
    assert loaded is not None
    return _to_out(loaded, sources, candidates, stale=stale)


@router.get(
    "/{session_id}/candidates",
    response_model=list[EvidenceCandidateOut],
)
async def get_candidates(
    session_id: uuid.UUID,
    session: SessionDep,
) -> list[EvidenceCandidateOut]:
    loaded, _, candidates, _ = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    return [_candidate_out(candidate) for candidate in candidates]


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
        raise HTTPException(
            status_code=409,
            detail="Evidence session is stale against DSpace",
        )
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
        raise HTTPException(
            status_code=409,
            detail=error.__class__.__name__,
        ) from error

    latest = draft.revisions[-1]
    return EvidenceCopyResult(
        draft_id=draft.draft_id,
        revision_id=latest.revision_id,
        version=latest.version,
        item_uuid=draft.item_uuid,
    )


@router.post(
    "/{session_id}/sources/pdf",
    response_model=EvidenceSessionOut,
    dependencies=[Depends(require_review_token)],
)
async def upload_pdf_source(
    session_id: uuid.UUID,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    author: Annotated[str, Form(min_length=2, max_length=120)],
) -> EvidenceSessionOut:
    loaded, _, _, stale = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    if stale:
        raise HTTPException(
            status_code=409,
            detail="Evidence session is stale against DSpace",
        )

    data = await file.read(MAX_PDF_BYTES + 1)

    try:
        source = await add_pdf_evidence_source(
            session,
            loaded,
            file_bytes=data,
            original_filename=file.filename or "",
            content_type=file.content_type or "",
            author=author,
        )
    except EvidencePdfTooLargeError as error:
        await session.rollback()
        raise HTTPException(status_code=413, detail=str(error)) from error
    except EvidencePdfInvalidTypeError as error:
        await session.rollback()
        raise HTTPException(status_code=415, detail=str(error)) from error
    except EvidencePdfTimeoutError as error:
        await session.rollback()
        raise HTTPException(
            status_code=422,
            detail="pdf_extraction_timeout: PDF extraction exceeded the configured timeout",
        ) from error
    except EvidenceValidationError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error

    try:
        await session.commit()
    except Exception:
        # add_pdf_evidence_source already flushed the row and wrote the
        # file to disk. If commit fails here, Postgres rolls the row back
        # but the file is untouched, so it must be removed explicitly to
        # avoid an orphan under evidence_pdf_storage_dir.
        await session.rollback()
        delete_pdf_artifact(source.source_id)
        raise

    loaded, sources, candidates, stale = await get_evidence_session(session, session_id)
    assert loaded is not None
    return _to_out(loaded, sources, candidates, stale=stale)


@router.post(
    "/{session_id}/sources/remote",
    response_model=EvidenceSessionOut,
    dependencies=[Depends(require_review_token)],
)
async def upload_remote_source(
    session_id: uuid.UUID,
    payload: EvidenceRemoteSourceCreate,
    session: SessionDep,
) -> EvidenceSessionOut:
    """Explicit backend-only remote fetch (ADR-016). The browser never fetches
    the URL itself: this route is the only place that opens the connection,
    behind the same CATALOG_REVIEW_TOKEN as every other evidence mutation.
    """
    loaded, _, _, stale = await get_evidence_session(session, session_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Evidence session not found")
    if stale:
        raise HTTPException(
            status_code=409,
            detail="Evidence session is stale against DSpace",
        )

    try:
        await add_remote_evidence_source(
            session,
            loaded,
            url=payload.url,
            author=payload.author,
        )
    except EvidenceRemoteFetchDisabledError as error:
        await session.rollback()
        raise HTTPException(status_code=403, detail="remote_fetch_disabled") from error
    except EvidenceRemoteUrlInvalidError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_url_invalid") from error
    except EvidenceRemoteTargetNotPublicError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_target_not_public") from error
    except EvidenceRemoteDnsResolutionError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_dns_resolution_failed") from error
    except EvidenceRemoteRedirectBlockedError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_redirect_blocked") from error
    except EvidenceRemoteRedirectLimitError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_redirect_limit") from error
    except EvidenceRemoteContentTypeNotAllowedError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_content_type_not_allowed") from error
    except EvidenceRemoteContentInvalidError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_content_invalid") from error
    except EvidenceRemotePdfInvalidError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_pdf_invalid") from error
    except EvidenceRemoteContentTooLargeError as error:
        await session.rollback()
        raise HTTPException(status_code=413, detail="remote_content_too_large") from error
    except EvidenceRemoteFetchTimeoutError as error:
        await session.rollback()
        raise HTTPException(status_code=422, detail="remote_fetch_timeout") from error
    except EvidenceRemoteUpstreamError as error:
        await session.rollback()
        raise HTTPException(status_code=502, detail="remote_upstream_error") from error

    try:
        await session.commit()
    except Exception:
        # No filesystem artifact to clean up here: add_remote_evidence_source
        # never writes the fetched body to disk (see ADR-016 Fase 7), so a
        # commit failure only needs a DB rollback.
        await session.rollback()
        raise

    loaded, sources, candidates, stale = await get_evidence_session(session, session_id)
    assert loaded is not None
    return _to_out(loaded, sources, candidates, stale=stale)
