import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import exists, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.api.schemas import (
    BitstreamOut,
    BundleOut,
    CatalogDraftOut,
    CatalogFindingOut,
    CatalogSuggestionOut,
    CatalogSuggestionsOut,
    DiagnosticsOut,
    DraftCreate,
    DraftRevisionCreate,
    DraftRevisionDecisionCreate,
    DraftRevisionDecisionOut,
    DraftRevisionOut,
    ItemDetailOut,
    ItemListOut,
    MetadataValueOut,
    PersistedSuggestionOut,
    PersistedSuggestionsOut,
    ReviewDecisionCreate,
    ReviewDecisionOut,
    SimilarItemOut,
    SimilarItemsOut,
    SimilarityEvidenceOut,
    SuggestionDecisionCreate,
    SuggestionDecisionOut,
    SuggestionHistoryEntryOut,
    SuggestionHistoryOut,
    SyncRunOut,
)
from cataloging_api.config import get_settings
from cataloging_api.db.models import (
    CatalogDraft,
    CatalogSuggestion,
    CatalogSuggestionDecision,
    DSpaceBundle,
    DSpaceItem,
    DSpaceMetadataValue,
    ReviewDecisionKind,
    SuggestionDecisionKind,
    SyncRun,
)
from cataloging_api.db.session import get_session
from cataloging_api.diagnostics.engine import diagnostic_profile_version
from cataloging_api.drafts.decisions import (
    DraftDecisionConflict,
    DraftDecisionValidationError,
    decide_draft_revision,
)
from cataloging_api.drafts.service import (
    DraftConflictError,
    DraftStaleError,
    DraftValidationError,
    append_draft_revision,
    create_draft,
)
from cataloging_api.profile.schemas import CollectionProfileOut
from cataloging_api.profile.service import build_collection_profile
from cataloging_api.reviews.security import review_token_is_valid
from cataloging_api.reviews.service import ReviewConflictError, record_review_decision
from cataloging_api.similarity.service import find_similar_items
from cataloging_api.suggestions.decisions import (
    SuggestionDecisionConflictError,
    SuggestionDecisionValidationError,
    record_suggestion_decision,
)
from cataloging_api.suggestions.service import (
    persist_current_suggestions,
    suggest_missing_metadata,
)
from cataloging_api.vocabularies.schemas import (
    ItemMetadataValidationOut,
    VocabularyRevisionCreate,
    VocabularyRevisionListOut,
    VocabularyRevisionOut,
)
from cataloging_api.vocabularies.service import (
    VocabularyConflictError,
    VocabularyValidationError,
    list_vocabulary_revisions,
    load_active_vocabulary_rules,
    replace_active_vocabulary,
    validate_item_metadata,
)
from cataloging_api.work_queue.schemas import WorkQueueOut
from cataloging_api.work_queue.service import build_work_queue

router = APIRouter()
SessionDep = Annotated[AsyncSession, Depends(get_session)]


def require_review_token(
    x_catalog_review_token: Annotated[str | None, Header()] = None,
) -> None:
    configured_token = get_settings().catalog_review_token
    if not configured_token:
        raise HTTPException(status_code=503, detail="Local review writes are not configured")
    if not review_token_is_valid(configured_token, x_catalog_review_token):
        raise HTTPException(status_code=401, detail="Invalid review token")


def draft_to_out(draft: CatalogDraft, current_source_hash: str) -> CatalogDraftOut:
    return CatalogDraftOut(
        draft_id=draft.draft_id,
        item_uuid=draft.item_uuid,
        base_source_hash=draft.base_source_hash,
        base_metadata=draft.base_metadata,
        status=draft.status,
        created_by=draft.created_by,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        stale=draft.base_source_hash != current_source_hash,
        revisions=[DraftRevisionOut.model_validate(revision) for revision in draft.revisions],
    )


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(text("select 1"))
    return {"status": "ok", "dspace_mode": "read-only"}


@router.get(
    "/api/controlled-vocabularies",
    response_model=VocabularyRevisionListOut,
)
async def get_controlled_vocabularies(
    session: SessionDep,
    field: str | None = Query(default=None, max_length=255),
    include_history: bool = False,
) -> VocabularyRevisionListOut:
    revisions = await list_vocabulary_revisions(
        session,
        field=field,
        include_history=include_history,
    )
    return VocabularyRevisionListOut(
        revisions=[VocabularyRevisionOut.model_validate(revision) for revision in revisions],
        total=len(revisions),
    )


