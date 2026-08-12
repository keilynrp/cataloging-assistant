import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogFinding,
    DSpaceCollection,
    DSpaceItem,
    DSpaceMetadataValue,
)
from cataloging_api.db.session import engine
from cataloging_api.dspace.normalizer import normalize_item
from cataloging_api.sync.repository import upsert_item
from tests.test_dspace_contract import load_fixture


@pytest.mark.integration
@pytest.mark.asyncio
async def test_item_upsert_is_idempotent() -> None:
    collection_uuid = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="123456789/4",
                name="P'UHREPECHA",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        await session.flush()
        item = normalize_item(
            load_fixture("item.json"), collection_uuid=str(collection_uuid), bundles=[]
        )
        assert (await upsert_item(session, item)).changed is True
        await session.flush()
        assert (await upsert_item(session, item)).changed is False
        await session.flush()

        item_count = await session.scalar(
            select(func.count()).select_from(DSpaceItem).where(DSpaceItem.uuid == item.uuid)
        )
        metadata_count = await session.scalar(
            select(func.count())
            .select_from(DSpaceMetadataValue)
            .where(DSpaceMetadataValue.item_uuid == item.uuid)
        )
        assert item_count == 1
        assert metadata_count == 3

        changed_raw = load_fixture("item.json")
        changed_raw["metadata"]["dc.subject.linguisticBranch"] = [{"value": "Tarasca", "place": 0}]
        changed_item = normalize_item(changed_raw, collection_uuid=str(collection_uuid), bundles=[])
        changed_result = await upsert_item(session, changed_item)
        assert changed_result.changed is True
        assert changed_result.has_new_findings is True
        await session.flush()
        finding = await session.scalar(
            select(CatalogFinding).where(CatalogFinding.item_uuid == item.uuid)
        )
        assert (finding.code, finding.severity) == ("CAT-LING-002", "error")
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
