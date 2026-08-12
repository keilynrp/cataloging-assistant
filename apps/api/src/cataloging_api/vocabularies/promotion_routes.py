import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.models import DSpaceVocabulary, DSpaceVocabularyEntry
from cataloging_api.db.session import get_session
from cataloging_api.reviews.security import review_token_is_valid
from cataloging_api.vocabularies.service import (
    VocabularyConflictError,
    VocabularyValidationError,
    normalize_term,
    replace_active_vocabulary,
)

router = APIRouter(prefix="/api/dspace-vocabularies", tags=["Vocabulary promotion"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
FIELDS = {
    "linguisticFamilyPairs": "dc.subject.linguisticFamily",
    "linguisticBranchPairs": "dc.subject.linguisticBranch",
    "linguiscgroupPairs": "dc.subject.linguiscgroup",
    "registeredLanguagePairs": "dc.description.registeredLanguage",
}


class PromotionCreate(BaseModel):
    request_id: uuid.UUID
    approved_by: str = Field(min_length=2, max_length=120)
    approval_note: str = Field(min_length=1, max_length=2000)
    collision_choices: list[str] = Field(default_factory=list, max_length=100)


def resolve_promotion_values(
    values: list[str],
    collision_choices: list[str],
) -> tuple[list[str], list[str]]:
    groups: dict[str, list[tuple[int, str]]] = {}
    for position, value in enumerate(values, start=1):
        groups.setdefault(normalize_term(value), []).append((position, value))

    collisions = {key: entries for key, entries in groups.items() if len(entries) > 1}
    ambiguous = {
        key: entries
        for key, entries in collisions.items()
        if len({value for _, value in entries}) > 1
    }
    choices: dict[str, str] = {}
    for choice in collision_choices:
        key = normalize_term(choice)
        variants = [value for _, value in ambiguous.get(key, [])]
        if key not in ambiguous or choice not in variants or key in choices:
            raise VocabularyValidationError("Invalid collision resolution")
        choices[key] = choice
    if set(choices) != set(ambiguous):
        raise VocabularyValidationError(
            "Every ambiguous normalized collision requires one explicit choice"
        )

    selected: list[str] = []
    selected_keys: set[str] = set()
    notes: list[str] = []
    for value in values:
        key = normalize_term(value)
        if key not in collisions:
            selected.append(value)
        elif key not in selected_keys:
            selected_value = choices.get(key, collisions[key][0][1])
            if value == selected_value:
                selected.append(value)
                selected_keys.add(key)

    for key, entries in sorted(collisions.items()):
        positions = ", ".join(str(position) for position, _ in entries)
        variants = [value for _, value in entries]
        if key in ambiguous:
            notes.append(
                f"Resolución humana: {choices[key]} <= {', '.join(variants)} "
                f"(posiciones ordinales {positions})"
            )
        else:
            notes.append(
                f"Colapso literal determinista: {variants[0]} "
                f"(posiciones ordinales {positions}; se conservó la primera)"
            )
    return selected, notes


@router.post("/{vocabulary_id}/promotions")
async def promote_vocabulary(
    vocabulary_id: str,
    payload: PromotionCreate,
    session: SessionDep,
    x_catalog_review_token: Annotated[str | None, Header()] = None,
) -> dict:
    settings = get_settings()
    if not settings.catalog_review_token:
        raise HTTPException(503, "Local review writes are not configured")
    if not review_token_is_valid(settings.catalog_review_token, x_catalog_review_token):
        raise HTTPException(401, "Invalid review token")
    field = FIELDS.get(vocabulary_id)
    vocabulary = await session.get(DSpaceVocabulary, vocabulary_id)
    if field is None or vocabulary is None:
        raise HTTPException(404, "Mapped DSpace vocabulary not found")
    entries = list(
        await session.scalars(
            select(DSpaceVocabularyEntry)
            .where(DSpaceVocabularyEntry.vocabulary_id == vocabulary_id)
            .order_by(DSpaceVocabularyEntry.position)
        )
    )
    try:
        selected_values, resolution_notes = resolve_promotion_values(
            [entry.value for entry in entries], payload.collision_choices
        )
    except VocabularyValidationError as error:
        raise HTTPException(422, str(error)) from error
    resolution_note = "\n".join([payload.approval_note, *resolution_notes])
    try:
        revision = await replace_active_vocabulary(
            session,
            request_id=payload.request_id,
            field=field,
            name=f"DSpace: {vocabulary.name}",
            source_uri=vocabulary.source_uri,
            version_label=f"dspace-{vocabulary.source_hash[:12]}",
            approved_by=payload.approved_by,
            approval_note=resolution_note,
            terms=[
                {"value": value, "authority": None, "language": None} for value in selected_values
            ],
        )
        await session.commit()
    except VocabularyConflictError as error:
        raise HTTPException(409, str(error)) from error
    except VocabularyValidationError as error:
        raise HTTPException(422, str(error)) from error
    return {
        "revision_id": revision.revision_id,
        "field": field,
        "version_label": revision.version_label,
        "term_count": len(selected_values),
    }
