"""OCR helpers for uploaded contract images."""

from __future__ import annotations

import re
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


class OCRQuality(TypedDict):
    """JSON-serializable OCR quality diagnostics."""

    score: float
    quality_level: str
    metrics: dict[str, Any]
    chosen_attempt: dict[str, Any] | None


class OCRResult(TypedDict):
    """Structured OCR result returned to the Streamlit app."""

    raw_text: str
    blocks: list[OCRBlock]
    ocr_available: bool
    error: str | None
    quality: OCRQuality
    attempts_summary: list[dict[str, Any]]


class OCRPageResult(TypedDict):
    """OCR result for one uploaded contract page."""

    page_index: int
    filename: str
    raw_text: str
    blocks: list[OCRBlock]
    ocr_available: bool
    error: str | None
    quality: OCRQuality
    attempts_summary: list[dict[str, Any]]


class OCRMultiPageResult(TypedDict):
    """Combined OCR result for a multi-page uploaded contract."""

    raw_text: str
    pages: list[OCRPageResult]
    ocr_available: bool
    errors: list[str]
    quality: OCRQuality


_OCR_UNAVAILABLE_MESSAGE = "OCR недоступен в этом окружении. Используй вставку текста договора."
_OCR_CONFIGS = [
    ("psm_6", "--oem 3 --psm 6 -c preserve_interword_spaces=1"),
    ("psm_4", "--oem 3 --psm 4 -c preserve_interword_spaces=1"),
    ("psm_11", "--oem 3 --psm 11 -c preserve_interword_spaces=1"),
]
_OCR_LANGUAGES = ["heb", "heb+eng"]
_QUALITY_ORDER = {"failed": 0, "low": 1, "medium": 2, "good": 3}
_KNOWN_ANCHORS = [
    "חוזה שכירות",
    "הסכם שכירות",
    "דמי שכירות",
    "תקופת השכירות",
    "תנאי תשלום",
    "שיקים",
    "צ'קים",
    "פיקדון",
    "ערבון",
    "ארנונה",
    "חשמל",
    "מים",
    "ועד בית",
    "המשכיר",
    "השוכר",
]
_USEFUL_CONTRACT_WORDS = [
    "שכירות",
    "תשלום",
    "תשלומים",
    "פיקדון",
    "ערבון",
    "ארנונה",
    "חשמל",
    "מים",
    "משכיר",
    "שוכר",
    "דירה",
    "נכס",
    "תקופה",
    "חתימה",
]
_MONEY_MARKERS = ["₪", 'ש"ח', "שח"]
_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_DIGIT_RE = re.compile(r"\d")
_SHORT_LATIN_TOKEN_RE = re.compile(r"\b[A-Za-z]{1,3}\b")
_LATIN_TOKEN_RE = re.compile(r"\b[A-Za-z]+\b")


def count_hebrew_chars(text: str) -> int:
    """Count Hebrew Unicode characters in OCR text."""

    return len(_HEBREW_RE.findall(text or ""))


def count_latin_chars(text: str) -> int:
    """Count Latin letters in OCR text."""

    return len(_LATIN_RE.findall(text or ""))


def count_known_anchors(text: str) -> int:
    """Count known Hebrew rental-contract anchor phrases in OCR text."""

    safe_text = text or ""
    return sum(1 for anchor in _KNOWN_ANCHORS if anchor in safe_text)


def _count_useful_contract_words(text: str) -> int:
    """Count simple Hebrew contract words that can appear on later pages."""

    safe_text = text or ""
    return sum(1 for word in _USEFUL_CONTRACT_WORDS if word in safe_text)


def is_ocr_text_usable(text: str) -> bool:
    """Return True when deterministic OCR text checks are enough for draft analysis."""

    safe_text = text or ""
    hebrew_chars = count_hebrew_chars(safe_text)
    latin_chars = count_latin_chars(safe_text)
    known_anchor_count = count_known_anchors(safe_text)
    useful_word_count = _count_useful_contract_words(safe_text)
    return (
        hebrew_chars >= 80
        and latin_chars <= hebrew_chars
        and (known_anchor_count >= 1 or useful_word_count >= 1)
    )


def _preprocess_image(image: object) -> object:
    """Backward-compatible default preprocessing used by older callers/tests."""

    return dict(_preprocessing_variants(image))["autocontrast_upscaled"]


