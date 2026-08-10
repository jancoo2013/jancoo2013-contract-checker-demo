from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from research.hebrew_contract_ocr.geometry_resource_budget import (
    MAX_SOURCE_PIXELS,
    PREVIEW_LONG_SIDE,
    GeometryResourceBudgetError,
    validate_geometry_resource_budget,
)


class TextInkMaskError(ValueError):
    pass


@dataclass(frozen=True)
class TextInkMaskResult:
    preview: Image.Image
    mask: np.ndarray
    source_to_preview_scale: float
    threshold: float
    foreground_ratio: float


def _make_preview(image: Image.Image) -> tuple[Image.Image, float]:
    try:
        validate_geometry_resource_budget(image)
    except GeometryResourceBudgetError as exc:
        raise TextInkMaskError(str(exc)) from exc

    preview = ImageOps.exif_transpose(image).convert("L")
    scale = min(1.0, PREVIEW_LONG_SIDE / max(preview.size))
    if scale < 1.0:
        preview = preview.resize(
            (
                max(1, int(round(preview.width * scale))),
                max(1, int(round(preview.height * scale))),
            ),
            Image.Resampling.LANCZOS,
        )
    return preview, scale


def build_text_ink_mask(image: Image.Image) -> TextInkMaskResult:
    preview, scale = _make_preview(image)
    radius = max(5.0, min(preview.size) * 0.012)
    background = preview.filter(ImageFilter.GaussianBlur(radius=radius))

    gray = np.asarray(preview, dtype=np.int16)
    local_background = np.asarray(background, dtype=np.int16)
    contrast = np.clip(local_background - gray, 0, 255).astype(np.float32)

    median = float(np.median(contrast))
    mad = float(np.median(np.abs(contrast - median)))
    percentile = float(np.percentile(contrast, 92.0))
    threshold = max(9.0, median + 4.0 * max(mad, 1.0), percentile * 0.42)
    threshold = min(threshold, 48.0)

    mask = contrast >= threshold
    foreground_ratio = float(np.count_nonzero(mask)) / float(mask.size)
    return TextInkMaskResult(
        preview=preview,
        mask=mask,
        source_to_preview_scale=scale,
        threshold=threshold,
        foreground_ratio=foreground_ratio,
    )
