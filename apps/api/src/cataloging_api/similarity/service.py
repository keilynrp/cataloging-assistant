import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cataloging_api.db.models import DSpaceItem, DSpaceMetadataValue
from cataloging_api.similarity.engine import (
    FIELD_WEIGHTS,
    SimilarityItem,
    SimilarityMatch,
    rank_similar_items,
)

MAX_CANDIDATES = 2000


@dataclass(frozen=True)
class SimilarityResult:
    source: DSpaceItem | None
    candidates_evaluated: int
    truncated: bool
    matches: list[tuple[DSpaceItem, SimilarityMatch]]


async def find_similar_items(
    session: AsyncSession,
    *,
    item_uuid: uuid.UUID,
    limit: int,
) -> SimilarityResult:
    source = await session.scalar(
        select(DSpaceItem)
        .where(DSpaceItem.uuid == item_uuid, DSpaceItem.is_active.is_(True))
        .options(
            selectinload(
                DSpaceItem.metadata_values.and_(DSpaceMetadataValue.field.in_(tuple(FIELD_WEIGHTS)))
            )
        )
    )
    if source is None:
        return SimilarityResult(None, 0, False, [])

    result = await session.scalars(
        select(DSpaceItem)
        .where(
            DSpaceItem.collection_uuid == source.collection_uuid,
            DSpaceItem.uuid != source.uuid,
            DSpaceItem.is_active.is_(True),
        )
        .options(
            selectinload(
                DSpaceItem.metadata_values.and_(DSpaceMetadataValue.field.in_(tuple(FIELD_WEIGHTS)))
            )
        )
        .order_by(DSpaceItem.uuid)
        .limit(MAX_CANDIDATES + 1)
    )
    candidate_rows = list(result)
    truncated = len(candidate_rows) > MAX_CANDIDATES
    candidate_rows = candidate_rows[:MAX_CANDIDATES]

    source_input = _to_similarity_item(source)
    candidate_inputs = [_to_similarity_item(item) for item in candidate_rows]
    ranked = rank_similar_items(source_input, candidate_inputs, limit=limit)
    rows_by_uuid = {item.uuid: item for item in candidate_rows}
    return SimilarityResult(
        source=source,
        candidates_evaluated=len(candidate_rows),
        truncated=truncated,
        matches=[(rows_by_uuid[match.item_uuid], match) for match in ranked],
    )


def _to_similarity_item(item: DSpaceItem) -> SimilarityItem:
    metadata: dict[str, list[str]] = {}
    for value in item.metadata_values:
        if value.field in FIELD_WEIGHTS:
            metadata.setdefault(value.field, []).append(value.value)
    return SimilarityItem(uuid=item.uuid, name=item.name, metadata=metadata)
