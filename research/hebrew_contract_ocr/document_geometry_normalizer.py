from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from research.hebrew_contract_ocr.content_region_bounds import (
    ContentRegionBounds,
    estimate_content_region,
)
from research.hebrew_contract_ocr.content_region_deskew_crop import (
    ContentRegionDeskewCropResult,
    apply_content_region_deskew_crop,
)
from research.hebrew_contract_ocr.text_angle_estimator import (
    TextAngleEstimate,
    estimate_text_angle,
)
from research.hebrew_contract_ocr.text_ink_mask import build_text_ink_mask


class DocumentGeometryNormalizerError(ValueError):
    pass


@dataclass(frozen=True)
class DocumentGeometryNormalizationResult:
    image: Image.Image
    decision: str
    preview_size: tuple[int, int]
    source_to_preview_scale: float
    foreground_ratio: float
    angle: TextAngleEstimate
    bounds: ContentRegionBounds
    transform: ContentRegionDeskewCropResult


def normalize_document_geometry(image: Image.Image) -> DocumentGeometryNormalizationResult:
    """Run the bounded document geometry pipeline on one source image."""
    if not isinstance(image, Image.Image):
        raise DocumentGeometryNormalizerError("image must be a PIL image")

    mask_result = build_text_ink_mask(image)
    angle = estimate_text_angle(mask_result.mask)
    bounds = estimate_content_region(
        mask_result.mask,
        deskew_rotation_degrees=angle.deskew_rotation_degrees,
        angle_decision=angle.decision,
    )
    transform = apply_content_region_deskew_crop(
        image,
        angle=angle,
        bounds=bounds,
    )

    return DocumentGeometryNormalizationResult(
        image=transform.image,
        decision=transform.decision,
        preview_size=mask_result.preview.size,
        source_to_preview_scale=mask_result.source_to_preview_scale,
        foreground_ratio=mask_result.foreground_ratio,
        angle=angle,
        bounds=bounds,
        transform=transform,
    )
