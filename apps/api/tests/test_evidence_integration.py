import uuid

import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import CatalogVocabularyRevision, DSpaceCollection, DSpaceItem
from cataloging_api.db.session import engine
from cataloging_api.evidence.models import CatalogEvidenceCandidate, CatalogEvidenceSession, CatalogEvidenceSource
from cataloging_api.evidence.service import EvidenceStaleError, EvidenceValidationError, copy_candidates_to_draft, create_evidence_session, extract_evidence_candidates, get_evidence_session
from cataloging_api.vocabularies.service import replace_active_vocabulary


async def activate_family_vocabulary(session: AsyncSession, terms: list[str], version: str) -> None:
    await replace_active_vocabulary(
        session,
        request_id=uuid.uuid4(),
        field="dc.subject.linguisticFamily",
        name="Fixture familias",
        source_uri="https://example.test/families",
        version_label=version,
        approved_by="Catalogadora",
        approval_note="Fixture de integración VERTICAL-017.",
        terms=[{"value": term, "authority": None, "language": "es"} for term in terms],
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_evidence_snapshot_is_idempotent_revalidated_and_stale_safe() -> None:
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)
    try:
        await session.execute(delete(CatalogEvidenceCandidate))
        await session.execute(delete(CatalogEvidenceSource))
        await session.execute(delete(CatalogEvidenceSession))
        await session.execute(
            delete(CatalogVocabularyRevision).where(
                CatalogVocabularyRevision.field == "dc.subject.linguisticFamily"
            )
        )
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/evidence",
                name="Evidence test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        session.add(
            DSpaceItem(
                uuid=item_uuid,
                collection_uuid=collection_uuid,
                handle="test/evidence-item",
                name="Evidence item",
                raw_json={"uuid": str(item_uuid)},
                source_hash="a" * 64,
            )
        )
        await session.flush()

        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url="https://example.test/article",
            text="dc.subject.linguisticFamily: Tarasca\nDOI 10.1234/example.55",
        )
        first = await extract_evidence_candidates(session, evidence)
        repeated = await extract_evidence_candidates(session, evidence)
        assert [candidate.candidate_id for candidate in repeated] == [candidate.candidate_id for candidate in first]

        family = next(candidate for candidate in first if candidate.metadata_field == "dc.subject.linguisticFamily")
        assert family.validation_json["status"] == "no_vocabulary"

        await activate_family_vocabulary(session, ["Yuto-nahua"], "1")
        with pytest.raises(EvidenceValidationError):
            await copy_candidates_to_draft(
                session,
                evidence_session=evidence,
                candidate_ids=[family.candidate_id],
                request_id=uuid.uuid4(),
                author="Catalogadora",
                note="Debe revalidar contra autoridad vigente.",
                draft_id=None,
                expected_version=None,
            )

        await activate_family_vocabulary(session, ["Tarasca"], "2")
        draft = await copy_candidates_to_draft(
            session,
            evidence_session=evidence,
            candidate_ids=[family.candidate_id],
            request_id=uuid.uuid4(),
            author="Catalogadora",
            note="Valor revisado contra vocabulario vigente.",
            draft_id=None,
            expected_version=None,
        )
        assert draft is not None
        assert draft.revisions[-1].metadata_patch["dc.subject.linguisticFamily"][0]["value"] == "Tarasca"

        await session.execute(
            update(DSpaceItem).where(DSpaceItem.uuid == item_uuid).values(source_hash="b" * 64)
        )
        await session.flush()
        loaded, _, _, stale = await get_evidence_session(session, evidence.session_id)
        assert loaded is not None
        assert stale is True
        with pytest.raises(EvidenceStaleError):
            await copy_candidates_to_draft(
                session,
                evidence_session=evidence,
                candidate_ids=[family.candidate_id],
                request_id=uuid.uuid4(),
                author="Catalogadora",
                note="Debe bloquearse por staleness.",
                draft_id=draft.draft_id,
                expected_version=1,
            )
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
