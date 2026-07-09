from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from research.handwriting_gate.gate_baseline import extract_features, sigmoid
from research.handwriting_gate.prepare_region_bags import NEGATIVE_BAG, POSITIVE_BAG


@dataclass(frozen=True)
class InstanceRow:
    path: Path
    page_id: str
    bag_id: str
    bag_label: str


@dataclass
class Bag:
    bag_id: str
    page_id: str
    target: int
    features: np.ndarray


@dataclass(frozen=True)
class MilModel:
    weights: np.ndarray
    bias: float
    mean: np.ndarray
    std: np.ndarray
    temperature: float


def load_region_manifest(path: Path) -> list[InstanceRow]:
    base = path.parent
    rows: list[InstanceRow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"path", "page_id", "bag_id", "bag_label"}
        if not required.issubset(reader.fieldnames or []):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"manifest is missing columns: {', '.join(missing)}")
        for line_no, raw in enumerate(reader, start=2):
            label = (raw["bag_label"] or "").strip()
            if label not in {POSITIVE_BAG, NEGATIVE_BAG}:
                raise ValueError(f"line {line_no}: unsupported bag_label {label!r}")
            page_id = (raw["page_id"] or "").strip()
            bag_id = (raw["bag_id"] or "").strip()
            rel_path = (raw["path"] or "").strip()
            if not page_id or not bag_id or not rel_path:
                raise ValueError(f"line {line_no}: path, page_id, and bag_id are required")
            rows.append(
                InstanceRow(
                    path=(base / rel_path).resolve(),
                    page_id=page_id,
                    bag_id=bag_id,
                    bag_label=label,
                )
            )
    if not rows:
        raise ValueError("manifest contains no rows")
    return rows


def build_bags(rows: Iterable[InstanceRow], image_size: int) -> list[Bag]:
    grouped: dict[str, list[InstanceRow]] = {}
    for row in rows:
        grouped.setdefault(row.bag_id, []).append(row)

    bags: list[Bag] = []
    for bag_id, members in sorted(grouped.items()):
        labels = {member.bag_label for member in members}
        pages = {member.page_id for member in members}
        if len(labels) != 1 or len(pages) != 1:
            raise ValueError(f"bag {bag_id!r} mixes labels or pages")
        label = next(iter(labels))
        target = 1 if label == POSITIVE_BAG else 0
        features = np.vstack([extract_features(member.path, image_size=image_size) for member in members])
        bags.append(Bag(bag_id=bag_id, page_id=next(iter(pages)), target=target, features=features))
    return bags


def _standardize_bags(bags: list[Bag]) -> tuple[list[Bag], np.ndarray, np.ndarray]:
    all_features = np.vstack([bag.features for bag in bags])
    mean = all_features.mean(axis=0)
    std = all_features.std(axis=0)
    std[std < 1e-6] = 1.0
    standardized = [
        Bag(
            bag_id=bag.bag_id,
            page_id=bag.page_id,
            target=bag.target,
            features=(bag.features - mean) / std,
        )
        for bag in bags
    ]
    return standardized, mean.astype(np.float32), std.astype(np.float32)


def _smooth_max_logit_and_feature_gradient(
    features: np.ndarray,
    weights: np.ndarray,
    bias: float,
    temperature: float,
) -> tuple[float, np.ndarray]:
    logits = features @ weights + bias
    scaled = logits / temperature
    maximum = float(np.max(scaled))
    exp_values = np.exp(scaled - maximum)
    softmax_weights = exp_values / exp_values.sum()
    bag_logit = temperature * (
        maximum + float(np.log(exp_values.sum())) - float(np.log(len(logits)))
    )
    feature_gradient = (softmax_weights[:, None] * features).sum(axis=0)
    return float(bag_logit), feature_gradient


