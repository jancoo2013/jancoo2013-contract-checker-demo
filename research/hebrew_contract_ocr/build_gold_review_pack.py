from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageStat


DEFAULT_QUOTAS: dict[str, int] = {
    "body": 30,
    "clause": 10,
    "numeric": 10,
    "mixed_punctuation": 10,
}
SELECTION_ORDER = ("mixed_punctuation", "numeric", "clause", "body")
CLAUSE_PREFIX_RE = re.compile(r"^\s*\d+(?:\.\d+)*\.?\s+")
LATIN_RE = re.compile(r"[A-Za-z]")
DIGIT_RE = re.compile(r"\d")
LONG_NUMBER_RE = re.compile(r"(?<!\d)\d{6,}(?!\d)")
DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b")
PII_MARKERS = (
    "ת.ז",
    "ת״ז",
    "שם מלא",
    "מרחוב",
    "טלפון",
    "דוא\"ל",
    "דוא״ל",
    "חשבון בנק",
)
PUNCTUATION = set(".,:;!?()[]{}\"'׳״/%+-")


@dataclass(frozen=True)
class Candidate:
    image: str
    text: str
    page: int
    line: int
    bbox: tuple[int, int, int, int]
    source_image: str
    page_image: str
    label_status: str
    selection_score: float
    category_scores: Mapping[str, float]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"expected an object on {path}:{line_number}")
            rows.append(row)
    return rows


def _index_unique(rows: Iterable[Mapping[str, Any]], key: str, source_name: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "")
        if not value:
            raise ValueError(f"missing {key!r} in {source_name}")
        if value in result:
            raise ValueError(f"duplicate {key}={value!r} in {source_name}")
        result[value] = row
    return result


def contains_probable_pii(text: str) -> bool:
    normalized = " ".join(text.split())
    return (
        "_" in normalized
        or LONG_NUMBER_RE.search(normalized) is not None
        or any(marker in normalized for marker in PII_MARKERS)
    )


def _punctuation_count(text: str) -> int:
    return sum(character in PUNCTUATION for character in text)


def _remaining_after_clause(text: str) -> str:
    return CLAUSE_PREFIX_RE.sub("", text, count=1)


def category_scores(text: str) -> dict[str, float]:
    punctuation = _punctuation_count(text)
    has_latin = LATIN_RE.search(text) is not None
    has_clause = CLAUSE_PREFIX_RE.search(text) is not None
    remaining = _remaining_after_clause(text)
    remaining_digits = len(DIGIT_RE.findall(remaining))
    has_numeric_content = bool(
        remaining_digits
        or DATE_RE.search(remaining)
        or "ש\"ח" in remaining
        or "ש״ח" in remaining
        or "₪" in remaining
        or "%" in remaining
    )
    return {
        "body": -1.0 if has_clause else min(len(text), 120) / 120,
        "clause": (2.0 if has_clause else -1.0) + min(text.count("."), 3) * 0.1,
        "numeric": (2.0 if has_numeric_content else -1.0) + min(remaining_digits, 8) * 0.08,
        "mixed_punctuation": (3.0 if has_latin else 0.0) + (1.0 if punctuation >= 3 else -1.0) + min(punctuation, 10) * 0.08,
    }


def image_clarity_score(path: Path) -> float:
    with Image.open(path) as source:
        image = source.convert("L")
    contrast = min(ImageStat.Stat(image).stddev[0] / 64.0, 1.0)
    edges = image.filter(ImageFilter.FIND_EDGES)
    edge_variance = ImageStat.Stat(edges).var[0]
    sharpness = min(math.log1p(edge_variance) / 8.0, 1.0)
    height_score = min(image.height / 24.0, 1.0)
    return 0.45 * contrast + 0.4 * sharpness + 0.15 * height_score


