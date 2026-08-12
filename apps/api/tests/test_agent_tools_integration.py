import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.agent.tools import TOOLS_BY_NAME
from cataloging_api.db.models import DSpaceCollection, DSpaceItem
from cataloging_api.db.session import engine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_items_tool_returns_matches_and_citations() -> None:
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/agent-tools",
                name="Agent tools test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        session.add(
            DSpaceItem(
                uuid=item_uuid,
                collection_uuid=collection_uuid,
                handle="test/agent-tools-item",
                name="Xilonen agent tools item",
                raw_json={"uuid": str(item_uuid)},
                source_hash="a" * 64,
            )
        )
        await session.flush()

        result = await TOOLS_BY_NAME["search_items"].handler(session, {"q": "Xilonen"})

        assert result.output["total"] >= 1
        assert any(item["uuid"] == str(item_uuid) for item in result.output["items"])
        assert {"label": "Xilonen agent tools item", "target_path": f"/items/{item_uuid}"} in (
            result.citations
        )
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_item_tool_returns_error_payload_for_missing_item() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        result = await TOOLS_BY_NAME["get_item"].handler(session, {"item_uuid": str(uuid.uuid4())})
        assert "error" in result.output
        assert result.citations == []
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_item_tool_rejects_invalid_uuid_without_raising() -> None:
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        result = await TOOLS_BY_NAME["get_item"].handler(session, {"item_uuid": "not-a-uuid"})
        assert "error" in result.output
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_item_tool_returns_detail_and_citation() -> None:
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/agent-get-item",
                name="Agent get_item test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        session.add(
            DSpaceItem(
                uuid=item_uuid,
                collection_uuid=collection_uuid,
                handle="test/agent-get-item-item",
                name="Agent get_item item",
                raw_json={"uuid": str(item_uuid), "secret": "should-not-leak-raw-json"},
                source_hash="b" * 64,
            )
        )
        await session.flush()

        result = await TOOLS_BY_NAME["get_item"].handler(session, {"item_uuid": str(item_uuid)})

        assert result.output["name"] == "Agent get_item item"
        assert "raw_json" not in result.output
        assert result.citations == [
            {"label": "Agent get_item item", "target_path": f"/items/{item_uuid}"}
        ]
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
