from __future__ import annotations

import hashlib
import io
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from PIL import Image, UnidentifiedImageError

SCHEMA_VERSION = 1
PILOT = "controlled_pii_reviewer_v0"
BASELINE_ALGORITHM = "marker_layout_baseline_v0"
RENDERER = "grayscale_opaque_mask_v0"
FINDING_CATEGORIES = frozenset({"missed_pii", "incomplete_mask", "over_redaction"})
PAGE_STATUSES = frozenset({"pass", "fail", "needs_review"})
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 64 * 1024 * 1024
MAX_PAGE_PIXELS = 4096 * 4096
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
PREDICTION_KEYS = {
    "schema_version", "algorithm", "image_id", "image", "image_sha256",
    "width", "height", "candidates",
}
DERIVATIVE_KEYS = {
    "schema_version", "renderer", "image_id", "source_image_sha256",
    "prediction_manifest_sha256", "derivative_image", "derivative_sha256",
    "width", "height", "mode", "mask_value", "mask_count", "masked_pixel_count",
}
REVIEW_KEYS = {
    "schema_version", "pilot", "image_id", "source_image_sha256",
    "prediction_manifest_sha256", "derivative_image_sha256", "width", "height",
    "page_status", "findings",
}
FINDING_KEYS = {"finding_id", "category", "geometry"}


class PIIReviewerPilotError(ValueError):
    pass


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _bounded(path: Path, limit: int, label: str) -> bytes:
    try:
        if path.stat().st_size > limit:
            raise PIIReviewerPilotError(f"{label} exceeds byte limit")
        payload = path.read_bytes()
    except OSError as exc:
        raise PIIReviewerPilotError(f"{label} is not readable") from exc
    if len(payload) > limit:
        raise PIIReviewerPilotError(f"{label} exceeds byte limit")
    return payload


