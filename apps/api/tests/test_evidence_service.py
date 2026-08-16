import uuid

import pytest

from cataloging_api.evidence.models import CatalogEvidenceSource
from cataloging_api.evidence.service import (
    EvidenceValidationError,
    _candidate_rows,
    _normalized_source_payload,
)


def source(*, kind: str, locator: str | None = None, text: str | None = None):
    return CatalogEvidenceSource(
        source_id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        kind=kind,
        locator=locator,
        content_text=text,
        content_hash="a" * 64,
        media_type="text/plain",
        metadata_json={},
    )


def test_requires_explicit_external_source() -> None:
    with pytest.raises(EvidenceValidationError):
        _normalized_source_payload(url=None, text=None)


def test_rejects_non_http_external_url() -> None:
    with pytest.raises(EvidenceValidationError):
        _normalized_source_payload(url="file:///etc/passwd", text=None)


def test_url_becomes_repository_url_candidate_without_fetching_remote_content() -> None:
    rows = list(
        _candidate_rows(
            source(kind="url", locator="https://example.org/article")
        )
    )
    assert rows == [
        (
            "dc.identifier.url",
            "https://example.org/article",
            {"kind": "source_url", "locator": "https://example.org/article"},
        )
    ]


def test_explicit_master_contract_lines_are_extracted_with_line_evidence() -> None:
    rows = list(
        _candidate_rows(
            source(
                kind="text",
                text=(
                    "dc.subject.linguisticFamily: Maya\n"
                    "dc.subject.linguiscgroup: Tseltal\n"
                    "not.a.contract.field: ignored\n"
                ),
            )
        )
    )
    assert [(field, value) for field, value, _ in rows] == [
        ("dc.subject.linguisticFamily", "Maya"),
        ("dc.subject.linguiscgroup", "Tseltal"),
    ]
    assert rows[0][2]["kind"] == "explicit_field_line"
    assert rows[0][2]["line"] == 1


def test_doi_issn_and_isbn_are_extracted_deterministically() -> None:
    rows = list(
        _candidate_rows(
            source(
                kind="text",
                text=(
                    "DOI 10.1234/example.55 ISSN 1853-1393 "
                    "ISBN 978-0-306-40615-7"
                ),
            )
        )
    )
    pairs = {(field, value) for field, value, _ in rows}
    assert ("dc.identifier.doi", "10.1234/example.55") in pairs
    assert ("dc.identifier.issn", "1853-1393") in pairs
    assert ("dc.identifier.isbn", "978-0-306-40615-7") in pairs