def _resize(image: object, scale: int) -> object:
    """Resize a PIL image-like object when the method is available."""

    if not hasattr(image, "resize") or not hasattr(image, "size"):
        return image
    from PIL import Image

    width, height = image.size  # type: ignore[attr-defined]
    lanczos = getattr(getattr(Image, "Resampling", Image), "LANCZOS", 1)
    return image.resize((int(width) * scale, int(height) * scale), lanczos)


def _preprocessing_variants(image: object) -> list[tuple[str, object]]:
    """Create several in-memory OCR preprocessing variants for printed documents."""

    from PIL import ImageOps

    try:
        from PIL import ImageFilter
    except ImportError:
        ImageFilter = None  # type: ignore[assignment]

    rgb_image = image.convert("RGB")
    grayscale_image = ImageOps.grayscale(rgb_image)
    grayscale_2x = _resize(grayscale_image, 2)
    autocontrast_upscaled = ImageOps.autocontrast(grayscale_2x)
    variants: list[tuple[str, object]] = [
        ("original_rgb", rgb_image),
        ("grayscale", grayscale_image),
        ("grayscale_upscaled_2x", grayscale_2x),
        ("grayscale_upscaled_3x", _resize(grayscale_image, 3)),
        ("autocontrast_upscaled", autocontrast_upscaled),
    ]
    if ImageFilter is not None and hasattr(autocontrast_upscaled, "filter"):
        variants.append(("sharpened_upscaled", autocontrast_upscaled.filter(ImageFilter.SHARPEN)))
    else:
        variants.append(("sharpened_upscaled", autocontrast_upscaled))

    try:
        import cv2
        import numpy as np

        gray_array = np.array(autocontrast_upscaled)
        thresholded = cv2.adaptiveThreshold(
            gray_array,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            11,
        )
        from PIL import Image

        variants.append(("adaptive_threshold", Image.fromarray(thresholded)))
    except Exception:
        # OpenCV is optional at runtime; skip this single variant if unavailable.
        pass

    return variants


def _parse_confidence(value: object) -> float | None:
    """Parse pytesseract confidence values, preserving unknown values as None."""

    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if confidence < 0:
        return None
    return confidence


def _average_block_confidence(blocks: list[OCRBlock]) -> float:
    """Return average OCR confidence normalized to 0..1."""

    values = [block["confidence"] for block in blocks if block.get("confidence") is not None]
    if not values:
        return 0.0
    average = sum(float(value) for value in values) / len(values)
    return round(max(0.0, min(average / 100.0, 1.0)), 4)


def _quality_level(score: float, raw_text: str) -> str:
    """Map score and text presence to a conservative quality label."""

    if not raw_text.strip():
        return "failed"
    if score >= 18:
        return "good"
    if score >= 10:
        return "medium"
    return "low"


def _empty_quality(level: str = "failed", error: str | None = None) -> OCRQuality:
    metrics = {
        "hebrew_char_count": 0,
        "hebrew_ratio": 0.0,
        "latin_char_count": 0,
        "latin_ratio": 0.0,
        "digit_count": 0,
        "money_marker_count": 0,
        "known_anchor_hits": 0,
        "known_anchors_found": [],
        "useful_contract_word_hits": 0,
        "ocr_text_usable": False,
        "garbage_score": 0.0,
        "avg_confidence": 0.0,
        "recognized_char_count": 0,
        "error": error,
    }
    return {"score": 0.0, "quality_level": level, "metrics": metrics, "chosen_attempt": None}


