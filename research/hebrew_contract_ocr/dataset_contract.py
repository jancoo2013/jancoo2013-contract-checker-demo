from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image


SCHEMA_VERSION = 1
DATA_TIERS = {"synthetic", "silver", "gold"}
SPLITS = {"train", "validation", "test"}
GOLD_LABEL_STATUSES = {"human_approved", "human_corrected"}
BIDI_CONTROL_CHARACTERS = {
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}
REQUIRED_FIELDS = {
    "schema_version",
    "dataset_id",
    "sample_id",
    "image",
    "text",
    "data_tier",
    "split",
    "label_status",
    "source_dataset",
    "source_id",
    "image_sha256",
    "text_sha256",
    "width",
    "height",
}


class DatasetContractError(ValueError):
    pass


@dataclass(frozen=True)
class CharsetContract:
    name: str
    schema_version: int
    ctc_blank_id: int
    normalization: str
    characters: tuple[str, ...]

    @property
    def character_set(self) -> frozenset[str]:
        return frozenset(self.characters)

    @property
    def character_to_id(self) -> dict[str, int]:
        return {character: index + 1 for index, character in enumerate(self.characters)}


@dataclass(frozen=True)
class SourceRecord:
    source_path: Path
    source_image: str
    text: str
    data_tier: str
    proposed_split: str
    label_status: str
    source_dataset: str
    source_id: str
    image_sha256: str
    text_sha256: str
    width: int
    height: int
    optional_metadata: Mapping[str, Any]


def default_charset_path() -> Path:
    return Path(__file__).with_name("charset_v0.json")


