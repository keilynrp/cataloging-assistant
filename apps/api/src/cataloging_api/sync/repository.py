import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogDraft,
    DSpaceBitstream,
    DSpaceBundle,
    DSpaceCollection,
    DSpaceItem,
    DSpaceMetadataValue,
    NotificationSeverity,
    SyncRun,
)
from cataloging_api.diagnostics.engine import (
    VocabularyRule,
    diagnostic_profile_version,
)
from cataloging_api.diagnostics.repository import replace_item_findings
from cataloging_api.dspace.normalizer import ItemData
from cataloging_api.notifications.constants import EventType
from cataloging_api.notifications.producer import record_notification_event


async def upsert_collection(session: AsyncSession, raw: dict[str, object]) -> None:
    collection_uuid = uuid.UUID(str(raw["uuid"]))
    statement = insert(DSpaceCollection).values(
        uuid=collection_uuid,
        handle=raw.get("handle"),
        name=raw.get("name") or "(sin nombre)",
        last_modified=_parse_datetime(raw.get("lastModified")),
        raw_json=raw,
        synced_at=datetime.now(UTC),
    )
    statement = statement.on_conflict_do_update(
        index_elements=[DSpaceCollection.uuid],
        set_={
            "handle": statement.excluded.handle,
            "name": statement.excluded.name,
            "last_modified": statement.excluded.last_modified,
            "raw_json": statement.excluded.raw_json,
            "synced_at": statement.excluded.synced_at,
        },
    )
    await session.execute(statement)


@dataclass(frozen=True)
class UpsertResult:
    changed: bool
    has_new_findings: bool


async def upsert_item(
    session: AsyncSession,
    item: ItemData,
    *,
    required_fields: Iterable[str] = (),
    vocabularies: Mapping[str, VocabularyRule] | None = None,
) -> UpsertResult:
    required = tuple(required_fields)
    rules = dict(vocabularies or {})
    existing = (
        await session.execute(
            select(DSpaceItem.source_hash, DSpaceItem.diagnostic_profile_version).where(
                DSpaceItem.uuid == item.uuid
            )
        )
    ).one_or_none()
    existing_hash = existing[0] if existing else None
    existing_profile = existing[1] if existing else None
    active_profile = diagnostic_profile_version(
        required,
        (rule.profile_key for rule in rules.values()),
    )
    now = datetime.now(UTC)
    changed = existing_hash != item.source_hash
    statement = insert(DSpaceItem).values(
        uuid=item.uuid,
        collection_uuid=item.collection_uuid,
        handle=item.handle,
        name=item.name,
        last_modified=item.last_modified,
        raw_json=item.raw_json,
        source_hash=item.source_hash,
        is_active=True,
        last_seen_at=now,
        synced_at=now,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[DSpaceItem.uuid],
        set_={
            "collection_uuid": statement.excluded.collection_uuid,
            "handle": statement.excluded.handle,
            "name": statement.excluded.name,
            "last_modified": statement.excluded.last_modified,
            "raw_json": statement.excluded.raw_json,
            "source_hash": statement.excluded.source_hash,
            "is_active": True,
            "last_seen_at": now,
            "synced_at": now,
        },
    )
    await session.execute(statement)
    if not changed:
        has_new_findings = False
        if existing_profile != active_profile:
            result = await replace_item_findings(
                session,
                item_uuid=item.uuid,
                source_hash=item.source_hash,
                metadata_values=((value.field, value.value) for value in item.metadata_values),
                required_fields=required,
                vocabularies=rules,
            )
            has_new_findings = result.has_new_findings
        return UpsertResult(changed=False, has_new_findings=has_new_findings)

    await session.execute(
        delete(DSpaceMetadataValue).where(DSpaceMetadataValue.item_uuid == item.uuid)
    )
    await session.execute(delete(DSpaceBundle).where(DSpaceBundle.item_uuid == item.uuid))
    session.add_all(
        [
            DSpaceMetadataValue(
                item_uuid=item.uuid,
                field=value.field,
                value=value.value,
                language=value.language,
                authority=value.authority,
                confidence=value.confidence,
                place=value.place,
            )
            for value in item.metadata_values
        ]
    )
    for bundle in item.bundles:
        session.add(
            DSpaceBundle(
                uuid=bundle.uuid,
                item_uuid=item.uuid,
                name=bundle.name,
                raw_json=bundle.raw_json,
                bitstreams=[
                    DSpaceBitstream(
                        uuid=bitstream.uuid,
                        name=bitstream.name,
                        mime_type=bitstream.mime_type,
                        size_bytes=bitstream.size_bytes,
                        content_url=bitstream.content_url,
                        raw_json=bitstream.raw_json,
                    )
                    for bitstream in bundle.bitstreams
                ],
            )
        )
    finding_result = await replace_item_findings(
        session,
        item_uuid=item.uuid,
        source_hash=item.source_hash,
        metadata_values=((value.field, value.value) for value in item.metadata_values),
        required_fields=required,
        vocabularies=rules,
    )
    if existing_hash is not None:
        stale_draft = await session.scalar(
            select(CatalogDraft).where(
                CatalogDraft.item_uuid == item.uuid,
                CatalogDraft.base_source_hash != item.source_hash,
            )
        )
        if stale_draft is not None:
            await record_notification_event(
                session,
                event_type=EventType.DRAFT_STALE,
                aggregate_type="draft",
                aggregate_id=str(stale_draft.draft_id),
                collection_uuid=item.collection_uuid,
                severity=NotificationSeverity.warning,
                title="Borrador local obsoleto",
                summary="La fuente DSpace del ítem cambió desde que se abrió el borrador.",
                deduplication_key=f"draft.stale:{stale_draft.draft_id}:{item.source_hash}",
                target_path=f"/items/{item.uuid}",
            )
    return UpsertResult(changed=True, has_new_findings=finding_result.has_new_findings)


async def mark_missing_inactive(
    session: AsyncSession, collection_uuid: uuid.UUID, seen_item_uuids: set[uuid.UUID]
) -> None:
    statement = update(DSpaceItem).where(DSpaceItem.collection_uuid == collection_uuid)
    if seen_item_uuids:
        statement = statement.where(DSpaceItem.uuid.not_in(seen_item_uuids))
    await session.execute(statement.values(is_active=False, synced_at=datetime.now(UTC)))


async def get_resumable_run(session: AsyncSession, collection_uuid: uuid.UUID) -> SyncRun | None:
    return await session.scalar(
        select(SyncRun)
        .where(
            SyncRun.collection_uuid == collection_uuid,
            SyncRun.status.in_(["partial", "failed"]),
        )
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    )


def _parse_datetime(value: object) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
