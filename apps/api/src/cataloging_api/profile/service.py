import uuid
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from cataloging_api.db.models import (
    DSpaceCollection,
    DSpaceItem,
    DSpaceMetadataValue,
    SyncRun,
)
from cataloging_api.profile.metrics import (
    FIELD_KEYS,
    FIELD_LABELS,
    RELATIONSHIP_SPECS,
    safe_rate,
    summarize_completeness_patterns,
)

TOP_VALUES_LIMIT = 10
TOP_RELATIONSHIPS_LIMIT = 25


async def build_collection_profile(
    session: AsyncSession, collection_uuid: uuid.UUID
) -> dict[str, object] | None:
    collection = await session.get(DSpaceCollection, collection_uuid)
    if collection is None:
        return None

    item_uuids = list(
        await session.scalars(
            select(DSpaceItem.uuid)
            .where(
                DSpaceItem.collection_uuid == collection_uuid,
                DSpaceItem.is_active.is_(True),
            )
            .order_by(DSpaceItem.uuid)
        )
    )
    active_items = len(item_uuids)
    nonblank = func.btrim(DSpaceMetadataValue.value) != ""

    coverage_rows = (
        await session.execute(
            select(
                DSpaceMetadataValue.field,
                func.count(distinct(DSpaceMetadataValue.item_uuid)),
                func.count(DSpaceMetadataValue.id),
                func.count(distinct(DSpaceMetadataValue.value)),
            )
            .join(DSpaceItem, DSpaceItem.uuid == DSpaceMetadataValue.item_uuid)
            .where(
                DSpaceItem.collection_uuid == collection_uuid,
                DSpaceItem.is_active.is_(True),
                DSpaceMetadataValue.field.in_(FIELD_KEYS),
                nonblank,
            )
            .group_by(DSpaceMetadataValue.field)
        )
    ).all()
    coverage_by_field = {
        field: (item_count, value_count, distinct_values)
        for field, item_count, value_count, distinct_values in coverage_rows
    }

    value_rows = (
        await session.execute(
            select(
                DSpaceMetadataValue.field,
                DSpaceMetadataValue.value,
                func.count(distinct(DSpaceMetadataValue.item_uuid)).label("item_count"),
                func.count(DSpaceMetadataValue.id).label("value_count"),
            )
            .join(DSpaceItem, DSpaceItem.uuid == DSpaceMetadataValue.item_uuid)
            .where(
                DSpaceItem.collection_uuid == collection_uuid,
                DSpaceItem.is_active.is_(True),
                DSpaceMetadataValue.field.in_(FIELD_KEYS),
                nonblank,
            )
            .group_by(DSpaceMetadataValue.field, DSpaceMetadataValue.value)
            .order_by(
                DSpaceMetadataValue.field,
                func.count(distinct(DSpaceMetadataValue.item_uuid)).desc(),
                DSpaceMetadataValue.value,
            )
        )
    ).all()
    top_values_by_field: dict[str, list[dict[str, object]]] = defaultdict(list)
    for field, value, item_count, value_count in value_rows:
        if len(top_values_by_field[field]) < TOP_VALUES_LIMIT:
            top_values_by_field[field].append(
                {
                    "value": value,
                    "item_count": item_count,
                    "value_count": value_count,
                    "item_rate": safe_rate(item_count, active_items),
                }
            )

    presence_rows = (
        await session.execute(
            select(DSpaceMetadataValue.item_uuid, DSpaceMetadataValue.field)
            .join(DSpaceItem, DSpaceItem.uuid == DSpaceMetadataValue.item_uuid)
            .where(
                DSpaceItem.collection_uuid == collection_uuid,
                DSpaceItem.is_active.is_(True),
                DSpaceMetadataValue.field.in_(FIELD_KEYS),
                nonblank,
            )
            .distinct()
        )
    ).all()
    patterns = summarize_completeness_patterns(item_uuids, presence_rows)

    relationships = []
    for from_field, to_field in RELATIONSHIP_SPECS:
        left = aliased(DSpaceMetadataValue)
        right = aliased(DSpaceMetadataValue)
        rows = (
            await session.execute(
                select(
                    left.value,
                    right.value,
                    func.count(distinct(left.item_uuid)).label("item_count"),
                )
                .join(DSpaceItem, DSpaceItem.uuid == left.item_uuid)
                .join(
                    right,
                    and_(right.item_uuid == left.item_uuid, right.field == to_field),
                )
                .where(
                    DSpaceItem.collection_uuid == collection_uuid,
                    DSpaceItem.is_active.is_(True),
                    left.field == from_field,
                    func.btrim(left.value) != "",
                    func.btrim(right.value) != "",
                )
                .group_by(left.value, right.value)
                .order_by(func.count(distinct(left.item_uuid)).desc(), left.value, right.value)
            )
        ).all()
        relationships.append(
            {
                "from_field": from_field,
                "to_field": to_field,
                "observed_pairs": len(rows),
                "pairs": [
                    {
                        "from_value": from_value,
                        "to_value": to_value,
                        "item_count": item_count,
                        "item_rate": safe_rate(item_count, active_items),
                    }
                    for from_value, to_value, item_count in rows[:TOP_RELATIONSHIPS_LIMIT]
                ],
            }
        )

    latest_sync = await session.scalar(
        select(SyncRun)
        .where(SyncRun.collection_uuid == collection_uuid)
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )
    fields = []
    for field in FIELD_KEYS:
        item_count, value_count, distinct_values = coverage_by_field.get(field, (0, 0, 0))
        fields.append(
            {
                "field": field,
                "label": FIELD_LABELS[field],
                "item_count": item_count,
                "missing_item_count": active_items - item_count,
                "value_count": value_count,
                "distinct_value_count": distinct_values,
                "coverage_rate": safe_rate(item_count, active_items),
                "top_values": top_values_by_field[field],
            }
        )

    return {
        "collection_uuid": collection.uuid,
        "collection_name": collection.name,
        "collection_handle": collection.handle,
        "generated_at": datetime.now(UTC),
        "source": "PostgreSQL local derivado de DSpace",
        "grain": "Ítem activo de la colección piloto",
        "active_items": active_items,
        "latest_sync_status": latest_sync.status.value if latest_sync else None,
        "latest_sync_finished_at": latest_sync.finished_at if latest_sync else None,
        "fields": fields,
        "completeness_patterns": [
            {
                "fields_present": list(pattern.fields_present),
                "item_count": pattern.item_count,
                "rate": pattern.rate,
            }
            for pattern in patterns
        ],
        "relationships": relationships,
        "interpretation": (
            "Las relaciones son observaciones del corpus, no vocabularios ni reglas "
            "institucionales aprobadas."
        ),
    }