def load_charset(path: Path | None = None) -> CharsetContract:
    charset_path = path or default_charset_path()
    payload = json.loads(charset_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DatasetContractError("charset must be a JSON object")
    characters = payload.get("characters")
    if not isinstance(characters, list) or not characters:
        raise DatasetContractError("charset characters must be a non-empty array")
    if any(not isinstance(character, str) or len(character) != 1 for character in characters):
        raise DatasetContractError("every charset entry must be exactly one Unicode character")
    if len(characters) != len(set(characters)):
        raise DatasetContractError("charset contains duplicate characters")
    if any(character in BIDI_CONTROL_CHARACTERS for character in characters):
        raise DatasetContractError("charset must not contain bidi control characters")
    if any(unicodedata.normalize("NFC", character) != character for character in characters):
        raise DatasetContractError("charset characters must already be NFC-normalized")
    contract = CharsetContract(
        name=str(payload.get("name") or ""),
        schema_version=int(payload.get("schema_version") or 0),
        ctc_blank_id=int(payload.get("ctc_blank_id", -1)),
        normalization=str(payload.get("normalization") or ""),
        characters=tuple(characters),
    )
    if contract.schema_version != SCHEMA_VERSION:
        raise DatasetContractError(f"unsupported charset schema_version: {contract.schema_version}")
    if contract.ctc_blank_id != 0:
        raise DatasetContractError("CTC blank ID must be 0")
    if contract.character_to_id.get(" ") != 1:
        raise DatasetContractError("ASCII space must be the first non-blank charset entry")
    return contract


def normalize_text(value: str) -> str:
    if not isinstance(value, str):
        raise DatasetContractError("text must be a string")
    controls = sorted({character for character in value if character in BIDI_CONTROL_CHARACTERS})
    if controls:
        codepoints = ", ".join(f"U+{ord(character):04X}" for character in controls)
        raise DatasetContractError(f"bidi control characters are forbidden: {codepoints}")
    normalized = unicodedata.normalize("NFC", value.replace("\ufeff", ""))
    return " ".join(normalized.split())


def unknown_characters(text: str, charset: CharsetContract) -> list[str]:
    return sorted(set(text).difference(charset.character_set), key=ord)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise DatasetContractError(f"invalid JSON on {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise DatasetContractError(f"expected an object on {path}:{line_number}")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _relative_path(value: Any, field_name: str = "image") -> PurePosixPath:
    if not isinstance(value, str) or not value.strip():
        raise DatasetContractError(f"{field_name} must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise DatasetContractError(f"unsafe {field_name} path: {value}")
    return path


def _resolve_under(root: Path, relative: PurePosixPath) -> Path:
    root_resolved = root.resolve()
    path = root_resolved.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root_resolved):
        raise DatasetContractError(f"path escapes dataset root: {relative}")
    return path


def _image_metadata(path: Path) -> tuple[int, int]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception as exc:
        raise DatasetContractError(f"invalid image: {path}") from exc


def _validate_text(text: str, charset: CharsetContract, source_id: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        raise DatasetContractError(f"empty text for {source_id}")
    unknown = unknown_characters(normalized, charset)
    if unknown:
        rendered = " ".join(f"{character!r}=U+{ord(character):04X}" for character in unknown)
        raise DatasetContractError(f"unknown characters for {source_id}: {rendered}")
    return normalized


def _require_identifier(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _source_image_path(dataset_root: Path, image_value: Any) -> tuple[str, Path]:
    relative = _relative_path(image_value)
    path = _resolve_under(dataset_root, relative)
    if not path.is_file():
        raise DatasetContractError(f"image does not exist: {path}")
    return relative.as_posix(), path


def _stable_sample_id(data_tier: str, source_dataset: str, source_id: str, text: str) -> str:
    digest = hashlib.sha256(
        f"{data_tier}\0{source_dataset}\0{source_id}\0{text}".encode("utf-8")
    ).hexdigest()[:20]
    prefix = {"synthetic": "syn", "silver": "sil", "gold": "gld"}[data_tier]
    return f"{prefix}_{digest}"


def _proposed_synthetic_split(row: Mapping[str, Any], text_hash: str, validation_fraction: float) -> str:
    split = str(row.get("split") or "")
    if split in {"train", "validation"}:
        return split
    fraction = int(text_hash[:16], 16) / 2**64
    return "validation" if fraction < validation_fraction else "train"


def _collect_source_records(
    rows: Sequence[Mapping[str, Any]],
    dataset_root: Path,
    data_tier: str,
    source_dataset: str,
    charset: CharsetContract,
    validation_fraction: float,
) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    seen_source_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        source_image, image_path = _source_image_path(dataset_root, row.get("image"))
        source_id = str(row.get("gold_id") or source_image)
        if source_id in seen_source_ids:
            raise DatasetContractError(f"duplicate source_id in {source_dataset}: {source_id}")
        seen_source_ids.add(source_id)
        raw_text = row.get("text")
        if not isinstance(raw_text, str):
            raise DatasetContractError(f"text must be a string for {source_id}")
        text = _validate_text(raw_text, charset, source_id)
        text_hash = sha256_text(text)
        width, height = _image_metadata(image_path)
        if data_tier == "synthetic":
            proposed_split = _proposed_synthetic_split(row, text_hash, validation_fraction)
            label_status = "synthetic_exact"
        elif data_tier == "silver":
            proposed_split = "train"
            label_status = str(row.get("label_status") or "silver_unversioned")
        else:
            review_status = str(row.get("review_status") or "")
            if review_status not in {"approved", "corrected"}:
                continue
            proposed_split = "test"
            label_status = f"human_{review_status}"
        optional_metadata = {
            key: row[key]
            for key in (
                "pack_id",
                "selection_category",
                "page",
                "line",
                "template_id",
                "text_source",
                "source_crop",
            )
            if key in row
        }
        records.append(
            SourceRecord(
                source_path=image_path,
                source_image=source_image,
                text=text,
                data_tier=data_tier,
                proposed_split=proposed_split,
                label_status=label_status,
                source_dataset=source_dataset,
                source_id=source_id,
                image_sha256=sha256_file(image_path),
                text_sha256=text_hash,
                width=width,
                height=height,
                optional_metadata=optional_metadata,
            )
        )
    if not records:
        raise DatasetContractError(f"no usable {data_tier} records found in {source_dataset}")
    return records


def _check_output_empty(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise DatasetContractError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise DatasetContractError(f"output directory must be empty: {output_dir}")


def _prepare_output(output_dir: Path) -> None:
    _check_output_empty(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def _final_training_splits(records: Sequence[SourceRecord]) -> tuple[dict[str, str], int]:
    grouped: dict[str, list[SourceRecord]] = defaultdict(list)
    for record in records:
        grouped[record.text_sha256].append(record)
    split_by_source: dict[str, str] = {}
    reassignments = 0
    for group in grouped.values():
        final_split = "train" if any(record.proposed_split == "train" for record in group) else "validation"
        for record in group:
            key = f"{record.data_tier}\0{record.source_dataset}\0{record.source_id}"
            split_by_source[key] = final_split
            reassignments += int(record.proposed_split != final_split)
    return split_by_source, reassignments


def _materialize_records(
    records: Sequence[SourceRecord],
    output_dir: Path,
    split_by_source: Mapping[str, str],
    dataset_id: str,
) -> list[dict[str, Any]]:
    canonical: list[dict[str, Any]] = []
    seen_sample_ids: set[str] = set()
    seen_image_hashes: dict[str, str] = {}
    for record in records:
        sample_id = _stable_sample_id(
            record.data_tier,
            record.source_dataset,
            record.source_id,
            record.text,
        )
        if sample_id in seen_sample_ids:
            raise DatasetContractError(f"duplicate generated sample_id: {sample_id}")
        seen_sample_ids.add(sample_id)
        previous_image = seen_image_hashes.get(record.image_sha256)
        if previous_image is not None:
            raise DatasetContractError(f"duplicate image bytes: {record.source_id} and {previous_image}")
        seen_image_hashes[record.image_sha256] = record.source_id
        suffix = record.source_path.suffix.lower() or ".png"
        relative_image = PurePosixPath("images", record.data_tier, f"{sample_id}{suffix}")
        destination = _resolve_under(output_dir, relative_image)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(record.source_path, destination)
        source_key = f"{record.data_tier}\0{record.source_dataset}\0{record.source_id}"
        split = split_by_source[source_key]
        row: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "dataset_id": dataset_id,
            "sample_id": sample_id,
            "image": relative_image.as_posix(),
            "text": record.text,
            "data_tier": record.data_tier,
            "split": split,
            "label_status": record.label_status,
            "source_dataset": record.source_dataset,
            "source_id": record.source_id,
            "image_sha256": record.image_sha256,
            "text_sha256": record.text_sha256,
            "width": record.width,
            "height": record.height,
        }
        row.update(record.optional_metadata)
        canonical.append(row)
    return canonical


def _dataset_summary(
    rows: Sequence[Mapping[str, Any]],
    dataset_id: str,
    charset: CharsetContract,
    split_reassignments: int = 0,
) -> dict[str, Any]:
    character_counts: Counter[str] = Counter()
    for row in rows:
        character_counts.update(str(row["text"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_id": dataset_id,
        "records": len(rows),
        "tiers": dict(sorted(Counter(str(row["data_tier"]) for row in rows).items())),
        "source_datasets": dict(sorted(Counter(str(row["source_dataset"]) for row in rows).items())),
        "splits": dict(sorted(Counter(str(row["split"]) for row in rows).items())),
        "split_reassignments_to_prevent_text_leakage": split_reassignments,
        "charset": charset.name,
        "characters_observed": len(character_counts),
        "character_counts": dict(sorted(character_counts.items(), key=lambda item: ord(item[0]))),
    }


def build_training_dataset(
    synthetic_manifest: Path,
    synthetic_root: Path,
    silver_manifest: Path,
    silver_root: Path,
    gold_manifest: Path,
    gold_root: Path,
    output_dir: Path,
    dataset_id: str = "hebrew_contract_ocr_training_v0",
    synthetic_dataset_id: str = "synthetic_v0",
    silver_dataset_id: str = "silver_verified_v1",
    charset_path: Path | None = None,
    validation_fraction: float = 0.1,
) -> dict[str, Any]:
    _check_output_empty(output_dir)
    dataset_id = _require_identifier(dataset_id, "dataset_id")
    synthetic_dataset_id = _require_identifier(synthetic_dataset_id, "synthetic_dataset_id")
    silver_dataset_id = _require_identifier(silver_dataset_id, "silver_dataset_id")
    if not 0.0 < validation_fraction < 1.0:
        raise DatasetContractError("validation_fraction must be between 0 and 1")
    charset = load_charset(charset_path)
    gold_validation = validate_manifest(gold_manifest, gold_root, charset_path=charset_path)
    if not gold_validation["valid"]:
        raise DatasetContractError(f"invalid gold manifest: {gold_validation['errors']}")
    gold_rows = read_jsonl(gold_manifest)
    if not gold_rows:
        raise DatasetContractError("gold manifest must contain at least one reviewed test row")
    if any(row.get("data_tier") != "gold" or row.get("split") != "test" for row in gold_rows):
        raise DatasetContractError("gold manifest must contain only test-only Gold rows")
    gold_image_hashes = {str(row["image_sha256"]) for row in gold_rows}
    gold_text_hashes = {str(row["text_sha256"]) for row in gold_rows}
    gold_source_ids = {str(row["source_crop"]) for row in gold_rows if row.get("source_crop")}
    synthetic = _collect_source_records(
        read_jsonl(synthetic_manifest),
        synthetic_root,
        "synthetic",
        synthetic_dataset_id,
        charset,
        validation_fraction,
    )
    silver = _collect_source_records(
        read_jsonl(silver_manifest),
        silver_root,
        "silver",
        silver_dataset_id,
        charset,
        validation_fraction,
    )
    records: list[SourceRecord] = []
    exclusions: list[dict[str, Any]] = []
    for record in (*synthetic, *silver):
        reasons = [
            reason
            for reason, matched in (
                ("image_sha256", record.image_sha256 in gold_image_hashes),
                ("text_sha256", record.text_sha256 in gold_text_hashes),
                (
                    "source_id",
                    record.data_tier == "silver" and record.source_id in gold_source_ids,
                ),
            )
            if matched
        ]
        if reasons:
            exclusions.append(
                {
                    "data_tier": record.data_tier,
                    "source_dataset": record.source_dataset,
                    "source_id": record.source_id,
                    "image_sha256": record.image_sha256,
                    "text_sha256": record.text_sha256,
                    "reasons": reasons,
                }
            )
        else:
            records.append(record)
    if not records:
        raise DatasetContractError("no training records remain after Gold exclusions")
    split_by_source, reassignments = _final_training_splits(records)
    _prepare_output(output_dir)
    rows = _materialize_records(records, output_dir, split_by_source, dataset_id)
    write_jsonl(output_dir / "manifest.jsonl", rows)
    write_jsonl(output_dir / "gold_exclusions.jsonl", exclusions)
    source_charset = charset_path or default_charset_path()
    shutil.copy2(source_charset, output_dir / "charset_v0.json")
    summary = _dataset_summary(rows, dataset_id, charset, reassignments)
    summary["gold_manifest_sha256"] = sha256_file(gold_manifest)
    summary["gold_exclusions"] = len(exclusions)
    summary["gold_exclusion_reasons"] = dict(
        sorted(Counter(reason for row in exclusions for reason in row["reasons"]).items())
    )
    validation = validate_manifest(output_dir / "manifest.jsonl", output_dir, charset_path=source_charset)
    if not validation["valid"]:
        raise DatasetContractError(f"materialized training dataset failed validation: {validation['errors']}")
    leakage = check_training_gold_leakage(output_dir / "manifest.jsonl", gold_manifest)
    if not leakage["clean"]:
        raise DatasetContractError("materialized training dataset still overlaps Gold")
    summary["validation"] = validation
    summary["gold_leakage"] = leakage
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def materialize_gold_dataset(
    review_manifest: Path,
    review_root: Path,
    output_dir: Path,
    dataset_id: str = "hebrew_contract_ocr_gold_v0",
    charset_path: Path | None = None,
) -> dict[str, Any]:
    _check_output_empty(output_dir)
    dataset_id = _require_identifier(dataset_id, "dataset_id")
    charset = load_charset(charset_path)
    raw_rows = read_jsonl(review_manifest)
    pack_ids = {str(row.get("pack_id") or "") for row in raw_rows if row.get("pack_id")}
    source_dataset = next(iter(pack_ids)) if len(pack_ids) == 1 else review_manifest.stem
    records = _collect_source_records(
        raw_rows,
        review_root,
        "gold",
        source_dataset,
        charset,
        validation_fraction=0.1,
    )
    _prepare_output(output_dir)
    split_by_source = {
        f"{record.data_tier}\0{record.source_dataset}\0{record.source_id}": "test"
        for record in records
    }
    rows = _materialize_records(records, output_dir, split_by_source, dataset_id)
    write_jsonl(output_dir / "manifest.jsonl", rows)
    source_charset = charset_path or default_charset_path()
    shutil.copy2(source_charset, output_dir / "charset_v0.json")
    summary = _dataset_summary(rows, dataset_id, charset)
    validation = validate_manifest(output_dir / "manifest.jsonl", output_dir, charset_path=source_charset)
    if not validation["valid"]:
        raise DatasetContractError(f"materialized gold dataset failed validation: {validation['errors']}")
    summary["validation"] = validation
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def validate_manifest(
    manifest_path: Path,
    dataset_root: Path,
    charset_path: Path | None = None,
) -> dict[str, Any]:
    charset = load_charset(charset_path)
    rows = read_jsonl(manifest_path)
    errors: list[str] = []
    warnings: list[str] = []
    sample_ids: set[str] = set()
    image_hash_to_sample: dict[str, str] = {}
    text_splits: dict[str, set[str]] = defaultdict(set)
    image_splits: dict[str, set[str]] = defaultdict(set)
    character_counts: Counter[str] = Counter()
    dataset_ids: set[str] = set()

    for index, row in enumerate(rows, start=1):
        label = str(row.get("sample_id") or f"row_{index}")
        missing = sorted(REQUIRED_FIELDS.difference(row))
        if missing:
            errors.append(f"{label}: missing fields: {', '.join(missing)}")
            continue
        if row.get("schema_version") != SCHEMA_VERSION:
            errors.append(f"{label}: unsupported schema_version {row.get('schema_version')!r}")
        if not isinstance(row.get("dataset_id"), str) or not str(row.get("dataset_id")).strip():
            errors.append(f"{label}: dataset_id must be a non-empty string")
        else:
            dataset_ids.add(str(row["dataset_id"]))
        if not isinstance(row.get("sample_id"), str) or not str(row.get("sample_id")).strip():
            errors.append(f"{label}: sample_id must be a non-empty string")
        for field_name in ("label_status", "source_dataset", "source_id"):
            if not isinstance(row.get(field_name), str) or not str(row.get(field_name)).strip():
                errors.append(f"{label}: {field_name} must be a non-empty string")
        if label in sample_ids:
            errors.append(f"{label}: duplicate sample_id")
        sample_ids.add(label)
        tier = str(row.get("data_tier"))
        split = str(row.get("split"))
        if tier not in DATA_TIERS:
            errors.append(f"{label}: invalid data_tier {tier!r}")
        if split not in SPLITS:
            errors.append(f"{label}: invalid split {split!r}")
        if tier in {"synthetic", "silver"} and split == "test":
            errors.append(f"{label}: {tier} data cannot use the test split")
        if tier == "gold" and split != "test":
            errors.append(f"{label}: gold data must use the test split")
        if tier == "gold" and row.get("label_status") not in GOLD_LABEL_STATUSES:
            errors.append(f"{label}: invalid gold label_status {row.get('label_status')!r}")
        try:
            raw_text = row.get("text")
            normalized = normalize_text(raw_text)
            if raw_text != normalized:
                errors.append(f"{label}: text is not in canonical normalized form")
            if not normalized:
                errors.append(f"{label}: empty text")
            unknown = unknown_characters(normalized, charset)
            if unknown:
                errors.append(
                    f"{label}: unknown characters: "
                    + " ".join(f"U+{ord(character):04X}" for character in unknown)
                )
            expected_text_hash = sha256_text(normalized)
            if row.get("text_sha256") != expected_text_hash:
                errors.append(f"{label}: text_sha256 mismatch")
            text_splits[expected_text_hash].add(split)
            character_counts.update(normalized)
        except DatasetContractError as exc:
            errors.append(f"{label}: {exc}")

        try:
            relative_image = _relative_path(row.get("image"))
            image_path = _resolve_under(dataset_root, relative_image)
            if not image_path.is_file():
                errors.append(f"{label}: missing image {relative_image}")
                continue
            actual_image_hash = sha256_file(image_path)
            if row.get("image_sha256") != actual_image_hash:
                errors.append(f"{label}: image_sha256 mismatch")
            previous = image_hash_to_sample.get(actual_image_hash)
            if previous is not None and previous != label:
                errors.append(f"{label}: duplicate image bytes also used by {previous}")
            image_hash_to_sample[actual_image_hash] = label
            image_splits[actual_image_hash].add(split)
            width, height = _image_metadata(image_path)
            if row.get("width") != width or row.get("height") != height:
                errors.append(f"{label}: image dimensions mismatch")
        except DatasetContractError as exc:
            errors.append(f"{label}: {exc}")

    for text_hash, splits in text_splits.items():
        if len(splits) > 1:
            errors.append(f"text leakage across splits for {text_hash}: {sorted(splits)}")
    for image_hash, splits in image_splits.items():
        if len(splits) > 1:
            errors.append(f"image leakage across splits for {image_hash}: {sorted(splits)}")
    if len(dataset_ids) > 1:
        errors.append(f"manifest contains multiple dataset_id values: {sorted(dataset_ids)}")
    if not rows:
        errors.append("manifest is empty")
    if rows and not any(str(row.get("split")) == "validation" for row in rows):
        if any(str(row.get("data_tier")) != "gold" for row in rows):
            warnings.append("training manifest has no validation rows")

    return {
        "schema_version": SCHEMA_VERSION,
        "valid": not errors,
        "records": len(rows),
        "errors": errors,
        "warnings": warnings,
        "tiers": dict(sorted(Counter(str(row.get("data_tier")) for row in rows).items())),
        "splits": dict(sorted(Counter(str(row.get("split")) for row in rows).items())),
        "characters_observed": len(character_counts),
    }


def check_training_gold_leakage(
    training_manifest: Path,
    gold_manifest: Path,
) -> dict[str, Any]:
    training_rows = read_jsonl(training_manifest)
    gold_rows = read_jsonl(gold_manifest)
    training_images = {str(row.get("image_sha256")): str(row.get("sample_id")) for row in training_rows}
    training_texts = {str(row.get("text_sha256")): str(row.get("sample_id")) for row in training_rows}
    image_overlaps = [
        {
            "gold_sample_id": str(row.get("sample_id")),
            "training_sample_id": training_images[str(row.get("image_sha256"))],
            "image_sha256": str(row.get("image_sha256")),
        }
        for row in gold_rows
        if str(row.get("image_sha256")) in training_images
    ]
    text_overlaps = [
        {
            "gold_sample_id": str(row.get("sample_id")),
            "training_sample_id": training_texts[str(row.get("text_sha256"))],
            "text_sha256": str(row.get("text_sha256")),
        }
        for row in gold_rows
        if str(row.get("text_sha256")) in training_texts
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "clean": not image_overlaps and not text_overlaps,
        "training_records": len(training_rows),
        "gold_records": len(gold_rows),
        "image_overlaps": image_overlaps,
        "text_overlaps": text_overlaps,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hebrew Contract OCR Dataset Contract v0 tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    training = subparsers.add_parser("build-training", help="Materialize synthetic + silver train/validation data.")
    training.add_argument("--synthetic-manifest", type=Path, required=True)
    training.add_argument("--synthetic-root", type=Path, required=True)
    training.add_argument("--silver-manifest", type=Path, required=True)
    training.add_argument("--silver-root", type=Path, required=True)
    training.add_argument("--gold-manifest", type=Path, required=True)
    training.add_argument("--gold-root", type=Path, required=True)
    training.add_argument("--output-dir", type=Path, required=True)
    training.add_argument("--dataset-id", default="hebrew_contract_ocr_training_v0")
    training.add_argument("--synthetic-dataset-id", required=True)
    training.add_argument("--silver-dataset-id", required=True)
    training.add_argument("--charset", type=Path)
    training.add_argument("--validation-fraction", type=float, default=0.1)

    gold = subparsers.add_parser("materialize-gold", help="Materialize accepted human review rows as test-only gold.")
    gold.add_argument("--review-manifest", type=Path, required=True)
    gold.add_argument("--review-root", type=Path, required=True)
    gold.add_argument("--output-dir", type=Path, required=True)
    gold.add_argument("--dataset-id", default="hebrew_contract_ocr_gold_v0")
    gold.add_argument("--charset", type=Path)

    validate = subparsers.add_parser("validate", help="Validate a canonical dataset manifest and its images.")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--dataset-root", type=Path, required=True)
    validate.add_argument("--charset", type=Path)

    leakage = subparsers.add_parser("check-leakage", help="Block exact image or text overlap between training and gold.")
    leakage.add_argument("--training-manifest", type=Path, required=True)
    leakage.add_argument("--training-root", type=Path, required=True)
    leakage.add_argument("--gold-manifest", type=Path, required=True)
    leakage.add_argument("--gold-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "build-training":
        result = build_training_dataset(
            args.synthetic_manifest,
            args.synthetic_root,
            args.silver_manifest,
            args.silver_root,
            args.gold_manifest,
            args.gold_root,
            args.output_dir,
            dataset_id=args.dataset_id,
            synthetic_dataset_id=args.synthetic_dataset_id,
            silver_dataset_id=args.silver_dataset_id,
            charset_path=args.charset,
            validation_fraction=args.validation_fraction,
        )
    elif args.command == "materialize-gold":
        result = materialize_gold_dataset(
            args.review_manifest,
            args.review_root,
            args.output_dir,
            dataset_id=args.dataset_id,
            charset_path=args.charset,
        )
    elif args.command == "validate":
        result = validate_manifest(args.manifest, args.dataset_root, charset_path=args.charset)
    else:
        training_validation = validate_manifest(args.training_manifest, args.training_root)
        if not training_validation["valid"]:
            raise DatasetContractError(f"invalid training manifest: {training_validation['errors']}")
        gold_validation = validate_manifest(args.gold_manifest, args.gold_root)
        if not gold_validation["valid"]:
            raise DatasetContractError(f"invalid gold manifest: {gold_validation['errors']}")
        result = check_training_gold_leakage(args.training_manifest, args.gold_manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.command in {"validate", "check-leakage"}:
        success = result["valid"] if args.command == "validate" else result["clean"]
        return 0 if success else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
