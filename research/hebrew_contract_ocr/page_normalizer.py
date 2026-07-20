from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


SCHEMA_VERSION = 1
PREVIEW_LONG_SIDE = 1800
STANDARD_MASTER_LONG_SIDE = 3508
HIGH_DETAIL_MASTER_LONG_SIDE = 4096
MIN_PAGE_LONG_SIDE = 2200
MIN_TEXT_BAND_HEIGHT = 24
PREFERRED_TEXT_BAND_HEIGHT = (30, 48)
LINE_RECOGNIZER_HEIGHT = 64
MAX_SOURCE_PIXELS = 150_000_000
QUAD_SAMPLING_INSET_PIXELS = 4.0
CROP_POLICY = "accepted_quadrilateral_else_full_frame"
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}

Point = tuple[float, float]
Corners = tuple[Point, Point, Point, Point]


class PageNormalizationError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizedPage:
    preview: Image.Image
    master: Image.Image
    report: Mapping[str, Any]


def _distance(first: Point, second: Point) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def _full_frame_corners(width: int, height: int) -> Corners:
    return (
        (0.0, 0.0),
        (float(width - 1), 0.0),
        (float(width - 1), float(height - 1)),
        (0.0, float(height - 1)),
    )


def _inset_corners(corners: Corners, pixels: float) -> Corners:
    center_x = sum(point[0] for point in corners) / 4.0
    center_y = sum(point[1] for point in corners) / 4.0
    inset: list[Point] = []
    for x, y in corners:
        distance = math.hypot(center_x - x, center_y - y)
        scale = min(1.0, pixels / max(distance, 1e-9))
        inset.append((x + (center_x - x) * scale, y + (center_y - y) * scale))
    return tuple(inset)  # type: ignore[return-value]


def _validate_corners(corners: Sequence[Sequence[float]], width: int, height: int) -> Corners:
    if len(corners) != 4:
        raise PageNormalizationError("corners must contain TL, TR, BR, BL points")
    try:
        points: Corners = tuple(
            (float(point[0]), float(point[1]))
            for point in corners
        )  # type: ignore[assignment]
    except (IndexError, TypeError, ValueError) as exc:
        raise PageNormalizationError("each corner must contain numeric x and y coordinates") from exc

    for x, y in points:
        if not math.isfinite(x) or not math.isfinite(y):
            raise PageNormalizationError("corner coordinates must be finite")
        if not 0.0 <= x <= width - 1 or not 0.0 <= y <= height - 1:
            raise PageNormalizationError("corner coordinates must stay inside the oriented source image")

    cross_products: list[float] = []
    for index in range(4):
        first = points[index]
        second = points[(index + 1) % 4]
        third = points[(index + 2) % 4]
        cross_products.append(
            (second[0] - first[0]) * (third[1] - second[1])
            - (second[1] - first[1]) * (third[0] - second[0])
        )
    if any(abs(value) < 1e-6 for value in cross_products):
        raise PageNormalizationError("page quadrilateral contains collinear corners")
    if not (all(value > 0 for value in cross_products) or all(value < 0 for value in cross_products)):
        raise PageNormalizationError("corners must form a convex TL, TR, BR, BL quadrilateral")

    area = 0.5 * abs(
        sum(
            points[index][0] * points[(index + 1) % 4][1]
            - points[(index + 1) % 4][0] * points[index][1]
            for index in range(4)
        )
    )
    if area < width * height * 0.02:
        raise PageNormalizationError("page quadrilateral is implausibly small")
    return points