def _float(row: Mapping[str, Any], key: str) -> float:
    value = row.get(key)
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_candidates(dataset_dir: Path) -> tuple[list[Candidate], dict[str, int]]:
    manifest_rows = read_jsonl(dataset_dir / "manifest.jsonl")
    label_rows = read_jsonl(dataset_dir / "silver_verified_v1.jsonl")
    verification_rows = read_jsonl(dataset_dir / "verification_v1.jsonl")
    manifest = _index_unique(manifest_rows, "image", "manifest.jsonl")
    verification = _index_unique(verification_rows, "image", "verification_v1.jsonl")

    candidates: list[Candidate] = []
    exclusions: dict[str, int] = {}

    def exclude(reason: str) -> None:
        exclusions[reason] = exclusions.get(reason, 0) + 1

    for label in label_rows:
        image_name = str(label.get("image") or "")
        text = " ".join(str(label.get("text") or "").split())
        metadata = manifest.get(image_name)
        audit = verification.get(image_name)
        if metadata is None or audit is None:
            exclude("missing_metadata")
            continue
        if not text or not any("\u0590" <= character <= "\u05ff" for character in text):
            exclude("no_hebrew_text")
            continue
        if contains_probable_pii(text):
            exclude("probable_pii_or_placeholder")
            continue
        if str(audit.get("final_status") or "") == "excluded":
            exclude("verification_excluded")
            continue
        image_path = dataset_dir / image_name
        page_path = dataset_dir / str(metadata.get("page_image") or "")
        if not image_path.is_file() or not page_path.is_file():
            exclude("missing_image")
            continue
        with Image.open(image_path) as crop:
            if crop.width < 70 or crop.height < 12:
                exclude("crop_too_small")
                continue
        raw_bbox = metadata.get("bbox")
        if not isinstance(raw_bbox, list) or len(raw_bbox) != 4:
            exclude("invalid_bbox")
            continue

        label_status = str(label.get("label_status") or "unversioned")
        status_score = 1.0 if label_status == "consensus_verified" else 0.7
        evidence_score = (
            1.2 * _float(audit, "surya_line_confidence")
            + 0.8 * _float(audit, "tesseract_similarity")
            + 0.8 * _float(audit, "page_similarity")
            + 0.5 * _float(audit, "vertical_overlap")
        )
        clarity = image_clarity_score(image_path)
        length_score = min(len(text) / 90.0, 1.0)
        score = status_score + evidence_score + 1.2 * clarity + 0.35 * length_score
        categories = category_scores(text)
        candidates.append(
            Candidate(
                image=image_name,
                text=text,
                page=int(metadata.get("page") or 0),
                line=int(metadata.get("line") or 0),
                bbox=tuple(int(value) for value in raw_bbox),
                source_image=str(metadata.get("source_image") or ""),
                page_image=str(metadata.get("page_image") or ""),
                label_status=label_status,
                selection_score=round(score, 6),
                category_scores=categories,
            )
        )
    return candidates, exclusions


def _eligible_for_category(candidate: Candidate, category: str) -> bool:
    threshold = 0.0 if category == "body" else 1.0
    return candidate.category_scores[category] >= threshold


def select_stratified(
    candidates: Sequence[Candidate],
    quotas: Mapping[str, int],
) -> list[tuple[str, Candidate]]:
    total = sum(quotas.values())
    if total < 1:
        raise ValueError("at least one candidate must be requested")
    pages = {candidate.page for candidate in candidates}
    if not pages:
        raise ValueError("no eligible candidates")
    page_cap = max(2, math.ceil(total / len(pages)) + 2)
    selected_images: set[str] = set()
    page_counts: dict[int, int] = {}
    selected: list[tuple[str, Candidate]] = []

    for category in SELECTION_ORDER:
        requested = int(quotas.get(category, 0))
        for _ in range(requested):
            pool = [
                candidate
                for candidate in candidates
                if candidate.image not in selected_images
                and _eligible_for_category(candidate, category)
                and page_counts.get(candidate.page, 0) < page_cap
            ]
            if not pool:
                raise ValueError(
                    f"cannot satisfy quota for {category}: requested {requested}, selected "
                    f"{sum(selected_category == category for selected_category, _ in selected)}"
                )
            candidate = max(
                pool,
                key=lambda item: (
                    item.selection_score
                    + item.category_scores[category]
                    - 0.32 * page_counts.get(item.page, 0),
                    -page_counts.get(item.page, 0),
                    -item.page,
                    -item.line,
                ),
            )
            selected.append((category, candidate))
            selected_images.add(candidate.image)
            page_counts[candidate.page] = page_counts.get(candidate.page, 0) + 1
    return selected


def _prepare_output(output_dir: Path) -> tuple[Path, Path]:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ValueError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise ValueError(f"output directory must be empty: {output_dir}")
    images_dir = output_dir / "images"
    review_dir = output_dir / "review"
    images_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    return images_dir, review_dir


def _create_review_images(
    dataset_dir: Path,
    candidate: Candidate,
    gold_id: str,
    images_dir: Path,
    review_dir: Path,
) -> tuple[str, str, str]:
    source_crop = dataset_dir / candidate.image
    exact_name = f"{gold_id}.png"
    exact_path = images_dir / exact_name
    shutil.copy2(source_crop, exact_path)

    with Image.open(source_crop) as source:
        crop = source.convert("RGB")
    zoom = crop.resize((crop.width * 4, crop.height * 4), Image.Resampling.LANCZOS)
    zoom_name = f"{gold_id}_crop_zoom.png"
    zoom.save(review_dir / zoom_name, format="PNG")

    with Image.open(dataset_dir / candidate.page_image) as source:
        page = source.convert("RGB")
    x0, y0, x1, y1 = candidate.bbox
    line_height = max(1, y1 - y0)
    vertical_padding = max(55, line_height * 3)
    context_top = max(0, y0 - vertical_padding)
    context_bottom = min(page.height, y1 + vertical_padding)
    context = page.crop((0, context_top, page.width, context_bottom))
    draw = ImageDraw.Draw(context)
    rectangle = (
        max(0, x0 - 3),
        max(0, y0 - context_top - 3),
        min(context.width - 1, x1 + 3),
        min(context.height - 1, y1 - context_top + 3),
    )
    draw.rectangle(rectangle, outline=(220, 30, 30), width=2)
    context = context.resize((context.width * 2, context.height * 2), Image.Resampling.LANCZOS)
    context_name = f"{gold_id}_context.png"
    context.save(review_dir / context_name, format="PNG")
    return f"images/{exact_name}", f"review/{zoom_name}", f"review/{context_name}"


