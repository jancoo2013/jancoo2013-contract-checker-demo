from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from PIL import Image, UnidentifiedImageError

from .line_segmenter import MAX_PAGE_PIXELS
from .pii_annotations import PII_CLASSES
from .pii_baseline import ALGORITHM as BASELINE_ALGORITHM, REASON_CODES

SCHEMA_VERSION = 1
RENDERER = "grayscale_opaque_mask_v0"
MASK_VALUE = 0
MAX_PREDICTION_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_SOURCE_IMAGE_BYTES = 64 * 1024 * 1024
TOP_KEYS = {"schema_version", "algorithm", "image_id", "image", "image_sha256", "width", "height", "candidates"}
CANDIDATE_KEYS = {"candidate_id", "proposed_class", "geometry", "review_status", "reason_codes"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


class PIIMaskRendererError(ValueError):
    pass


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _bounded_bytes(path: Path, limit: int, label: str) -> bytes:
    try:
        if path.stat().st_size > limit:
            raise PIIMaskRendererError(f"{label} exceeds byte limit")
        data = path.read_bytes()
    except OSError as exc:
        raise PIIMaskRendererError(f"{label} is not readable") from exc
    if len(data) > limit:
        raise PIIMaskRendererError(f"{label} exceeds byte limit")
    return data


def _resolve(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise PIIMaskRendererError("image must be a non-empty relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PIIMaskRendererError(f"unsafe image path: {value}")
    try:
        root = root.resolve(strict=True)
        path = root.joinpath(*relative.parts).resolve(strict=True)
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise PIIMaskRendererError(f"image escapes root or does not exist: {value}") from exc
    if not path.is_file():
        raise PIIMaskRendererError(f"image does not exist: {value}")
    return path


def _read_manifest(path: Path) -> tuple[list[dict[str, Any]], str]:
    raw = _bounded_bytes(path, MAX_PREDICTION_MANIFEST_BYTES, "prediction manifest")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PIIMaskRendererError("prediction manifest must be valid UTF-8") from exc
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


def _validated_pages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pages, image_ids, candidate_ids = [], set(), set()
    for number, row in enumerate(rows, 1):
        missing, unknown = sorted(TOP_KEYS - set(row)), sorted(set(row) - TOP_KEYS)
        if missing or unknown:
            raise PIIMaskRendererError(f"row {number}: missing={missing}, unknown={unknown}")
        if not _integer(row["schema_version"]) or row["schema_version"] != SCHEMA_VERSION:
            raise PIIMaskRendererError(f"row {number}: invalid schema_version")
        if not isinstance(row["algorithm"], str) or row["algorithm"] != BASELINE_ALGORITHM:
            raise PIIMaskRendererError(f"row {number}: unsupported baseline algorithm")
        image_id, width, height = row["image_id"], row["width"], row["height"]
        if not isinstance(image_id, str) or not ID_RE.fullmatch(image_id) or image_id in image_ids:
            raise PIIMaskRendererError(f"row {number}: invalid or duplicate image_id")
        image_ids.add(image_id)
        if not _integer(width) or not _integer(height) or width <= 0 or height <= 0 or width * height > MAX_PAGE_PIXELS:
            raise PIIMaskRendererError(f"{image_id}: invalid or excessive dimensions")
        expected_sha = row["image_sha256"]
        if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
            raise PIIMaskRendererError(f"{image_id}: invalid image_sha256")
        if not isinstance(row["image"], str) or not row["image"]:
            raise PIIMaskRendererError(f"{image_id}: invalid image path")
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
            proposed_class, review_status, reasons = candidate["proposed_class"], candidate["review_status"], candidate["reason_codes"]
            if not isinstance(proposed_class, str) or proposed_class not in PII_CLASSES:
                raise PIIMaskRendererError(f"{label}: invalid proposed_class")
            if not isinstance(review_status, str) or review_status != "needs_review":
                raise PIIMaskRendererError(f"{label}: invalid review_status")
            if not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons):
                raise PIIMaskRendererError(f"{label}: reason_codes must be an array of strings")
            if len(reasons) != len(set(reasons)) or any(reason not in REASON_CODES for reason in reasons):
                raise PIIMaskRendererError(f"{label}: invalid reason_codes")
            boxes.append(_bbox(candidate, width, height, label))
        pages.append({"image_id": image_id, "image": row["image"], "source_sha256": expected_sha,
                      "width": width, "height": height, "boxes": tuple(sorted(boxes))})
    return pages


def _render_png(source_bytes: bytes, boxes: tuple[tuple[int, int, int, int], ...], size: tuple[int, int]) -> tuple[bytes, int]:
    try:
        with Image.open(io.BytesIO(source_bytes)) as source:
            if source.size != size or source.width * source.height > MAX_PAGE_PIXELS:
                raise PIIMaskRendererError("source image dimensions do not match manifest")
            source.load(); grayscale = source.convert("L")
    except PIIMaskRendererError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PIIMaskRendererError("source image decode failed") from exc
    flattened = Image.frombytes("L", grayscale.size, grayscale.tobytes())
    coverage = Image.new("1", flattened.size, 0)
    for box in boxes:
        coverage.paste(1, box)
    flattened.paste(MASK_VALUE, mask=coverage)
    buffer = io.BytesIO(); flattened.save(buffer, format="PNG", optimize=False, compress_level=9)
    return buffer.getvalue(), coverage.histogram()[1]


def _verify(payload: bytes, expected_sha: str, size: tuple[int, int], boxes: Iterable[tuple[int, int, int, int]]) -> None:
    if _sha(payload) != expected_sha:
        raise PIIMaskRendererError("derivative hash mismatch")
    try:
        with Image.open(io.BytesIO(payload)) as decoded:
            decoded.load()
            if decoded.mode != "L" or decoded.size != size or decoded.info or decoded.getexif():
                raise PIIMaskRendererError("derivative is not clean flattened grayscale")
            if any(decoded.crop(box).getextrema() != (MASK_VALUE, MASK_VALUE) for box in boxes):
                raise PIIMaskRendererError("derivative does not fully cover every bbox")
    except PIIMaskRendererError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PIIMaskRendererError("derivative decode failed") from exc


def _write_exact(path: Path, payload: bytes) -> str:
    try:
        with path.open("xb") as handle:
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        published = path.read_bytes()
    except OSError as exc:
        path.unlink(missing_ok=True)
        raise PIIMaskRendererError("derivative publication failed") from exc
    if published != payload:
        path.unlink(missing_ok=True)
        raise PIIMaskRendererError("derivative changed during publication")
    return _sha(payload)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render_masked_derivatives(prediction_manifest: Path, image_root: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise PIIMaskRendererError("output directory must be absent or empty")
    rows, prediction_sha = _read_manifest(prediction_manifest)
    pages = _validated_pages(rows)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent))
    try:
        (staging / "images").mkdir(); manifest_rows, boxes_by_id = [], {}
        for page in pages:
            source_path = _resolve(image_root, page["image"])
            source_bytes = _bounded_bytes(source_path, MAX_SOURCE_IMAGE_BYTES, f"{page['image_id']} source image")
            if _sha(source_bytes) != page["source_sha256"]:
                raise PIIMaskRendererError(f"{page['image_id']}: image hash mismatch")
            payload, masked_pixels = _render_png(source_bytes, page["boxes"], (page["width"], page["height"]))
            relative = Path("images") / f"{page['image_id']}.png"
            derivative_sha = _write_exact(staging / relative, payload)
            _verify(payload, derivative_sha, (page["width"], page["height"]), page["boxes"])
            if _sha(_bounded_bytes(source_path, MAX_SOURCE_IMAGE_BYTES, f"{page['image_id']} source image")) != page["source_sha256"]:
                raise PIIMaskRendererError(f"{page['image_id']}: source changed during rendering")
            boxes_by_id[page["image_id"]] = page["boxes"]
            manifest_rows.append({"schema_version": SCHEMA_VERSION, "renderer": RENDERER,
                "image_id": page["image_id"], "source_image_sha256": page["source_sha256"],
                "prediction_manifest_sha256": prediction_sha, "derivative_image": relative.as_posix(),
                "derivative_sha256": derivative_sha, "width": page["width"], "height": page["height"],
                "mode": "L", "mask_value": MASK_VALUE, "mask_count": len(page["boxes"]),
                "masked_pixel_count": masked_pixels})
            del source_bytes, payload
        summary = {"schema_version": SCHEMA_VERSION, "renderer": RENDERER,
            "prediction_manifest_sha256": prediction_sha, "pages": len(manifest_rows),
            "masks": sum(row["mask_count"] for row in manifest_rows),
            "masked_pixels": sum(row["masked_pixel_count"] for row in manifest_rows)}
        (staging / "manifest.jsonl").write_text("".join(_canonical(row) + "\n" for row in manifest_rows), encoding="utf-8")
        (staging / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        for row in manifest_rows:
            payload = _bounded_bytes(staging / row["derivative_image"], MAX_SOURCE_IMAGE_BYTES, f"{row['image_id']} derivative")
            _verify(payload, row["derivative_sha256"], (row["width"], row["height"]), boxes_by_id[row["image_id"]])
        if output_dir.exists():
            output_dir.rmdir()
        staging.replace(output_dir)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
