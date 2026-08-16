import pytest

from cataloging_api.evidence.pdf_extraction import (
    MAX_PDF_PAGES,
    PdfRejectedError,
    extract_pdf_text,
    looks_like_pdf,
    page_for_offset,
)
from tests.pdf_fixtures import (
    corrupt_pdf,
    encrypted_pdf,
    non_pdf_bytes,
    pdf_with_many_pages,
    pdf_with_text,
    pdf_without_text,
)


def test_looks_like_pdf_checks_magic_bytes() -> None:
    assert looks_like_pdf(b"%PDF-1.4\n...") is True
    assert looks_like_pdf(non_pdf_bytes()) is False
    assert looks_like_pdf(b"") is False


def test_extracts_text_and_records_hash_and_page_count() -> None:
    data = pdf_with_text(["dc.subject.linguisticFamily: Tarasca", "DOI 10.1234/example.55"])
    result = extract_pdf_text(data)

    assert result.status == "extracted"
    assert result.page_count == 1
    assert result.extracted_text_hash is not None
    assert "Tarasca" in result.text
    assert "10.1234/example.55" in result.text
    assert result.page_char_offsets == [0]


def test_pdf_without_text_layer_is_no_extractable_text() -> None:
    result = extract_pdf_text(pdf_without_text())

    assert result.status == "no_extractable_text"
    assert result.text == ""
    assert result.extracted_text_hash is None
    assert result.page_count == 1


def test_multi_page_offsets_are_cumulative() -> None:
    data = pdf_with_text(["Página uno"])
    result = extract_pdf_text(data)
    assert result.page_char_offsets == [0]


def test_bytes_without_pdf_magic_are_rejected() -> None:
    with pytest.raises(PdfRejectedError) as excinfo:
        extract_pdf_text(non_pdf_bytes())
    assert excinfo.value.reason == "not_a_pdf"


def test_corrupt_pdf_is_rejected() -> None:
    with pytest.raises(PdfRejectedError):
        extract_pdf_text(corrupt_pdf())


def test_encrypted_pdf_is_rejected() -> None:
    with pytest.raises(PdfRejectedError) as excinfo:
        extract_pdf_text(encrypted_pdf())
    assert excinfo.value.reason == "encrypted"


def test_pdf_exceeding_page_limit_is_rejected() -> None:
    data = pdf_with_many_pages(MAX_PDF_PAGES + 1)
    with pytest.raises(PdfRejectedError) as excinfo:
        extract_pdf_text(data)
    assert excinfo.value.reason == "too_many_pages"


def test_pdf_at_page_limit_is_accepted() -> None:
    data = pdf_with_many_pages(MAX_PDF_PAGES)
    result = extract_pdf_text(data)
    assert result.page_count == MAX_PDF_PAGES


def test_page_for_offset_finds_containing_page() -> None:
    offsets = [0, 100, 250]
    assert page_for_offset(offsets, 0) == 1
    assert page_for_offset(offsets, 99) == 1
    assert page_for_offset(offsets, 100) == 2
    assert page_for_offset(offsets, 249) == 2
    assert page_for_offset(offsets, 250) == 3
    assert page_for_offset(offsets, 10_000) == 3


def test_extraction_module_performs_no_network_io() -> None:
    import ast
    import inspect

    from cataloging_api.evidence import pdf_extraction

    source = inspect.getsource(pdf_extraction)
    tree = ast.parse(source)
    imported_names = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    network_capable = {"httpx", "requests", "urllib", "socket", "aiohttp", "http"}
    assert not (imported_names & network_capable)
