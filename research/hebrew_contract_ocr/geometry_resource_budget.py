from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


PREVIEW_LONG_SIDE = 1800
MAX_SOURCE_PIXELS = 32_000_000
MAX_SOURCE_LONG_SIDE = 8_192
MAX_GEOMETRY_ACCOUNTED_BYTES = 384 * 1024 * 1024

# Full-resolution transform accounting keeps the existing conservative allowance
# for Pillow interpolation/internal copies.
_TRANSFORM_INTERNAL_HEADROOM_BYTES_PER_PIXEL = 4

# The preview pipeline keeps several bounded L/NumPy buffers alive at once:
# preview/background images, int16 grayscale/background arrays, float32 local
# contrast, threshold/median/percentile scratch, boolean masks and later
# preview-level geometry copies. 48 bytes per preview pixel is a deliberately
# conservative reserve for that working set rather than an RSS measurement.
PREVIEW_ANALYSIS_WORKING_BYTES_PER_PIXEL = 48

# normalize_document_geometry() retains the L preview and bool mask while the
# full-resolution physical transform runs. The shared budget includes both so
# direct transform callers use the same conservative contract.
PERSISTENT_PREVIEW_BYTES_PER_PIXEL = 2

# Only modes that the current physical transform path can either handle
# natively or convert to RGB are admitted. LAB is intentionally absent: the
# audited reference runtime cannot rely on LAB -> RGB conversion support.
_SOURCE_MODE_BYTES_PER_PIXEL = {
    "1": 1,
    "L": 1,
    "P": 1,
    "LA": 2,
    "I;16": 2,
    "I;16L": 2,
    "I;16B": 2,
    "I;16N": 2,
    "RGB": 3,
    "YCbCr": 3,
    "HSV": 3,
    "RGBA": 4,
    "RGBX": 4,
    "CMYK": 4,
    "I": 4,
    "F": 4,
}
_NATIVE_TRANSFORM_MODES = {"L", "RGB", "RGBA", "CMYK"}


class GeometryResourceBudgetError(ValueError):
    pass


@dataclass(frozen=True)
class GeometryResourceBudget:
    source_size: tuple[int, int]
    source_mode: str
    source_pixels: int
    source_bytes_per_pixel: int
    preview_size: tuple[int, int]
    preview_pixels: int
    transform_peak_bytes_per_pixel: int
    transform_phase_bytes: int
    preview_analysis_phase_bytes: int
    accounted_peak_bytes: int


def _source_bytes_per_pixel(mode: str) -> int:
    if not isinstance(mode, str):
        raise GeometryResourceBudgetError(
            f"unsupported source image mode for geometry budget: {mode!r}"
        )
    try:
        return _SOURCE_MODE_BYTES_PER_PIXEL[mode]
    except KeyError as exc:
        raise GeometryResourceBudgetError(
            f"unsupported source image mode for geometry budget: {mode!r}"
        ) from exc


def _transform_peak_bytes_per_pixel(mode: str) -> tuple[int, int]:
    source_bytes = _source_bytes_per_pixel(mode)
    if mode in _NATIVE_TRANSFORM_MODES:
        peak_bytes = 4 * source_bytes + _TRANSFORM_INTERNAL_HEADROOM_BYTES_PER_PIXEL
    else:
        # Caller source + EXIF-oriented source + RGB conversion/rotation/crop
        # + fixed per-pixel interpolation/headroom allowance.
        peak_bytes = (
            2 * source_bytes + 9 + _TRANSFORM_INTERNAL_HEADROOM_BYTES_PER_PIXEL
        )
    return source_bytes, peak_bytes


def _preview_size(size: tuple[int, int]) -> tuple[int, int]:
    width, height = size
    scale = min(1.0, PREVIEW_LONG_SIDE / max(width, height))
    return (
        max(1, int(round(width * scale))),
        max(1, int(round(height * scale))),
    )


def assess_geometry_resource_budget(
    size: tuple[int, int],
    mode: str,
) -> GeometryResourceBudget:
    if (
        not isinstance(size, tuple)
        or len(size) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) for value in size)
    ):
        raise GeometryResourceBudgetError("source size must be two integers")
    width, height = size
    if width <= 0 or height <= 0:
        raise GeometryResourceBudgetError("source image dimensions must be positive")
    if max(width, height) > MAX_SOURCE_LONG_SIDE:
        raise GeometryResourceBudgetError(
            f"source dimension exceeds the {MAX_SOURCE_LONG_SIDE:,}-pixel long-side limit"
        )

    pixels = width * height
    if pixels > MAX_SOURCE_PIXELS:
        raise GeometryResourceBudgetError(
            f"source exceeds the {MAX_SOURCE_PIXELS:,}-pixel safety limit"
        )

    source_bytes, transform_bytes_per_pixel = _transform_peak_bytes_per_pixel(mode)
    preview_size = _preview_size(size)
    preview_pixels = preview_size[0] * preview_size[1]

    # Phase 1: full-resolution EXIF/convert/rotate/crop work. This also covers
    # the earlier full-resolution preview preparation because that path needs
    # fewer source-sized copies than the physical-transform allowance. The
    # top-level normalizer retains one L preview and one bool mask concurrently.
    transform_phase_bytes = (
        pixels * transform_bytes_per_pixel
        + preview_pixels * PERSISTENT_PREVIEW_BYTES_PER_PIXEL
    )

    # Phase 2: preview analysis after full-resolution temporaries have been
    # released. The caller-owned source remains alive while the bounded preview
    # working set is built and analyzed.
    preview_analysis_phase_bytes = (
        pixels * source_bytes
        + preview_pixels * PREVIEW_ANALYSIS_WORKING_BYTES_PER_PIXEL
    )

    accounted_peak_bytes = max(transform_phase_bytes, preview_analysis_phase_bytes)
    if accounted_peak_bytes > MAX_GEOMETRY_ACCOUNTED_BYTES:
        raise GeometryResourceBudgetError(
            "source exceeds the geometry accounted-memory budget: "
            f"{accounted_peak_bytes:,} > {MAX_GEOMETRY_ACCOUNTED_BYTES:,} bytes"
        )

    return GeometryResourceBudget(
        source_size=size,
        source_mode=mode,
        source_pixels=pixels,
        source_bytes_per_pixel=source_bytes,
        preview_size=preview_size,
        preview_pixels=preview_pixels,
        transform_peak_bytes_per_pixel=transform_bytes_per_pixel,
        transform_phase_bytes=transform_phase_bytes,
        preview_analysis_phase_bytes=preview_analysis_phase_bytes,
        accounted_peak_bytes=accounted_peak_bytes,
    )


def validate_geometry_resource_budget(image: Image.Image) -> GeometryResourceBudget:
    if not isinstance(image, Image.Image):
        raise GeometryResourceBudgetError("source must be a PIL image")
    return assess_geometry_resource_budget(image.size, image.mode)
