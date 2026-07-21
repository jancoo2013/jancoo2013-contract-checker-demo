from __future__ import annotations

import hashlib
import io
import json
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image

from .line_segmenter import MAX_PAGE_PIXELS, segment_page
from .pii_annotations import PII_CLASSES, validate_annotation_manifest

SCHEMA_VERSION = 1
ALGORITHM = "marker_layout_baseline_v0"
REASON_CODES = frozenset({
    "party_header_zone",
    "property_address_zone",
    "signature_zone",
    "right_label_shape",
    "digit_pattern",
    "segmentation_review",
})


class PIIBaselineError(ValueError):
    pass


def _canonical_jsonl(rows: Sequence[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def _resolve_image(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise PIIBaselineError("image must be a non-empty relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PIIBaselineError(f"unsafe image path: {value}")
    root = root.resolve()
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise PIIBaselineError(f"image escapes root or does not exist: {value}")
    return path


def _load_identity_rows(manifest_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        rows.append({
            "image_id": row["image_id"],
            "image": row["image"],
            "image_sha256": row["image_sha256"],
            "width": row["width"],
            "height": row["height"],
        })
    return rows


def _runs(flags: np.ndarray) -> list[tuple[int, int]]:
    indices = np.flatnonzero(flags)
    if not indices.size:
        return []
    result: list[tuple[int, int]] = []
    start = previous = int(indices[0])
    for raw in indices[1:]:
        index = int(raw)
        if index - previous > 2:
            result.append((start, previous + 1))
            start = index
        previous = index
    result.append((start, previous + 1))
    return result


def _digit_pattern(ink: np.ndarray) -> bool:
    height, width = ink.shape
    if height < 8 or width < 20:
        return False
    runs = _runs(np.any(ink, axis=0))
    widths = [end - start for start, end in runs]
    compact = [value for value in widths if 1 <= value <= max(3, int(round(height * 0.85)))]
    return 7 <= len(runs) <= 14 and len(compact) >= max(7, len(runs) - 1)


def _expanded_bbox(bbox: Sequence[int], width: int, height: int) -> list[int]:
    x0, y0, x1, y1 = map(int, bbox)
    line_height = y1 - y0
    pad_x = max(4, int(round(line_height * 1.25)))
    pad_y = max(2, int(round(line_height * 0.30)))
    return [
        max(0, x0 - pad_x),
        max(0, y0 - pad_y),
        min(width, x1 + pad_x),
        min(height, y1 + pad_y),
    ]


def predict_page(image: Image.Image, image_id: str) -> list[dict[str, Any]]:
    grayscale = image.convert("L")
    width, height = grayscale.size
    if width <= 0 or height <= 0 or width * height > MAX_PAGE_PIXELS:
        raise PIIBaselineError("page dimensions exceed baseline limits")
    segmented = segment_page(grayscale)
    pixels = np.asarray(grayscale, dtype=np.uint8)
    ink = pixels <= segmented.threshold
    candidates: list[dict[str, Any]] = []

    for line in segmented.lines:
        x0, y0, x1, y1 = line.bbox
        if "foreground_too_small" in line.reasons:
            continue
        center_y = ((y0 + y1) / 2.0) / height
        line_width = x1 - x0
        proposed_class: str | None = None
        reasons: list[str] = []

        if 0.18 <= center_y < 0.42:
            proposed_class = "property_address"
            reasons.append("property_address_zone")
        elif center_y < 0.18:
            proposed_class = "other_likely_pii"
            reasons.append("party_header_zone")
        elif center_y >= 0.72:
            proposed_class = "signature"
            reasons.append("signature_zone")
        elif x1 >= int(width * 0.72) and line_width <= int(width * 0.38):
            proposed_class = "other_likely_pii"
            reasons.append("right_label_shape")
        elif line_width <= int(width * 0.60) and _digit_pattern(ink[y0:y1, x0:x1]):
            proposed_class = "other_likely_pii"
            reasons.append("digit_pattern")

        if proposed_class is None:
            continue
        if line.status != "accepted":
            reasons.append("segmentation_review")
        if proposed_class not in PII_CLASSES or any(reason not in REASON_CODES for reason in reasons):
            raise PIIBaselineError("internal error: unsupported candidate classification")
        order = len(candidates) + 1
        candidates.append({
            "candidate_id": f"{image_id}-C{order:04d}",
            "proposed_class": proposed_class,
            "geometry": {"type": "bbox", "coordinates": _expanded_bbox(line.bbox, width, height)},
            "review_status": "needs_review",
            "reason_codes": sorted(set(reasons)),
        })
    return candidates


def generate_baseline_predictions(
    annotation_manifest: Path,
    image_root: Path,
    output_manifest: Path,
) -> dict[str, Any]:
    validation = validate_annotation_manifest(annotation_manifest, image_root)
    if not validation["valid"]:
        raise PIIBaselineError("annotation manifest is invalid: " + "; ".join(validation["errors"]))
    if output_manifest.exists():
        raise PIIBaselineError("output manifest already exists")

    rows: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    candidate_count = 0
    for identity in _load_identity_rows(annotation_manifest):
        path = _resolve_image(image_root, identity["image"])
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != identity["image_sha256"]:
            raise PIIBaselineError(f"{identity['image_id']}: image hash changed after validation")
        with Image.open(io.BytesIO(data)) as source:
            if source.size != (identity["width"], identity["height"]):
                raise PIIBaselineError(f"{identity['image_id']}: image dimensions changed after validation")
            if source.width * source.height > MAX_PAGE_PIXELS:
                raise PIIBaselineError(f"{identity['image_id']}: image exceeds baseline pixel limit")
            source.load()
            candidates = predict_page(source, identity["image_id"])
        for candidate in candidates:
            class_counts[candidate["proposed_class"]] += 1
        candidate_count += len(candidates)
        rows.append({
            "schema_version": SCHEMA_VERSION,
            "algorithm": ALGORITHM,
            **identity,
            "candidates": candidates,
        })

    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_manifest.with_name(f".{output_manifest.name}.tmp")
    try:
        temporary.write_text(_canonical_jsonl(rows), encoding="utf-8")
        temporary.replace(output_manifest)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "schema_version": SCHEMA_VERSION,
        "algorithm": ALGORITHM,
        "pages": len(rows),
        "candidates": candidate_count,
        "pii_classes": dict(sorted(class_counts.items())),
    }
