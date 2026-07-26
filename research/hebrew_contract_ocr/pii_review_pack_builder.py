from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from PIL import Image, UnidentifiedImageError

from .line_segmenter import MAX_PAGE_PIXELS, RESOLUTION_STATUSES, segment_directory
from .pii_annotations import validate_annotation_manifest
from .pii_baseline import generate_baseline_predictions
from .pii_mask_renderer import render_masked_derivatives
from .pii_reviewer_pilot import load_review_pages

SCHEMA_VERSION = 1
BUILDER = "controlled_pii_review_pack_builder_v0"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 64 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
LINE_KEYS = frozenset({
    "schema_version", "page_id", "line_id", "order", "bbox", "bbox_convention",
    "segmentation_status", "status", "reasons", "upstream_resolution_status",
    "foreground_pixels", "line_image", "line_sha256", "source_master_sha256",
})
LINE_STATUSES = frozenset({"accepted", "review", "reject"})


class PIIReviewPackBuilderError(ValueError):
    pass


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_jsonl(rows: Sequence[Mapping[str, Any]]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def _bounded(path: Path, limit: int, label: str) -> bytes:
    try:
        if path.stat().st_size > limit:
            raise PIIReviewPackBuilderError(f"{label} exceeds byte limit")
        payload = path.read_bytes()
    except OSError as exc:
        raise PIIReviewPackBuilderError(f"{label} is not readable") from exc
    if len(payload) > limit:
        raise PIIReviewPackBuilderError(f"{label} exceeds byte limit")
    return payload


def _jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    payload = _bounded(path, MAX_MANIFEST_BYTES, label)
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PIIReviewPackBuilderError(f"{label} must be UTF-8") from exc
    if not lines:
        raise PIIReviewPackBuilderError(f"{label} must be non-empty")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise PIIReviewPackBuilderError(f"blank line in {label} at {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PIIReviewPackBuilderError(f"invalid JSON in {label} at {number}") from exc
        if not isinstance(row, dict):
            raise PIIReviewPackBuilderError(f"{label} row {number} must be an object")
        rows.append(row)
    return rows


def _resolve(root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise PIIReviewPackBuilderError(f"{label} must be a relative POSIX path")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or relative.as_posix() != value
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise PIIReviewPackBuilderError(f"unsafe {label}: {value}")
    try:
        resolved_root = root.resolve(strict=True)
        path = resolved_root.joinpath(*relative.parts).resolve(strict=True)
        path.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise PIIReviewPackBuilderError(f"{label} escapes root or does not exist") from exc
    if not path.is_file():
        raise PIIReviewPackBuilderError(f"{label} does not exist")
    return path


def _write_exact(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.read_bytes() != payload:
            raise PIIReviewPackBuilderError(f"published file changed: {path.name}")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _copy_sources(
    normalized_dir: Path,
    segmentation_dir: Path,
    staging_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    page_rows = _jsonl(segmentation_dir / "pages.jsonl", "segmentation pages")
    annotations: list[dict[str, Any]] = []
    identities: dict[str, dict[str, Any]] = {}
    for number, row in enumerate(page_rows, 1):
        required = {
            "schema_version", "page_id", "width", "height",
            "source_master", "source_master_sha256",
        }
        if not required.issubset(row):
            raise PIIReviewPackBuilderError(f"segmentation page {number}: missing identity fields")
        page_id, width, height = row["page_id"], row["width"], row["height"]
        digest = row["source_master_sha256"]
        if (
            row["schema_version"] != SCHEMA_VERSION
            or not isinstance(page_id, str)
            or not ID_RE.fullmatch(page_id)
            or page_id in identities
            or isinstance(width, bool)
            or not isinstance(width, int)
            or isinstance(height, bool)
            or not isinstance(height, int)
            or width <= 0
            or height <= 0
            or width * height > MAX_PAGE_PIXELS
            or not isinstance(digest, str)
            or not SHA_RE.fullmatch(digest)
        ):
            raise PIIReviewPackBuilderError(f"segmentation page {number}: invalid identity")
        source_path = _resolve(normalized_dir, row["source_master"], f"{page_id} source master")
        payload = _bounded(source_path, MAX_IMAGE_BYTES, f"{page_id} source master")
        if _sha(payload) != digest:
            raise PIIReviewPackBuilderError(f"{page_id}: source master hash mismatch")
        try:
            with Image.open(io.BytesIO(payload)) as image:
                image.load()
                if image.format != "PNG" or image.mode != "L" or image.size != (width, height):
                    raise PIIReviewPackBuilderError(
                        f"{page_id}: source master must be matching grayscale PNG"
                    )
        except PIIReviewPackBuilderError:
            raise
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise PIIReviewPackBuilderError(f"{page_id}: source master decode failed") from exc

        relative = Path("sources") / f"{page_id}.png"
        _write_exact(staging_dir / relative, payload)
        annotation = {
            "schema_version": SCHEMA_VERSION,
            "image_id": page_id,
            "image": relative.as_posix(),
            "image_sha256": digest,
            "width": width,
            "height": height,
            "page_status": "needs_review",
            "regions": [],
        }
        annotations.append(annotation)
        identities[page_id] = {
            "image_sha256": digest,
            "width": width,
            "height": height,
        }
    return annotations, identities


def _safe_relative_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value:
        raise PIIReviewPackBuilderError(f"{label} must be a relative POSIX path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PIIReviewPackBuilderError(f"unsafe {label}")
    return value


def _validate_line_manifest(
    manifest_path: Path,
    identities: Mapping[str, Mapping[str, Any]],
) -> int:
    rows = _jsonl(manifest_path, "line segmentation manifest")
    line_ids: set[str] = set()
    orders: dict[str, list[int]] = {page_id: [] for page_id in identities}
    for number, row in enumerate(rows, 1):
        if set(row) != LINE_KEYS:
            raise PIIReviewPackBuilderError(f"line {number}: invalid fields")
        page_id, line_id, order = row["page_id"], row["line_id"], row["order"]
        if (
            row["schema_version"] != SCHEMA_VERSION
            or not isinstance(page_id, str)
            or page_id not in identities
            or not isinstance(line_id, str)
            or not ID_RE.fullmatch(line_id)
            or line_id in line_ids
            or isinstance(order, bool)
            or not isinstance(order, int)
            or order <= 0
        ):
            raise PIIReviewPackBuilderError(f"line {number}: invalid identity")
        line_ids.add(line_id)
        orders[page_id].append(order)
        identity = identities[page_id]
        width, height = identity["width"], identity["height"]
        bbox = row["bbox"]
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or any(isinstance(value, bool) or not isinstance(value, int) for value in bbox)
        ):
            raise PIIReviewPackBuilderError(f"line {number}: invalid bbox")
        x0, y0, x1, y1 = bbox
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise PIIReviewPackBuilderError(f"line {number}: bbox out of bounds")
        foreground = row["foreground_pixels"]
        if (
            row["bbox_convention"] != "xyxy_half_open"
            or row["segmentation_status"] not in LINE_STATUSES
            or row["status"] not in LINE_STATUSES
            or row["upstream_resolution_status"] not in RESOLUTION_STATUSES
            or row["source_master_sha256"] != identity["image_sha256"]
            or isinstance(foreground, bool)
            or not isinstance(foreground, int)
            or not 0 <= foreground <= (x1 - x0) * (y1 - y0)
            or not isinstance(row["reasons"], list)
            or any(not isinstance(reason, str) for reason in row["reasons"])
            or len(row["reasons"]) != len(set(row["reasons"]))
            or not isinstance(row["line_sha256"], str)
            or not SHA_RE.fullmatch(row["line_sha256"])
        ):
            raise PIIReviewPackBuilderError(f"line {number}: invalid binding")
        _safe_relative_string(row["line_image"], f"line {number} image")

    for page_id, page_orders in orders.items():
        if sorted(page_orders) != list(range(1, len(page_orders) + 1)):
            raise PIIReviewPackBuilderError(f"{page_id}: line order is not contiguous")
        if not page_orders:
            raise PIIReviewPackBuilderError(f"{page_id}: no neutral review lines")
    return len(rows)


def build_review_pack(normalized_dir: Path, output_dir: Path) -> dict[str, Any]:
    try:
        normalized = normalized_dir.expanduser().resolve(strict=True)
    except OSError as exc:
        raise PIIReviewPackBuilderError("normalized directory does not exist") from exc
    if not normalized.is_dir():
        raise PIIReviewPackBuilderError("normalized input must be a directory")

    output = output_dir.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise PIIReviewPackBuilderError("output pack already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    published = False
    try:
        work = staging / ".work"
        work.mkdir()
        segmentation_dir = work / "line_segmentation"
        segmentation_summary = segment_directory(normalized, segmentation_dir)

        annotations, identities = _copy_sources(normalized, segmentation_dir, staging)
        annotation_manifest = work / "annotation-manifest.jsonl"
        _write_exact(annotation_manifest, _canonical_jsonl(annotations))
        annotation_report = validate_annotation_manifest(annotation_manifest, staging)
        if not annotation_report["valid"]:
            raise PIIReviewPackBuilderError(
                "generated identity manifest is invalid: " + "; ".join(annotation_report["errors"])
            )

        predictions = staging / "predictions.jsonl"
        baseline_summary = generate_baseline_predictions(annotation_manifest, staging, predictions)
        renderer_dir = staging / "renderer"
        renderer_summary = render_masked_derivatives(predictions, staging, renderer_dir)

        final_lines_dir = staging / "line_segmentation"
        final_lines_dir.mkdir()
        line_payload = _bounded(
            segmentation_dir / "manifest.jsonl",
            MAX_MANIFEST_BYTES,
            "line segmentation manifest",
        )
        _write_exact(final_lines_dir / "manifest.jsonl", line_payload)

        pages, pilot_summary = load_review_pages(predictions, staging, renderer_dir)
        line_count = _validate_line_manifest(final_lines_dir / "manifest.jsonl", identities)
        expected_ids = list(identities)
        if (
            [page["image_id"] for page in pages] != expected_ids
            or segmentation_summary["pages"] != len(expected_ids)
            or baseline_summary["pages"] != len(expected_ids)
            or renderer_summary["pages"] != len(expected_ids)
            or pilot_summary["pages"] != len(expected_ids)
        ):
            raise PIIReviewPackBuilderError("generated pack page identities disagree")

        shutil.rmtree(work)
        if output.exists() or output.is_symlink():
            raise PIIReviewPackBuilderError("output pack appeared during build")
        os.rename(staging, output)
        published = True
        return {
            "schema_version": SCHEMA_VERSION,
            "builder": BUILDER,
            "pages": len(expected_ids),
            "lines": line_count,
            "candidates": baseline_summary["candidates"],
            "prediction_manifest_sha256": pilot_summary["prediction_manifest_sha256"],
            "output_dir": str(output),
        }
    except PIIReviewPackBuilderError:
        raise
    except Exception as exc:
        raise PIIReviewPackBuilderError(str(exc)) from exc
    finally:
        if not published:
            shutil.rmtree(staging, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build one validated local Android PII review pack from normalized pages."
    )
    parser.add_argument("--normalized-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = build_review_pack(args.normalized_dir, args.output_dir)
    except PIIReviewPackBuilderError as exc:
        print(f"PACK FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"PACK READY: {summary['pages']} pages, "
        f"{summary['candidates']} candidates, {summary['output_dir']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