def _target_size(corners: Corners, profile: str) -> tuple[int, int, dict[str, Any]]:
    top_left, top_right, bottom_right, bottom_left = corners
    measured_width = 1.0 + (_distance(top_left, top_right) + _distance(bottom_left, bottom_right)) / 2.0
    measured_height = 1.0 + (_distance(top_left, bottom_left) + _distance(top_right, bottom_right)) / 2.0
    if measured_width < 1.0 or measured_height < 1.0:
        raise PageNormalizationError("page quadrilateral has invalid dimensions")

    if profile == "standard":
        requested_long_side = STANDARD_MASTER_LONG_SIDE
    elif profile == "high-detail":
        requested_long_side = HIGH_DETAIL_MASTER_LONG_SIDE
    else:
        raise PageNormalizationError(f"unsupported normalization profile: {profile}")

    measured_long = max(measured_width, measured_height)
    scale = min(1.0, requested_long_side / measured_long)
    output_width = max(1, int(math.floor(measured_width * scale)))
    output_height = max(1, int(math.floor(measured_height * scale)))
    geometry = {
        "measured_quad_width": round(measured_width, 3),
        "measured_quad_height": round(measured_height, 3),
        "measured_long_side": round(measured_long, 3),
        "requested_long_side": requested_long_side,
        "upscaled": False,
    }
    return output_width, output_height, geometry


def _preview(image: Image.Image) -> Image.Image:
    preview = image.convert("RGB")
    if max(preview.size) > PREVIEW_LONG_SIDE:
        preview.thumbnail((PREVIEW_LONG_SIDE, PREVIEW_LONG_SIDE), Image.Resampling.LANCZOS)
    return preview


def _otsu_threshold(grayscale: np.ndarray) -> int:
    histogram = np.bincount(grayscale.reshape(-1), minlength=256).astype(np.float64)
    total = float(grayscale.size)
    weighted_total = float(np.dot(np.arange(256, dtype=np.float64), histogram))
    background_weight = 0.0
    background_sum = 0.0
    best_variance = -1.0
    best_threshold = 127
    for threshold in range(256):
        background_weight += histogram[threshold]
        if background_weight == 0.0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0.0:
            break
        background_sum += threshold * histogram[threshold]
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_total - background_sum) / foreground_weight
        between_variance = background_weight * foreground_weight * (background_mean - foreground_mean) ** 2
        if between_variance > best_variance:
            best_variance = between_variance
            best_threshold = threshold
    return best_threshold


def estimate_text_band_height(image: Image.Image) -> float | None:
    grayscale = np.asarray(ImageOps.grayscale(image), dtype=np.uint8)
    height, width = grayscale.shape
    x_margin = max(1, int(round(width * 0.05)))
    y_margin = max(1, int(round(height * 0.05)))
    region = grayscale[y_margin : height - y_margin, x_margin : width - x_margin]
    if region.size == 0:
        return None
    threshold = min(200, max(64, _otsu_threshold(region)))
    row_ink = np.count_nonzero(region < threshold, axis=1)
    minimum_ink = max(8, int(round(region.shape[1] * 0.0025)))
    maximum_ink = max(minimum_ink + 1, int(round(region.shape[1] * 0.45)))
    active = (row_ink >= minimum_ink) & (row_ink <= maximum_ink)

    runs: list[int] = []
    start: int | None = None
    last_active: int | None = None
    for index, is_active in enumerate(active):
        if is_active:
            if start is None:
                start = index
            last_active = index
        elif start is not None and last_active is not None and index - last_active > 2:
            run_height = last_active - start + 1
            if 6 <= run_height <= 96:
                runs.append(run_height)
            start = None
            last_active = None
    if start is not None and last_active is not None:
        run_height = last_active - start + 1
        if 6 <= run_height <= 96:
            runs.append(run_height)
    if len(runs) < 2:
        return None
    ordinary_text_runs = [height for height in runs if height >= MIN_TEXT_BAND_HEIGHT]
    if len(ordinary_text_runs) >= 2 and len(ordinary_text_runs) >= math.ceil(len(runs) * 0.2):
        runs = ordinary_text_runs
    return round(float(statistics.median(runs)), 3)


def _resolution_status(master: Image.Image, text_band_height: float | None) -> tuple[str, bool | None]:
    if max(master.size) < MIN_PAGE_LONG_SIDE:
        return "fail_page_too_small", False
    if text_band_height is None:
        return "review_no_text_measurement", None
    if text_band_height < MIN_TEXT_BAND_HEIGHT:
        return "fail_text_too_small", False
    return "pass", True


