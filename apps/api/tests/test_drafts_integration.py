import uuid

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogDraft,
    CatalogDraftRevision,
    CatalogVocabularyRevision,
    DSpaceCollection,
    DSpaceItem,
    DSpaceMetadataValue,
)
from cataloging_api.db.session import engine
from cataloging_api.drafts.service import (
    DraftStaleError,
    append_draft_revision,
    create_draft,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_draft_is_versioned_idempotent_and_detects_stale_source() -> None:
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    create_request_id = uuid.uuid4()
    revision_request_id = uuid.uuid4()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        await session.execute(delete(CatalogVocabularyRevision))
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/drafts",
                name="Draft test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        item = DSpaceItem(
            uuid=item_uuid,
            collection_uuid=collection_uuid,
            handle="test/draft-item",
            name="Draft item",
            raw_json={"uuid": str(item_uuid)},
            source_hash="a" * 64,
        )
        item.metadata_values.append(
            DSpaceMetadataValue(
                field="dc.subject.linguiscgroup",
                value="Tarasco (Purépecha)",
                language="es",
                authority=None,
                confidence=600,
                place=0,
            )
        )
        session.add(item)
        await session.flush()

        draft = await create_draft(
            session,
            item_uuid=item_uuid,
            request_id=create_request_id,
            author="Catalogadora",
            note="Primera propuesta humana.",
            changes={"dc.subject.linguisticFamily": ["Tarasca"]},
        )
        repeated = await create_draft(
            session,
            item_uuid=item_uuid,
            request_id=create_request_id,
            author="Catalogadora",
            note="Primera propuesta humana.",
            changes={"dc.subject.linguisticFamily": ["Tarasca"]},
        )
        assert draft is not None
        assert repeated is not None
        assert repeated.draft_id == draft.draft_id
        assert draft.base_metadata["dc.subject.linguiscgroup"][0]["language"] == "es"
        assert draft.revisions[0].validation_snapshot["status"] == "not_configured"

        revised = await append_draft_revision(
            session,
            item_uuid=item_uuid,
            draft_id=draft.draft_id,
            request_id=revision_request_id,
            expected_version=1,
            author="Catalogadora",
            note="Segunda revisión humana.",
            changes={"dc.subject.linguisticFamily": ["Tarasca", "Yuto-nahua"]},
        )
        assert revised is not None
        assert [revision.version for revision in revised.revisions] == [1, 2]
        assert revised.revisions[-1].validation_snapshot["status"] == "not_configured"
        assert (
            await session.scalar(
                select(func.count())
                .select_from(CatalogDraft)
                .where(CatalogDraft.item_uuid == item_uuid)
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count())
                .select_from(CatalogDraftRevision)
                .where(CatalogDraftRevision.draft_id == draft.draft_id)
            )
            == 2
        )

        await session.execute(
            update(DSpaceItem).where(DSpaceItem.uuid == item_uuid).values(source_hash="c" * 64)
        )
        await session.flush()
        with pytest.raises(DraftStaleError):
            await append_draft_revision(
                session,
                item_uuid=item_uuid,
                draft_id=draft.draft_id,
                request_id=uuid.uuid4(),
                expected_version=2,
                author="Catalogadora",
                note="Debe bloquearse.",
                changes={"dc.subject.linguisticFamily": ["Tarasca"]},
            )
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
