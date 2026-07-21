from __future__ import annotations

import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image

SCHEMA_VERSION = 1
PII_CLASSES = frozenset({
    "person_name", "israeli_id", "phone", "email", "property_address", "other_address",
    "signature", "initials", "stamp", "bank_identifier", "cheque_identifier",
    "handwritten_identifier", "other_likely_pii",
})
PAGE_STATUSES = frozenset({"reviewed_with_pii", "reviewed_no_pii", "needs_review"})
REVIEW_STATUSES = frozenset({"readable", "ambiguous", "unreadable"})
REGION_FLAGS = frozenset({"handwritten", "truncated", "inseparable_from_legal_text"})
REASON_CODES = frozenset({"field_marker", "layout_zone", "digit_pattern", "signature_shape", "context", "other"})
TOP_KEYS = frozenset({"schema_version", "image_id", "image", "image_sha256", "width", "height", "page_status", "regions"})
REGION_KEYS = frozenset({"region_id", "pii_class", "geometry", "review_status", "flags", "reason_codes"})
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(ID_RE.fullmatch(value))


def _resolve_image(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("image must be a non-empty relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe image path")
    root = root.resolve()
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError("image path escapes root")
    if not path.is_file():
        raise ValueError("image does not exist")
    return path


def _geometry_error(value: Any, width: int, height: int) -> str | None:
    if not isinstance(value, dict) or set(value) != {"type", "coordinates"}:
        return "geometry must contain exactly type and coordinates"
    kind, coordinates = value["type"], value["coordinates"]
    if not isinstance(kind, str):
        return "geometry type must be a string"
    if kind == "bbox":
        if not isinstance(coordinates, list) or len(coordinates) != 4 or not all(_integer(v) for v in coordinates):
            return "bbox coordinates must be four integers"
        x0, y0, x1, y1 = coordinates
        return None if 0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height else "bbox must have positive in-bounds area"
    if kind != "polygon" or not isinstance(coordinates, list) or len(coordinates) < 3:
        return "geometry must be bbox or a polygon with at least three points"
    points: list[tuple[int, int]] = []
    for point in coordinates:
        if not isinstance(point, list) or len(point) != 2 or not all(_integer(v) for v in point):
            return "polygon points must be integer pairs"
        x, y = point
        if not (0 <= x <= width and 0 <= y <= height):
            return "polygon point is outside image bounds"
        points.append((x, y))
    area2 = abs(sum(a * d - c * b for (a, b), (c, d) in zip(points, points[1:] + points[:1])))
    return None if area2 else "polygon must have positive area"


def _enum_list_error(value: Any, allowed: frozenset[str], field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return f"{field} must be an array of strings"
    if len(value) != len(set(value)):
        return f"{field} contains duplicates"
    unknown = sorted(set(value) - allowed)
    return f"unknown {field}: {unknown}" if unknown else None


def _report(
    errors: list[str],
    pages: Counter[str],
    classes: Counter[str],
    records: int,
    regions_total: int,
    manifest_sha256: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_sha256": manifest_sha256,
        "valid": not errors,
        "evaluation_ready": not errors and not pages.get("needs_review", 0),
        "records": records,
        "regions": regions_total,
        "page_statuses": dict(sorted(pages.items())),
        "pii_classes": dict(sorted(classes.items())),
        "errors": errors,
    }


def load_annotation_manifest(
    manifest_path: Path,
    image_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    errors: list[str] = []
    image_ids: set[str] = set()
    region_ids: set[str] = set()
    pages: Counter[str] = Counter()
    classes: Counter[str] = Counter()
    parsed_rows: list[dict[str, Any]] = []
    records = regions_total = 0

    manifest_sha256: str | None = None
    try:
        raw = manifest_path.read_bytes()
        manifest_sha256 = hashlib.sha256(raw).hexdigest()
        lines = raw.decode("utf-8").splitlines()
    except OSError as exc:
        lines, errors = [], [str(exc)]
    except UnicodeDecodeError as exc:
        lines, errors = [], [f"manifest is not valid UTF-8: {exc.reason}"]

    for number, line in enumerate(lines, 1):
        if not line.strip():
            errors.append(f"line {number}: blank lines are forbidden")
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {number}: invalid JSON: {exc.msg}")
            continue
        if not isinstance(row, dict):
            errors.append(f"line {number}: row must be an object")
            continue
        records += 1
        parsed_rows.append(row)
        label = str(row.get("image_id") or f"line_{number}")
        missing, unknown = sorted(TOP_KEYS - set(row)), sorted(set(row) - TOP_KEYS)
        if missing:
            errors.append(f"{label}: missing fields: {', '.join(missing)}")
        if unknown:
            errors.append(f"{label}: unknown fields are forbidden: {', '.join(unknown)}")
        if missing:
            continue

        if not _integer(row["schema_version"]) or row["schema_version"] != SCHEMA_VERSION:
            errors.append(f"{label}: schema_version must be integer {SCHEMA_VERSION}")
        image_id = row["image_id"]
        if not _identifier(image_id):
            errors.append(f"{label}: invalid image_id")
        elif image_id in image_ids:
            errors.append(f"{label}: duplicate image_id")
        else:
            image_ids.add(image_id)
        width, height = row["width"], row["height"]
        if not _integer(width) or not _integer(height) or width <= 0 or height <= 0:
            errors.append(f"{label}: width and height must be positive integers")
            width = height = 0
        image_sha = row["image_sha256"]
        if not isinstance(image_sha, str) or not SHA_RE.fullmatch(image_sha):
            errors.append(f"{label}: image_sha256 must be lowercase SHA-256")
        try:
            path = _resolve_image(image_root, row["image"])
            image_bytes = path.read_bytes()
            if isinstance(image_sha, str) and SHA_RE.fullmatch(image_sha):
                if hashlib.sha256(image_bytes).hexdigest() != image_sha:
                    errors.append(f"{label}: image hash mismatch")
            with Image.open(io.BytesIO(image_bytes)) as image:
                actual_size = image.size
                image.verify()
            if width and height and actual_size != (width, height):
                errors.append(f"{label}: image dimensions do not match manifest")
        except (OSError, ValueError) as exc:
            errors.append(f"{label}: {exc}")

        status, regions = row["page_status"], row["regions"]
        if not isinstance(status, str) or status not in PAGE_STATUSES:
            errors.append(f"{label}: unknown page_status: {status!r}")
        else:
            pages[status] += 1
        if not isinstance(regions, list):
            errors.append(f"{label}: regions must be an array")
            continue
        if status == "reviewed_with_pii" and not regions:
            errors.append(f"{label}: reviewed_with_pii requires regions")
        if status == "reviewed_no_pii" and regions:
            errors.append(f"{label}: reviewed_no_pii requires no regions")

        for index, region in enumerate(regions, 1):
            region_label = f"{label}/region_{index}"
            if not isinstance(region, dict):
                errors.append(f"{region_label}: region must be an object")
                continue
            required = {"region_id", "pii_class", "geometry", "review_status"}
            missing = sorted(required - set(region))
            unknown = sorted(set(region) - REGION_KEYS)
            if missing:
                errors.append(f"{region_label}: missing fields: {', '.join(missing)}")
            if unknown:
                errors.append(f"{region_label}: unknown fields are forbidden: {', '.join(unknown)}")
            if missing:
                continue
            region_id = region["region_id"]
            if not _identifier(region_id):
                errors.append(f"{region_label}: invalid region_id")
            elif region_id in region_ids:
                errors.append(f"{region_label}: duplicate region_id")
            else:
                region_ids.add(region_id)
            pii_class = region["pii_class"]
            if not isinstance(pii_class, str) or pii_class not in PII_CLASSES:
                errors.append(f"{region_label}: unknown pii_class: {pii_class!r}")
            else:
                classes[pii_class] += 1
            review_status = region["review_status"]
            if not isinstance(review_status, str) or review_status not in REVIEW_STATUSES:
                errors.append(f"{region_label}: unknown review_status: {review_status!r}")
            if width and height and (message := _geometry_error(region["geometry"], width, height)):
                errors.append(f"{region_label}: {message}")
            for field, allowed in (("flags", REGION_FLAGS), ("reason_codes", REASON_CODES)):
                if message := _enum_list_error(region.get(field), allowed, field):
                    errors.append(f"{region_label}: {message}")
            regions_total += 1

    if records == 0:
        errors.append("manifest must contain at least one page")
    return _report(errors, pages, classes, records, regions_total, manifest_sha256), parsed_rows


def validate_annotation_manifest(manifest_path: Path, image_root: Path) -> dict[str, Any]:
    report, _ = load_annotation_manifest(manifest_path, image_root)
    return report
