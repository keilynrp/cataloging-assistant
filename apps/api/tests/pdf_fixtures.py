"""Minimal PDF byte fixtures built at test time. No binaries are committed."""

from __future__ import annotations

import io

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def pdf_with_text(lines: list[str]) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    escaped_lines = [
        line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)") for line in lines
    ]
    y = 720
    ops: list[str] = []
    for line in escaped_lines:
        ops.append(f"BT /F1 12 Tf 72 {y} Td ({line}) Tj ET")
        y -= 20
    content_bytes = "\n".join(ops).encode("latin-1")

    content = DecodedStreamObject()
    content.set_data(content_bytes)
    content_ref = writer._add_object(content)  # noqa: SLF001 - documented pypdf pattern for custom content

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)  # noqa: SLF001
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )

    page[NameObject("/Contents")] = content_ref
    page[NameObject("/Resources")] = resources

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def pdf_without_text() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def pdf_with_many_pages(count: int) -> bytes:
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def encrypted_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt(user_password="secret", owner_password="secret-owner")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def corrupt_pdf() -> bytes:
    return b"%PDF-1.4\nthis is not a well-formed pdf body, no valid xref table follows"


def non_pdf_bytes() -> bytes:
    return b"this file pretends to be evidence but is not a pdf at all"


def fake_extension_pdf_bytes() -> bytes:
    # A real, valid, textual PDF -- used to test that magic-byte checking
    # still passes it, distinguishing "wrong extension" from "not a PDF".
    return pdf_with_text(["Real PDF content with a fake extension test."])