def train_mil(
    bags: list[Bag],
    epochs: int,
    learning_rate: float,
    l2: float,
    temperature: float,
) -> MilModel:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    if not bags:
        raise ValueError("no bags supplied")
    targets = {bag.target for bag in bags}
    if targets != {0, 1}:
        raise ValueError("training bags must contain both classes")

    standardized, mean, std = _standardize_bags(bags)
    dimension = standardized[0].features.shape[1]
    weights = np.zeros(dimension, dtype=np.float32)
    bias = 0.0

    positive_count = sum(bag.target == 1 for bag in standardized)
    negative_count = len(standardized) - positive_count

    for _ in range(epochs):
        grad_weights = np.zeros_like(weights)
        grad_bias = 0.0

        for bag in standardized:
            bag_logit, feature_gradient = _smooth_max_logit_and_feature_gradient(
                bag.features,
                weights,
                bias,
                temperature,
            )
            probability = float(sigmoid(np.asarray(bag_logit)))
            class_count = positive_count if bag.target == 1 else negative_count
            class_weight = len(standardized) / (2.0 * class_count)
            error = (probability - bag.target) * class_weight
            grad_weights += error * feature_gradient
            grad_bias += error

        grad_weights = grad_weights / len(standardized) + l2 * weights
        grad_bias /= len(standardized)
        weights -= learning_rate * grad_weights.astype(np.float32)
        bias -= learning_rate * grad_bias

    return MilModel(
        weights=weights,
        bias=bias,
        mean=mean,
        std=std,
        temperature=temperature,
    )


def score_bag(bag: Bag, model: MilModel) -> float:
    features = (bag.features - model.mean) / model.std
    bag_logit, _ = _smooth_max_logit_and_feature_gradient(
        features,
        model.weights,
        model.bias,
        model.temperature,
    )
    return float(sigmoid(np.asarray(bag_logit)))


def binary_metrics(targets: list[int], scores: list[float], threshold: float) -> dict[str, float | int]:
    if len(targets) != len(scores):
        raise ValueError("targets and scores length mismatch")
    tp = tn = fp = fn = 0
    for target, score in zip(targets, scores, strict=True):
        prediction = int(score >= threshold)
        if target == 1 and prediction == 1:
            tp += 1
        elif target == 0 and prediction == 0:
            tn += 1
        elif target == 0 and prediction == 1:
            fp += 1
        else:
            fn += 1
    positives = tp + fn
    negatives = tn + fp
    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "recall": tp / positives if positives else 0.0,
        "false_negative_rate": fn / positives if positives else 0.0,
        "false_positive_rate": fp / negatives if negatives else 0.0,
    }


def choose_threshold(
    targets: list[int],
    scores: list[float],
    min_recall: float,
) -> tuple[float, dict[str, float | int]]:
    if not 0.0 < min_recall <= 1.0:
        raise ValueError("min_recall must be in (0, 1]")
    candidates = sorted({0.0, 1.0, *[float(score) for score in scores]})
    feasible: list[tuple[float, float, float, dict[str, float | int]]] = []
    fallback: list[tuple[float, float, float, dict[str, float | int]]] = []
    for threshold in candidates:
        metrics = binary_metrics(targets, scores, threshold)
        record = (
            float(metrics["false_positive_rate"]),
            -float(metrics["recall"]),
            -threshold,
            metrics,
        )
        fallback.append(record)
        if float(metrics["recall"]) >= min_recall:
            feasible.append(record)
    selected = min(feasible or fallback)
    threshold = -selected[2]
    return threshold, selected[3]


