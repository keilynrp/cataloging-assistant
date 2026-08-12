import unicodedata
from collections import Counter
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.models import (
    DSpaceItem,
    DSpaceMetadataValue,
    DSpaceVocabulary,
    DSpaceVocabularyEntry,
)
from cataloging_api.db.session import get_session
from cataloging_api.vocabularies.service import normalize_term

router = APIRouter(prefix="/api/dspace-vocabularies", tags=["DSpace vocabulary mirror"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
VOCABULARY_FIELDS = {
    "linguisticFamilyPairs": "dc.subject.linguisticFamily",
    "linguisticBranchPairs": "dc.subject.linguisticBranch",
    "linguiscgroupPairs": "dc.subject.linguiscgroup",
    "registeredLanguagePairs": "dc.description.registeredLanguage",
}


def normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().casefold())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


class VocabularySummary(BaseModel):
    vocabulary_id: str
    name: str
    hierarchical: bool
    scrollable: bool
    source_uri: str
    synced_at: datetime
    entry_count: int


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    entry_id: str
    value: str
    display: str | None
    selectable: bool
    parent_id: str | None
    position: int


@router.get("")
async def list_vocabularies(session: SessionDep) -> dict:
    rows = (
        await session.execute(
            select(DSpaceVocabulary, func.count(DSpaceVocabularyEntry.row_id))
            .outerjoin(DSpaceVocabularyEntry)
            .group_by(DSpaceVocabulary.vocabulary_id)
            .order_by(DSpaceVocabulary.name)
        )
    ).all()
    values = [
        VocabularySummary(
            vocabulary_id=v.vocabulary_id,
            name=v.name,
            hierarchical=v.hierarchical,
            scrollable=v.scrollable,
            source_uri=v.source_uri,
            synced_at=v.synced_at,
            entry_count=count,
        )
        for v, count in rows
    ]
    return {
        "vocabularies": values,
        "total": len(values),
        "entry_total": sum(v.entry_count for v in values),
    }


@router.get("/{vocabulary_id}")
async def get_vocabulary(
    vocabulary_id: str,
    session: SessionDep,
    page: int = Query(0, ge=0),
    size: int = Query(100, ge=1, le=500),
) -> dict:
    vocabulary = await session.get(DSpaceVocabulary, vocabulary_id)
    if vocabulary is None:
        raise HTTPException(404, "DSpace vocabulary not found")
    condition = DSpaceVocabularyEntry.vocabulary_id == vocabulary_id
    total = (
        await session.scalar(
            select(func.count()).select_from(DSpaceVocabularyEntry).where(condition)
        )
        or 0
    )
    entries = list(
        await session.scalars(
            select(DSpaceVocabularyEntry)
            .where(condition)
            .order_by(DSpaceVocabularyEntry.position)
            .offset(page * size)
            .limit(size)
        )
    )
    summary = VocabularySummary(
        vocabulary_id=vocabulary.vocabulary_id,
        name=vocabulary.name,
        hierarchical=vocabulary.hierarchical,
        scrollable=vocabulary.scrollable,
        source_uri=vocabulary.source_uri,
        synced_at=vocabulary.synced_at,
        entry_count=total,
    )
    return {
        **summary.model_dump(),
        "entries": [EntryOut.model_validate(e) for e in entries],
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size,
    }


@router.get("/{vocabulary_id}/comparison")
async def compare_vocabulary(vocabulary_id: str, session: SessionDep) -> dict:
    field = VOCABULARY_FIELDS.get(vocabulary_id)
    if field is None:
        raise HTTPException(400, "Vocabulary is not mapped to a pilot linguistic field")
    terms = list(
        await session.scalars(
            select(DSpaceVocabularyEntry)
            .where(DSpaceVocabularyEntry.vocabulary_id == vocabulary_id)
            .order_by(DSpaceVocabularyEntry.position)
        )
    )
    rows = (
        await session.execute(
            select(DSpaceMetadataValue.value, func.count(DSpaceMetadataValue.item_uuid.distinct()))
            .join(DSpaceItem)
            .where(
                DSpaceItem.collection_uuid == get_settings().dspace_pilot_collection_uuid,
                DSpaceItem.is_active.is_(True),
                DSpaceMetadataValue.field == field,
            )
            .group_by(DSpaceMetadataValue.value)
            .order_by(DSpaceMetadataValue.value)
        )
    ).all()
    exact = {term.value for term in terms}
    duplicate_terms = sorted(
        value for value, count in Counter(term.value for term in terms).items() if count > 1
    )
    normalized_groups: dict[str, list[str]] = {}
    for term in terms:
        normalized_groups.setdefault(normalize_term(term.value), []).append(term.value)
    normalized_duplicate_terms = [
        variants for variants in normalized_groups.values() if len(variants) > 1
    ]
    normalized_terms: dict[str, list[str]] = {}
    for term in terms:
        normalized_terms.setdefault(normalized(term.value), []).append(term.value)
    values = []
    used_exact = set()
    for value, item_count in rows:
        candidates = [value] if value in exact else normalized_terms.get(normalized(value), [])
        status = "exact" if value in exact else "normalized" if candidates else "outside"
        if status == "exact":
            used_exact.add(value)
        values.append(
            {"value": value, "item_count": item_count, "status": status, "candidates": candidates}
        )
    unused = sorted(exact - used_exact)
    return {
        "vocabulary_id": vocabulary_id,
        "field": field,
        "term_count": len(terms),
        "distinct_term_count": len(exact),
        "duplicate_term_count": len(terms) - len(exact),
        "duplicate_terms": duplicate_terms,
        "normalized_duplicate_count": len(normalized_duplicate_terms),
        "normalized_duplicate_terms": normalized_duplicate_terms,
        "observed_value_count": len(values),
        "exact_count": sum(v["status"] == "exact" for v in values),
        "normalized_count": sum(v["status"] == "normalized" for v in values),
        "outside_count": sum(v["status"] == "outside" for v in values),
        "unused_term_count": len(unused),
        "values": values,
        "unused_terms": unused,
    }