@router.post(
    "/api/controlled-vocabularies",
    response_model=VocabularyRevisionOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def create_controlled_vocabulary_revision(
    payload: VocabularyRevisionCreate,
    session: SessionDep,
) -> VocabularyRevisionOut:
    try:
        revision = await replace_active_vocabulary(
            session,
            request_id=payload.request_id,
            field=payload.field,
            name=payload.name,
            source_uri=payload.source_uri,
            version_label=payload.version_label,
            approved_by=payload.approved_by,
            approval_note=payload.approval_note,
            terms=[term.model_dump() for term in payload.terms],
        )
        await session.commit()
    except VocabularyValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (VocabularyConflictError, IntegrityError) as error:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Vocabulary revision conflicts with current local state",
        ) from error
    return VocabularyRevisionOut.model_validate(revision)


@router.get(
    "/api/items/{item_uuid}/metadata-validation",
    response_model=ItemMetadataValidationOut,
)
async def get_item_metadata_validation(
    item_uuid: uuid.UUID,
    session: SessionDep,
) -> ItemMetadataValidationOut:
    validation = await validate_item_metadata(session, item_uuid)
    if validation is None:
        raise HTTPException(status_code=404, detail="Active item not found")
    return ItemMetadataValidationOut.model_validate(validation)


@router.get("/api/catalog-profile", response_model=CollectionProfileOut)
async def get_catalog_profile(session: SessionDep) -> CollectionProfileOut:
    collection_uuid = uuid.UUID(get_settings().dspace_pilot_collection_uuid)
    profile = await build_collection_profile(session, collection_uuid)
    if profile is None:
        raise HTTPException(status_code=404, detail="Pilot collection not found")
    return CollectionProfileOut.model_validate(profile)


@router.get("/api/work-queue", response_model=WorkQueueOut)
async def get_work_queue(
    session: SessionDep,
    q: str | None = None,
    severity: str | None = Query(default=None, pattern="^(error|warning)$"),
    finding_code: str | None = Query(default=None, max_length=100),
    review: str | None = Query(default=None, pattern="^(pending|reviewed|deferred)$"),
    suggestion_filter: str | None = Query(
        default=None, alias="suggestions", pattern="^(pending|none)$"
    ),
    draft_filter: str | None = Query(
        default=None,
        alias="draft",
        pattern="^(none|open|approved|rejected|superseded|stale)$",
    ),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=25, ge=1, le=100),
) -> WorkQueueOut:
    collection_uuid = uuid.UUID(get_settings().dspace_pilot_collection_uuid)
    queue = await build_work_queue(
        session,
        collection_uuid,
        q=q,
        severity=severity,
        finding_code=finding_code,
        review=review,
        suggestion_filter=suggestion_filter,
        draft_filter=draft_filter,
        page=page,
        size=size,
    )
    if queue is None:
        raise HTTPException(status_code=404, detail="Pilot collection not found")
    return WorkQueueOut.model_validate(queue)


async def search_active_items(
    session: AsyncSession,
    *,
    q: str | None = None,
    linguistic_family: str | None = None,
    linguistic_branch: str | None = None,
    linguistic_group: str | None = None,
    registered_language: str | None = None,
    page: int = 0,
    size: int = 20,
) -> ItemListOut:
    filters = [DSpaceItem.is_active.is_(True)]
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                DSpaceItem.name.ilike(pattern),
                DSpaceItem.handle.ilike(pattern),
                exists().where(
                    DSpaceMetadataValue.item_uuid == DSpaceItem.uuid,
                    DSpaceMetadataValue.value.ilike(pattern),
                ),
            )
        )
    field_filters = {
        "dc.subject.linguisticFamily": linguistic_family,
        "dc.subject.linguisticBranch": linguistic_branch,
        "dc.subject.linguiscgroup": linguistic_group,
        "dc.description.registeredLanguage": registered_language,
    }
    for field, value in field_filters.items():
        if value:
            filters.append(
                exists().where(
                    DSpaceMetadataValue.item_uuid == DSpaceItem.uuid,
                    DSpaceMetadataValue.field == field,
                    DSpaceMetadataValue.value == value,
                )
            )

    total = await session.scalar(select(func.count()).select_from(DSpaceItem).where(*filters))
    result = await session.scalars(
        select(DSpaceItem)
        .where(*filters)
        .order_by(DSpaceItem.last_modified.desc().nullslast(), DSpaceItem.name)
        .offset(page * size)
        .limit(size)
    )
    return ItemListOut(items=list(result), page=page, size=size, total=total or 0)


