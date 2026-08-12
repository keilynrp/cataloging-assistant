import uuid

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogFinding,
    CatalogReviewDecision,
    DSpaceCollection,
    DSpaceItem,
    ReviewDecisionKind,
)
from cataloging_api.db.session import engine
from cataloging_api.reviews.service import record_review_decision


@pytest.mark.integration
@pytest.mark.asyncio
async def test_review_decision_is_idempotent_and_keeps_finding_snapshot() -> None:
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    finding_id = uuid.uuid4()
    request_id = uuid.uuid4()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/review",
                name="Review test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        session.add(
            DSpaceItem(
                uuid=item_uuid,
                collection_uuid=collection_uuid,
                handle="test/item",
                name="Review item",
                raw_json={"uuid": str(item_uuid)},
                source_hash="a" * 64,
            )
        )
        session.add(
            CatalogFinding(
                finding_id=finding_id,
                item_uuid=item_uuid,
                code="CAT-TEST-001",
                severity="warning",
                affected_fields=["dc.test"],
                explanation="Test finding",
                fingerprint="b" * 64,
                rule_version="rule-v1",
                source_hash="a" * 64,
            )
        )
        await session.flush()

        first = await record_review_decision(
            session,
            item_uuid=item_uuid,
            finding_id=finding_id,
            request_id=request_id,
            decision=ReviewDecisionKind.confirmed,
            reviewer="Catalogadora",
            note="Confirmado con evidencia local.",
        )
        second = await record_review_decision(
            session,
            item_uuid=item_uuid,
            finding_id=finding_id,
            request_id=request_id,
            decision=ReviewDecisionKind.confirmed,
            reviewer="Catalogadora",
            note="Confirmado con evidencia local.",
        )
        assert first is not None
        assert second is not None
        assert first.decision_id == second.decision_id
        assert (
            await session.scalar(
                select(func.count())
                .select_from(CatalogReviewDecision)
                .where(CatalogReviewDecision.request_id == request_id)
            )
            == 1
        )

        await session.execute(delete(CatalogFinding).where(CatalogFinding.finding_id == finding_id))
        await session.flush()
        stored = await session.scalar(
            select(CatalogReviewDecision).where(
                CatalogReviewDecision.decision_id == first.decision_id
            )
        )
        assert stored is not None
        assert stored.finding_code == "CAT-TEST-001"
        assert stored.finding_affected_fields == ["dc.test"]
        assert stored.source_hash == "a" * 64
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
