from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tempfile
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from PIL import Image, UnidentifiedImageError


SCHEMA_VERSION = 1
SET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,79}$")
PAGE_ID_RE = re.compile(r"^P[0-9]{4,}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STATUSES = {"accepted", "review", "reject"}


class CandidateFreezeError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_jsonl(rows: Sequence[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def _read_manifest(path: Path) -> tuple[list[dict[str, Any]], str]:
    try:
        snapshot = path.read_bytes()
        text = snapshot.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CandidateFreezeError(f"could not read UTF-8 manifest: {path}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            row = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise CandidateFreezeError(f"invalid JSON on manifest line {line_number}") from exc
        if not isinstance(row, dict):
            raise CandidateFreezeError(f"manifest line {line_number} must be an object")
        rows.append(row)
    if not rows:
        raise CandidateFreezeError("segmentation manifest is empty")
    return rows, _sha256(snapshot)


def _safe_source_path(root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CandidateFreezeError("line_image must be a safe relative POSIX path")
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise CandidateFreezeError("line_image must be a safe relative POSIX path")
    try:
        root_resolved = root.resolve(strict=True)
        path = root.joinpath(*relative.parts).resolve(strict=True)
        path.relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise CandidateFreezeError("line_image resolves outside the input directory") from exc
    if not path.is_file():
        raise CandidateFreezeError(f"line image does not exist: {value}")
    return path


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CandidateFreezeError(f"{field} must be a positive integer")
    return value


def _validate_row(row: Mapping[str, Any], row_number: int) -> None:
    schema_version = row.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != SCHEMA_VERSION:
        raise CandidateFreezeError(f"invalid schema_version on row {row_number}")
    page_id = row.get("page_id")
    if not isinstance(page_id, str) or PAGE_ID_RE.fullmatch(page_id) is None:
        raise CandidateFreezeError(f"invalid page_id on row {row_number}")
    order = _positive_int(row.get("order"), "order")
    if row.get("line_id") != f"{page_id}-L{order:04d}":
        raise CandidateFreezeError(f"line_id/order mismatch on row {row_number}")
    for field in ("status", "segmentation_status"):
        if row.get(field) not in STATUSES:
            raise CandidateFreezeError(f"invalid {field} on row {row_number}")
    reasons = row.get("reasons")
    if not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons):
        raise CandidateFreezeError(f"invalid reasons on row {row_number}")


def _accepted_image(
    input_dir: Path,
    row: Mapping[str, Any],
) -> tuple[bytes, int, int]:
    if row["segmentation_status"] != "accepted" or row["reasons"]:
        raise CandidateFreezeError(f"accepted row has non-accepted geometry: {row['line_id']}")
    if row.get("upstream_resolution_status") != "pass":
        raise CandidateFreezeError(f"accepted row lacks upstream resolution pass: {row['line_id']}")
    for field in ("line_sha256", "source_master_sha256"):
        if not isinstance(row.get(field), str) or SHA256_RE.fullmatch(row[field]) is None:
            raise CandidateFreezeError(f"invalid {field}: {row['line_id']}")
    bbox = row.get("bbox")
    if (
        not isinstance(bbox, list)
        or len(bbox) != 4
        or any(isinstance(value, bool) or not isinstance(value, int) for value in bbox)
        or bbox[2] <= bbox[0]
        or bbox[3] <= bbox[1]
        or row.get("bbox_convention") != "xyxy_half_open"
    ):
        raise CandidateFreezeError(f"invalid bbox: {row['line_id']}")
    image_path = _safe_source_path(input_dir, row.get("line_image"))
    image_bytes = image_path.read_bytes()
    if _sha256(image_bytes) != row["line_sha256"]:
        raise CandidateFreezeError(f"line image hash mismatch: {row['line_id']}")
    try:
        with io.BytesIO(image_bytes) as buffer, Image.open(buffer) as image:
            width, height = image.size
            if image.mode != "L":
                raise CandidateFreezeError(f"line image must use grayscale L: {row['line_id']}")
            image.load()
    except Image.DecompressionBombError as exc:
        raise CandidateFreezeError(f"unsafe line image: {row['line_id']}") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise CandidateFreezeError(f"could not decode line image: {row['line_id']}") from exc
    if (width, height) != (bbox[2] - bbox[0], bbox[3] - bbox[1]):
        raise CandidateFreezeError(f"line image dimensions disagree with bbox: {row['line_id']}")
    return image_bytes, width, height


def _pilot_ids(rows: Sequence[Mapping[str, Any]], pilot_count: int) -> set[str]:
    by_page: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_page[str(row["page_id"])].append(str(row["line_id"]))
    selected: list[str] = []
    offset = 0
    while len(selected) < pilot_count:
        for page_rows in by_page.values():
            if offset < len(page_rows):
                selected.append(page_rows[offset])
                if len(selected) == pilot_count:
                    return set(selected)
        offset += 1
    return set(selected)


def _build_to_staging(
    input_dir: Path,
    output_dir: Path,
    *,
    candidate_set_id: str,
    pilot_count: int,
) -> dict[str, Any]:
    rows, source_manifest_sha256 = _read_manifest(input_dir / "manifest.jsonl")
    seen: set[str] = set()
    accepted: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=1):
        _validate_row(row, row_number)
        line_id = str(row["line_id"])
        if line_id in seen:
            raise CandidateFreezeError(f"duplicate line_id: {line_id}")
        seen.add(line_id)
        if row["status"] == "accepted":
            accepted.append(row)
    if pilot_count <= 0 or pilot_count >= len(accepted):
        raise CandidateFreezeError("pilot_count must leave non-empty pilot and evaluation cohorts")

    pilot = _pilot_ids(accepted, pilot_count)
    lines_dir = output_dir / "lines"
    lines_dir.mkdir(parents=True)
    candidate_rows: list[dict[str, Any]] = []
    seen_image_hashes: set[str] = set()
    for row in accepted:
        image_bytes, width, height = _accepted_image(input_dir, row)
        line_id = str(row["line_id"])
        image_sha256 = str(row["line_sha256"])
        if image_sha256 in seen_image_hashes:
            raise CandidateFreezeError(f"duplicate accepted line image: {line_id}")
        seen_image_hashes.add(image_sha256)
        relative_image = Path("lines") / f"{line_id}.png"
        (output_dir / relative_image).write_bytes(image_bytes)
        candidate_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "candidate_set_id": candidate_set_id,
                "candidate_id": f"GCV0-{line_id}",
                "cohort": "pilot" if line_id in pilot else "evaluation",
                "source_id": line_id,
                "page_id": row["page_id"],
                "line_id": line_id,
                "order": row["order"],
                "bbox": row["bbox"],
                "bbox_convention": "xyxy_half_open",
                "image": relative_image.as_posix(),
                "image_sha256": image_sha256,
                "width": width,
                "height": height,
                "source_master_sha256": row["source_master_sha256"],
                "source_segmentation_manifest_sha256": source_manifest_sha256,
            }
        )
    manifest_path = output_dir / "candidates.jsonl"
    manifest_path.write_text(_canonical_jsonl(candidate_rows), encoding="utf-8")
    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_set_id": candidate_set_id,
        "source_segmentation_manifest_sha256": source_manifest_sha256,
        "source_rows": len(rows),
        "candidate_rows": len(candidate_rows),
        "pilot_rows": pilot_count,
        "evaluation_rows": len(candidate_rows) - pilot_count,
        "cohort_assignment": "page_round_robin_v0",
        "candidate_manifest": manifest_path.name,
        "candidate_manifest_sha256": _sha256(manifest_path.read_bytes()),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def freeze_candidates(
    input_dir: Path,
    output_dir: Path,
    *,
    candidate_set_id: str,
    pilot_count: int = 10,
) -> dict[str, Any]:
    if not input_dir.is_dir():
        raise CandidateFreezeError(f"input directory does not exist: {input_dir}")
    if SET_ID_RE.fullmatch(candidate_set_id) is None:
        raise CandidateFreezeError("candidate_set_id must be 3-80 safe identifier characters")
    if output_dir.exists():
        raise CandidateFreezeError(f"output directory already exists: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{output_dir.name}.staging-", dir=output_dir.parent
    ) as temporary_directory:
        staging_dir = Path(temporary_directory)
        summary = _build_to_staging(
            input_dir,
            staging_dir,
            candidate_set_id=candidate_set_id,
            pilot_count=pilot_count,
        )
        try:
            staging_dir.replace(output_dir)
        except OSError as exc:
            raise CandidateFreezeError(f"could not publish candidate set: {output_dir}") from exc
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze high-resolution OCR Gold candidates before model predictions."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--candidate-set-id", required=True)
    parser.add_argument("--pilot-count", type=int, default=10)
    args = parser.parse_args()
    summary = freeze_candidates(
        args.input_dir,
        args.output_dir,
        candidate_set_id=args.candidate_set_id,
        pilot_count=args.pilot_count,
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
