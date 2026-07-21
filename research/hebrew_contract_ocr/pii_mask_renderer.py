from __future__ import annotations

import hashlib
import io
import json
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, UnidentifiedImageError

from .line_segmenter import MAX_PAGE_PIXELS
from .pii_annotations import PII_CLASSES
from .pii_baseline import ALGORITHM as BASELINE_ALGORITHM, REASON_CODES

SCHEMA_VERSION = 1
RENDERER = "grayscale_opaque_mask_v0"
MASK_VALUE = 0
TOP_KEYS = {
    "schema_version", "algorithm", "image_id", "image", "image_sha256",
    "width", "height", "candidates",
}
CANDIDATE_KEYS = {
    "candidate_id", "proposed_class", "geometry", "review_status", "reason_codes",
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class PIIMaskRendererError(ValueError):
    pass


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _resolve(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise PIIMaskRendererError("image must be a non-empty relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PIIMaskRendererError(f"unsafe image path: {value}")
    try:
        path = root.resolve().joinpath(*relative.parts).resolve(strict=True)
        path.relative_to(root.resolve())
    except (OSError, ValueError) as exc:
        raise PIIMaskRendererError(f"image escapes root or does not exist: {value}") from exc
    if not path.is_file():
        raise PIIMaskRendererError(f"image does not exist: {value}")
    return path


def _read_manifest(path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise PIIMaskRendererError("prediction manifest must be readable UTF-8") from exc
    if not lines:
        raise PIIMaskRendererError("prediction manifest must contain at least one page")
    rows = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise PIIMaskRendererError(f"blank line in prediction manifest at line {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PIIMaskRendererError(f"invalid JSON at line {number}") from exc
        if not isinstance(row, dict):
            raise PIIMaskRendererError(f"prediction row {number} must be an object")
        rows.append(row)
    return rows, _sha(raw)


def _bbox(candidate: dict[str, Any], width: int, height: int, label: str) -> tuple[int, int, int, int]:
    geometry = candidate.get("geometry")
    if not isinstance(geometry, dict) or set(geometry) != {"type", "coordinates"}:
        raise PIIMaskRendererError(f"{label}: invalid geometry fields")
    coordinates = geometry["coordinates"]
    if geometry["type"] != "bbox" or not isinstance(coordinates, list) or len(coordinates) != 4:
        raise PIIMaskRendererError(f"{label}: renderer v0 requires bbox geometry")
    if not all(_integer(value) for value in coordinates):
        raise PIIMaskRendererError(f"{label}: bbox coordinates must be integers")
    x0, y0, x1, y1 = coordinates
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise PIIMaskRendererError(f"{label}: bbox must have positive in-bounds area")
    return x0, y0, x1, y1


def _prepare(rows: list[dict[str, Any]], image_root: Path) -> list[dict[str, Any]]:
    prepared, image_ids, candidate_ids = [], set(), set()
    for number, row in enumerate(rows, 1):
        missing, unknown = sorted(TOP_KEYS - set(row)), sorted(set(row) - TOP_KEYS)
        if missing or unknown:
            raise PIIMaskRendererError(f"row {number}: missing={missing}, unknown={unknown}")
        if not _integer(row["schema_version"]) or row["schema_version"] != SCHEMA_VERSION:
            raise PIIMaskRendererError(f"row {number}: invalid schema_version")
        if row["algorithm"] != BASELINE_ALGORITHM:
            raise PIIMaskRendererError(f"row {number}: unsupported baseline algorithm")
        image_id = row["image_id"]
        if not isinstance(image_id, str) or not ID_RE.fullmatch(image_id) or image_id in image_ids:
            raise PIIMaskRendererError(f"row {number}: invalid or duplicate image_id")
        image_ids.add(image_id)
        width, height = row["width"], row["height"]
        if not _integer(width) or not _integer(height) or width <= 0 or height <= 0:
            raise PIIMaskRendererError(f"{image_id}: invalid dimensions")
        if width * height > MAX_PAGE_PIXELS:
            raise PIIMaskRendererError(f"{image_id}: image exceeds renderer pixel limit")
        expected_sha = row["image_sha256"]
        if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
            raise PIIMaskRendererError(f"{image_id}: invalid image_sha256")
        path = _resolve(image_root, row["image"])
        source_bytes = path.read_bytes()
        if _sha(source_bytes) != expected_sha:
            raise PIIMaskRendererError(f"{image_id}: image hash mismatch")
        try:
            with Image.open(io.BytesIO(source_bytes)) as source:
                if source.size != (width, height):
                    raise PIIMaskRendererError(f"{image_id}: image dimensions do not match manifest")
                source.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise PIIMaskRendererError(f"{image_id}: source image decode failed") from exc
        candidates = row["candidates"]
        if not isinstance(candidates, list):
            raise PIIMaskRendererError(f"{image_id}: candidates must be an array")
        boxes = []
        for index, candidate in enumerate(candidates, 1):
            label = f"{image_id}/candidate_{index}"
            if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_KEYS:
                raise PIIMaskRendererError(f"{label}: invalid candidate fields")
            candidate_id = candidate["candidate_id"]
            if not isinstance(candidate_id, str) or not ID_RE.fullmatch(candidate_id) or candidate_id in candidate_ids:
                raise PIIMaskRendererError(f"{label}: invalid or duplicate candidate_id")
            candidate_ids.add(candidate_id)
            reasons = candidate["reason_codes"]
            if candidate["proposed_class"] not in PII_CLASSES or candidate["review_status"] != "needs_review":
                raise PIIMaskRendererError(f"{label}: invalid class or review_status")
            if not isinstance(reasons, list) or len(reasons) != len(set(reasons)) or any(r not in REASON_CODES for r in reasons):
                raise PIIMaskRendererError(f"{label}: invalid reason_codes")
            boxes.append(_bbox(candidate, width, height, label))
        prepared.append({
            "image_id": image_id, "path": path, "source_bytes": source_bytes,
            "source_sha256": expected_sha, "width": width, "height": height,
            "boxes": tuple(sorted(boxes)),
        })
    return prepared


def _save_png(source_bytes: bytes, boxes: tuple[tuple[int, int, int, int], ...], path: Path) -> tuple[str, int]:
    with Image.open(io.BytesIO(source_bytes)) as source:
        source.load()
        grayscale = source.convert("L")
    flattened = Image.frombytes("L", grayscale.size, grayscale.tobytes())
    coverage = Image.new("1", flattened.size, 0)
    for box in boxes:
        coverage.paste(1, box)
    flattened.paste(MASK_VALUE, mask=coverage)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        flattened.save(temporary, format="PNG", optimize=False, compress_level=9)
        saved = temporary.read_bytes()
        with Image.open(io.BytesIO(saved)) as decoded:
            decoded.load()
            if decoded.mode != "L" or decoded.size != flattened.size or decoded.info or decoded.getexif():
                raise PIIMaskRendererError("saved derivative is not clean flattened grayscale")
            if any(decoded.crop(box).getextrema() != (MASK_VALUE, MASK_VALUE) for box in boxes):
                raise PIIMaskRendererError("saved derivative does not fully cover every bbox")
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return _sha(saved), coverage.histogram()[1]


def render_masked_derivatives(prediction_manifest: Path, image_root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise PIIMaskRendererError("output directory must be absent or empty")
    rows, prediction_sha = _read_manifest(prediction_manifest)
    prepared = _prepare(rows, image_root)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent) as temp:
        staging, manifest_rows = Path(temp), []
        (staging / "images").mkdir()
        for page in prepared:
            relative = Path("images") / f"{page['image_id']}.png"
            derivative_sha, masked_pixels = _save_png(page["source_bytes"], page["boxes"], staging / relative)
            if _sha(page["path"].read_bytes()) != page["source_sha256"]:
                raise PIIMaskRendererError(f"{page['image_id']}: source changed during rendering")
            manifest_rows.append({
                "schema_version": SCHEMA_VERSION, "renderer": RENDERER,
                "image_id": page["image_id"], "source_image_sha256": page["source_sha256"],
                "prediction_manifest_sha256": prediction_sha,
                "derivative_image": relative.as_posix(), "derivative_sha256": derivative_sha,
                "width": page["width"], "height": page["height"], "mode": "L",
                "mask_value": MASK_VALUE, "mask_count": len(page["boxes"]),
                "masked_pixel_count": masked_pixels,
            })
        canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        (staging / "manifest.jsonl").write_text("".join(canonical(row) + "\n" for row in manifest_rows), encoding="utf-8")
        summary = {
            "schema_version": SCHEMA_VERSION, "renderer": RENDERER,
            "prediction_manifest_sha256": prediction_sha, "pages": len(manifest_rows),
            "masks": sum(row["mask_count"] for row in manifest_rows),
            "masked_pixels": sum(row["masked_pixel_count"] for row in manifest_rows),
        }
        (staging / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if output_dir.exists():
            output_dir.rmdir()
        staging.replace(output_dir)
    return summary
