import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.db.models import (
    CatalogDraft,
    CatalogDraftRevision,
    DSpaceItem,
)
from cataloging_api.vocabularies.service import (
    build_metadata_validation_snapshot,
    load_active_vocabulary_rules,
)

LINGUISTIC_FIELDS = (
    "dc.subject.linguisticFamily",
    "dc.subject.linguisticBranch",
    "dc.subject.linguiscgroup",
    "dc.description.registeredLanguage",
)


class DraftConflictError(Exception):
    """A draft already exists or the optimistic version is no longer current."""


class DraftStaleError(Exception):
    """The DSpace-derived source changed after the draft was opened."""


class DraftValidationError(Exception):
    """The proposed metadata patch is outside the restricted draft contract."""


def normalize_metadata_patch(changes: dict[str, list[str]]) -> dict[str, list[dict[str, Any]]]:
    if not changes:
        raise DraftValidationError("At least one linguistic field is required")
    if set(changes) - set(LINGUISTIC_FIELDS):
        raise DraftValidationError("Only the four linguistic fields may be drafted")

    normalized: dict[str, list[dict[str, Any]]] = {}
    for field in LINGUISTIC_FIELDS:
        if field not in changes:
            continue
        values = changes[field]
        if len(values) > 20:
            raise DraftValidationError("A field may contain at most 20 values")
        clean_values = [value.strip() for value in values if value.strip()]
        if any(len(value) > 1000 for value in clean_values):
            raise DraftValidationError("A metadata value may contain at most 1000 characters")
        normalized[field] = [
            {
                "value": value,
                "language": None,
                "authority": None,
                "confidence": None,
                "place": place,
            }
            for place, value in enumerate(clean_values)
        ]
    return normalized


def patch_values(
    patch: dict[str, list[dict[str, Any]]],
) -> dict[str, list[str]]:
    return {field: [str(entry["value"]) for entry in entries] for field, entries in patch.items()}


def snapshot_linguistic_metadata(item: DSpaceItem) -> dict[str, list[dict[str, Any]]]:
    snapshot: dict[str, list[dict[str, Any]]] = {field: [] for field in LINGUISTIC_FIELDS}
    for metadata in item.metadata_values:
        if metadata.field in snapshot:
            snapshot[metadata.field].append(
                {
                    "value": metadata.value,
                    "language": metadata.language,
                    "authority": metadata.authority,
                    "confidence": metadata.confidence,
                    "place": metadata.place,
                }
            )
    return snapshot


async def _existing_request(
    session: AsyncSession,
    request_id: uuid.UUID,
) -> CatalogDraftRevision | None:
    return await session.scalar(
        select(CatalogDraftRevision)
        .where(CatalogDraftRevision.request_id == request_id)
        .options(selectinload(CatalogDraftRevision.draft).selectinload(CatalogDraft.revisions))
    )


async def create_draft(
    session: AsyncSession,
    *,
    item_uuid: uuid.UUID,
    request_id: uuid.UUID,
    author: str,
    note: str,
    changes: dict[str, list[str]],
) -> CatalogDraft | None:
    existing_request = await _existing_request(session, request_id)
    if existing_request is not None:
        if existing_request.draft.item_uuid != item_uuid:
            raise DraftConflictError
        return existing_request.draft

    item = await session.scalar(
        select(DSpaceItem)
        .where(DSpaceItem.uuid == item_uuid, DSpaceItem.is_active.is_(True))
        .options(selectinload(DSpaceItem.metadata_values))
    )
    if item is None:
        return None
    existing_draft = await session.scalar(
        select(CatalogDraft).where(CatalogDraft.item_uuid == item_uuid)
    )
    if existing_draft is not None:
        raise DraftConflictError

    patch = normalize_metadata_patch(changes)
    vocabularies = await load_active_vocabulary_rules(session)
    validation_snapshot = build_metadata_validation_snapshot(patch_values(patch), vocabularies)
    revision = CatalogDraftRevision(
        request_id=request_id,
        version=1,
        metadata_patch=patch,
        validation_snapshot=validation_snapshot,
        author=author.strip(),
        note=note.strip(),
    )
    draft = CatalogDraft(
        item_uuid=item_uuid,
        base_source_hash=item.source_hash,
        base_metadata=snapshot_linguistic_metadata(item),
        created_by=author.strip(),
        revisions=[revision],
    )
    session.add(draft)
    await session.flush()
    return draft


async def append_draft_revision(
    session: AsyncSession,
    *,
    item_uuid: uuid.UUID,
    draft_id: uuid.UUID,
    request_id: uuid.UUID,
    expected_version: int,
    author: str,
    note: str,
    changes: dict[str, list[str]],
) -> CatalogDraft | None:
    existing_request = await _existing_request(session, request_id)
    if existing_request is not None:
        if existing_request.draft.item_uuid != item_uuid or existing_request.draft_id != draft_id:
            raise DraftConflictError
        return existing_request.draft

    draft = await session.scalar(
        select(CatalogDraft)
        .where(CatalogDraft.draft_id == draft_id, CatalogDraft.item_uuid == item_uuid)
        .options(selectinload(CatalogDraft.revisions), selectinload(CatalogDraft.item))
    )
    if draft is None:
        return None
    if draft.item.source_hash != draft.base_source_hash:
        raise DraftStaleError
    current_version = draft.revisions[-1].version
    if current_version != expected_version:
        raise DraftConflictError

    patch = normalize_metadata_patch(changes)
    vocabularies = await load_active_vocabulary_rules(session)
    validation_snapshot = build_metadata_validation_snapshot(patch_values(patch), vocabularies)
    revision = CatalogDraftRevision(
        request_id=request_id,
        version=current_version + 1,
        metadata_patch=patch,
        validation_snapshot=validation_snapshot,
        author=author.strip(),
        note=note.strip(),
    )
    draft.revisions.append(revision)
    draft.updated_at = datetime.now(UTC)
    await session.flush()
    return draft
