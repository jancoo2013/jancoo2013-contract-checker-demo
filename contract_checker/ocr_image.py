"""OCR helpers for uploaded contract images."""

from __future__ import annotations

from typing import BinaryIO, TypedDict


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