@router.get("/api/items", response_model=ItemListOut)
async def list_items(
    session: SessionDep,
    q: str | None = None,
    linguistic_family: str | None = None,
    linguistic_branch: str | None = None,
    linguistic_group: str | None = None,
    registered_language: str | None = None,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
) -> ItemListOut:
    return await search_active_items(
        session,
        q=q,
        linguistic_family=linguistic_family,
        linguistic_branch=linguistic_branch,
        linguistic_group=linguistic_group,
        registered_language=registered_language,
        page=page,
        size=size,
    )


@router.get("/api/items/{item_uuid}/similar", response_model=SimilarItemsOut)
async def get_similar_items(
    item_uuid: uuid.UUID,
    session: SessionDep,
    limit: int = Query(default=5, ge=1, le=20),
) -> SimilarItemsOut:
    result = await find_similar_items(session, item_uuid=item_uuid, limit=limit)
    if result.source is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return SimilarItemsOut(
        source_uuid=result.source.uuid,
        method="structured-v1",
        candidates_evaluated=result.candidates_evaluated,
        truncated=result.truncated,
        items=[
            SimilarItemOut(
                uuid=item.uuid,
                handle=item.handle,
                name=item.name,
                score=match.score,
                evidence=[
                    SimilarityEvidenceOut(
                        kind=evidence.kind,
                        field=evidence.field,
                        values=list(evidence.values),
                        contribution=evidence.contribution,
                    )
                    for evidence in match.evidence
                ],
            )
            for item, match in result.matches
        ],
    )


@router.get("/api/items/{item_uuid}/suggestions", response_model=CatalogSuggestionsOut)
async def get_item_suggestions(item_uuid: uuid.UUID, session: SessionDep) -> CatalogSuggestionsOut:
    suggestions = await suggest_missing_metadata(session, item_uuid)
    if suggestions is None:
        raise HTTPException(status_code=404, detail="Active item not found")
    return CatalogSuggestionsOut(
        item_uuid=item_uuid,
        method="similarity-consensus-v1",
        suggestions=[CatalogSuggestionOut(**suggestion.__dict__) for suggestion in suggestions],
    )


@router.post(
    "/api/items/{item_uuid}/suggestions/generate",
    response_model=PersistedSuggestionsOut,
    dependencies=[Depends(require_review_token)],
)
async def generate_item_suggestions(
    item_uuid: uuid.UUID, session: SessionDep
) -> PersistedSuggestionsOut:
    suggestions = await persist_current_suggestions(session, item_uuid)
    if suggestions is None:
        raise HTTPException(status_code=404, detail="Active item not found")
    await session.commit()
    return PersistedSuggestionsOut(
        item_uuid=item_uuid,
        suggestions=[
            PersistedSuggestionOut.model_validate(suggestion) for suggestion in suggestions
        ],
    )


