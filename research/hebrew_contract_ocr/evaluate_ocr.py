from __future__ import annotations

import argparse
import json
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from research.hebrew_contract_ocr.dataset_contract import (
    CharsetContract,
    DatasetContractError,
    check_training_gold_leakage,
    load_charset,
    normalize_text,
    read_jsonl,
    unknown_characters,
    validate_manifest,
)


@dataclass
class EditAccumulator:
    reference_characters: int = 0
    matches: int = 0
    substitutions: int = 0
    deletions: int = 0
    insertions: int = 0

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def cer(self) -> float | None:
        if not self.reference_characters:
            return None
        return self.errors / self.reference_characters

    def to_dict(self) -> dict[str, int | float | None]:
        return {
            "reference_characters": self.reference_characters,
            "matches": self.matches,
            "substitutions": self.substitutions,
            "deletions": self.deletions,
            "insertions": self.insertions,
            "errors": self.errors,
            "cer": self.cer,
        }


Alignment = list[tuple[str, str | None, str | None]]


def align_characters(reference: str, prediction: str) -> Alignment:
    rows = len(reference) + 1
    columns = len(prediction) + 1
    costs = [[0] * columns for _ in range(rows)]
    operations = [[""] * columns for _ in range(rows)]
    for row in range(1, rows):
        costs[row][0] = row
        operations[row][0] = "deletion"
    for column in range(1, columns):
        costs[0][column] = column
        operations[0][column] = "insertion"

    for row in range(1, rows):
        for column in range(1, columns):
            same = reference[row - 1] == prediction[column - 1]
            diagonal_operation = "match" if same else "substitution"
            choices = (
                (costs[row - 1][column - 1] + (0 if same else 1), 0, diagonal_operation),
                (costs[row - 1][column] + 1, 1, "deletion"),
                (costs[row][column - 1] + 1, 2, "insertion"),
            )
            cost, _, operation = min(choices)
            costs[row][column] = cost
            operations[row][column] = operation

    alignment: Alignment = []
    row = len(reference)
    column = len(prediction)
    while row or column:
        operation = operations[row][column]
        if operation in {"match", "substitution"}:
            alignment.append((operation, reference[row - 1], prediction[column - 1]))
            row -= 1
            column -= 1
        elif operation == "deletion":
            alignment.append((operation, reference[row - 1], None))
            row -= 1
        elif operation == "insertion":
            alignment.append((operation, None, prediction[column - 1]))
            column -= 1
        else:
            raise DatasetContractError("internal alignment error")
    alignment.reverse()
    return alignment


def character_class(character: str) -> str:
    if "\u05d0" <= character <= "\u05ea":
        return "hebrew"
    if character.isdigit():
        return "digits"
    if ("A" <= character <= "Z") or ("a" <= character <= "z"):
        return "latin"
    if character == " ":
        return "space"
    category = unicodedata.category(character)
    if category.startswith("P") or category.startswith("S"):
        return "punctuation_symbols"
    return "other"


def accumulate_alignment(
    alignment: Iterable[tuple[str, str | None, str | None]],
    overall: EditAccumulator,
    slices: Mapping[str, EditAccumulator],
) -> None:
    for operation, reference_character, prediction_character in alignment:
        if reference_character is not None:
            category = character_class(reference_character)
            overall.reference_characters += 1
            slices[category].reference_characters += 1
        else:
            if prediction_character is None:
                raise DatasetContractError("alignment operation contains no characters")
            category = character_class(prediction_character)

        if operation == "match":
            overall.matches += 1
            slices[category].matches += 1
        elif operation == "substitution":
            overall.substitutions += 1
            slices[category].substitutions += 1
        elif operation == "deletion":
            overall.deletions += 1
            slices[category].deletions += 1
        elif operation == "insertion":
            overall.insertions += 1
            slices[category].insertions += 1
        else:
            raise DatasetContractError(f"unknown alignment operation: {operation}")


def _prediction_map(path: Path, charset: CharsetContract) -> dict[str, str]:
    predictions: dict[str, str] = {}
    for index, row in enumerate(read_jsonl(path), start=1):
        sample_id = str(row.get("sample_id") or "")
        if not sample_id:
            raise DatasetContractError(f"prediction row {index} is missing sample_id")
        if sample_id in predictions:
            raise DatasetContractError(f"duplicate prediction sample_id: {sample_id}")
        raw_prediction = row.get("prediction", row.get("text", ""))
        if not isinstance(raw_prediction, str):
            raise DatasetContractError(f"prediction {sample_id} must be a string")
        prediction = normalize_text(raw_prediction)
        unknown = unknown_characters(prediction, charset)
        if unknown:
            rendered = " ".join(f"U+{ord(character):04X}" for character in unknown)
            raise DatasetContractError(f"prediction {sample_id} contains unknown characters: {rendered}")
        predictions[sample_id] = prediction
    return predictions