def _render_review_html(items: Sequence[Mapping[str, Any]], pack_id: str) -> str:
    template_path = Path(__file__).with_name("gold_review_template.html")
    template = template_path.read_text(encoding="utf-8")
    payload = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    replacements = {
        "__GOLD_ITEMS_JSON__": payload,
        "__GOLD_PACK_ID__": json.dumps(pack_id),
    }
    for marker, replacement in replacements.items():
        if template.count(marker) != 1:
            raise ValueError(f"review template must contain exactly one {marker} marker")
        template = template.replace(marker, replacement)
    return template


def build_review_pack(
    dataset_dir: Path,
    output_dir: Path,
    quotas: Mapping[str, int] = DEFAULT_QUOTAS,
) -> dict[str, Any]:
    candidates, exclusions = build_candidates(dataset_dir)
    selected = select_stratified(candidates, quotas)
    fingerprint_payload = [
        {"category": category, "image": candidate.image, "text": candidate.text}
        for category, candidate in selected
    ]
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    pack_id = f"gold-review-v0-{fingerprint}"
    images_dir, review_dir = _prepare_output(output_dir)
    rows: list[dict[str, Any]] = []

    for index, (category, candidate) in enumerate(selected, start=1):
        gold_id = f"GS{index:04d}"
        image, review_crop, context_image = _create_review_images(
            dataset_dir,
            candidate,
            gold_id,
            images_dir,
            review_dir,
        )
        rows.append(
            {
                "schema_version": 1,
                "pack_id": pack_id,
                "gold_id": gold_id,
                "image": image,
                "review_crop": review_crop,
                "context_image": context_image,
                "preliminary_text": candidate.text,
                "selection_category": category,
                "page": candidate.page,
                "line": candidate.line,
                "bbox": list(candidate.bbox),
                "source_image": candidate.source_image,
                "source_crop": candidate.image,
                "silver_label_status": candidate.label_status,
                "selection_score": candidate.selection_score,
                "review_status": "pending",
                "text": candidate.text,
                "reviewer_notes": "",
            }
        )

    manifest_path = output_dir / "gold_candidates_v0.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (output_dir / "review.html").write_text(_render_review_html(rows, pack_id), encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("GOLD_REVIEW_INSTRUCTIONS.md"), output_dir / "INSTRUCTIONS.md")

    category_counts = {
        category: sum(row["selection_category"] == category for row in rows)
        for category in DEFAULT_QUOTAS
    }
    page_counts: dict[str, int] = {}
    for row in rows:
        page_key = str(row["page"])
        page_counts[page_key] = page_counts.get(page_key, 0) + 1
    summary: dict[str, Any] = {
        "schema_version": 1,
        "pack_id": pack_id,
        "status": "candidate_review_pack_not_gold",
        "selected": len(rows),
        "eligible_pool": len(candidates),
        "quotas": dict(quotas),
        "categories": category_counts,
        "pages": page_counts,
        "preselection_exclusions": exclusions,
        "review_entrypoint": "review.html",
        "candidate_manifest": manifest_path.name,
        "gold_rule": "Only rows exported as approved or corrected by a Hebrew-capable reviewer become gold.",
    }
    (output_dir / "selection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an offline, stratified Gold Set v0 review pack from the local silver line archive."
    )
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--body", type=int, default=DEFAULT_QUOTAS["body"])
    parser.add_argument("--clause", type=int, default=DEFAULT_QUOTAS["clause"])
    parser.add_argument("--numeric", type=int, default=DEFAULT_QUOTAS["numeric"])
    parser.add_argument("--mixed-punctuation", type=int, default=DEFAULT_QUOTAS["mixed_punctuation"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    quotas = {
        "body": args.body,
        "clause": args.clause,
        "numeric": args.numeric,
        "mixed_punctuation": args.mixed_punctuation,
    }
    if any(value < 0 for value in quotas.values()):
        raise ValueError("category quotas cannot be negative")
    summary = build_review_pack(args.dataset_dir, args.output_dir, quotas)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
