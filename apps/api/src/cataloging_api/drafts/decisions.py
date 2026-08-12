import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.db.models import (
    CatalogDraft,
    CatalogDraftRevisionDecision,
)


class DraftDecisionConflict(RuntimeError):
    pass


class DraftDecisionValidationError(ValueError):
    pass


def decision_fingerprint(
    *,
    item_uuid: uuid.UUID,
    draft_id: uuid.UUID,
    revision_id: uuid.UUID,
    decision: str,
    reviewer: str,
    note: str,
    validation_override: bool,
) -> str:
    payload = {
        "item_uuid": str(item_uuid),
        "draft_id": str(draft_id),
        "revision_id": str(revision_id),
        "decision": decision,
        "reviewer": reviewer.strip(),
        "note": note.strip(),
        "validation_override": validation_override,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def decide_draft_revision(
    session: AsyncSession,
    *,
    item_uuid: uuid.UUID,
    draft_id: uuid.UUID,
    revision_id: uuid.UUID,
    request_id: uuid.UUID,
    decision: str,
    reviewer: str,
    note: str,
    validation_override: bool,
) -> CatalogDraftRevisionDecision | None:
    existing = await session.scalar(
        select(CatalogDraftRevisionDecision).where(
            CatalogDraftRevisionDecision.request_id == request_id
        )
    )
    fingerprint = decision_fingerprint(
        item_uuid=item_uuid,
        draft_id=draft_id,
        revision_id=revision_id,
        decision=decision,
        reviewer=reviewer,
        note=note,
        validation_override=validation_override,
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise DraftDecisionConflict("Request identifier reused with different decision")
        return existing

    draft = await session.scalar(
        select(CatalogDraft)
        .where(CatalogDraft.draft_id == draft_id, CatalogDraft.item_uuid == item_uuid)
        .options(selectinload(CatalogDraft.revisions), selectinload(CatalogDraft.item))
        .with_for_update()
    )
    if draft is None:
        return None
    if draft.item.source_hash != draft.base_source_hash:
        raise DraftDecisionConflict("Draft source is stale")
    revision = draft.revisions[-1]
    if revision.revision_id != revision_id:
        raise DraftDecisionConflict("Only the latest draft revision may be decided")
    if decision not in {"approved", "rejected"}:
        raise DraftDecisionValidationError("Unsupported draft decision")
    validation_status = revision.validation_snapshot.get("status")
    if decision == "approved" and validation_status == "invalid" and not validation_override:
        raise DraftDecisionValidationError("Invalid vocabulary values require documented override")
    if validation_override and decision != "approved":
        raise DraftDecisionValidationError("Validation override only applies to approval")

    record = CatalogDraftRevisionDecision(
        request_id=request_id,
        request_fingerprint=fingerprint,
        draft_id=draft_id,
        revision_id=revision_id,
        item_uuid=item_uuid,
        decision=decision,
        reviewer=reviewer.strip(),
        note=note.strip(),
        source_hash=draft.item.source_hash,
        validation_snapshot=revision.validation_snapshot,
        validation_override=validation_override,
    )
    session.add(record)
    await session.flush()
    return record
