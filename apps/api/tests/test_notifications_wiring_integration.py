import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogFinding,
    DSpaceCollection,
    DSpaceItem,
    NotificationEvent,
    ReviewDecisionKind,
)
from cataloging_api.db.session import engine
from cataloging_api.reviews.service import record_review_decision
from cataloging_api.vocabularies.service import replace_active_vocabulary


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deferred_review_decision_emits_notification_event() -> None:
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
                handle="test/notify-review",
                name="Notify review test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        session.add(
            DSpaceItem(
                uuid=item_uuid,
                collection_uuid=collection_uuid,
                handle="test/notify-review-item",
                name="Notify review item",
                raw_json={"uuid": str(item_uuid)},
                source_hash="a" * 64,
            )
        )
        session.add(
            CatalogFinding(
                finding_id=finding_id,
                item_uuid=item_uuid,
                code="CAT-TEST-002",
                severity="warning",
                affected_fields=["dc.test"],
                explanation="Test finding",
                fingerprint="c" * 64,
                rule_version="rule-v1",
                source_hash="a" * 64,
            )
        )
        await session.flush()

        review = await record_review_decision(
            session,
            item_uuid=item_uuid,
            finding_id=finding_id,
            request_id=request_id,
            decision=ReviewDecisionKind.deferred,
            reviewer="Catalogadora",
            note="Pospuesto para revisión posterior.",
        )
        assert review is not None

        event = await session.scalar(
            select(NotificationEvent).where(
                NotificationEvent.deduplication_key == f"review.deferred:{request_id}"
            )
        )
        assert event is not None
        assert event.event_type == "review.deferred"
        assert event.collection_uuid == collection_uuid
        assert event.target_path == f"/items/{item_uuid}"
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_promoting_a_vocabulary_revision_emits_notification_event() -> None:
    request_id = uuid.uuid4()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        revision = await replace_active_vocabulary(
            session,
            request_id=request_id,
            field="dc.subject.linguisticFamily",
            name="Familias lingüísticas de prueba",
            source_uri="https://example.org/vocab",
            version_label="v-test",
            approved_by="Referente catalográfico",
            approval_note="Aprobación de prueba.",
            terms=[{"value": "Tarasca", "authority": None, "language": None}],
        )
        assert revision is not None

        event = await session.scalar(
            select(NotificationEvent).where(
                NotificationEvent.deduplication_key == f"vocabulary.promoted:{revision.revision_id}"
            )
        )
        assert event is not None
        assert event.event_type == "vocabulary.promoted"
        assert event.target_path == "/controlled-terms"
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
