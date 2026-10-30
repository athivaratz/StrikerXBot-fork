"""PDF checks and rendering that do not need Discord.

The file stays in memory so a crash cannot leave a temp PDF on disk.
"""

import pymupdf

MAX_PDF_BYTES = 10 * 1024 * 1024


class PdfRequestError(Exception):
    """A short reason the caller can show in Discord."""


def validate_pdf_request(filename: str, size: int, page: int) -> str | None:
    if not filename.lower().endswith(".pdf"):
        return "The file name must end with .pdf."
    if size > MAX_PDF_BYTES:
        return "The PDF must be 10 MB or smaller."
    if page < 1:
        return "Page must be 1 or higher."
    return None


def validate_page_range(page: int, page_count: int) -> str | None:
    if page > page_count:
        return f"This file has {page_count} pages. Choose a page in that range."
    return None


def render_pdf_page(data: bytes, page: int, dpi: int) -> bytes:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError) as err:
        raise PdfRequestError("That file could not be opened as a PDF.") from err
    try:
        if doc.needs_pass or doc.is_encrypted:
            raise PdfRequestError("That PDF is password protected.")
        reason = validate_page_range(page, doc.page_count)
        if reason is not None:
            raise PdfRequestError(reason)
        pixmap = doc[page - 1].get_pixmap(dpi=dpi)
        return pixmap.tobytes("png")
    finally:
        doc.close()