def normalize_page(
    image: Image.Image,
    *,
    corners: Sequence[Sequence[float]] | None = None,
    profile: str = "standard",
    apply_exif_orientation: bool = True,
) -> NormalizedPage:
    raw_width, raw_height = image.size
    if raw_width <= 0 or raw_height <= 0:
        raise PageNormalizationError("source image dimensions must be positive")
    if raw_width * raw_height > MAX_SOURCE_PIXELS:
        raise PageNormalizationError(
            f"source exceeds the {MAX_SOURCE_PIXELS:,}-pixel reference-tool safety limit"
        )
    oriented = ImageOps.exif_transpose(image) if apply_exif_orientation else image.copy()
    oriented.load()
    source_width, source_height = oriented.size

    used_full_frame = corners is None
    normalized_corners = _validate_corners(
        corners if corners is not None else _full_frame_corners(source_width, source_height),
        source_width,
        source_height,
    )
    output_width, output_height, geometry = _target_size(normalized_corners, profile)
    sampling_corners = (
        normalized_corners
        if used_full_frame
        else _inset_corners(normalized_corners, QUAD_SAMPLING_INSET_PIXELS)
    )
    top_left, top_right, bottom_right, bottom_left = sampling_corners
    quad = (
        top_left[0],
        top_left[1],
        bottom_left[0],
        bottom_left[1],
        bottom_right[0],
        bottom_right[1],
        top_right[0],
        top_right[1],
    )
    grayscale = ImageOps.grayscale(oriented)
    master = grayscale.transform(
        (output_width, output_height),
        Image.Transform.QUAD,
        quad,
        resample=Image.Resampling.BICUBIC,
        fillcolor=255,
    )
    text_band_height = estimate_text_band_height(master)
    status, quality_gate_passed = _resolution_status(master, text_band_height)
    preview_image = _preview(oriented)
    report = {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "source_width": source_width,
        "source_height": source_height,
        "source_pixels": source_width * source_height,
        "exif_orientation_applied": apply_exif_orientation,
        "preview_width": preview_image.width,
        "preview_height": preview_image.height,
        "master_width": master.width,
        "master_height": master.height,
        "master_mode": master.mode,
        "corners_tl_tr_br_bl": [[round(x, 3), round(y, 3)] for x, y in normalized_corners],
        "sampling_corners_tl_tr_br_bl": [
            [round(x, 3), round(y, 3)] for x, y in sampling_corners
        ],
        "quad_sampling_inset_pixels": 0.0 if used_full_frame else QUAD_SAMPLING_INSET_PIXELS,
        "used_full_frame": used_full_frame,
        "crop_policy": CROP_POLICY,
        "outside_quadrilateral_discarded": not used_full_frame,
        "estimated_text_band_height": text_band_height,
        "minimum_text_band_height": MIN_TEXT_BAND_HEIGHT,
        "preferred_text_band_height": list(PREFERRED_TEXT_BAND_HEIGHT),
        "resolution_status": status,
        "quality_gate_passed": quality_gate_passed,
        **geometry,
    }
    return NormalizedPage(preview=preview_image, master=master, report=report)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)]


def _load_corners(path: Path | None) -> dict[str, Sequence[Sequence[float]] | None]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PageNormalizationError("corners JSON must be an object keyed by source filename")
    invalid = [key for key, value in payload.items() if value is not None and not isinstance(value, list)]
    if invalid:
        raise PageNormalizationError(f"corners JSON entries must be arrays or null: {invalid}")
    return {str(key): value for key, value in payload.items()}


def _check_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise PageNormalizationError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise PageNormalizationError(f"output directory must be empty: {output_dir}")


def _save_verified_png(image: Image.Image, path: Path) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        image.save(temporary_path, format="PNG", optimize=True)
        with Image.open(temporary_path) as decoded:
            decoded.load()
            if decoded.size != image.size or decoded.mode != image.mode:
                raise PageNormalizationError(f"saved page master changed shape or mode: {path.name}")
        temporary_path.replace(path)
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        if isinstance(exc, PageNormalizationError):
            raise
        raise PageNormalizationError(f"saved page master failed decode verification: {path.name}") from exc