@router.post(
    "/api/suggestions/{suggestion_id}/decisions",
    response_model=SuggestionDecisionOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def create_suggestion_decision(
    suggestion_id: uuid.UUID,
    payload: SuggestionDecisionCreate,
    session: SessionDep,
) -> SuggestionDecisionOut:
    try:
        row = await record_suggestion_decision(
            session,
            suggestion_id=suggestion_id,
            request_id=payload.request_id,
            decision=SuggestionDecisionKind(payload.decision),
            corrected_value=payload.corrected_value,
            reviewer=payload.reviewer,
            note=payload.note,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        await session.commit()
    except SuggestionDecisionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except SuggestionDecisionConflictError as error:
        raise HTTPException(status_code=409, detail="Request identifier conflict") from error
    return SuggestionDecisionOut.model_validate(row)


@router.get("/api/items/{item_uuid}/suggestion-history", response_model=SuggestionHistoryOut)
async def get_suggestion_history(item_uuid: uuid.UUID, session: SessionDep) -> SuggestionHistoryOut:
    item = await session.scalar(select(DSpaceItem).where(DSpaceItem.uuid == item_uuid))
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    suggestions = list(
        await session.scalars(
            select(CatalogSuggestion)
            .where(CatalogSuggestion.item_uuid == item_uuid)
            .order_by(CatalogSuggestion.created_at)
        )
    )
    suggestion_ids = [row.suggestion_id for row in suggestions]
    decisions = (
        list(
            await session.scalars(
                select(CatalogSuggestionDecision)
                .where(CatalogSuggestionDecision.suggestion_id.in_(suggestion_ids))
                .order_by(CatalogSuggestionDecision.created_at)
            )
        )
        if suggestion_ids
        else []
    )
    grouped: dict[uuid.UUID, list[SuggestionDecisionOut]] = {}
    for decision in decisions:
        grouped.setdefault(decision.suggestion_id, []).append(
            SuggestionDecisionOut.model_validate(decision)
        )
    return SuggestionHistoryOut(
        item_uuid=item_uuid,
        entries=[
            SuggestionHistoryEntryOut(
                suggestion_id=row.suggestion_id,
                fingerprint=row.fingerprint,
                source_hash=row.source_hash,
                source_stale=row.source_hash != item.source_hash,
                field=row.field,
                proposed_value=row.proposed_value,
                confidence=row.confidence,
                method=row.method,
                method_version=row.method_version,
                explanation=row.explanation,
                evidence=row.evidence,
                created_at=row.created_at,
                decisions=grouped.get(row.suggestion_id, []),
            )
            for row in suggestions
        ],
    )


@router.get("/api/items/{item_uuid}", response_model=ItemDetailOut)
async def get_item(item_uuid: uuid.UUID, session: SessionDep) -> ItemDetailOut:
    item = await session.scalar(
        select(DSpaceItem)
        .where(DSpaceItem.uuid == item_uuid)
        .options(
            selectinload(DSpaceItem.metadata_values),
            selectinload(DSpaceItem.bundles).selectinload(DSpaceBundle.bitstreams),
            selectinload(DSpaceItem.findings),
            selectinload(DSpaceItem.review_decisions),
            selectinload(DSpaceItem.drafts).selectinload(CatalogDraft.revisions),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    metadata: dict[str, list[MetadataValueOut]] = {}
    for value in item.metadata_values:
        metadata.setdefault(value.field, []).append(
            MetadataValueOut(
                value=value.value,
                language=value.language,
                authority=value.authority,
                confidence=value.confidence,
                place=value.place,
            )
        )
    bundles = [
        BundleOut(
            uuid=bundle.uuid,
            name=bundle.name,
            bitstreams=[
                BitstreamOut(
                    uuid=bitstream.uuid,
                    name=bitstream.name,
                    mime_type=bitstream.mime_type,
                    size_bytes=bitstream.size_bytes,
                    content_url=bitstream.content_url,
                )
                for bitstream in bundle.bitstreams
            ],
        )
        for bundle in item.bundles
    ]
    active_vocabularies = await load_active_vocabulary_rules(session)
    active_profile = diagnostic_profile_version(
        get_settings().required_fields,
        (rule.profile_key for rule in active_vocabularies.values()),
    )
    diagnostics = DiagnosticsOut(
        status=(
            "current"
            if item.diagnostic_source_hash == item.source_hash
            and item.diagnostic_profile_version == active_profile
            else "stale"
        ),
        profile_version=item.diagnostic_profile_version,
        evaluated_at=item.diagnosed_at,
        findings=[
            CatalogFindingOut(
                finding_id=finding.finding_id,
                fingerprint=finding.fingerprint,
                code=finding.code,
                severity=finding.severity,
                affected_fields=finding.affected_fields,
                explanation=finding.explanation,
                rule_version=finding.rule_version,
                detected_at=finding.detected_at,
            )
            for finding in sorted(item.findings, key=lambda value: (value.severity, value.code))
        ],
    )
    return ItemDetailOut(
        uuid=item.uuid,
        handle=item.handle,
        name=item.name,
        collection_uuid=item.collection_uuid,
        last_modified=item.last_modified,
        is_active=item.is_active,
        metadata=metadata,
        bundles=bundles,
        raw_json=item.raw_json,
        diagnostics=diagnostics,
        review_decisions=item.review_decisions,
        drafts=[draft_to_out(draft, item.source_hash) for draft in item.drafts],
    )


@router.post(
    "/api/items/{item_uuid}/findings/{finding_id}/decisions",
    response_model=ReviewDecisionOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def create_review_decision(
    item_uuid: uuid.UUID,
    finding_id: uuid.UUID,
    payload: ReviewDecisionCreate,
    session: SessionDep,
) -> ReviewDecisionOut:
    try:
        review = await record_review_decision(
            session,
            item_uuid=item_uuid,
            finding_id=finding_id,
            request_id=payload.request_id,
            decision=ReviewDecisionKind(payload.decision),
            reviewer=payload.reviewer,
            note=payload.note,
        )
    except ReviewConflictError as error:
        raise HTTPException(
            status_code=409,
            detail="Review request identifier already used",
        ) from error
    if review is None:
        raise HTTPException(status_code=404, detail="Current finding not found")
    await session.commit()
    await session.refresh(review)
    return ReviewDecisionOut.model_validate(review)


@router.post(
    "/api/items/{item_uuid}/drafts",
    response_model=CatalogDraftOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def create_local_draft(
    item_uuid: uuid.UUID,
    payload: DraftCreate,
    session: SessionDep,
) -> CatalogDraftOut:
    try:
        draft = await create_draft(
            session,
            item_uuid=item_uuid,
            request_id=payload.request_id,
            author=payload.author,
            note=payload.note,
            changes=payload.changes,
        )
    except DraftValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DraftConflictError as error:
        raise HTTPException(
            status_code=409,
            detail="A local draft already exists or the request identifier was reused",
        ) from error
    if draft is None:
        raise HTTPException(status_code=404, detail="Active item not found")
    await session.commit()
    return draft_to_out(draft, draft.base_source_hash)


@router.post(
    "/api/items/{item_uuid}/drafts/{draft_id}/revisions",
    response_model=CatalogDraftOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def create_local_draft_revision(
    item_uuid: uuid.UUID,
    draft_id: uuid.UUID,
    payload: DraftRevisionCreate,
    session: SessionDep,
) -> CatalogDraftOut:
    try:
        draft = await append_draft_revision(
            session,
            item_uuid=item_uuid,
            draft_id=draft_id,
            request_id=payload.request_id,
            expected_version=payload.expected_version,
            author=payload.author,
            note=payload.note,
            changes=payload.changes,
        )
    except DraftValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DraftStaleError as error:
        raise HTTPException(
            status_code=409,
            detail="The DSpace-derived item changed; the draft must be rebased",
        ) from error
    except DraftConflictError as error:
        raise HTTPException(
            status_code=409,
            detail="The draft version changed or the request identifier was reused",
        ) from error

    if draft is None:
        raise HTTPException(status_code=404, detail="Local draft not found")
    await session.commit()
    return draft_to_out(draft, draft.base_source_hash)


@router.get("/api/sync-runs/latest", response_model=SyncRunOut)
async def latest_sync_run(session: SessionDep) -> SyncRun:
    run = await session.scalar(select(SyncRun).order_by(SyncRun.started_at.desc()).limit(1))
    if run is None:
        raise HTTPException(status_code=404, detail="No synchronization run found")
    return run


@router.post(
    "/api/items/{item_uuid}/drafts/{draft_id}/decisions",
    response_model=DraftRevisionDecisionOut,
    status_code=201,
    dependencies=[Depends(require_review_token)],
)
async def decide_local_draft_revision(
    item_uuid: uuid.UUID,
    draft_id: uuid.UUID,
    payload: DraftRevisionDecisionCreate,
    session: SessionDep,
) -> DraftRevisionDecisionOut:
    try:
        decision = await decide_draft_revision(
            session,
            item_uuid=item_uuid,
            draft_id=draft_id,
            revision_id=payload.revision_id,
            request_id=payload.request_id,
            decision=payload.decision,
            reviewer=payload.reviewer,
            note=payload.note,
            validation_override=payload.validation_override,
        )
    except DraftDecisionValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except DraftDecisionConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if decision is None:
        raise HTTPException(status_code=404, detail="Local draft not found")
    await session.commit()
    await session.refresh(decision)
    return DraftRevisionDecisionOut.model_validate(decision)
