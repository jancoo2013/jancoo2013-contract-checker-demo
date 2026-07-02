"""Backend helpers for text-based PDF lease-template input.

This module is intentionally UI-free and Gemini-free. It extracts text from a
text-layer PDF so the app can later support a fast PDF template mode without
changing the existing photo/image masking flow.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from typing import Any


PDF_TEXT_STATUS_TEXT = "text_pdf"
PDF_TEXT_STATUS_EMPTY_OR_SCANNED = "scanned_or_empty_pdf"
DEFAULT_MAX_PDF_PAGES = 30
MIN_TEXT_CHARS_FOR_TEXT_PDF = 200
MIN_HEBREW_CHARS_FOR_TEXT_PDF = 50


class PDFTextExtractionError(Exception):
    """Controlled PDF extraction error that must not include PDF text snippets."""


@dataclass(frozen=True)
class PDFTextExtractionResult:
    """Result of extracting text from a PDF template."""

    filename: str
    page_count: int
    extracted_text: str
    status: str
    total_char_count: int
    hebrew_char_count: int
    problems: list[str]

    @property
    def usable_text_pdf(self) -> bool:
        return self.status == PDF_TEXT_STATUS_TEXT

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "page_count": self.page_count,
            "status": self.status,
            "total_char_count": self.total_char_count,
            "hebrew_char_count": self.hebrew_char_count,
            "problems": list(self.problems),
            "usable_text_pdf": self.usable_text_pdf,
        }


def count_hebrew_chars(text: str) -> int:
    return sum(1 for char in text if "\u0590" <= char <= "\u05ff")


def build_pdf_page_header(*, page_number: int, filename: str) -> str:
    return f"--- PDF PAGE {page_number}: {filename} ---"


def assemble_pdf_page_texts(*, filename: str, page_texts: list[str]) -> str:
    blocks: list[str] = []
    for index, page_text in enumerate(page_texts, start=1):
        blocks.append(f"{build_pdf_page_header(page_number=index, filename=filename)}\n{page_text.strip()}")
    return "\n\n".join(blocks).strip()


def classify_pdf_text(*, text: str, page_count: int) -> tuple[str, list[str]]:
    problems: list[str] = []
    total_chars = len(text.strip())
    hebrew_chars = count_hebrew_chars(text)

    if page_count <= 0:
        problems.append("PDF contains no pages.")
    if total_chars < MIN_TEXT_CHARS_FOR_TEXT_PDF:
        problems.append("PDF extracted text is too short for text-template mode.")
    if hebrew_chars < MIN_HEBREW_CHARS_FOR_TEXT_PDF:
        problems.append("PDF extracted text contains too few Hebrew characters for Hebrew lease-template mode.")

    status = PDF_TEXT_STATUS_EMPTY_OR_SCANNED if problems else PDF_TEXT_STATUS_TEXT
    return status, problems


def _load_pymupdf() -> Any:
    if importlib.util.find_spec("fitz") is None:
        raise PDFTextExtractionError("PyMuPDF is not installed")
    try:
        import fitz  # type: ignore[import-not-found]
    except Exception as exc:
        raise PDFTextExtractionError("PyMuPDF is unavailable") from exc
    return fitz


def extract_text_from_pdf_bytes(
    pdf_bytes: bytes,
    *,
    filename: str = "document.pdf",
    max_pages: int = DEFAULT_MAX_PDF_PAGES,
) -> PDFTextExtractionResult:
    """Extract page-separated text from a text-layer PDF.

    This helper does not perform OCR and does not send anything to Gemini. It is
    intended only for blank/text PDF lease templates. Scanned PDFs should fall
    back to the existing image/manual-mask flow later at the UI layer.
    """

    if not isinstance(pdf_bytes, bytes) or not pdf_bytes:
        raise PDFTextExtractionError("PDF bytes are empty")
    if max_pages <= 0:
        raise PDFTextExtractionError("max_pages must be positive")

    fitz = _load_pymupdf()
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFTextExtractionError("Could not open PDF") from exc

    try:
        page_count = int(getattr(document, "page_count", len(document)))
        if page_count > max_pages:
            raise PDFTextExtractionError(f"PDF has too many pages: {page_count}; max allowed is {max_pages}")

        page_texts: list[str] = []
        for page_index in range(page_count):
            page = document.load_page(page_index)
            try:
                page_text = page.get_text("text", sort=True)
            except TypeError:
                page_text = page.get_text("text")
            page_texts.append(str(page_text or ""))
    finally:
        close = getattr(document, "close", None)
        if callable(close):
            close()

    extracted_text = assemble_pdf_page_texts(filename=filename, page_texts=page_texts)
    status, problems = classify_pdf_text(text=extracted_text, page_count=page_count)
    return PDFTextExtractionResult(
        filename=filename,
        page_count=page_count,
        extracted_text=extracted_text,
        status=status,
        total_char_count=len(extracted_text.strip()),
        hebrew_char_count=count_hebrew_chars(extracted_text),
        problems=problems,
    )
