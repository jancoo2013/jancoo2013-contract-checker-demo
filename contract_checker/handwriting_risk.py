"""Local image-only handwriting risk scaffold."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image, ImageOps


HandwritingRiskStatus = Literal[
    "handwriting_detected",
    "no_handwriting_detected",
    "uncertain",
]


@dataclass(frozen=True)
class ImageRegion:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass(frozen=True)
class HandwritingRiskAssessment:
    status: HandwritingRiskStatus
    confidence: float
    reasons: tuple[str, ...]
    suggested_regions: tuple[ImageRegion, ...]


@dataclass(frozen=True)
class _TileComponent:
    x1: int
    y1: int
    x2: int
    y2: int
    tile_count: int


def assess_handwriting_risk_from_image(
    image: object,
    *,
    max_dimension: int = 900,
) -> HandwritingRiskAssessment:
    try:
        grayscale, scale_x, scale_y = _prepare_grayscale_image(image, max_dimension=max_dimension)
    except Exception:
        return HandwritingRiskAssessment(
            status="uncertain",
            confidence=0.0,
            reasons=("image_processing_failed",),
            suggested_regions=(),
        )

    pixels = np.asarray(grayscale, dtype=np.uint8)
    if pixels.size == 0:
        return HandwritingRiskAssessment(
            status="uncertain",
            confidence=0.0,
            reasons=("image_processing_failed",),
            suggested_regions=(),
        )

    height, width = pixels.shape
    dark_mask = pixels < 105
    dark_ratio = float(np.count_nonzero(dark_mask)) / float(width * height)

    if dark_ratio < 0.0004:
        return HandwritingRiskAssessment(
            status="no_handwriting_detected",
            confidence=0.75,
            reasons=("no_handwriting_like_regions_detected",),
            suggested_regions=(),
        )

    components = _find_dark_tile_components(dark_mask)
    candidates = _find_suspicious_components(components, dark_mask)

    if candidates:
        regions = tuple(
            _scale_region(component, scale_x=scale_x, scale_y=scale_y)
            for component in candidates[:3]
        )
        reasons = ["freeform_dark_cluster_detected"]
        if any(component.y1 >= int(height * 0.58) for component in candidates):
            reasons.insert(0, "signature_zone_dark_cluster_detected")
        return HandwritingRiskAssessment(
            status="handwriting_detected",
            confidence=0.82,
            reasons=tuple(dict.fromkeys(reasons)),
            suggested_regions=regions,
        )

    if dark_ratio < 0.002:
        return HandwritingRiskAssessment(
            status="uncertain",
            confidence=0.25,
            reasons=("too_little_text_or_ink_to_assess",),
            suggested_regions=(),
        )

    return HandwritingRiskAssessment(
        status="no_handwriting_detected",
        confidence=0.62,
        reasons=("no_handwriting_like_regions_detected",),
        suggested_regions=(),
    )


def _prepare_grayscale_image(image: object, *, max_dimension: int) -> tuple[Image.Image, float, float]:
    if isinstance(image, Image.Image):
        pil_image = image
    elif isinstance(image, np.ndarray):
        pil_image = Image.fromarray(image)
    else:
        pil_image = Image.open(image)  # type: ignore[arg-type]

    grayscale = ImageOps.grayscale(pil_image)
    original_width, original_height = grayscale.size

    longest_side = max(original_width, original_height)
    if longest_side > max_dimension:
        ratio = max_dimension / float(longest_side)
        resized_size = (
            max(1, int(original_width * ratio)),
            max(1, int(original_height * ratio)),
        )
        grayscale = grayscale.resize(resized_size, Image.Resampling.LANCZOS)

    resized_width, resized_height = grayscale.size
    scale_x = original_width / float(resized_width)
    scale_y = original_height / float(resized_height)
    return grayscale, scale_x, scale_y


def _find_dark_tile_components(dark_mask: np.ndarray) -> list[_TileComponent]:
    height, width = dark_mask.shape
    tile_size = max(10, min(width, height) // 45)
    rows = (height + tile_size - 1) // tile_size
    cols = (width + tile_size - 1) // tile_size

    active = np.zeros((rows, cols), dtype=bool)
    for row in range(rows):
        y1 = row * tile_size
        y2 = min(height, y1 + tile_size)
        for col in range(cols):
            x1 = col * tile_size
            x2 = min(width, x1 + tile_size)
            tile = dark_mask[y1:y2, x1:x2]
            if tile.size and float(np.count_nonzero(tile)) / float(tile.size) >= 0.035:
                active[row, col] = True

    components: list[_TileComponent] = []
    visited = np.zeros_like(active)
    for row in range(rows):
        for col in range(cols):
            if not active[row, col] or visited[row, col]:
                continue
            queue: deque[tuple[int, int]] = deque([(row, col)])
            visited[row, col] = True
            min_row = max_row = row
            min_col = max_col = col
            tile_count = 0
            while queue:
                current_row, current_col = queue.popleft()
                tile_count += 1
                min_row = min(min_row, current_row)
                max_row = max(max_row, current_row)
                min_col = min(min_col, current_col)
                max_col = max(max_col, current_col)
                for next_row in range(current_row - 1, current_row + 2):
                    for next_col in range(current_col - 1, current_col + 2):
                        if (
                            0 <= next_row < rows
                            and 0 <= next_col < cols
                            and active[next_row, next_col]
                            and not visited[next_row, next_col]
                        ):
                            visited[next_row, next_col] = True
                            queue.append((next_row, next_col))
            components.append(
                _TileComponent(
                    x1=min_col * tile_size,
                    y1=min_row * tile_size,
                    x2=min(width, (max_col + 1) * tile_size),
                    y2=min(height, (max_row + 1) * tile_size),
                    tile_count=tile_count,
                )
            )
    return components


def _find_suspicious_components(
    components: list[_TileComponent],
    dark_mask: np.ndarray,
) -> list[_TileComponent]:
    height, width = dark_mask.shape
    suspicious: list[_TileComponent] = []

    for component in components:
        component_width = component.x2 - component.x1
        component_height = component.y2 - component.y1
        if component_width <= 0 or component_height <= 0:
            continue

        width_ratio = component_width / float(width)
        height_ratio = component_height / float(height)
        region = dark_mask[component.y1 : component.y2, component.x1 : component.x2]
        density = float(np.count_nonzero(region)) / float(region.size)
        lower_zone = component.y1 >= int(height * 0.58)

        compact_freeform = (
            0.08 <= width_ratio <= 0.62
            and 0.025 <= height_ratio <= 0.22
            and 0.015 <= density <= 0.38
            and component.tile_count >= 4
        )
        lower_signature_like = lower_zone and compact_freeform
        non_paragraph_freeform = compact_freeform and width_ratio <= 0.45 and component_height >= 18

        if lower_signature_like or non_paragraph_freeform:
            suspicious.append(component)

    suspicious.sort(key=lambda component: (component.y1 < int(height * 0.58), -component.tile_count))
    return suspicious


def _scale_region(component: _TileComponent, *, scale_x: float, scale_y: float) -> ImageRegion:
    return ImageRegion(
        x1=max(0, int(component.x1 * scale_x)),
        y1=max(0, int(component.y1 * scale_y)),
        x2=max(0, int(component.x2 * scale_x)),
        y2=max(0, int(component.y2 * scale_y)),
    )
