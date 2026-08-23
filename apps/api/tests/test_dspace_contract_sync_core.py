import uuid
from unittest.mock import AsyncMock

import pytest

from cataloging_api.dspace import contract_sync_core
from cataloging_api.dspace.client import DSpaceError, HalCollectionPage
from cataloging_api.dspace.contract_store import DSpaceContractSyncRun

ENDPOINT = "/core/metadatafields"


@pytest.mark.asyncio
async def test_collect_surface_resumes_from_confirmed_checkpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    run = DSpaceContractSyncRun(
        run_id=uuid.uuid4(),
        collector_version="vertical-022/1",
        status="RUNNING",
        checkpoints={"metadata_fields": 2},
        pages_completed=2,
        raw_payload_hashes=[],
    )
    session = AsyncMock()
    requested_pages: list[int] = []

    async def loader(*, page: int, size: int) -> HalCollectionPage:
        requested_pages.append(page)
        payload = {
            "_embedded": {"metadatafields": [{"id": page}]},
            "page": {"number": page, "totalPages": 3, "totalElements": 3},
        }
        return HalCollectionPage(
            items=[{"id": page}],
            page=page,
            total_pages=3,
            total_elements=3,
            raw_payload=payload,
        )

    async def persist(*_args, **kwargs) -> object:
        assert kwargs["endpoint"] == ENDPOINT
        checkpoints = dict(run.checkpoints or {})
        checkpoints[kwargs["surface"]] = kwargs["page_number"] + 1
        run.checkpoints = checkpoints
        return object()

    monkeypatch.setattr(contract_sync_core, "persist_page_and_advance_checkpoint", persist)

    await contract_sync_core._collect_surface(
        session,
        run=run,
        surface="metadata_fields",
        endpoint=ENDPOINT,
        loader=loader,
        page_size=100,
    )

    assert requested_pages == [2]
    assert run.checkpoints["metadata_fields"] == 3
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_collect_surface_commits_each_page_before_requesting_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = DSpaceContractSyncRun(
        run_id=uuid.uuid4(),
        collector_version="vertical-022/1",
        status="RUNNING",
        checkpoints={},
        pages_completed=0,
        raw_payload_hashes=[],
    )
    session = AsyncMock()
    events: list[str] = []

    async def loader(*, page: int, size: int) -> HalCollectionPage:
        events.append(f"load:{page}")
        return HalCollectionPage(
            items=[{"id": page}],
            page=page,
            total_pages=2,
            total_elements=2,
            raw_payload={"_embedded": {"x": [{"id": page}]}, "page": {"number": page}},
        )

    async def persist(*_args, **kwargs) -> object:
        page_number = kwargs["page_number"]
        events.append(f"persist:{page_number}")
        run.checkpoints = {"metadata_fields": page_number + 1}
        return object()

    async def commit() -> None:
        events.append("commit")

    session.commit.side_effect = commit
    monkeypatch.setattr(contract_sync_core, "persist_page_and_advance_checkpoint", persist)

    await contract_sync_core._collect_surface(
        session,
        run=run,
        surface="metadata_fields",
        endpoint=ENDPOINT,
        loader=loader,
        page_size=100,
    )

    assert events == [
        "load:0",
        "persist:0",
        "commit",
        "load:1",
        "persist:1",
        "commit",
    ]


@pytest.mark.asyncio
async def test_collect_surface_rejects_mismatched_response_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = DSpaceContractSyncRun(
        run_id=uuid.uuid4(),
        collector_version="vertical-022/1",
        status="RUNNING",
        checkpoints={"metadata_fields": 1},
        pages_completed=1,
        raw_payload_hashes=[],
    )
    session = AsyncMock()

    async def loader(*, page: int, size: int) -> HalCollectionPage:
        assert page == 1
        return HalCollectionPage(
            items=[],
            page=0,
            total_pages=1,
            total_elements=0,
            raw_payload={"_embedded": {"metadatafields": []}, "page": {"number": 0}},
        )

    persist = AsyncMock()
    monkeypatch.setattr(contract_sync_core, "persist_page_and_advance_checkpoint", persist)

    with pytest.raises(DSpaceError) as exc_info:
        await contract_sync_core._collect_surface(
            session,
            run=run,
            surface="metadata_fields",
            endpoint=ENDPOINT,
            loader=loader,
            page_size=100,
        )

    assert exc_info.value.code == "invalid_hal"
    persist.assert_not_awaited()
    session.commit.assert_not_awaited()
