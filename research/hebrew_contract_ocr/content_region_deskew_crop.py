from __future__ import annotations

from dataclasses import dataclass
import math

from PIL import Image, ImageOps

from research.hebrew_contract_ocr.content_region_bounds import ContentRegionBounds
from research.hebrew_contract_ocr.text_angle_estimator import TextAngleEstimate
from research.hebrew_contract_ocr.text_ink_mask import (
    MAX_SOURCE_PIXELS,
    PREVIEW_LONG_SIDE,
)


MAX_ABS_DESKEW_DEGREES = 12.0
Box = tuple[int, int, int, int]


class ContentRegionDeskewCropError(ValueError):
    pass


@dataclass(frozen=True)
class ContentRegionDeskewCropResult:
    image: Image.Image
    decision: str
    source_size: tuple[int, int]
    output_size: tuple[int, int]
    rotation_applied_degrees: float
    crop_box_source: Box | None
    fallback_reasons: tuple[str, ...]


def _validate_angle(angle: TextAngleEstimate) -> None:
    if not isinstance(angle, TextAngleEstimate):
        raise ContentRegionDeskewCropError("angle must be a TextAngleEstimate")
    if angle.decision not in {"accepted", "rejected"}:
        raise ContentRegionDeskewCropError("invalid angle decision")
    if not math.isfinite(angle.deskew_rotation_degrees):
        raise ContentRegionDeskewCropError("deskew rotation must be finite")
    if abs(angle.deskew_rotation_degrees) > MAX_ABS_DESKEW_DEGREES:
        raise ContentRegionDeskewCropError("deskew rotation exceeds the bounded contract")


def _validate_box(box: object, preview_size: tuple[int, int]) -> Box:
    if (
        not isinstance(box, tuple)
        or len(box) != 4
        or any(not isinstance(value, int) or isinstance(value, bool) for value in box)
    ):
        raise ContentRegionDeskewCropError("safe crop bounds must be four integers")
    left, top, right, bottom = box
    width, height = preview_size
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ContentRegionDeskewCropError("safe crop bounds exceed the preview")
    return box


def _validate_bounds(
    bounds: ContentRegionBounds,
    angle: TextAngleEstimate,
    expected_preview_size: tuple[int, int],
) -> Box | None:
    if not isinstance(bounds, ContentRegionBounds):
        raise ContentRegionDeskewCropError("bounds must be ContentRegionBounds")
    if bounds.preview_size != expected_preview_size:
        raise ContentRegionDeskewCropError(
            "bounds preview size does not match the oriented source image"
        )
    if bounds.decision not in {"accepted", "rotation_only", "full_frame_fallback"}:
        raise ContentRegionDeskewCropError("invalid content-region decision")
    if not math.isfinite(bounds.deskew_rotation_degrees):
        raise ContentRegionDeskewCropError("bounds deskew rotation must be finite")
    if not math.isclose(
        bounds.deskew_rotation_degrees,
        angle.deskew_rotation_degrees,
        rel_tol=0.0,
        abs_tol=1e-6,
    ):
        raise ContentRegionDeskewCropError("angle and bounds rotations disagree")

    if angle.decision == "rejected":
        if bounds.decision != "full_frame_fallback":
            raise ContentRegionDeskewCropError(
                "rejected angle requires full-frame bounds fallback"
            )
        if bounds.coordinate_space != "source_preview":
            raise ContentRegionDeskewCropError(
                "full-frame fallback must use source-preview coordinates"
            )
    else:
        if bounds.decision == "full_frame_fallback":
            raise ContentRegionDeskewCropError(
                "accepted angle cannot use full-frame bounds fallback"
            )
        if bounds.coordinate_space != "deskewed_preview":
            raise ContentRegionDeskewCropError(
                "accepted angle requires deskewed-preview coordinates"
            )

    if bounds.decision == "accepted":
        if angle.decision != "accepted":
            raise ContentRegionDeskewCropError(
                "crop acceptance requires an accepted angle"
            )
        return _validate_box(bounds.safe_crop_bounds, bounds.preview_size)

    if bounds.safe_crop_bounds is not None:
        raise ContentRegionDeskewCropError(
            "non-accepted content region cannot provide safe crop bounds"
        )
    return None


