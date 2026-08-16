"""Targeted remote-fetch tests that need finer control (monkeypatching a
blocking extractor, asserting on internal timing) than the declarative
Golden Set case.json format comfortably supports. Declarative scenarios
(non-2xx rejection, MIME/size limits, SSRF blocking, redirect handling)
live in tests/golden/evidence instead; see test_golden_set.py.

No test in this file performs a real HTTP call or real DNS lookup.
"""

from __future__ import annotations

import time

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from cataloging_api.config import get_settings
from cataloging_api.evidence import service as evidence_service
from cataloging_api.evidence.models import CatalogEvidenceSource
from cataloging_api.evidence.service import (
    EvidenceRemotePdfTimeoutError,
    add_remote_evidence_source,
)
from tests.test_evidence_pdf_integration import _EvidenceFixture, _pdf_only_session

REMOTE_URL = "https://93.184.216.34:443/slow.pdf"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remote_pdf_extraction_runs_off_loop_and_enforces_timeout(monkeypatch) -> None:
    # A blocking time.sleep() call proves the extractor runs off the event
    # loop: if _persist_remote_source awaited extract_pdf_text directly
    # (instead of via asyncio.to_thread), this sleep would block the whole
    # loop and asyncio.wait_for could never fire to cut it off.
    def slow_extract(_data: bytes):
        time.sleep(0.3)
        raise AssertionError("extraction must never complete once the timeout has fired")

    monkeypatch.setattr(evidence_service, "extract_pdf_text", slow_extract)

    overridden_settings = get_settings().model_copy(
        update={
            "evidence_remote_fetch_enabled": True,
            "evidence_pdf_extraction_timeout_seconds": 0.05,
        }
    )
    monkeypatch.setattr(evidence_service, "get_settings", lambda: overridden_settings)

    with respx.mock(assert_all_mocked=True, assert_all_called=False) as router:
        router.get(REMOTE_URL).mock(
            return_value=Response(
                200,
                headers={"content-type": "application/pdf"},
                content=b"%PDF-1.4 not real content",
            )
        )
        async with _EvidenceFixture() as (session, item_uuid):
            evidence = await _pdf_only_session(session, item_uuid)
            with pytest.raises(EvidenceRemotePdfTimeoutError):
                await add_remote_evidence_source(
                    session,
                    evidence,
                    url=REMOTE_URL,
                    author="Catalogadora",
                )
            # Fails closed: no source persisted for the timed-out fetch.
            persisted = list(
                await session.scalars(
                    select(CatalogEvidenceSource).where(
                        CatalogEvidenceSource.session_id == evidence.session_id
                    )
                )
            )
            assert persisted == []
