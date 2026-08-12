import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.db.models import (
    CatalogDraft,
    CatalogSuggestion,
    CatalogSuggestionDecision,
    DSpaceItem,
    SuggestionDecisionKind,
)
from cataloging_api.drafts.service import (
    DraftConflictError,
    DraftStaleError,
    append_draft_revision,
    create_draft,
)


class SuggestionDecisionConflictError(Exception):
    pass


class SuggestionDecisionValidationError(Exception):
    pass


async def record_suggestion_decision(
    session: AsyncSession,
    *,
    suggestion_id: uuid.UUID,
    request_id: uuid.UUID,
    decision: SuggestionDecisionKind,
    corrected_value: str | None,
    reviewer: str,
    note: str,
) -> CatalogSuggestionDecision | None:
    existing = await session.scalar(
        select(CatalogSuggestionDecision).where(CatalogSuggestionDecision.request_id == request_id)
    )
    if existing is not None:
        if existing.suggestion_id != suggestion_id:
            raise SuggestionDecisionConflictError
        return existing
    corrected = (corrected_value or "").strip() or None
    if decision is SuggestionDecisionKind.corrected and corrected is None:
        raise SuggestionDecisionValidationError("corrected_value is required")
    suggestion = await session.scalar(
        select(CatalogSuggestion).where(CatalogSuggestion.suggestion_id == suggestion_id)
    )
    if suggestion is None:
        return None
    item = await session.scalar(select(DSpaceItem).where(DSpaceItem.uuid == suggestion.item_uuid))
    if item is None:
        return None
    draft_revision_id = None
    if decision in {SuggestionDecisionKind.accepted, SuggestionDecisionKind.corrected}:
        if suggestion.source_hash != item.source_hash:
            raise SuggestionDecisionValidationError("suggestion source is stale")
        value = (
            corrected if decision is SuggestionDecisionKind.corrected else suggestion.proposed_value
        )
        draft = await session.scalar(
            select(CatalogDraft)
            .where(CatalogDraft.item_uuid == suggestion.item_uuid)
            .options(selectinload(CatalogDraft.revisions))
        )
        draft_request_id = uuid.uuid5(request_id, "suggestion-draft-revision")
        changes = {suggestion.field: [value]}
        try:
            if draft is None:
                draft = await create_draft(
                    session,
                    item_uuid=suggestion.item_uuid,
                    request_id=draft_request_id,
                    author=reviewer,
                    note=note,
                    changes=changes,
                )
            else:
                latest = draft.revisions[-1]
                changes = {
                    field: [entry["value"] for entry in entries]
                    for field, entries in latest.metadata_patch.items()
                } | changes
                draft = await append_draft_revision(
                    session,
                    item_uuid=suggestion.item_uuid,
                    draft_id=draft.draft_id,
                    request_id=draft_request_id,
                    expected_version=latest.version,
                    author=reviewer,
                    note=note,
                    changes=changes,
                )
        except DraftStaleError as error:
            raise SuggestionDecisionValidationError("draft source is stale") from error
        except DraftConflictError as error:
            raise SuggestionDecisionConflictError from error
        if draft is None:
            return None
        draft_revision_id = draft.revisions[-1].revision_id
    row = CatalogSuggestionDecision(
        request_id=request_id,
        suggestion_id=suggestion.suggestion_id,
        item_uuid=suggestion.item_uuid,
        decision=decision,
        corrected_value=corrected,
        reviewer=reviewer.strip(),
        note=note.strip(),
        suggestion_source_hash=suggestion.source_hash,
        current_source_hash=item.source_hash,
        source_stale=suggestion.source_hash != item.source_hash,
        draft_revision_id=draft_revision_id,
    )
    session.add(row)
    await session.flush()
    return row