def _oriented_source(image: Image.Image) -> Image.Image:
    if not isinstance(image, Image.Image):
        raise ContentRegionDeskewCropError("image must be a PIL image")
    oriented = ImageOps.exif_transpose(image)
    width, height = oriented.size
    if width <= 0 or height <= 0:
        raise ContentRegionDeskewCropError("source image dimensions must be positive")
    if width * height > MAX_SOURCE_PIXELS:
        raise ContentRegionDeskewCropError(
            f"source exceeds the {MAX_SOURCE_PIXELS:,}-pixel safety limit"
        )
    return oriented


def _expected_preview_size(source_size: tuple[int, int]) -> tuple[int, int]:
    width, height = source_size
    scale = min(1.0, PREVIEW_LONG_SIDE / max(width, height))
    return (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )


def _source_crop_box(
    preview_box: Box,
    preview_size: tuple[int, int],
    source_size: tuple[int, int],
) -> Box:
    preview_width, preview_height = preview_size
    source_width, source_height = source_size
    scale_x = source_width / preview_width
    scale_y = source_height / preview_height
    left, top, right, bottom = preview_box
    mapped = (
        max(0, int(math.floor(left * scale_x))),
        max(0, int(math.floor(top * scale_y))),
        min(source_width, int(math.ceil(right * scale_x))),
        min(source_height, int(math.ceil(bottom * scale_y))),
    )
    if mapped[0] >= mapped[2] or mapped[1] >= mapped[3]:
        raise ContentRegionDeskewCropError("mapped crop bounds are empty")
    return mapped


def _rotation_source(image: Image.Image) -> tuple[Image.Image, object]:
    if image.mode == "L":
        return image, 255
    if image.mode == "RGB":
        return image, (255, 255, 255)
    if image.mode == "RGBA":
        return image, (255, 255, 255, 255)
    if image.mode == "CMYK":
        return image, (0, 0, 0, 0)
    converted = image.convert("RGB")
    return converted, (255, 255, 255)


def apply_content_region_deskew_crop(
    image: Image.Image,
    *,
    angle: TextAngleEstimate,
    bounds: ContentRegionBounds,
) -> ContentRegionDeskewCropResult:
    _validate_angle(angle)
    source = _oriented_source(image)
    source_size = source.size
    preview_size = _expected_preview_size(source_size)
    preview_box = _validate_bounds(bounds, angle, preview_size)

    if angle.decision != "accepted" or bounds.decision != "accepted":
        reasons = {
            "upstream_transform_not_fully_accepted",
            *angle.rejection_reasons,
            *bounds.rejection_reasons,
        }
        return ContentRegionDeskewCropResult(
            image=source,
            decision="full_frame_fallback",
            source_size=source_size,
            output_size=source_size,
            rotation_applied_degrees=0.0,
            crop_box_source=None,
            fallback_reasons=tuple(sorted(reasons)),
        )

    if preview_box is None:
        raise ContentRegionDeskewCropError("accepted transform is missing crop bounds")
    crop_box = _source_crop_box(preview_box, preview_size, source_size)
    rotation = float(angle.deskew_rotation_degrees)
    rotation_source, fill = _rotation_source(source)
    if abs(rotation) < 1e-9:
        deskewed = rotation_source.copy()
    else:
        deskewed = rotation_source.rotate(
            rotation,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=fill,
        )
    output = deskewed.crop(crop_box)
    return ContentRegionDeskewCropResult(
        image=output,
        decision="deskewed_and_cropped",
        source_size=source_size,
        output_size=output.size,
        rotation_applied_degrees=rotation,
        crop_box_source=crop_box,
        fallback_reasons=(),
    )
