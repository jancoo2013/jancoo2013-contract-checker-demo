from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from research.handwriting_gate.gate_baseline import (
    aggregate_pages,
    build_feature_matrix,
    choose_threshold,
    load_tile_manifest,
    page_metrics,
    score_matrix,
)


def train_logistic(
    features: np.ndarray,
    targets: np.ndarray,
    epochs: int = 400,
    learning_rate: float = 0.08,
    l2: float = 1e-4,
) -> tuple[np.ndarray, float]:
    if len(np.unique(targets)) < 2:
        raise ValueError("training split must contain both classes")
    weights = np.zeros(features.shape[1], dtype=np.float32)
    bias = 0.0
    positives = max(float(np.sum(targets == 1.0)), 1.0)
    negatives = max(float(np.sum(targets == 0.0)), 1.0)
    sample_weights = np.where(targets == 1.0, len(targets) / (2.0 * positives), len(targets) / (2.0 * negatives))

    for _ in range(epochs):
        scores = score_matrix(features, weights, bias)
        error = (scores - targets) * sample_weights
        grad_w = (features.T @ error) / len(features) + l2 * weights
        grad_b = float(np.mean(error))
        weights -= learning_rate * grad_w.astype(np.float32)
        bias -= learning_rate * grad_b
    return weights, bias


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a lightweight research baseline for hand-mark detection.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model-out", type=Path, required=True)
    parser.add_argument("--report-out", type=Path, required=True)
    parser.add_argument("--image-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--min-recall", type=float, default=0.99)
    args = parser.parse_args()

    rows = load_tile_manifest(args.manifest)
    train_rows = [row for row in rows if row.split == "train"]
    val_rows = [row for row in rows if row.split == "val"]
    if not train_rows or not val_rows:
        raise SystemExit("train and val splits must both be non-empty")

    x_train, y_train = build_feature_matrix(train_rows, image_size=args.image_size)
    mean = x_train.mean(axis=0)
    std = x_train.std(axis=0)
    std[std < 1e-6] = 1.0
    x_train = (x_train - mean) / std

    weights, bias = train_logistic(
        x_train,
        y_train,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
    )

    x_val, _ = build_feature_matrix(val_rows, image_size=args.image_size)
    x_val = (x_val - mean) / std
    val_scores = score_matrix(x_val, weights, bias)
    pages = aggregate_pages(val_rows, val_scores)
    page_targets = [target for target, _ in pages.values()]
    page_scores = [score for _, score in pages.values()]
    threshold, threshold_metrics = choose_threshold(page_targets, page_scores, min_recall=args.min_recall)

    args.model_out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.model_out,
        weights=weights,
        bias=np.asarray([bias], dtype=np.float32),
        mean=mean.astype(np.float32),
        std=std.astype(np.float32),
        image_size=np.asarray([args.image_size], dtype=np.int32),
        threshold=np.asarray([threshold], dtype=np.float32),
    )

    report = {
        "model": "linear_pixel_edge_baseline",
        "purpose": "research_only_not_production_gate",
        "train_tiles": len(train_rows),
        "validation_tiles": len(val_rows),
        "validation_pages": len(pages),
        "threshold": threshold,
        "threshold_selection": {"min_page_recall": args.min_recall},
        "validation_page_metrics": page_metrics(val_rows, val_scores, threshold),
        "threshold_metrics": threshold_metrics,
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
