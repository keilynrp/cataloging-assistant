from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 300
PDF_MAGIC = b"%PDF-"
ALLOWED_PDF_CONTENT_TYPE = "application/pdf"
PAGE_SEPARATOR = "\f"
EXTRACTOR_NAME = "pypdf"


class PdfRejectedError(ValueError):
    """Raised when a PDF cannot be safely or usefully parsed.

    The caller must not persist a source or write bytes to disk when this
    is raised: rejection happens before anything is committed.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class PdfExtractionResult:
    status: str  # "extracted" | "no_extractable_text"
    text: str
    extracted_text_hash: str | None
    page_count: int
    page_char_offsets: list[int] = field(default_factory=list)


def looks_like_pdf(data: bytes) -> bool:
    return data[: len(PDF_MAGIC)] == PDF_MAGIC


def extract_pdf_text(data: bytes) -> PdfExtractionResult:
    """Extract text from PDF bytes already known to be well-formed magic bytes.

    Pure, synchronous, offline: only reads structure and text streams via
    pypdf. Never executes JavaScript, launch actions, or embedded files;
    never follows links; never shells out. Raises PdfRejectedError for any
    condition where nothing should be persisted (encrypted, too many pages,
    unparseable).
    """
    if not looks_like_pdf(data):
        raise PdfRejectedError("not_a_pdf")

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as error:
        raise PdfRejectedError("unparseable") from error
    except Exception as error:  # pragma: no cover - defensive, pypdf can raise broadly
        raise PdfRejectedError("unparseable") from error

    if reader.is_encrypted:
        raise PdfRejectedError("encrypted")

    try:
        page_count = len(reader.pages)
    except Exception as error:  # pragma: no cover - defensive
        raise PdfRejectedError("unparseable") from error

    if page_count == 0:
        raise PdfRejectedError("no_pages")
    if page_count > MAX_PDF_PAGES:
        raise PdfRejectedError("too_many_pages")

    page_texts: list[str] = []
    for page in reader.pages:
        try:
            page_texts.append(page.extract_text() or "")
        except Exception:  # pragma: no cover - a single unparsable page must not abort the batch
            page_texts.append("")

    page_char_offsets: list[int] = []
    offset = 0
    for page_text in page_texts:
        page_char_offsets.append(offset)
        offset += len(page_text) + len(PAGE_SEPARATOR)
    full_text = PAGE_SEPARATOR.join(page_texts)

    if not full_text.strip():
        return PdfExtractionResult(
            status="no_extractable_text",
            text="",
            extracted_text_hash=None,
            page_count=page_count,
            page_char_offsets=page_char_offsets,
        )

    text_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    return PdfExtractionResult(
        status="extracted",
        text=full_text,
        extracted_text_hash=text_hash,
        page_count=page_count,
        page_char_offsets=page_char_offsets,
    )


def page_for_offset(page_char_offsets: list[int], offset: int) -> int:
    """1-indexed page number containing a character offset in the joined text.

    Offsets are derived from this module's own page concatenation, so this
    is reliable for the text pypdf reported for each page. It is not a
    claim about visual page layout in the original PDF.
    """
    page_index = 0
    for index, start in enumerate(page_char_offsets):
        if start <= offset:
            page_index = index
        else:
            break
    return page_index + 1
