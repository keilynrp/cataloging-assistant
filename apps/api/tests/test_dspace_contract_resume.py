from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cataloging_api.dspace.contract_sync_core import _surface_checkpoint_is_complete


@pytest.mark.asyncio
async def test_completed_surface_checkpoint_is_skipped() -> None:
    run = SimpleNamespace(
        run_id="run-1",
        checkpoints={"metadata_fields": 3},
    )
    persisted = SimpleNamespace(
        raw_payload={
            "page": {
                "number": 2,
                "totalPages": 3,
                "totalElements": 292,
            }
        }
    )
    result = SimpleNamespace(scalar_one_or_none=lambda: persisted)
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    assert await _surface_checkpoint_is_complete(
        session,
        run=run,
        surface="metadata_fields",
    ) is True


@pytest.mark.asyncio
async def test_incomplete_surface_checkpoint_is_not_skipped() -> None:
    run = SimpleNamespace(
        run_id="run-1",
        checkpoints={"metadata_fields": 2},
    )
    persisted = SimpleNamespace(
        raw_payload={
            "page": {
                "number": 1,
                "totalPages": 3,
                "totalElements": 292,
            }
        }
    )
    result = SimpleNamespace(scalar_one_or_none=lambda: persisted)
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    assert await _surface_checkpoint_is_complete(
        session,
        run=run,
        surface="metadata_fields",
    ) is False


@pytest.mark.asyncio
async def test_checkpoint_without_persisted_last_page_is_not_trusted() -> None:
    run = SimpleNamespace(
        run_id="run-1",
        checkpoints={"metadata_fields": 3},
    )
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    assert await _surface_checkpoint_is_complete(
        session,
        run=run,
        surface="metadata_fields",
    ) is False
