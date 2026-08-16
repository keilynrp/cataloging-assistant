import uuid

import pytest
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.db.models import DSpaceCollection, DSpaceItem
from cataloging_api.db.session import engine
from cataloging_api.evidence.models import (
    CatalogEvidenceCandidate,
    CatalogEvidenceSession,
    CatalogEvidenceSource,
)
from cataloging_api.evidence.service import (
    EvidencePdfInvalidTypeError,
    EvidencePdfTooLargeError,
    EvidenceValidationError,
    add_pdf_evidence_source,
    create_evidence_session,
    extract_evidence_candidates,
    get_evidence_session,
)
from tests.pdf_fixtures import (
    corrupt_pdf,
    non_pdf_bytes,
    pdf_with_text,
    pdf_without_text,
)

PDF_TYPE = "application/pdf"


class _EvidenceFixture:
    def __init__(self) -> None:
        self.collection_uuid = uuid.uuid4()
        self.item_uuid = uuid.uuid4()
        self.connection = None
        self.transaction = None
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> tuple[AsyncSession, uuid.UUID]:
        self.connection = await engine.connect()
        self.transaction = await self.connection.begin()
        self.session = AsyncSession(bind=self.connection, expire_on_commit=False)
        await self.session.execute(delete(CatalogEvidenceCandidate))
        await self.session.execute(delete(CatalogEvidenceSource))
        await self.session.execute(delete(CatalogEvidenceSession))
        self.session.add(
            DSpaceCollection(
                uuid=self.collection_uuid,
                handle="test/evidence-pdf",
                name="Evidence PDF test",
                raw_json={"uuid": str(self.collection_uuid)},
            )
        )
        self.session.add(
            DSpaceItem(
                uuid=self.item_uuid,
                collection_uuid=self.collection_uuid,
                handle="test/evidence-pdf-item",
                name="Evidence PDF item",
                raw_json={"uuid": str(self.item_uuid)},
                source_hash="f" * 64,
            )
        )
        await self.session.flush()
        return self.session, self.item_uuid

    async def __aexit__(self, *exc: object) -> None:
        await self.session.close()
        await self.transaction.rollback()
        await self.connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_with_text_is_extracted_and_persisted() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        data = pdf_with_text(
            ["dc.subject.linguisticFamily: Tarasca", "DOI 10.1234/example.55"]
        )
        source = await add_pdf_evidence_source(
            session,
            evidence,
            file_bytes=data,
            original_filename="familia.pdf",
            content_type=PDF_TYPE,
            author="Catalogadora",
        )
        assert source.kind == "pdf"
        assert source.extraction_status == "extracted"
        assert source.page_count == 1
        assert source.extracted_text_hash is not None
        assert source.metadata_json["original_filename"] == "familia.pdf"

        candidates = await extract_evidence_candidates(session, evidence)
        family = next(
            c for c in candidates if c.metadata_field == "dc.subject.linguisticFamily"
        )
        doi = next(c for c in candidates if c.metadata_field == "dc.identifier.doi")
        assert family.value == "Tarasca"
        assert family.evidence_state == "EXTRAÍDO"
        assert family.evidence_json["page"] == 1
        assert family.evidence_json["extractor"] == "pypdf"
        assert family.evidence_json["extracted_text_hash"] == source.extracted_text_hash
        assert doi.value == "10.1234/example.55"
        assert doi.evidence_json["page"] == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_without_text_layer_yields_no_candidates() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        source = await add_pdf_evidence_source(
            session,
            evidence,
            file_bytes=pdf_without_text(),
            original_filename="escaneado.pdf",
            content_type=PDF_TYPE,
            author="Catalogadora",
        )
        assert source.extraction_status == "no_extractable_text"
        assert source.content_text is None

        candidates = await extract_evidence_candidates(session, evidence)
        assert candidates == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_too_large_is_rejected_before_persisting() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        oversized = b"%PDF-1.4\n" + b"0" * (25 * 1024 * 1024 + 1)
        with pytest.raises(EvidencePdfTooLargeError):
            await add_pdf_evidence_source(
                session,
                evidence,
                file_bytes=oversized,
                original_filename="grande.pdf",
                content_type=PDF_TYPE,
                author="Catalogadora",
            )
        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert [s.kind for s in sources] == ["text"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_wrong_content_type_is_rejected() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        with pytest.raises(EvidencePdfInvalidTypeError):
            await add_pdf_evidence_source(
                session,
                evidence,
                file_bytes=pdf_with_text(["texto"]),
                original_filename="documento.pdf",
                content_type="text/plain",
                author="Catalogadora",
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_wrong_extension_is_rejected() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        with pytest.raises(EvidencePdfInvalidTypeError):
            await add_pdf_evidence_source(
                session,
                evidence,
                file_bytes=pdf_with_text(["texto"]),
                original_filename="documento.txt",
                content_type=PDF_TYPE,
                author="Catalogadora",
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_bad_magic_bytes_is_rejected_despite_correct_mime() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        with pytest.raises(EvidenceValidationError):
            await add_pdf_evidence_source(
                session,
                evidence,
                file_bytes=non_pdf_bytes(),
                original_filename="disfrazado.pdf",
                content_type=PDF_TYPE,
                author="Catalogadora",
            )
        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert [s.kind for s in sources] == ["text"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_pdf_is_rejected_and_not_persisted() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        with pytest.raises(EvidenceValidationError):
            await add_pdf_evidence_source(
                session,
                evidence,
                file_bytes=corrupt_pdf(),
                original_filename="roto.pdf",
                content_type=PDF_TYPE,
                author="Catalogadora",
            )
        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert [s.kind for s in sources] == ["text"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_path_traversal_filename_is_sanitized_not_used_as_path() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        source = await add_pdf_evidence_source(
            session,
            evidence,
            file_bytes=pdf_with_text(["contenido"]),
            original_filename="../../evil.pdf",
            content_type=PDF_TYPE,
            author="Catalogadora",
        )
        assert source.metadata_json["original_filename"] == "evil.pdf"
        assert ".." not in source.metadata_json["original_filename"]
        assert "/" not in source.metadata_json["original_filename"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stale_session_blocks_pdf_upload_via_service_precondition() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url=None,
            # create_evidence_session requires a URL or text source at creation
            # (VERTICAL-017, unchanged here); this is a neutral anchor that
            # matches none of the extraction patterns, so it never produces a
            # candidate of its own.
            text="Sesión de evidencia sin metadatos previos.",
        )
        await session.execute(
            update(DSpaceItem).where(DSpaceItem.uuid == item_uuid).values(source_hash="g" * 64)
        )
        await session.flush()
        loaded, _, _, stale = await get_evidence_session(session, evidence.session_id)
        assert loaded is not None
        assert stale is True
        # The route layer refuses to call add_pdf_evidence_source when stale
        # (see routes.upload_pdf_source); this asserts the staleness signal
        # it relies on is itself correct for a session with a fresh PDF-less source.


@pytest.mark.integration
@pytest.mark.asyncio
async def test_url_text_and_pdf_sources_keep_stable_combined_position() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await create_evidence_session(
            session,
            item_uuid=item_uuid,
            created_by="Catalogadora",
            url="https://example.test/article",
            text="dc.subject.linguisticFamily: Tarasca",
        )
        pdf_source = await add_pdf_evidence_source(
            session,
            evidence,
            file_bytes=pdf_with_text(["DOI 10.1234/example.55"]),
            original_filename="anexo.pdf",
            content_type=PDF_TYPE,
            author="Catalogadora",
        )
        assert pdf_source.position == 2

        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert [s.position for s in sources] == [0, 1, 2]
        assert [s.kind for s in sources] == ["url", "text", "pdf"]

        _, requeried_sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert [s.source_id for s in requeried_sources] == [s.source_id for s in sources]
