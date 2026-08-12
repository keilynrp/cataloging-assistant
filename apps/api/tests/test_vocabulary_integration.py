import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import (
    CatalogVocabularyRevision,
    DSpaceCollection,
    DSpaceItem,
    DSpaceMetadataValue,
)
from cataloging_api.db.session import engine
from cataloging_api.vocabularies.service import (
    VocabularyConflictError,
    list_vocabulary_revisions,
    replace_active_vocabulary,
    validate_item_metadata,
)


def revision_payload(
    *,
    request_id: uuid.UUID,
    terms: list[str],
    version: str,
) -> dict[str, object]:
    return {
        "request_id": request_id,
        "field": "dc.subject.linguisticFamily",
        "name": "Vocabulario institucional de prueba",
        "source_uri": "https://example.test/vocab/families",
        "version_label": version,
        "approved_by": "Referente catalográfico",
        "approval_note": "Fixture aprobado sólo para la prueba automatizada.",
        "terms": [{"value": term, "authority": None, "language": "es"} for term in terms],
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vocabulary_revisions_are_auditable_idempotent_and_validate_exactly() -> None:
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    first_request = uuid.uuid4()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        await session.execute(
            delete(CatalogVocabularyRevision).where(
                CatalogVocabularyRevision.field == "dc.subject.linguisticFamily"
            )
        )
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/vocabulary",
                name="Vocabulary test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        item = DSpaceItem(
            uuid=item_uuid,
            collection_uuid=collection_uuid,
            handle="test/vocabulary-item",
            name="Vocabulary item",
            raw_json={"uuid": str(item_uuid)},
            source_hash="a" * 64,
        )
        item.metadata_values.append(
            DSpaceMetadataValue(
                field="dc.subject.linguisticFamily",
                value="Tarasca",
                language="es",
                authority=None,
                confidence=600,
                place=0,
            )
        )
        session.add(item)
        await session.flush()

        first = await replace_active_vocabulary(
            session,
            **revision_payload(
                request_id=first_request,
                terms=["Tarasca"],
                version="1",
            ),
        )
        repeated = await replace_active_vocabulary(
            session,
            **revision_payload(
                request_id=first_request,
                terms=["Tarasca"],
                version="1",
            ),
        )
        assert repeated.revision_id == first.revision_id
        validation = await validate_item_metadata(session, item_uuid)
        assert validation is not None
        assert validation["status"] == "valid"
        assert validation["fields"][0]["values"][0]["approved"] is True

        with pytest.raises(VocabularyConflictError):
            await replace_active_vocabulary(
                session,
                **revision_payload(
                    request_id=first_request,
                    terms=["Yuto-nahua"],
                    version="changed",
                ),
            )

        second = await replace_active_vocabulary(
            session,
            **revision_payload(
                request_id=uuid.uuid4(),
                terms=["Yuto-nahua"],
                version="2",
            ),
        )
        assert second.revision_id != first.revision_id
        active = await list_vocabulary_revisions(session, field="dc.subject.linguisticFamily")
        history = await list_vocabulary_revisions(
            session, field="dc.subject.linguisticFamily", include_history=True
        )
        assert [revision.revision_id for revision in active] == [second.revision_id]
        assert len(history) == 2
        assert sum(revision.is_active for revision in history) == 1

        validation = await validate_item_metadata(session, item_uuid)
        assert validation is not None
        assert validation["status"] == "invalid"
        assert validation["fields"][0]["values"][0]["approved"] is False
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
