"""OCR helpers for uploaded contract images."""

from __future__ import annotations

from typing import Any, BinaryIO, Iterable, TypedDict


class BoundingBox(TypedDict):
    """OCR bounding box coordinates in pixels."""

    left: int
    top: int
    width: int
    height: int


class OCRBlock(TypedDict):
    """A text block returned by Tesseract diagnostics."""

    text: str
    confidence: float | None
    bbox: BoundingBox


class OCRResult(TypedDict):
    """Structured OCR result returned to the Streamlit app."""

    raw_text: str
    blocks: list[OCRBlock]
    ocr_available: bool
    error: str | None


class OCRPageResult(TypedDict):
    """OCR result for one uploaded contract page."""

    page_index: int
    filename: str
    raw_text: str
    blocks: list[OCRBlock]
    ocr_available: bool
    error: str | None


class OCRMultiPageResult(TypedDict):
    """Combined OCR result for a multi-page uploaded contract."""

    raw_text: str
    pages: list[OCRPageResult]
    ocr_available: bool
    errors: list[str]


_OCR_UNAVAILABLE_MESSAGE = "OCR недоступен в этом окружении. Используй вставку текста договора."


def _preprocess_image(image: object) -> object:
    """Apply light preprocessing that is safe for printed document images."""

    from PIL import ImageOps

    rgb_image = image.convert("RGB")
    grayscale_image = ImageOps.grayscale(rgb_image)
    normalized_image = ImageOps.autocontrast(grayscale_image)
    return normalized_image.point(lambda pixel: 255 if pixel > 180 else 0)


def _parse_confidence(value: object) -> float | None:
    """Parse pytesseract confidence values, preserving unknown values as None."""

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence < 0:
        return None
    return confidence


def _missing_tesseract_result(_error: Exception) -> OCRResult:
    """Return a non-crashing result for missing Tesseract or language data."""

    return {
        "raw_text": "",
        "blocks": [],
        "ocr_available": False,
        "error": _OCR_UNAVAILABLE_MESSAGE,
    }


def page_separator(page_index: int, filename: str) -> str:
    """Return the Russian page separator used in combined OCR text."""

    safe_filename = filename or f"page-{page_index}"
    return f"--- СТРАНИЦА {page_index}: {safe_filename} ---"


def combine_ocr_page_texts(pages: Iterable[dict[str, Any]]) -> str:
    """Combine page OCR text with stable separators for review and analysis."""

    chunks: list[str] = []
    for fallback_index, page in enumerate(pages, start=1):
        page_index = int(page.get("page_index") or fallback_index)
        filename = str(page.get("filename") or f"page-{page_index}")
        raw_text = str(page.get("raw_text") or "")
        chunks.append(f"{page_separator(page_index, filename)}\n{raw_text}".rstrip())
    return "\n\n".join(chunks)


def ocr_image_to_text(image_file: BinaryIO) -> OCRResult:
    """Extract editable Hebrew/English text and OCR blocks from an uploaded image.

    Args:
        image_file: A Streamlit uploaded image file or any binary file-like object.

    Returns:
        A dictionary containing raw OCR text, optional block-level data,
        availability, and an error message. Missing Tesseract binaries or Hebrew
        language data are reported without raising to the UI.
    """

    try:
        import pytesseract
        from PIL import Image
        from pytesseract import Output
    except ImportError as error:
        return _missing_tesseract_result(error)

    handled_errors = (
        getattr(pytesseract, "TesseractError", RuntimeError),
        getattr(pytesseract, "TesseractNotFoundError", RuntimeError),
        FileNotFoundError,
        ImportError,
        OSError,
    )

    try:
        image = Image.open(image_file)
        processed_image = _preprocess_image(image)
        raw_text = pytesseract.image_to_string(processed_image, lang="heb+eng")
        ocr_data = pytesseract.image_to_data(processed_image, lang="heb+eng", output_type=Output.DICT)
    except handled_errors as error:
        return _missing_tesseract_result(error)

    blocks: list[OCRBlock] = []
    texts = ocr_data.get("text", [])
    confidences = ocr_data.get("conf", [None] * len(texts))
    lefts = ocr_data.get("left", [0] * len(texts))
    tops = ocr_data.get("top", [0] * len(texts))
    widths = ocr_data.get("width", [0] * len(texts))
    heights = ocr_data.get("height", [0] * len(texts))
    for index, text in enumerate(texts):
        clean_text = str(text).strip()
        if not clean_text:
            continue
        blocks.append(
            {
                "text": clean_text,
                "confidence": _parse_confidence(confidences[index] if index < len(confidences) else None),
                "bbox": {
                    "left": int(lefts[index] if index < len(lefts) else 0),
                    "top": int(tops[index] if index < len(tops) else 0),
                    "width": int(widths[index] if index < len(widths) else 0),
                    "height": int(heights[index] if index < len(heights) else 0),
                },
            }
        )

    return {
        "raw_text": raw_text,
        "blocks": blocks,
        "ocr_available": True,
        "error": None,
    }


def ocr_images_to_text(image_files: Iterable[BinaryIO]) -> OCRMultiPageResult:
    """OCR all uploaded contract page images and combine them into one document.

    Pages are processed in the order provided by Streamlit. A failed page is
    represented in diagnostics but does not stop OCR for the remaining pages.
    """

    pages: list[OCRPageResult] = []
    errors: list[str] = []

    for page_index, image_file in enumerate(image_files, start=1):
        filename = str(getattr(image_file, "name", f"page-{page_index}"))
        try:
            if hasattr(image_file, "seek"):
                image_file.seek(0)
            result = ocr_image_to_text(image_file)
        except Exception as error:  # Defensive: one bad upload must not crash all pages.
            message = str(error) or error.__class__.__name__
            result = {
                "raw_text": "",
                "blocks": [],
                "ocr_available": False,
                "error": message,
            }

        page_error = result.get("error")
        page: OCRPageResult = {
            "page_index": page_index,
            "filename": filename,
            "raw_text": str(result.get("raw_text") or ""),
            "blocks": list(result.get("blocks") or []),
            "ocr_available": bool(result.get("ocr_available")),
            "error": str(page_error) if page_error else None,
        }
        if page["error"]:
            errors.append(f"Страница {page_index} ({filename}): {page['error']}")
        pages.append(page)

    return {
        "raw_text": combine_ocr_page_texts(pages),
        "pages": pages,
        "ocr_available": any(page["ocr_available"] for page in pages),
        "errors": errors,
    }


def ocr_json_to_text(payload: object) -> str:
    """Extract text from single-page or multi-page OCR JSON payloads."""

    if not isinstance(payload, dict):
        return ""

    pages_payload = payload.get("pages")
    if isinstance(pages_payload, list):
        pages: list[dict[str, Any]] = []
        for page_index, raw_page in enumerate(pages_payload, start=1):
            if not isinstance(raw_page, dict):
                continue
            pages.append(
                {
                    "page_index": raw_page.get("page_index") or page_index,
                    "filename": raw_page.get("filename") or f"page-{page_index}",
                    "raw_text": raw_page.get("raw_text") or raw_page.get("text") or "",
                }
            )
        return combine_ocr_page_texts(pages)

    return str(payload.get("raw_text") or payload.get("text") or "")