def _resolve(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise PIIReviewerPilotError(f"{label} must be a relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PIIReviewerPilotError(f"unsafe {label}: {value}")
    try:
        root = root.resolve(strict=True)
        path = root.joinpath(*relative.parts).resolve(strict=True)
        path.relative_to(root)
    except (OSError, ValueError) as exc:
        raise PIIReviewerPilotError(f"{label} escapes root or does not exist") from exc
    if not path.is_file():
        raise PIIReviewerPilotError(f"{label} does not exist")
    return path


def _jsonl(path: Path, label: str) -> tuple[list[dict[str, Any]], str]:
    raw = _bounded(path, MAX_MANIFEST_BYTES, label)
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PIIReviewerPilotError(f"{label} must be UTF-8") from exc
    if not lines:
        raise PIIReviewerPilotError(f"{label} must be non-empty")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise PIIReviewerPilotError(f"blank line in {label} at {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PIIReviewerPilotError(f"invalid JSON in {label} at {number}") from exc
        if not isinstance(row, dict):
            raise PIIReviewerPilotError(f"{label} row {number} must be an object")
        rows.append(row)
    return rows, _sha(raw)


def _verify_image(path: Path, digest: str, size: tuple[int, int], label: str, mode: str | None = None) -> None:
    payload = _bounded(path, MAX_IMAGE_BYTES, label)
    if _sha(payload) != digest:
        raise PIIReviewerPilotError(f"{label} hash mismatch")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.size != size or image.width * image.height > MAX_PAGE_PIXELS:
                raise PIIReviewerPilotError(f"{label} dimensions mismatch")
            image.load()
            if mode is not None and image.mode != mode:
                raise PIIReviewerPilotError(f"{label} must use mode {mode}")
    except PIIReviewerPilotError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise PIIReviewerPilotError(f"{label} decode failed") from exc


def load_review_pages(prediction_manifest: Path, image_root: Path, renderer_output: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    predictions, prediction_sha = _jsonl(prediction_manifest, "prediction manifest")
    derivatives, _ = _jsonl(renderer_output / "manifest.jsonl", "renderer manifest")
    if len(predictions) != len(derivatives):
        raise PIIReviewerPilotError("prediction/renderer page counts differ")
    pages: list[dict[str, Any]] = []
    seen: set[str] = set()
    for number, (prediction, derivative) in enumerate(zip(predictions, derivatives), 1):
        if set(prediction) != PREDICTION_KEYS or set(derivative) != DERIVATIVE_KEYS:
            raise PIIReviewerPilotError(f"row {number}: invalid manifest fields")
        image_id, width, height = prediction["image_id"], prediction["width"], prediction["height"]
        source_sha, candidates = prediction["image_sha256"], prediction["candidates"]
        if not isinstance(image_id, str) or not ID_RE.fullmatch(image_id) or image_id in seen:
            raise PIIReviewerPilotError(f"row {number}: invalid or duplicate image_id")
        seen.add(image_id)
        if not _integer(width) or not _integer(height) or width <= 0 or height <= 0 or width * height > MAX_PAGE_PIXELS:
            raise PIIReviewerPilotError(f"{image_id}: invalid dimensions")
        if not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha) or not isinstance(candidates, list):
            raise PIIReviewerPilotError(f"{image_id}: invalid source identity")
        if prediction["schema_version"] != SCHEMA_VERSION or prediction["algorithm"] != BASELINE_ALGORITHM:
            raise PIIReviewerPilotError(f"{image_id}: unsupported prediction schema")
        expected = {
            "schema_version": SCHEMA_VERSION, "renderer": RENDERER, "image_id": image_id,
            "source_image_sha256": source_sha, "prediction_manifest_sha256": prediction_sha,
            "width": width, "height": height, "mode": "L", "mask_value": 0,
            "mask_count": len(candidates),
        }
        if any(derivative.get(key) != value for key, value in expected.items()):
            raise PIIReviewerPilotError(f"{image_id}: renderer binding mismatch")
        derivative_sha = derivative["derivative_sha256"]
        if not isinstance(derivative_sha, str) or not SHA_RE.fullmatch(derivative_sha):
            raise PIIReviewerPilotError(f"{image_id}: invalid derivative hash")
        if not _integer(derivative["masked_pixel_count"]) or derivative["masked_pixel_count"] < 0:
            raise PIIReviewerPilotError(f"{image_id}: invalid masked_pixel_count")
        source_path = _resolve(image_root, prediction["image"], "source image")
        derivative_path = _resolve(renderer_output, derivative["derivative_image"], "derivative image")
        _verify_image(source_path, source_sha, (width, height), f"{image_id} source")
        _verify_image(derivative_path, derivative_sha, (width, height), f"{image_id} derivative", "L")
        pages.append({
            "image_id": image_id, "width": width, "height": height,
            "source_path": source_path, "source_image_sha256": source_sha,
            "prediction_manifest_sha256": prediction_sha,
            "derivative_path": derivative_path, "derivative_image_sha256": derivative_sha,
        })
    return pages, {"schema_version": SCHEMA_VERSION, "pilot": PILOT, "pages": len(pages), "prediction_manifest_sha256": prediction_sha}


def _bbox(geometry: Any, width: int, height: int, label: str) -> dict[str, Any]:
    if not isinstance(geometry, dict) or set(geometry) != {"type", "coordinates"}:
        raise PIIReviewerPilotError(f"{label}: invalid geometry")
    coordinates = geometry["coordinates"]
    if geometry["type"] != "bbox" or not isinstance(coordinates, list) or len(coordinates) != 4:
        raise PIIReviewerPilotError(f"{label}: geometry must be bbox")
    if not all(_integer(value) for value in coordinates):
        raise PIIReviewerPilotError(f"{label}: bbox coordinates must be integers")
    x0, y0, x1, y1 = coordinates
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise PIIReviewerPilotError(f"{label}: bbox must have positive in-bounds area")
    return {"type": "bbox", "coordinates": [x0, y0, x1, y1]}


def make_review_row(page: Mapping[str, Any], status: str, findings: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if status not in PAGE_STATUSES:
        raise PIIReviewerPilotError("invalid page_status")
    normalized = []
    for index, finding in enumerate(findings, 1):
        if not isinstance(finding, Mapping) or set(finding) != {"category", "geometry"}:
            raise PIIReviewerPilotError(f"finding {index}: invalid fields")
        category = finding["category"]
        if not isinstance(category, str) or category not in FINDING_CATEGORIES:
            raise PIIReviewerPilotError(f"finding {index}: invalid category")
        normalized.append({
            "finding_id": f"{page['image_id']}-F{index:04d}", "category": category,
            "geometry": _bbox(finding["geometry"], page["width"], page["height"], f"finding {index}"),
        })
    if status == "pass" and normalized:
        raise PIIReviewerPilotError("pass page cannot contain findings")
    if status == "fail" and not normalized:
        raise PIIReviewerPilotError("fail page requires findings")
    return {
        "schema_version": SCHEMA_VERSION, "pilot": PILOT, "image_id": page["image_id"],
        "source_image_sha256": page["source_image_sha256"],
        "prediction_manifest_sha256": page["prediction_manifest_sha256"],
        "derivative_image_sha256": page["derivative_image_sha256"],
        "width": page["width"], "height": page["height"],
        "page_status": status, "findings": normalized,
    }


def validate_review_rows(rows: Sequence[Mapping[str, Any]], pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(rows) != len(pages):
        raise PIIReviewerPilotError("review/page counts differ")
    validated = []
    for number, (row, page) in enumerate(zip(rows, pages), 1):
        if not isinstance(row, Mapping) or set(row) != REVIEW_KEYS:
            raise PIIReviewerPilotError(f"review row {number}: invalid fields")
        findings = row["findings"]
        if not isinstance(findings, list) or any(not isinstance(item, Mapping) or set(item) != FINDING_KEYS for item in findings):
            raise PIIReviewerPilotError(f"review row {number}: invalid findings")
        compact = [{"category": item["category"], "geometry": item["geometry"]} for item in findings]
        rebuilt = make_review_row(page, row["page_status"], compact)
        if rebuilt != dict(row):
            raise PIIReviewerPilotError(f"review row {number}: identity or canonical order mismatch")
        validated.append(rebuilt)
    return validated


def write_review_manifest(output: Path, rows: Sequence[Mapping[str, Any]], pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    validated = validate_review_rows(rows, pages)
    if output.exists():
        raise PIIReviewerPilotError("review output already exists")
    payload = "".join(_canonical(row) + "\n" for row in validated).encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload); handle.flush(); os.fsync(handle.fileno())
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "schema_version": SCHEMA_VERSION, "pilot": PILOT, "manifest_sha256": _sha(payload),
        "pages": len(validated), "findings": sum(len(row["findings"]) for row in validated),
        **{status: sum(row["page_status"] == status for row in validated) for status in sorted(PAGE_STATUSES)},
    }