def _missing_tesseract_result(_error: Exception) -> OCRResult:
    """Return a non-crashing result for missing Tesseract or language data."""

    return {
        "raw_text": "",
        "blocks": [],
        "ocr_available": False,
        "error": _OCR_UNAVAILABLE_MESSAGE,
        "quality": _empty_quality("failed", _OCR_UNAVAILABLE_MESSAGE),
        "attempts_summary": [],
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


def _parse_blocks(ocr_data: dict[str, list[Any]]) -> list[OCRBlock]:
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
    return blocks


def score_ocr_result(raw_text: str, blocks: list[OCRBlock]) -> dict[str, Any]:
    """Score OCR text for Hebrew rental-contract usefulness and Latin garbage."""

    text = raw_text or ""
    hebrew_char_count = count_hebrew_chars(text)
    latin_char_count = count_latin_chars(text)
    digit_count = len(_DIGIT_RE.findall(text))
    recognized_char_count = hebrew_char_count + latin_char_count + digit_count
    text_char_count = max(1, hebrew_char_count + latin_char_count)
    hebrew_ratio = hebrew_char_count / text_char_count
    latin_ratio = latin_char_count / text_char_count
    money_marker_count = sum(text.count(marker) for marker in _MONEY_MARKERS)
    anchors_found = [anchor for anchor in _KNOWN_ANCHORS if anchor in text]
    known_anchor_hits = count_known_anchors(text)
    useful_contract_word_hits = _count_useful_contract_words(text)
    ocr_text_usable = is_ocr_text_usable(text)
    latin_tokens = _LATIN_TOKEN_RE.findall(text)
    short_latin_tokens = _SHORT_LATIN_TOKEN_RE.findall(text)
    garbage_score = 0.0
    if latin_ratio > 0.25:
        garbage_score += (latin_ratio - 0.25) * 10
    if len(short_latin_tokens) >= 5:
        garbage_score += min(len(short_latin_tokens) / 3, 8)
    if latin_tokens and len(short_latin_tokens) / max(1, len(latin_tokens)) > 0.6:
        garbage_score += 2
    avg_confidence = _average_block_confidence(blocks)
    total_score = (
        known_anchor_hits * 3
        + money_marker_count * 2
        + hebrew_ratio * 10
        + avg_confidence * 5
        - latin_ratio * 8
        - garbage_score
    )
    total_score = round(max(0.0, total_score), 3)

    return {
        "hebrew_char_count": hebrew_char_count,
        "hebrew_ratio": round(hebrew_ratio, 4),
        "latin_char_count": latin_char_count,
        "latin_ratio": round(latin_ratio, 4),
        "digit_count": digit_count,
        "money_marker_count": money_marker_count,
        "known_anchor_hits": known_anchor_hits,
        "known_anchors_found": anchors_found,
        "useful_contract_word_hits": useful_contract_word_hits,
        "ocr_text_usable": ocr_text_usable,
        "garbage_score": round(garbage_score, 3),
        "avg_confidence": avg_confidence,
        "recognized_char_count": recognized_char_count,
        "total_score": total_score,
    }


def _quality_from_attempt(attempt: dict[str, Any]) -> OCRQuality:
    metrics = score_ocr_result(str(attempt.get("raw_text") or ""), list(attempt.get("blocks") or []))
    score = float(metrics["total_score"])
    chosen_attempt = {
        "config_name": attempt.get("config_name"),
        "language": attempt.get("language"),
        "preprocessing_variant": attempt.get("preprocessing_variant"),
        "avg_confidence": metrics["avg_confidence"],
    }
    raw_text = str(attempt.get("raw_text") or "")
    deterministic_level = "medium" if bool(metrics.get("ocr_text_usable")) else _quality_level(0.0, raw_text)
    return {
        "score": score,
        "quality_level": deterministic_level,
        "metrics": metrics,
        "chosen_attempt": chosen_attempt,
    }


def _attempt_summary(attempt: dict[str, Any], quality: OCRQuality | None = None) -> dict[str, Any]:
    if quality is None:
        quality = _quality_from_attempt(attempt)
    text = str(attempt.get("raw_text") or "")
    return {
        "config_name": attempt.get("config_name"),
        "language": attempt.get("language"),
        "preprocessing_variant": attempt.get("preprocessing_variant"),
        "score": quality["score"],
        "quality_level": quality["quality_level"],
        "avg_confidence": quality["metrics"].get("avg_confidence", 0.0),
        "known_anchor_hits": quality["metrics"].get("known_anchor_hits", 0),
        "latin_ratio": quality["metrics"].get("latin_ratio", 0.0),
        "recognized_char_count": len(text),
        "error": attempt.get("error"),
    }


def ocr_image_to_text(image_file: BinaryIO) -> OCRResult:
    """Extract editable text using multiple OCR preprocessing/config attempts."""

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
        variants = _preprocessing_variants(image)
    except handled_errors as error:
        return _missing_tesseract_result(error)

    attempts: list[dict[str, Any]] = []
    attempts_summary: list[dict[str, Any]] = []
    for variant_name, processed_image in variants:
        for language in _OCR_LANGUAGES:
            for config_name, config in _OCR_CONFIGS:
                attempt: dict[str, Any] = {
                    "raw_text": "",
                    "blocks": [],
                    "config_name": config_name,
                    "language": language,
                    "preprocessing_variant": variant_name,
                    "error": None,
                }
                try:
                    raw_text = pytesseract.image_to_string(processed_image, lang=language, config=config)
                    ocr_data = pytesseract.image_to_data(
                        processed_image,
                        lang=language,
                        config=config,
                        output_type=Output.DICT,
                    )
                    attempt["raw_text"] = raw_text
                    attempt["blocks"] = _parse_blocks(ocr_data)
                    attempts.append(attempt)
                    attempts_summary.append(_attempt_summary(attempt))
                except handled_errors as error:
                    attempt["error"] = str(error) or error.__class__.__name__
                    attempts_summary.append(_attempt_summary(attempt))
                    continue

    if not attempts:
        error = attempts_summary[0]["error"] if attempts_summary else _OCR_UNAVAILABLE_MESSAGE
        return {
            "raw_text": "",
            "blocks": [],
            "ocr_available": False,
            "error": str(error),
            "quality": _empty_quality("failed", str(error)),
            "attempts_summary": attempts_summary,
        }

    best_attempt = max(attempts, key=lambda item: _quality_from_attempt(item)["score"])
    quality = _quality_from_attempt(best_attempt)
    return {
        "raw_text": str(best_attempt.get("raw_text") or ""),
        "blocks": list(best_attempt.get("blocks") or []),
        "ocr_available": True,
        "error": None,
        "quality": quality,
        "attempts_summary": attempts_summary,
    }


def _aggregate_quality(pages: list[OCRPageResult]) -> OCRQuality:
    if not pages:
        return _empty_quality("failed", "Нет страниц для OCR")
    worst_level = min(
        (page["quality"]["quality_level"] for page in pages),
        key=lambda level: _QUALITY_ORDER.get(level, 0),
    )
    total_chars = sum(max(1, int(page["quality"]["metrics"].get("recognized_char_count", 0))) for page in pages)
    weighted_score = sum(
        float(page["quality"].get("score", 0.0))
        * max(1, int(page["quality"]["metrics"].get("recognized_char_count", 0)))
        for page in pages
    ) / max(1, total_chars)
    combined_text = "\n".join(page["raw_text"] for page in pages)
    combined_blocks = [block for page in pages for block in page.get("blocks", [])]
    metrics = score_ocr_result(combined_text, combined_blocks)
    metrics["weighted_page_score"] = round(weighted_score, 3)
    metrics["ocr_text_usable"] = all(
        bool(page["quality"]["metrics"].get("ocr_text_usable")) for page in pages
    )
    return {
        "score": round(weighted_score, 3),
        "quality_level": worst_level,
        "metrics": metrics,
        "chosen_attempt": {"aggregation": "lowest_page_quality_weighted_score"},
    }


def ocr_images_to_text(image_files: Iterable[BinaryIO]) -> OCRMultiPageResult:
    """OCR all uploaded contract page images and combine them into one document."""

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
                "quality": _empty_quality("failed", message),
                "attempts_summary": [],
            }

        page_error = result.get("error")
        page: OCRPageResult = {
            "page_index": page_index,
            "filename": filename,
            "raw_text": str(result.get("raw_text") or ""),
            "blocks": list(result.get("blocks") or []),
            "ocr_available": bool(result.get("ocr_available")),
            "error": str(page_error) if page_error else None,
            "quality": result.get("quality") or _empty_quality("failed", str(page_error) if page_error else None),
            "attempts_summary": list(result.get("attempts_summary") or []),
        }
        if page["error"]:
            errors.append(f"Страница {page_index} ({filename}): {page['error']}")
        pages.append(page)

    return {
        "raw_text": combine_ocr_page_texts(pages),
        "pages": pages,
        "ocr_available": any(page["ocr_available"] for page in pages),
        "errors": errors,
        "quality": _aggregate_quality(pages),
    }


def is_ocr_quality_sufficient(quality: dict[str, Any] | None) -> bool:
    """Return True only when OCR quality is good enough for normal analysis."""

    if not quality:
        return False
    metrics = quality.get("metrics") or {}
    if "ocr_text_usable" in metrics:
        return bool(metrics.get("ocr_text_usable"))
    return str(quality.get("quality_level") or "failed") in {"good", "medium"}


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