def normalize_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    corners_json: Path | None = None,
    assume_full_frame: bool = False,
    profile: str = "standard",
    apply_exif_orientation: bool = True,
) -> dict[str, Any]:
    if not input_dir.is_dir():
        raise PageNormalizationError(f"input directory does not exist: {input_dir}")
    _check_output_directory(output_dir)
    sources = sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
        ),
        key=_natural_key,
    )
    if not sources:
        raise PageNormalizationError(f"no supported page images found in {input_dir}")
    corners_by_name = _load_corners(corners_json)
    unknown_corner_names = sorted(set(corners_by_name).difference(path.name for path in sources))
    if unknown_corner_names:
        raise PageNormalizationError(f"corners JSON contains unknown files: {unknown_corner_names}")
    if not assume_full_frame:
        missing = [path.name for path in sources if path.name not in corners_by_name]
        if missing:
            raise PageNormalizationError(
                "page corners are required for phone photos; missing entries: " + ", ".join(missing)
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = output_dir / "pages"
    previews_dir = output_dir / "previews"
    pages_dir.mkdir()
    previews_dir.mkdir()
    rows: list[dict[str, Any]] = []
    seen_stems: set[str] = set()
    for page_index, source_path in enumerate(sources, start=1):
        stem_key = source_path.stem.casefold()
        if stem_key in seen_stems:
            raise PageNormalizationError(f"duplicate source filename stem: {source_path.stem}")
        seen_stems.add(stem_key)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            try:
                with Image.open(source_path) as source_image:
                    result = normalize_page(
                        source_image,
                        corners=corners_by_name.get(source_path.name),
                        profile=profile,
                        apply_exif_orientation=apply_exif_orientation,
                    )
            except (UnidentifiedImageError, OSError) as exc:
                raise PageNormalizationError(f"could not decode {source_path}") from exc

        page_name = f"page_{page_index:04d}.png"
        preview_name = f"page_{page_index:04d}_preview.jpg"
        master_path = pages_dir / page_name
        preview_path = previews_dir / preview_name
        _save_verified_png(result.master, master_path)
        result.preview.save(preview_path, format="JPEG", quality=88, optimize=True)
        rows.append(
            {
                **dict(result.report),
                "page_id": f"P{page_index:04d}",
                "source_name": source_path.name,
                "source_sha256": _sha256_file(source_path),
                "master_image": master_path.relative_to(output_dir).as_posix(),
                "master_sha256": _sha256_file(master_path),
                "preview_image": preview_path.relative_to(output_dir).as_posix(),
                "preview_sha256": _sha256_file(preview_path),
            }
        )

    manifest_path = output_dir / "manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    status_counts = dict(sorted(Counter(str(row["resolution_status"]) for row in rows).items()))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "exif_orientation_applied": apply_exif_orientation,
        "pages": len(rows),
        "resolution_statuses": status_counts,
        "quality_failures": sum(
            count for status, count in status_counts.items() if status.startswith("fail_")
        ),
        "preview_long_side": PREVIEW_LONG_SIDE,
        "standard_master_long_side": STANDARD_MASTER_LONG_SIDE,
        "high_detail_master_long_side": HIGH_DETAIL_MASTER_LONG_SIDE,
        "minimum_page_long_side": MIN_PAGE_LONG_SIDE,
        "minimum_text_band_height": MIN_TEXT_BAND_HEIGHT,
        "line_recognizer_height": LINE_RECOGNIZER_HEIGHT,
        "crop_policy": CROP_POLICY,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize local contract page photos to the OCR Image Resolution Contract v0."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--corners-json", type=Path)
    parser.add_argument("--assume-full-frame", action="store_true")
    parser.add_argument("--profile", choices=("standard", "high-detail"), default="standard")
    parser.add_argument(
        "--ignore-exif-orientation",
        action="store_true",
        help="Use only when pixels are already upright but the file retains a stale orientation tag.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = normalize_directory(
        args.input_dir,
        args.output_dir,
        corners_json=args.corners_json,
        assume_full_frame=args.assume_full_frame,
        profile=args.profile,
        apply_exif_orientation=not args.ignore_exif_orientation,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if summary["quality_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