def run_lopo(
    bags: list[Bag],
    epochs: int,
    learning_rate: float,
    l2: float,
    temperature: float,
    min_recall: float,
) -> dict[str, object]:
    pages = sorted({bag.page_id for bag in bags})
    if len(pages) < 3:
        raise ValueError("leave-one-page-out evaluation needs at least 3 pages")

    fold_reports: list[dict[str, object]] = []
    all_targets: list[int] = []
    all_scores: list[float] = []
    all_thresholds: list[float] = []
    page_hits = 0

    for held_out_page in pages:
        train_bags = [bag for bag in bags if bag.page_id != held_out_page]
        test_bags = [bag for bag in bags if bag.page_id == held_out_page]
        model = train_mil(
            train_bags,
            epochs=epochs,
            learning_rate=learning_rate,
            l2=l2,
            temperature=temperature,
        )

        train_targets = [bag.target for bag in train_bags]
        train_scores = [score_bag(bag, model) for bag in train_bags]
        threshold, train_threshold_metrics = choose_threshold(
            train_targets,
            train_scores,
            min_recall=min_recall,
        )

        test_targets = [bag.target for bag in test_bags]
        test_scores = [score_bag(bag, model) for bag in test_bags]
        fold_metrics = binary_metrics(test_targets, test_scores, threshold)

        positive_scores = [score for target, score in zip(test_targets, test_scores, strict=True) if target == 1]
        page_score = max(positive_scores, default=0.0)
        page_detected = page_score >= threshold
        page_hits += int(page_detected)

        positive_errors = [
            {"bag_id": bag.bag_id, "score": score}
            for bag, score in zip(test_bags, test_scores, strict=True)
            if bag.target == 1 and score < threshold
        ]
        negative_errors = [
            {"bag_id": bag.bag_id, "score": score}
            for bag, score in zip(test_bags, test_scores, strict=True)
            if bag.target == 0 and score >= threshold
        ]
        positive_errors.sort(key=lambda item: float(item["score"]))
        negative_errors.sort(key=lambda item: -float(item["score"]))

        fold_reports.append(
            {
                "held_out_page": held_out_page,
                "threshold": threshold,
                "threshold_selection_train_metrics": train_threshold_metrics,
                "test_bag_metrics": fold_metrics,
                "page_score": page_score,
                "page_detected": page_detected,
                "positive_region_bags": sum(target == 1 for target in test_targets),
                "negative_singleton_bags": sum(target == 0 for target in test_targets),
                "false_negative_regions": positive_errors,
                "false_positive_negative_tiles": negative_errors,
            }
        )

        all_targets.extend(test_targets)
        all_scores.extend(test_scores)
        all_thresholds.extend([threshold] * len(test_targets))

    aggregate_tp = aggregate_tn = aggregate_fp = aggregate_fn = 0
    for target, score, threshold in zip(all_targets, all_scores, all_thresholds, strict=True):
        prediction = int(score >= threshold)
        if target == 1 and prediction == 1:
            aggregate_tp += 1
        elif target == 0 and prediction == 0:
            aggregate_tn += 1
        elif target == 0 and prediction == 1:
            aggregate_fp += 1
        else:
            aggregate_fn += 1

    region_total = aggregate_tp + aggregate_fn
    negative_total = aggregate_tn + aggregate_fp
    aggregate = {
        "positive_region_bags": region_total,
        "negative_singleton_bags": negative_total,
        "tp": aggregate_tp,
        "tn": aggregate_tn,
        "fp": aggregate_fp,
        "fn": aggregate_fn,
        "region_recall": aggregate_tp / region_total if region_total else 0.0,
        "region_false_negative_rate": aggregate_fn / region_total if region_total else 0.0,
        "negative_tile_false_positive_rate": aggregate_fp / negative_total if negative_total else 0.0,
        "positive_page_recall": page_hits / len(pages),
        "positive_pages_detected": page_hits,
        "positive_pages_total": len(pages),
    }

    return {
        "evaluation": "leave_one_page_out",
        "important_limitations": [
            "All available pages are positive filled pages; page-level false-positive rate cannot be estimated from this dataset.",
            "Region bags are weak labels derived from redaction differences and may contain label noise.",
            "Threshold selection uses training-fold bag scores; final acceptance thresholds require an independent validation set.",
        ],
        "aggregate": aggregate,
        "folds": fold_reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a linear MIL leave-one-page-out handwriting experiment.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    parser.add_argument("--image-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=300)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--l2", type=float, default=1e-4)
    parser.add_argument("--temperature", type=float, default=0.25)
    parser.add_argument("--min-recall", type=float, default=0.95)
    args = parser.parse_args()

    rows = load_region_manifest(args.manifest)
    bags = build_bags(rows, image_size=args.image_size)
    report = run_lopo(
        bags=bags,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        temperature=args.temperature,
        min_recall=args.min_recall,
    )
    report["parameters"] = {
        "image_size": args.image_size,
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "l2": args.l2,
        "temperature": args.temperature,
        "min_recall": args.min_recall,
    }

    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
