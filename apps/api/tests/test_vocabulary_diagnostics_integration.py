import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import CatalogFinding, DSpaceCollection, DSpaceItem
from cataloging_api.db.session import engine
from cataloging_api.diagnostics.engine import VocabularyRule, diagnostic_profile_version
from cataloging_api.diagnostics.repository import replace_item_findings

FIELD = "dc.description.registeredLanguage"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_repository_persists_vocabulary_finding_and_profile_revision() -> None:
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    rule = VocabularyRule(
        revision_key=f"{FIELD}:{uuid.uuid4()}",
        name="Lenguas aprobadas",
        source_uri="https://example.test/languages",
        version_label="1",
        approved_by="Referente",
        terms=frozenset({"Purépecha"}),
    )
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/vocabulary-diagnostic",
                name="Vocabulary diagnostic",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        item = DSpaceItem(
            uuid=item_uuid,
            collection_uuid=collection_uuid,
            handle="test/vocabulary-diagnostic-item",
            name="Vocabulary diagnostic item",
            raw_json={"uuid": str(item_uuid)},
            source_hash="d" * 64,
        )
        session.add(item)
        await session.flush()

        result = await replace_item_findings(
            session,
            item_uuid=item_uuid,
            source_hash=item.source_hash,
            metadata_values=((FIELD, "purépecha"),),
            vocabularies={FIELD: rule},
        )
        await session.flush()
        finding = await session.scalar(
            select(CatalogFinding).where(CatalogFinding.item_uuid == item_uuid)
        )
        await session.refresh(item)

        assert result.count == 1
        assert result.has_new_findings is True
        assert finding is not None
        assert (finding.code, finding.severity) == ("CAT-VOCAB-001", "warning")
        assert item.diagnostic_profile_version == diagnostic_profile_version(
            (),
            (rule.profile_key,),
        )

        result = await replace_item_findings(
            session,
            item_uuid=item_uuid,
            source_hash=item.source_hash,
            metadata_values=((FIELD, "Purépecha"),),
            vocabularies={FIELD: rule},
        )
        await session.flush()
        assert result.count == 0
        assert result.has_new_findings is False
        assert (
            await session.scalar(
                select(func.count())
                .select_from(CatalogFinding)
                .where(CatalogFinding.item_uuid == item_uuid)
            )
            == 0
        )
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