def evaluate_predictions(
    ground_truth_manifest: Path,
    ground_truth_root: Path,
    predictions_path: Path,
    charset_path: Path | None = None,
    allow_non_gold: bool = False,
    training_manifest: Path | None = None,
    training_root: Path | None = None,
    evaluation_split: str | None = None,
) -> dict[str, Any]:
    charset = load_charset(charset_path)
    validation = validate_manifest(ground_truth_manifest, ground_truth_root, charset_path=charset_path)
    if not validation["valid"]:
        raise DatasetContractError(f"invalid ground-truth manifest: {validation['errors']}")
    manifest_rows = read_jsonl(ground_truth_manifest)
    if evaluation_split is None:
        evaluation_split = "test" if any(row.get("data_tier") == "gold" for row in manifest_rows) else "validation"
    if evaluation_split not in {"train", "validation", "test"}:
        raise DatasetContractError(f"invalid evaluation split: {evaluation_split}")
    ground_truth = [row for row in manifest_rows if row.get("split") == evaluation_split]
    if not ground_truth:
        raise DatasetContractError(f"ground-truth manifest has no rows in split {evaluation_split!r}")
    gold_evaluation = all(
        row.get("data_tier") == "gold" and row.get("split") == "test"
        for row in ground_truth
    )
    if not gold_evaluation and not allow_non_gold:
        raise DatasetContractError(
            "ground truth is not test-only gold; pass allow_non_gold only for pipeline smoke tests"
        )
    leakage: dict[str, Any] | None = None
    if training_manifest is not None:
        if training_root is None:
            raise DatasetContractError("training_root is required with training_manifest")
        training_validation = validate_manifest(training_manifest, training_root, charset_path=charset_path)
        if not training_validation["valid"]:
            raise DatasetContractError(f"invalid training manifest: {training_validation['errors']}")
        leakage = check_training_gold_leakage(training_manifest, ground_truth_manifest)
        if not leakage["clean"]:
            raise DatasetContractError("training/gold leakage detected; evaluation is blocked")

    predictions = _prediction_map(predictions_path, charset)
    truth_ids = {str(row["sample_id"]) for row in ground_truth}
    extra_ids = sorted(set(predictions).difference(truth_ids))
    if extra_ids:
        raise DatasetContractError(f"predictions contain unknown sample IDs: {extra_ids}")

    overall = EditAccumulator()
    slices: defaultdict[str, EditAccumulator] = defaultdict(EditAccumulator)
    category_accumulators: defaultdict[str, EditAccumulator] = defaultdict(EditAccumulator)
    per_sample: list[dict[str, Any]] = []
    missing_ids: list[str] = []

    for row in ground_truth:
        sample_id = str(row["sample_id"])
        reference = str(row["text"])
        if sample_id not in predictions:
            missing_ids.append(sample_id)
        prediction = predictions.get(sample_id, "")
        alignment = align_characters(reference, prediction)
        sample_overall = EditAccumulator()
        sample_slices: defaultdict[str, EditAccumulator] = defaultdict(EditAccumulator)
        accumulate_alignment(alignment, sample_overall, sample_slices)
        accumulate_alignment(alignment, overall, slices)
        selection_category = str(row.get("selection_category") or "unspecified")
        category_slices: defaultdict[str, EditAccumulator] = defaultdict(EditAccumulator)
        accumulate_alignment(alignment, category_accumulators[selection_category], category_slices)
        per_sample.append(
            {
                "sample_id": sample_id,
                "selection_category": selection_category,
                **sample_overall.to_dict(),
            }
        )

    worst_samples = sorted(
        per_sample,
        key=lambda row: (float(row["cer"] or 0.0), int(row["errors"]), str(row["sample_id"])),
        reverse=True,
    )[:20]
    return {
        "schema_version": 1,
        "metric": "exact_character_error_rate_v0",
        "gold_evaluation": gold_evaluation,
        "evaluation_split": evaluation_split,
        "manifest_records": len(manifest_rows),
        "records": len(ground_truth),
        "predictions_received": len(predictions),
        "missing_predictions": missing_ids,
        "overall": overall.to_dict(),
        "character_slices": {
            category: slices[category].to_dict()
            for category in ("hebrew", "digits", "punctuation_symbols", "latin", "space", "other")
        },
        "selection_categories": {
            category: accumulator.to_dict()
            for category, accumulator in sorted(category_accumulators.items())
        },
        "worst_samples": worst_samples,
        "training_gold_leakage": leakage,
        "normalization": charset.normalization,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate logical-order Hebrew OCR predictions with exact CER.")
    parser.add_argument("--ground-truth-manifest", type=Path, required=True)
    parser.add_argument("--ground-truth-root", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--charset", type=Path)
    parser.add_argument("--training-manifest", type=Path)
    parser.add_argument("--training-root", type=Path)
    parser.add_argument("--split", choices=("train", "validation", "test"))
    parser.add_argument(
        "--allow-non-gold",
        action="store_true",
        help="Allow synthetic/silver ground truth only for pipeline smoke tests; never call the result real OCR quality.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = evaluate_predictions(
        args.ground_truth_manifest,
        args.ground_truth_root,
        args.predictions,
        charset_path=args.charset,
        allow_non_gold=args.allow_non_gold,
        training_manifest=args.training_manifest,
        training_root=args.training_root,
        evaluation_split=args.split,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            raise DatasetContractError(f"output already exists: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
