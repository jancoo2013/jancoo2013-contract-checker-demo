from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


MAX_SOURCE_PIXELS = 32_000_000
MAX_SOURCE_LONG_SIDE = 8_192
MAX_GEOMETRY_ACCOUNTED_BYTES = 384 * 1024 * 1024
_INTERNAL_HEADROOM_BYTES_PER_PIXEL = 4

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
    "LAB": 3,
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
    accounted_peak_bytes_per_pixel: int
    accounted_peak_bytes: int


def _source_bytes_per_pixel(mode: str) -> int:
    try:
        return _SOURCE_MODE_BYTES_PER_PIXEL[mode]
    except KeyError as exc:
        raise GeometryResourceBudgetError(
            f"unsupported source image mode for geometry budget: {mode!r}"
        ) from exc


def _accounted_peak_bytes_per_pixel(mode: str) -> tuple[int, int]:
    source_bytes = _source_bytes_per_pixel(mode)
    if mode in _NATIVE_TRANSFORM_MODES:
        peak_bytes = 4 * source_bytes + _INTERNAL_HEADROOM_BYTES_PER_PIXEL
    else:
        # Caller source + EXIF-oriented source + RGB conversion/rotation/crop
        # + fixed per-pixel interpolation/headroom allowance.
        peak_bytes = 2 * source_bytes + 9 + _INTERNAL_HEADROOM_BYTES_PER_PIXEL
    return source_bytes, peak_bytes


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

    source_bytes, peak_bytes_per_pixel = _accounted_peak_bytes_per_pixel(mode)
    accounted_peak_bytes = pixels * peak_bytes_per_pixel
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
        accounted_peak_bytes_per_pixel=peak_bytes_per_pixel,
        accounted_peak_bytes=accounted_peak_bytes,
    )


def validate_geometry_resource_budget(image: Image.Image) -> GeometryResourceBudget:
    if not isinstance(image, Image.Image):
        raise GeometryResourceBudgetError("source must be a PIL image")
    return assess_geometry_resource_budget(image.size, image.mode)
