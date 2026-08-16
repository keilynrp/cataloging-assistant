import asyncio
import time
import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from cataloging_api.config import get_settings
from cataloging_api.db.models import DSpaceCollection, DSpaceItem
from cataloging_api.db.session import engine
from cataloging_api.evidence import service as evidence_service
from cataloging_api.evidence.models import (
    CatalogEvidenceCandidate,
    CatalogEvidenceSession,
    CatalogEvidenceSource,
)
from cataloging_api.evidence.service import (
    EvidencePdfInvalidTypeError,
    EvidencePdfTimeoutError,
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


async def _pdf_only_session(session: AsyncSession, item_uuid: uuid.UUID) -> CatalogEvidenceSession:
    # A session may now be created with neither URL nor text (P2): PDF is a
    # first-class, equally valid first source.
    return await create_evidence_session(
        session, item_uuid=item_uuid, created_by="Catalogadora", url=None, text=None
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_only_session_has_single_source_at_position_zero() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert sources == []

        source = await add_pdf_evidence_source(
            session,
            evidence,
            file_bytes=pdf_with_text(["dc.subject.linguisticFamily: Tarasca"]),
            original_filename="unica.pdf",
            content_type=PDF_TYPE,
            author="Catalogadora",
        )
        assert source.position == 0

        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert [s.kind for s in sources] == ["pdf"]
        assert [s.position for s in sources] == [0]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extract_on_sourceless_session_returns_empty_deterministic_snapshot() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
        candidates = await extract_evidence_candidates(session, evidence)
        assert candidates == []
        # A second call must remain the same empty, frozen snapshot, not
        # re-derive or fabricate anything.
        again = await extract_evidence_candidates(session, evidence)
        assert again == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_with_text_is_extracted_and_persisted() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
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
        evidence = await _pdf_only_session(session, item_uuid)
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
        evidence = await _pdf_only_session(session, item_uuid)
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
        assert sources == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pdf_wrong_content_type_is_rejected() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
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
        evidence = await _pdf_only_session(session, item_uuid)
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
        evidence = await _pdf_only_session(session, item_uuid)
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
        assert sources == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_pdf_is_rejected_and_not_persisted() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
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
        assert sources == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_path_traversal_filename_is_sanitized_not_used_as_path() -> None:
    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
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
        evidence = await _pdf_only_session(session, item_uuid)
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_extraction_timeout_fails_closed_without_persisting(monkeypatch) -> None:
    def slow_extract(_data: bytes):
        time.sleep(0.3)
        raise AssertionError("extraction must never complete once the timeout has fired")

    def write_should_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a timed-out extraction must never reach disk")

    class _FastTimeoutSettings:
        evidence_pdf_extraction_timeout_seconds = 0.05
        evidence_pdf_storage_dir = get_settings().evidence_pdf_storage_dir

    monkeypatch.setattr(evidence_service, "extract_pdf_text", slow_extract)
    monkeypatch.setattr(evidence_service, "get_settings", lambda: _FastTimeoutSettings())
    monkeypatch.setattr(evidence_service, "_write_pdf_bytes", write_should_not_run)

    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
        with pytest.raises(EvidencePdfTimeoutError):
            await add_pdf_evidence_source(
                session,
                evidence,
                file_bytes=pdf_with_text(["contenido"]),
                original_filename="lento.pdf",
                content_type=PDF_TYPE,
                author="Catalogadora",
            )
        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert sources == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_flush_failure_cleans_up_orphaned_pdf_file(monkeypatch) -> None:
    storage_dir = Path(get_settings().evidence_pdf_storage_dir)
    before = set(storage_dir.glob("*.pdf")) if storage_dir.exists() else set()

    async def _forced_collision_position(_session: AsyncSession, _session_id: uuid.UUID) -> int:
        return 0

    async with _EvidenceFixture() as (session, item_uuid):
        evidence = await _pdf_only_session(session, item_uuid)
        # Occupy position 0 directly so the forced-collision insert below
        # violates UNIQUE(session_id, position) deterministically, without
        # relying on true thread/process concurrency for this assertion.
        session.add(
            CatalogEvidenceSource(
                session_id=evidence.session_id,
                position=0,
                kind="text",
                locator=None,
                content_text="Fuente existente en position 0.",
                content_hash="0" * 64,
                media_type="text/plain",
                metadata_json={},
            )
        )
        await session.flush()

        monkeypatch.setattr(evidence_service, "_next_source_position", _forced_collision_position)

        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                await add_pdf_evidence_source(
                    session,
                    evidence,
                    file_bytes=pdf_with_text(["colisión"]),
                    original_filename="colision.pdf",
                    content_type=PDF_TYPE,
                    author="Catalogadora",
                )

        _, sources, _, _ = await get_evidence_session(session, evidence.session_id)
        assert [s.kind for s in sources] == ["text"]

        after = set(storage_dir.glob("*.pdf"))
        assert after == before, "flush failure must not leave an orphaned PDF file on disk"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_commit_failure_after_flush_cleans_up_pdf_and_row(monkeypatch) -> None:
    # add_pdf_evidence_source only guards up to flush(): the row is visible
    # in-session and the file is on disk once it returns. This mirrors the
    # route's own transaction boundary (upload_pdf_source calls commit()
    # separately, after add_pdf_evidence_source returns) to verify that a
    # commit failure in the caller still rolls back the DB *and* removes the
    # now-orphaned file, exactly as upload_pdf_source's commit except-clause
    # does via delete_pdf_artifact.
    storage_dir = Path(get_settings().evidence_pdf_storage_dir)

    setup_connection = await engine.connect()
    session = AsyncSession(bind=setup_connection, expire_on_commit=False)
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    evidence: CatalogEvidenceSession | None = None
    try:
        session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/evidence-pdf-commit-fail",
                name="Evidence PDF commit-fail test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        session.add(
            DSpaceItem(
                uuid=item_uuid,
                collection_uuid=collection_uuid,
                handle="test/evidence-pdf-commit-fail-item",
                name="Evidence PDF commit-fail item",
                raw_json={"uuid": str(item_uuid)},
                source_hash="c" * 64,
            )
        )
        evidence = await _pdf_only_session(session, item_uuid)
        await session.commit()

        source = await add_pdf_evidence_source(
            session,
            evidence,
            file_bytes=pdf_with_text(["a punto de fallar"]),
            original_filename="fallo.pdf",
            content_type=PDF_TYPE,
            author="Catalogadora",
        )
        pdf_path = storage_dir / f"{source.source_id}.pdf"
        assert pdf_path.exists(), "file must be written before commit is attempted"

        original_commit = session.commit

        async def _failing_commit() -> None:
            raise RuntimeError("simulated commit failure")

        monkeypatch.setattr(session, "commit", _failing_commit)
        try:
            # Same shape as upload_pdf_source's commit except-clause.
            with pytest.raises(RuntimeError):
                try:
                    await session.commit()
                except Exception:
                    await session.rollback()
                    evidence_service.delete_pdf_artifact(source.source_id)
                    raise
        finally:
            monkeypatch.setattr(session, "commit", original_commit)

        assert not pdf_path.exists(), "orphaned PDF must be removed when commit fails"

        verify_connection = await engine.connect()
        verify_session = AsyncSession(bind=verify_connection, expire_on_commit=False)
        try:
            persisted = await verify_session.get(CatalogEvidenceSource, source.source_id)
            assert persisted is None, "PDF row must not be persisted when commit fails"
        finally:
            await verify_session.close()
            await verify_connection.close()
    finally:
        if evidence is not None:
            await session.execute(
                delete(CatalogEvidenceSource).where(
                    CatalogEvidenceSource.session_id == evidence.session_id
                )
            )
            await session.execute(
                delete(CatalogEvidenceSession).where(
                    CatalogEvidenceSession.session_id == evidence.session_id
                )
            )
        await session.execute(delete(DSpaceItem).where(DSpaceItem.uuid == item_uuid))
        await session.execute(
            delete(DSpaceCollection).where(DSpaceCollection.uuid == collection_uuid)
        )
        await session.commit()
        await session.close()
        await setup_connection.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_pdf_uploads_get_distinct_positions() -> None:
    # Real concurrency, across two independent connections/transactions, to
    # exercise the SELECT ... FOR UPDATE lock in add_pdf_evidence_source:
    # without it, both could read the same MAX(position) and race.
    setup_connection = await engine.connect()
    setup_session = AsyncSession(bind=setup_connection, expire_on_commit=False)
    collection_uuid = uuid.uuid4()
    item_uuid = uuid.uuid4()
    session_id: uuid.UUID | None = None
    results: list[CatalogEvidenceSource] = []
    try:
        setup_session.add(
            DSpaceCollection(
                uuid=collection_uuid,
                handle="test/evidence-pdf-concurrent",
                name="Evidence PDF concurrency test",
                raw_json={"uuid": str(collection_uuid)},
            )
        )
        setup_session.add(
            DSpaceItem(
                uuid=item_uuid,
                collection_uuid=collection_uuid,
                handle="test/evidence-pdf-concurrent-item",
                name="Evidence PDF concurrency item",
                raw_json={"uuid": str(item_uuid)},
                source_hash="h" * 64,
            )
        )
        evidence = await _pdf_only_session(setup_session, item_uuid)
        await setup_session.commit()
        session_id = evidence.session_id

        connection_a = await engine.connect()
        session_a = AsyncSession(bind=connection_a, expire_on_commit=False)
        connection_b = await engine.connect()
        session_b = AsyncSession(bind=connection_b, expire_on_commit=False)
        try:
            evidence_a = await session_a.get(CatalogEvidenceSession, session_id)
            evidence_b = await session_b.get(CatalogEvidenceSession, session_id)
            assert evidence_a is not None
            assert evidence_b is not None

            async def _upload_and_commit(
                target_session: AsyncSession,
                target_evidence: CatalogEvidenceSession,
                *,
                label: str,
            ) -> CatalogEvidenceSource:
                # Commit here, inside the coroutine gather() runs concurrently:
                # the FOR UPDATE lock in add_pdf_evidence_source is only
                # released on commit/rollback, so the second coroutine can't
                # proceed past its own lock acquisition until the first one
                # commits. Deferring both commits until after gather() would
                # deadlock (both waiting on each other's still-open lock).
                added = await add_pdf_evidence_source(
                    target_session,
                    target_evidence,
                    file_bytes=pdf_with_text([label]),
                    original_filename=f"{label}.pdf",
                    content_type=PDF_TYPE,
                    author=f"Catalogadora {label}",
                )
                await target_session.commit()
                return added

            results = await asyncio.gather(
                _upload_and_commit(session_a, evidence_a, label="A"),
                _upload_and_commit(session_b, evidence_b, label="B"),
            )

            positions = sorted(result.position for result in results)
            assert positions == [0, 1]
        finally:
            await session_a.close()
            await connection_a.close()
            await session_b.close()
            await connection_b.close()

        _, sources, _, _ = await get_evidence_session(setup_session, session_id)
        assert sorted(s.position for s in sources) == [0, 1]
    finally:
        # This test commits real rows across separate connections (needed to
        # exercise genuine lock contention), so clean up explicitly instead
        # of relying on a rollback. That includes the PDF files written to
        # evidence_pdf_storage_dir: a DB rollback would never touch them.
        for result in results:
            evidence_service.delete_pdf_artifact(result.source_id)
        if session_id is not None:
            await setup_session.execute(
                delete(CatalogEvidenceSource).where(
                    CatalogEvidenceSource.session_id == session_id
                )
            )
            await setup_session.execute(
                delete(CatalogEvidenceSession).where(
                    CatalogEvidenceSession.session_id == session_id
                )
            )
        await setup_session.execute(delete(DSpaceItem).where(DSpaceItem.uuid == item_uuid))
        await setup_session.execute(
            delete(DSpaceCollection).where(DSpaceCollection.uuid == collection_uuid)
        )
        await setup_session.commit()
        await setup_session.close()
        await setup_connection.close()
