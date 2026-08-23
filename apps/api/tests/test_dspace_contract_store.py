import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from cataloging_api.dspace.contract_store import (
    DSpaceContractRawPage,
    DSpaceContractSyncRun,
    canonical_raw_hash,
    checkpoint_next_page,
    persist_page_and_advance_checkpoint,
)


def _run() -> DSpaceContractSyncRun:
    return DSpaceContractSyncRun(
        run_id=uuid.uuid4(),
        collector_version="vertical-022/1",
        status="RUNNING",
        checkpoints={},
        pages_completed=0,
        raw_payload_hashes=[],
    )


def _session_with_existing(existing: DSpaceContractRawPage | None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing
    session.execute.return_value = result
    return session


def test_canonical_raw_hash_is_order_independent_for_json_objects() -> None:
    left = {"page": {"number": 0}, "_embedded": {"x": [{"b": 2, "a": 1}]}}
    right = {"_embedded": {"x": [{"a": 1, "b": 2}]}, "page": {"number": 0}}
    assert canonical_raw_hash(left) == canonical_raw_hash(right)


@pytest.mark.asyncio
async def test_new_page_is_persisted_before_checkpoint_advances() -> None:
    run = _run()
    session = _session_with_existing(None)
    payload = {"_embedded": {"metadatafields": [{"id": 1}]}, "page": {"number": 0}}

    page = await persist_page_and_advance_checkpoint(
        session,
        run=run,
        surface="metadata_fields",
        page_number=0,
        request_params={"page": 0, "size": 100},
        raw_payload=payload,
    )

    session.add.assert_called_once_with(page)
    assert session.flush.await_count == 2
    assert run.pages_completed == 1
    assert checkpoint_next_page(run, "metadata_fields") == 1
    assert run.raw_payload_hashes == [canonical_raw_hash(payload)]


@pytest.mark.asyncio
async def test_retry_same_page_and_hash_is_idempotent() -> None:
    run = _run()
    payload = {"_embedded": {"metadatafields": [{"id": 1}]}, "page": {"number": 0}}
    existing = DSpaceContractRawPage(
        page_id=uuid.uuid4(),
        run_id=run.run_id,
        surface="metadata_fields",
        page_number=0,
        request_params={"page": 0},
        raw_payload=payload,
        raw_hash=canonical_raw_hash(payload),
    )
    session = _session_with_existing(existing)

    returned = await persist_page_and_advance_checkpoint(
        session,
        run=run,
        surface="metadata_fields",
        page_number=0,
        request_params={"page": 0},
        raw_payload=payload,
    )

    assert returned is existing
    session.add.assert_not_called()
    assert run.pages_completed == 0
    assert checkpoint_next_page(run, "metadata_fields") == 1


@pytest.mark.asyncio
async def test_retry_same_page_with_different_evidence_never_overwrites() -> None:
    run = _run()
    first_payload = {"_embedded": {"metadatafields": [{"id": 1}]}, "page": {"number": 0}}
    existing = DSpaceContractRawPage(
        page_id=uuid.uuid4(),
        run_id=run.run_id,
        surface="metadata_fields",
        page_number=0,
        request_params={"page": 0},
        raw_payload=first_payload,
        raw_hash=canonical_raw_hash(first_payload),
    )
    session = _session_with_existing(existing)

    with pytest.raises(ValueError, match="contract_raw_page_conflict"):
        await persist_page_and_advance_checkpoint(
            session,
            run=run,
            surface="metadata_fields",
            page_number=0,
            request_params={"page": 0},
            raw_payload={"_embedded": {"metadatafields": [{"id": 999}]}},
        )

    assert checkpoint_next_page(run, "metadata_fields") == 0
    session.add.assert_not_called()
