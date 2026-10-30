"""PDF request checks and an in-memory render."""

import pymupdf
import pytest

from bot.services.pdf_render import (
    MAX_PDF_BYTES,
    PdfRequestError,
    render_pdf_page,
    validate_page_range,
    validate_pdf_request,
)


def test_validate_pdf_request_checks_name_size_and_page() -> None:
    assert validate_pdf_request("notes.PDF", 12, 1) is None
    assert validate_pdf_request("notes.txt", 12, 1) is not None
    assert validate_pdf_request("notes.pdf", MAX_PDF_BYTES, 1) is None
    assert validate_pdf_request("notes.pdf", MAX_PDF_BYTES + 1, 1) is not None
    assert validate_pdf_request("notes.pdf", 12, 0) is not None


def test_validate_page_range() -> None:
    assert validate_page_range(2, 2) is None
    assert validate_page_range(3, 2) is not None


def _two_page_pdf() -> bytes:
    doc = pymupdf.open()
    doc.new_page()
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    return data


def test_render_page_two_is_a_png() -> None:
    png = render_pdf_page(_two_page_pdf(), 2, 72)
    assert png.startswith(b"\x89PNG")


def test_render_rejects_corrupt_bytes() -> None:
    with pytest.raises(PdfRequestError, match="opened as a PDF"):
        render_pdf_page(b"not a pdf", 1, 72)


def test_render_rejects_an_encrypted_pdf() -> None:
    doc = pymupdf.open()
    doc.new_page()
    data = doc.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="secret")
    doc.close()
    with pytest.raises(PdfRequestError, match="password"):
        render_pdf_page(data, 1, 72)
